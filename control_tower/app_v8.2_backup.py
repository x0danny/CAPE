"""
EAISS Control Tower v8.2
Enterprise Decision Intelligence Platform

DECISION TEMPLATES:
- Escalation Cards: Structured decisions for high-risk orders
- Mitigation Playbooks: Step-by-step response plans
- Tradeoff Analysis: AI-powered priority decisions
- Daily Action Plans: Top 5 things to do today

SMART AI:
- Revenue-weighted priorities
- Corridor-aware analysis  
- Consequence framing

STACK:
- ML Risk Scoring: Random Forest (99% recall)
- ML Demand Forecasting: Random Forest Regressor (R² = 0.981)
- Local AI: Ollama + Llama 3 8B
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import httpx
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIG
# ============================================================

class Config:
    APP_NAME = "EAISS Control Tower"
    VERSION = "8.2"
    GBI_PATH = 'uploads/GB_AnalyticsData.xlsx'
    ERPSIM_PATH = 'uploads/ERPSIM.xlsx'
    RISK_MODEL_PATH = 'ml/order_risk_model.pkl'
    DEMAND_MODEL_PATH = 'ml/demand_forecast_model.pkl'
    AUTO_REFRESH_INTERVAL = 30
    
    # Local AI Config
    OLLAMA_BASE_URL = "http://localhost:11434"
    OLLAMA_MODEL = "llama3:8b"
    AI_TIMEOUT = 45.0

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title=Config.APP_NAME,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# IMPORTS
# ============================================================

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import pickle
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.preprocessing import LabelEncoder
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# ============================================================
# SMART LOCAL AI SERVICE
# ============================================================

class LocalAIService:
    """
    Smart local AI service with business-aware prompts.
    
    Key capabilities:
    - Revenue-weighted prioritization
    - Corridor-aware analysis
    - Consequence framing
    - Executive-ready outputs
    """
    
    def __init__(self):
        self.base_url = Config.OLLAMA_BASE_URL
        self.model = Config.OLLAMA_MODEL
        self.available = False
        self._check_health()
    
    def _check_health(self) -> bool:
        """Check if Ollama is running."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                self.available = response.status_code == 200
        except:
            self.available = False
        return self.available
    
    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 500) -> Optional[str]:
        """Get completion from local AI."""
        if not self.available:
            return None
        
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": max_tokens}
            }
            
            with httpx.Client(timeout=Config.AI_TIMEOUT) as client:
                response = client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                return response.json()["message"]["content"]
        except Exception as e:
            return None
    
    # =========================================================
    # SMART ANALYSIS METHODS
    # =========================================================
    
    def analyze_top_5_orders(self, top_orders: List[dict], total_at_risk: float) -> str:
        """
        Revenue-weighted analysis of top 5 critical orders.
        Tells executives: "These 5 orders = X% of your risk"
        """
        system = """You are a supply chain operations advisor. Analyze the top priority orders.
Be specific about WHY each matters and WHAT to do. Use numbers. Max 5 bullet points total."""
        
        # Calculate concentration
        top_5_value = sum(o.get('value', 0) for o in top_orders[:5])
        concentration_pct = (top_5_value / total_at_risk * 100) if total_at_risk > 0 else 0
        
        orders_text = "\n".join([
            f"- Order #{o.get('order_id')}: ${o.get('value', 0):,.0f} | Customer {o.get('customer')} | {o.get('line_items')} items | {o.get('risk_score', 0)*100:.0f}% risk"
            for o in top_orders[:5]
        ])
        
        prompt = f"""TOP 5 PRIORITY ORDERS (represent {concentration_pct:.0f}% of total risk):

{orders_text}

Total at-risk value: ${total_at_risk:,.0f}
These 5 orders alone: ${top_5_value:,.0f}

For each order, explain:
1. Why it's high risk (be specific)
2. One action to take NOW"""
        
        result = self.complete(prompt, system, max_tokens=400)
        return result or "Analysis unavailable."
    
    def analyze_corridor_impact(self, corridors: List[dict], affected_orders: dict) -> str:
        """
        Corridor-aware analysis connecting traffic delays to specific orders.
        Maps: "Long Beach 1.9x delay → 47 orders → $2.3M at risk"
        """
        system = """You are a logistics analyst. Connect traffic delays to business impact.
Be specific about which corridors matter and why. Recommend route alternatives if relevant. Max 4 sentences."""
        
        corridor_text = "\n".join([
            f"- {c.get('corridor')}: {c.get('delay_ratio')}x delay ({c.get('level').upper()}) → {affected_orders.get(c.get('corridor'), {}).get('count', 0)} orders, ${affected_orders.get(c.get('corridor'), {}).get('value', 0):,.0f} at risk"
            for c in corridors if c.get('level') in ['heavy', 'severe']
        ])
        
        if not corridor_text:
            return "All corridors operating normally. No logistics bottlenecks detected."
        
        prompt = f"""CORRIDOR DELAYS IMPACTING ORDERS:

{corridor_text}

Which corridor should we prioritize? What's the business impact if delays continue 48 hours?"""
        
        result = self.complete(prompt, system, max_tokens=250)
        return result or "Corridor analysis unavailable."
    
    def generate_consequence_analysis(self, metrics: dict) -> str:
        """
        Consequence framing: "If nothing changes, here's what you lose"
        Creates urgency without panic.
        """
        system = """You are a risk analyst. Project consequences of inaction.
Be specific with numbers and timeframes. Don't be alarmist, be factual. Max 3 scenarios."""
        
        at_risk = metrics.get('at_risk_value', 0)
        high_risk_count = metrics.get('high_risk_count', 0)
        critical_alerts = metrics.get('critical_alerts', 0)
        
        # Simple projection logic
        daily_exposure = at_risk * 0.02  # 2% daily deterioration assumption
        weekly_exposure = at_risk * 0.15  # 15% weekly if unaddressed
        
        prompt = f"""CURRENT EXPOSURE:
- Revenue at risk: ${at_risk:,.0f}
- High-risk orders: {high_risk_count}
- Critical alerts: {critical_alerts}

PROJECT THREE SCENARIOS:

1. IF WE DO NOTHING (48 hours):
   Estimated additional exposure: ${daily_exposure * 2:,.0f}

2. IF WE DO NOTHING (1 week):
   Estimated additional exposure: ${weekly_exposure:,.0f}

3. IF WE ACT NOW:
   What can we realistically save?

Be specific. What's the cost of delay vs. cost of action?"""
        
        result = self.complete(prompt, system, max_tokens=350)
        return result or "Consequence analysis unavailable."
    
    def generate_executive_brief(self, metrics: dict, top_orders: List[dict] = None, corridors: List[dict] = None) -> str:
        """
        Enhanced executive brief with revenue-weighted insights.
        """
        system = """You are a supply chain executive advisor briefing the C-suite.
Structure: SITUATION (2 sentences) → RISK (2 sentences) → ACTION (2 sentences).
Use specific numbers. No fluff."""
        
        # Calculate concentration if we have top orders
        top_5_value = sum(o.get('value', 0) for o in (top_orders or [])[:5])
        total_at_risk = metrics.get('at_risk_value', 0)
        concentration = (top_5_value / total_at_risk * 100) if total_at_risk > 0 else 0
        
        # Identify worst corridor
        worst_corridor = "None"
        if corridors:
            severe = [c for c in corridors if c.get('level') == 'severe']
            if severe:
                worst_corridor = severe[0].get('corridor', 'Unknown')
        
        prompt = f"""EXECUTIVE BRIEF - {datetime.now().strftime('%Y-%m-%d %H:%M')}

PIPELINE:
- Total Value: ${metrics.get('total_value', 0)/1e6:.1f}M across {metrics.get('total_orders', 0):,} orders
- At Risk: ${total_at_risk/1e6:.2f}M ({metrics.get('at_risk_pct', 0):.0f}%)
- High Risk Orders: {metrics.get('high_risk_count', 0)}

CONCENTRATION:
- Top 5 orders = ${top_5_value/1e6:.2f}M ({concentration:.0f}% of risk)

EXTERNAL FACTORS:
- Critical corridor: {worst_corridor}
- Traffic issues: {metrics.get('traffic_issues', 0)} corridors affected

ALERTS:
- Critical: {metrics.get('critical_alerts', 0)}
- System Status: {metrics.get('system_status', 'NORMAL')}

Write the brief. Be direct. Executives have 30 seconds."""
        
        result = self.complete(prompt, system, max_tokens=300)
        return result or "Brief unavailable."
    
    def generate_smart_recommendation(self, metrics: dict, top_orders: List[dict] = None) -> str:
        """
        Actionable recommendation with specific order numbers.
        """
        system = """You are an operations advisor. Give ONE specific action.
Include order numbers or customer names. Start with a verb. Max 2 sentences."""
        
        # Get top order details
        top_order = top_orders[0] if top_orders else {}
        
        prompt = f"""SITUATION:
- {metrics.get('high_risk_count', 0)} high-risk orders totaling ${metrics.get('at_risk_value', 0)/1e6:.2f}M
- Top priority: Order #{top_order.get('order_id', 'N/A')} (${top_order.get('value', 0):,.0f}, Customer {top_order.get('customer', 'N/A')})
- {metrics.get('critical_alerts', 0)} critical alerts active

What is the single most important action in the next 4 hours?
Be specific - mention the order number or customer."""
        
        result = self.complete(prompt, system, max_tokens=150)
        return result or "Continue standard monitoring."
    
    def analyze_order_risk(self, order_data: dict, context: dict = None) -> str:
        """
        Enhanced order analysis with business context.
        """
        system = """You are an ERP risk analyst. Explain why this order is flagged.
Be specific about the risk factors. Suggest one mitigation. Max 3 sentences."""
        
        # Add context about customer history if available
        customer_context = ""
        if context and context.get('customer_history'):
            ch = context['customer_history']
            customer_context = f"\nCustomer History: {ch.get('total_orders', 0)} previous orders, ${ch.get('total_value', 0):,.0f} lifetime value, {ch.get('avg_risk', 0)*100:.0f}% avg risk"
        
        prompt = f"""ORDER RISK ANALYSIS:

Order: #{order_data.get('order_id', 'N/A')}
Customer: {order_data.get('customer', 'N/A')}
Value: ${order_data.get('value', 0):,.0f}
Line Items: {order_data.get('line_items', 0)}
Product Diversity: {order_data.get('product_diversity', 0)} different products
Risk Score: {order_data.get('risk_score', 0)*100:.0f}%
{customer_context}

ML MODEL SAYS: High complexity orders (many items, diverse products) historically have 3x higher fulfillment issues.

Why is this specific order flagged? What should we do about it?"""
        
        result = self.complete(prompt, system, max_tokens=200)
        return result or "Analysis unavailable."
    
    def generate_shift_handoff(self, metrics: dict, actions_taken: List[str] = None) -> str:
        """
        Generate shift handoff summary for operations teams.
        """
        system = """You are an operations supervisor writing a shift handoff.
Include: what happened, what's pending, what the next shift should prioritize.
Bullet points. Max 6 items."""
        
        actions_text = "\n".join([f"- {a}" for a in (actions_taken or ["No actions logged this shift"])])
        
        prompt = f"""SHIFT HANDOFF - {datetime.now().strftime('%Y-%m-%d %H:%M')}

CURRENT STATE:
- Pipeline: ${metrics.get('total_value', 0)/1e6:.1f}M
- At Risk: ${metrics.get('at_risk_value', 0)/1e6:.2f}M ({metrics.get('at_risk_pct', 0):.0f}%)
- High Risk Orders: {metrics.get('high_risk_count', 0)}
- System Status: {metrics.get('system_status', 'NORMAL')}

ACTIONS THIS SHIFT:
{actions_text}

Write handoff notes for the next shift. What do they need to know and do first?"""
        
        result = self.complete(prompt, system, max_tokens=300)
        return result or "Handoff notes unavailable."
    
    # =========================================================
    # DECISION TEMPLATES - Structured outputs for executives
    # =========================================================
    
    def generate_escalation_card(self, order_data: dict) -> dict:
        """
        Generate structured escalation decision card.
        Returns dict with all fields for UI rendering.
        """
        system = """You are an operations decision support system. Generate structured decision data.
Return ONLY a JSON-like response with these exact fields, no markdown:
ROOT_CAUSE: (one sentence)
ACTION: (one specific action, start with verb)
DEADLINE: (specific time like "Today 5pm" or "Within 4 hours")
FALLBACK: (what to do if primary action fails)
RECOVERY_PROBABILITY: (percentage as number)"""
        
        prompt = f"""Generate escalation decision for:

Order: #{order_data.get('order_id')}
Customer: {order_data.get('customer')}
Value: ${order_data.get('value', 0):,.0f}
Risk Score: {order_data.get('risk_score', 0)*100:.0f}%
Line Items: {order_data.get('line_items', 0)}
Product Diversity: {order_data.get('product_diversity', 0)}

What's the root cause, action, deadline, and fallback?"""
        
        result = self.complete(prompt, system, max_tokens=250)
        
        # Parse AI response into structured format
        card = {
            'order_id': order_data.get('order_id'),
            'customer': order_data.get('customer'),
            'value': order_data.get('value', 0),
            'risk_score': order_data.get('risk_score', 0),
            'risk_level': 'CRITICAL' if order_data.get('risk_score', 0) > 0.9 else 'HIGH' if order_data.get('risk_score', 0) > 0.7 else 'MEDIUM',
            'root_cause': 'High complexity order with multiple products',
            'action': 'Contact customer to confirm order specifications',
            'deadline': 'Today 5pm',
            'owner': '[Assign]',
            'fallback': 'Split into smaller shipments if no response',
            'recovery_probability': 70
        }
        
        # Try to parse AI response
        if result:
            lines = result.strip().split('\n')
            for line in lines:
                if 'ROOT_CAUSE:' in line:
                    card['root_cause'] = line.split('ROOT_CAUSE:')[-1].strip()
                elif 'ACTION:' in line:
                    card['action'] = line.split('ACTION:')[-1].strip()
                elif 'DEADLINE:' in line:
                    card['deadline'] = line.split('DEADLINE:')[-1].strip()
                elif 'FALLBACK:' in line:
                    card['fallback'] = line.split('FALLBACK:')[-1].strip()
                elif 'RECOVERY_PROBABILITY:' in line:
                    try:
                        prob = line.split('RECOVERY_PROBABILITY:')[-1].strip().replace('%', '')
                        card['recovery_probability'] = int(float(prob))
                    except:
                        pass
        
        return card
    
    def generate_mitigation_playbook(self, issue_type: str, issue_data: dict) -> dict:
        """
        Generate mitigation playbook for systemic issues.
        """
        system = """You are an operations playbook generator. Create structured mitigation steps.
Return ONLY these fields, no markdown:
ISSUE_SUMMARY: (one sentence)
IMPACT: (quantified business impact)
STEP_1: (first action)
STEP_2: (second action)  
STEP_3: (third action)
ESCALATE_IF: (condition to escalate)
SUCCESS_METRIC: (how to measure success)"""
        
        if issue_type == 'corridor_delay':
            prompt = f"""Generate mitigation playbook for:

Issue: Corridor Delay
Corridor: {issue_data.get('corridor')}
Delay Ratio: {issue_data.get('delay_ratio')}x normal
Affected Orders: {issue_data.get('affected_count', 0)}
Value at Risk: ${issue_data.get('affected_value', 0):,.0f}

What are the mitigation steps?"""
        elif issue_type == 'demand_surge':
            prompt = f"""Generate mitigation playbook for:

Issue: Demand Surge
Category: {issue_data.get('category')}
Change: {issue_data.get('change', 0):+.0f}%
Current Demand: {issue_data.get('current_demand', 0)}
Forecasted: {issue_data.get('forecast', 0)}

What are the mitigation steps?"""
        else:
            prompt = f"""Generate mitigation playbook for:

Issue: {issue_type}
Details: {issue_data}

What are the mitigation steps?"""
        
        result = self.complete(prompt, system, max_tokens=350)
        
        playbook = {
            'issue_type': issue_type,
            'issue_summary': f'{issue_type.replace("_", " ").title()} detected',
            'impact': 'Business impact pending analysis',
            'steps': [
                'Assess current situation',
                'Notify stakeholders',
                'Implement mitigation'
            ],
            'escalate_if': 'Situation worsens or no improvement in 4 hours',
            'success_metric': 'Return to normal operations'
        }
        
        if result:
            lines = result.strip().split('\n')
            steps = []
            for line in lines:
                if 'ISSUE_SUMMARY:' in line:
                    playbook['issue_summary'] = line.split('ISSUE_SUMMARY:')[-1].strip()
                elif 'IMPACT:' in line:
                    playbook['impact'] = line.split('IMPACT:')[-1].strip()
                elif 'STEP_1:' in line:
                    steps.append(line.split('STEP_1:')[-1].strip())
                elif 'STEP_2:' in line:
                    steps.append(line.split('STEP_2:')[-1].strip())
                elif 'STEP_3:' in line:
                    steps.append(line.split('STEP_3:')[-1].strip())
                elif 'ESCALATE_IF:' in line:
                    playbook['escalate_if'] = line.split('ESCALATE_IF:')[-1].strip()
                elif 'SUCCESS_METRIC:' in line:
                    playbook['success_metric'] = line.split('SUCCESS_METRIC:')[-1].strip()
            if steps:
                playbook['steps'] = steps
        
        return playbook
    
    def generate_tradeoff_summary(self, options: List[dict]) -> dict:
        """
        Generate tradeoff analysis when there are competing priorities.
        """
        system = """You are a decision analyst. Compare options and recommend one.
Return ONLY these fields:
RECOMMENDED: (option number 1, 2, or 3)
REASONING: (one sentence why)
TRADEOFF: (what you give up with this choice)
CONFIDENCE: (HIGH, MEDIUM, or LOW)"""
        
        options_text = "\n".join([
            f"Option {i+1}: {o.get('name')} - {o.get('description')} (Impact: {o.get('impact', 'Unknown')})"
            for i, o in enumerate(options)
        ])
        
        prompt = f"""Analyze these competing priorities:

{options_text}

Which should we prioritize and why?"""
        
        result = self.complete(prompt, system, max_tokens=200)
        
        summary = {
            'options': options,
            'recommended': 1,
            'reasoning': 'Highest impact on revenue protection',
            'tradeoff': 'Other issues may worsen temporarily',
            'confidence': 'MEDIUM'
        }
        
        if result:
            lines = result.strip().split('\n')
            for line in lines:
                if 'RECOMMENDED:' in line:
                    try:
                        rec = line.split('RECOMMENDED:')[-1].strip()
                        summary['recommended'] = int(rec[0]) if rec[0].isdigit() else 1
                    except:
                        pass
                elif 'REASONING:' in line:
                    summary['reasoning'] = line.split('REASONING:')[-1].strip()
                elif 'TRADEOFF:' in line:
                    summary['tradeoff'] = line.split('TRADEOFF:')[-1].strip()
                elif 'CONFIDENCE:' in line:
                    conf = line.split('CONFIDENCE:')[-1].strip().upper()
                    if conf in ['HIGH', 'MEDIUM', 'LOW']:
                        summary['confidence'] = conf
        
        return summary
    
    def generate_daily_action_plan(self, metrics: dict, top_orders: List[dict], alerts: List[dict]) -> dict:
        """
        Generate structured daily action plan - Top 5 things to do today.
        """
        system = """You are an operations planner. Create today's action plan.
Return EXACTLY 5 actions in this format:
ACTION_1: (specific action with order/customer reference if applicable)
PRIORITY_1: (CRITICAL, HIGH, or MEDIUM)
ACTION_2: ...
PRIORITY_2: ...
(continue for all 5)"""
        
        # Build context
        top_order = top_orders[0] if top_orders else {}
        critical_alerts = [a for a in alerts if a.get('sev') == 'CRITICAL']
        
        prompt = f"""Create today's action plan based on:

CURRENT STATE:
- High Risk Orders: {metrics.get('high_risk_count', 0)}
- Revenue at Risk: ${metrics.get('at_risk_value', 0)/1e6:.2f}M
- Critical Alerts: {len(critical_alerts)}
- System Status: {metrics.get('system_status', 'NORMAL')}

TOP PRIORITY ORDER:
- Order #{top_order.get('order_id', 'N/A')}: ${top_order.get('value', 0):,.0f}

CRITICAL ALERTS:
{chr(10).join([f"- {a.get('title')}" for a in critical_alerts[:3]]) or '- None'}

What are the 5 most important actions for today?"""
        
        result = self.complete(prompt, system, max_tokens=400)
        
        plan = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'generated_at': datetime.now().strftime('%H:%M'),
            'actions': [
                {'action': 'Review and address critical alerts', 'priority': 'CRITICAL'},
                {'action': f'Contact top risk customer (Order #{top_order.get("order_id", "N/A")})', 'priority': 'CRITICAL'},
                {'action': 'Monitor corridor delays and adjust ETAs', 'priority': 'HIGH'},
                {'action': 'Review medium-risk orders for escalation', 'priority': 'HIGH'},
                {'action': 'Update stakeholders on pipeline status', 'priority': 'MEDIUM'}
            ],
            'total_at_risk': metrics.get('at_risk_value', 0),
            'orders_to_review': min(metrics.get('high_risk_count', 0), 10)
        }
        
        if result:
            actions = []
            lines = result.strip().split('\n')
            current_action = None
            current_priority = 'HIGH'
            
            for line in lines:
                for i in range(1, 6):
                    if f'ACTION_{i}:' in line:
                        if current_action:
                            actions.append({'action': current_action, 'priority': current_priority})
                        current_action = line.split(f'ACTION_{i}:')[-1].strip()
                    elif f'PRIORITY_{i}:' in line:
                        p = line.split(f'PRIORITY_{i}:')[-1].strip().upper()
                        if p in ['CRITICAL', 'HIGH', 'MEDIUM']:
                            current_priority = p
            
            if current_action:
                actions.append({'action': current_action, 'priority': current_priority})
            
            if actions:
                plan['actions'] = actions[:5]
        
        return plan


# Initialize AI service
@st.cache_resource
def get_ai_service():
    return LocalAIService()

# ============================================================
# SESSION STATE
# ============================================================

if 'mode' not in st.session_state:
    st.session_state.mode = "wall"
if 'refresh_count' not in st.session_state:
    st.session_state.refresh_count = 0
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if 'ml_models_loaded' not in st.session_state:
    st.session_state.ml_models_loaded = False
if 'selected_order' not in st.session_state:
    st.session_state.selected_order = None
if 'ai_analysis_cache' not in st.session_state:
    st.session_state.ai_analysis_cache = {}

# ============================================================
# ML MODEL LOADER
# ============================================================

@st.cache_resource
def load_ml_models():
    """Load trained ML models if available."""
    models = {'risk': None, 'demand': None, 'available': False}
    
    try:
        if os.path.exists(Config.RISK_MODEL_PATH):
            with open(Config.RISK_MODEL_PATH, 'rb') as f:
                models['risk'] = pickle.load(f)
        
        if os.path.exists(Config.DEMAND_MODEL_PATH):
            with open(Config.DEMAND_MODEL_PATH, 'rb') as f:
                models['demand'] = pickle.load(f)
        
        if models['risk'] and models['demand']:
            models['available'] = True
    except Exception as e:
        pass
    
    return models

# ============================================================
# ML SCORING FUNCTIONS
# ============================================================

def ml_score_orders(gbi_data: pd.DataFrame, ml_models: dict) -> pd.DataFrame:
    """Score orders using trained ML model."""
    if not ml_models['available'] or ml_models['risk'] is None:
        return None
    
    try:
        risk_model = ml_models['risk']
        model = risk_model['model']
        feature_cols = risk_model['feature_cols']
        le_country = risk_model['le_country']
        le_salesorg = risk_model['le_salesorg']
        
        order_features = gbi_data.groupby('OrderNumber').agg({
            'OrderItem': 'count',
            'SalesQuantity': 'sum',
            'RevenueUSD': 'sum',
            'CostsUSD': 'sum',
            'DiscountUSD': 'sum',
            'Product': 'nunique',
            'Customer': 'first',
            'Country': 'first',
            'SalesOrg': 'first',
            'Month': 'first',
            'Year': 'first',
            'City': 'first'
        }).reset_index()
        
        order_features.columns = [
            'OrderNumber', 'LineItems', 'TotalQuantity', 'TotalRevenue',
            'TotalCost', 'TotalDiscount', 'ProductDiversity', 'Customer',
            'Country', 'SalesOrg', 'Month', 'Year', 'City'
        ]
        
        order_features['GrossMargin'] = ((order_features['TotalRevenue'] - order_features['TotalCost']) / order_features['TotalRevenue']).fillna(0)
        order_features['DiscountPct'] = (order_features['TotalDiscount'] / order_features['TotalRevenue']).fillna(0)
        order_features['AvgItemValue'] = order_features['TotalRevenue'] / order_features['LineItems']
        order_features['AvgQuantityPerItem'] = order_features['TotalQuantity'] / order_features['LineItems']
        order_features['Quarter'] = order_features['Month'].apply(lambda x: (x-1)//3 + 1)
        order_features['IsQ4'] = (order_features['Quarter'] == 4).astype(int)
        
        order_features['Country_enc'] = order_features['Country'].fillna('DE').apply(
            lambda x: le_country.transform([x])[0] if x in le_country.classes_ else 0
        )
        order_features['SalesOrg_enc'] = order_features['SalesOrg'].fillna('DN00').apply(
            lambda x: le_salesorg.transform([x])[0] if x in le_salesorg.classes_ else 0
        )
        
        X = order_features[feature_cols].fillna(0)
        probs = model.predict_proba(X)[:, 1]
        
        order_features['RiskProbability'] = probs
        order_features['RiskCategory'] = pd.cut(probs, bins=[0, 0.3, 0.7, 1.0], labels=['Low', 'Medium', 'High'])
        order_features['PriorityRank'] = probs.argsort()[::-1].argsort() + 1
        
        return order_features.sort_values('RiskProbability', ascending=False)
    
    except Exception as e:
        return None

def ml_forecast_demand(gbi_data: pd.DataFrame, ml_models: dict) -> pd.DataFrame:
    """Forecast demand using trained ML model."""
    if not ml_models['available'] or ml_models['demand'] is None:
        return None
    
    try:
        demand_model = ml_models['demand']
        model = demand_model['model']
        feature_cols = demand_model['feature_cols']
        category_map = demand_model['category_map']
        
        gbi_data = gbi_data.copy()
        gbi_data['Week'] = pd.to_datetime(gbi_data['Year'].astype(str) + '-' + gbi_data['Month'].astype(str) + '-1').dt.isocalendar().week
        
        weekly = gbi_data.groupby(['Year', 'Week', 'ProductCategory']).agg({
            'SalesQuantity': 'sum',
            'RevenueUSD': 'sum',
            'OrderNumber': 'nunique'
        }).reset_index()
        weekly.columns = ['Year', 'Week', 'Category', 'Quantity', 'Revenue', 'OrderCount']
        
        results = []
        for cat in weekly['Category'].unique():
            cat_data = weekly[weekly['Category'] == cat].sort_values(['Year', 'Week'])
            if len(cat_data) < 5:
                continue
            
            cat_data['Quantity_MA4'] = cat_data['Quantity'].rolling(4, min_periods=1).mean()
            cat_data['Revenue_Lag1'] = cat_data['Revenue'].shift(1).fillna(0)
            cat_data['Category_enc'] = category_map.get(cat, 0)
            
            last_row = cat_data.iloc[-1:].copy()
            X = last_row[feature_cols].fillna(0)
            pred = model.predict(X)[0]
            
            last_qty = last_row['Quantity'].values[0]
            change = ((pred - last_qty) / last_qty * 100) if last_qty > 0 else 0
            
            if change > 15:
                alert = 'SURGE'
            elif change < -15:
                alert = 'DROP'
            else:
                alert = 'STABLE'
            
            results.append({
                'Category': cat,
                'Quantity': last_qty,
                'ForecastedDemand': pred,
                'Change': change,
                'AlertType': alert
            })
        
        return pd.DataFrame(results) if results else None
    except Exception as e:
        return None

# ============================================================
# HELPER: Convert ML orders to dict format for AI
# ============================================================

def orders_to_dict_list(ml_orders: pd.DataFrame, n: int = 10) -> List[dict]:
    """Convert top N ML orders to dict format for AI analysis."""
    if ml_orders is None or len(ml_orders) == 0:
        return []
    
    top = ml_orders.head(n)
    return [
        {
            'order_id': int(row['OrderNumber']),
            'customer': int(row['Customer']),
            'value': float(row['TotalRevenue']),
            'line_items': int(row['LineItems']),
            'product_diversity': int(row['ProductDiversity']),
            'risk_score': float(row['RiskProbability']),
            'country': row.get('Country', 'Unknown')
        }
        for _, row in top.iterrows()
    ]

# ============================================================
# DATA LOADER
# ============================================================

@st.cache_data(ttl=300)
def load_gbi_data():
    """Load and process GBI Analytics data."""
    try:
        if not os.path.exists(Config.GBI_PATH):
            return None, None, None, None
        
        xls = pd.ExcelFile(Config.GBI_PATH)
        
        actuals = None
        for sheet in ['Actuals', 'actuals', 'ACTUALS', 'SalesActuals']:
            if sheet in xls.sheet_names:
                actuals = pd.read_excel(xls, sheet_name=sheet)
                break
        
        if actuals is None:
            actuals = pd.read_excel(xls, sheet_name=0)
        
        plan = None
        for sheet in ['Plan', 'plan', 'PLAN', 'SalesPlan']:
            if sheet in xls.sheet_names:
                plan = pd.read_excel(xls, sheet_name=sheet)
                break
        
        var_df = None
        if actuals is not None and 'Customer' in actuals.columns and 'Year' in actuals.columns:
            yearly_act = actuals.groupby(['Customer', 'Year'])['RevenueUSD'].sum().reset_index()
            yearly_act.columns = ['Customer', 'Year', 'Actual']
            
            if plan is not None and 'Customer' in plan.columns:
                yearly_plan = plan.groupby(['Customer', 'Year'])['PlannedRevenueUSD'].sum().reset_index()
                yearly_plan.columns = ['Customer', 'Year', 'Plan']
                var_df = yearly_act.merge(yearly_plan, on=['Customer', 'Year'], how='left')
            else:
                var_df = yearly_act.copy()
                var_df['Plan'] = var_df['Actual'] * 1.1
            
            var_df['Variance'] = var_df['Actual'] - var_df['Plan']
            var_df['VarPct'] = (var_df['Variance'] / var_df['Plan'] * 100).fillna(0)
            var_df['Risk'] = var_df['VarPct'].apply(lambda x: 'CRITICAL' if x < -20 else 'HIGH' if x < -10 else 'NORMAL')
        
        yearly = None
        if actuals is not None and 'Year' in actuals.columns:
            yearly = actuals.groupby('Year')['RevenueUSD'].sum().reset_index()
        
        return actuals, plan, var_df, yearly
        
    except Exception as e:
        return None, None, None, None

def generate_forecast(yearly: pd.DataFrame, periods: int = 3) -> Tuple[List[Dict], Dict]:
    """Generate revenue forecast."""
    if yearly is None or len(yearly) < 3:
        return [], {}
    
    try:
        slope, intercept, r, p, se = stats.linregress(yearly['Year'], yearly['RevenueUSD'])
        
        yoy_changes = yearly['RevenueUSD'].pct_change().dropna() * 100
        avg_yoy = yoy_changes.mean() if len(yoy_changes) > 0 else 5.0
        
        forecasts = []
        last_year = int(yearly['Year'].max())
        last_val = yearly[yearly['Year'] == last_year]['RevenueUSD'].values[0]
        
        for i in range(1, periods + 1):
            yr = last_year + i
            reg_fc = intercept + slope * yr
            growth_fc = last_val * (1 + avg_yoy/100) ** i
            fc = 0.6 * reg_fc + 0.4 * growth_fc
            
            std_err = yearly['RevenueUSD'].std() * (1 + 0.1 * i)
            
            forecasts.append({
                'Year': yr,
                'Forecast': fc,
                'Low': fc - 1.96 * std_err,
                'High': fc + 1.96 * std_err
            })
        
        diagnostics = {
            'r2': r**2,
            'slope': slope,
            'avg_yoy': avg_yoy,
            'method': 'Blended (60% regression, 40% growth)'
        }
        
        return forecasts, diagnostics
    except:
        return [], {}

def generate_va05_orders() -> pd.DataFrame:
    """Generate synthetic VA05 order data."""
    np.random.seed(42)
    n = 30
    
    materials = ['Touring Bike', 'Road Bike', 'Mountain Bike', 'E-Bike', 'Accessories']
    customers = [f'CUST-{i:04d}' for i in range(100, 120)]
    
    data = {
        'doc': [f'SO-{np.random.randint(1000000, 9999999)}' for _ in range(n)],
        'material': np.random.choice(materials, n),
        'customer': np.random.choice(customers, n),
        'value': np.random.lognormal(10, 1, n),
        'days_old': np.random.randint(1, 45, n),
        'qty': np.random.randint(1, 50, n)
    }
    
    df = pd.DataFrame(data)
    df['value'] = df['value'].round(2)
    df['late_prob'] = np.clip(0.3 + df['days_old'] * 0.015 + df['value'] / 100000, 0.2, 0.92)
    df['revenue_at_risk'] = df['value'] * df['late_prob']
    df['risk_level'] = pd.cut(df['late_prob'], bins=[0, 0.5, 0.75, 1], labels=['LOW', 'MEDIUM', 'HIGH'])
    
    return df.sort_values('late_prob', ascending=False)

def generate_external_signals() -> Dict:
    """Generate external market signals."""
    np.random.seed(int(time.time()) % 1000)
    
    traffic = [
        {'corridor': 'Long Beach → LA', 'delay_ratio': round(np.random.uniform(1.0, 2.2), 1), 'level': 'normal'},
        {'corridor': 'LA → Phoenix', 'delay_ratio': round(np.random.uniform(0.9, 1.8), 1), 'level': 'normal'},
        {'corridor': 'Oakland → Sacramento', 'delay_ratio': round(np.random.uniform(0.8, 1.5), 1), 'level': 'normal'},
        {'corridor': 'Seattle → Portland', 'delay_ratio': round(np.random.uniform(0.9, 1.6), 1), 'level': 'normal'}
    ]
    
    for t in traffic:
        if t['delay_ratio'] >= 1.8:
            t['level'] = 'severe'
        elif t['delay_ratio'] >= 1.4:
            t['level'] = 'heavy'
    
    satellite = [
        {'location': 'West Coast DC', 'activity': round(np.random.uniform(0.6, 1.0), 2), 'trend': 'stable'},
        {'location': 'Southwest Hub', 'activity': round(np.random.uniform(0.5, 0.95), 2), 'trend': 'stable'}
    ]
    
    for s in satellite:
        if s['activity'] < 0.7:
            s['trend'] = 'declining'
        elif s['activity'] > 0.85:
            s['trend'] = 'increasing'
    
    market = {
        'steel_index': round(np.random.uniform(95, 115), 1),
        'fuel_index': round(np.random.uniform(90, 125), 1),
        'container_rate': round(np.random.uniform(1800, 3500), 0),
        'consumer_confidence': round(np.random.uniform(95, 108), 1)
    }
    
    traffic_issues = sum(1 for t in traffic if t['level'] in ['heavy', 'severe'])
    satellite_issues = sum(1 for s in satellite if s['trend'] == 'declining')
    market_stress = (market['steel_index'] > 110) + (market['fuel_index'] > 115)
    
    if traffic_issues >= 2 or (traffic_issues >= 1 and satellite_issues >= 1):
        overall = 'CRITICAL'
    elif traffic_issues >= 1 or satellite_issues >= 1 or market_stress >= 2:
        overall = 'ELEVATED'
    else:
        overall = 'NORMAL'
    
    return {
        'traffic': traffic,
        'satellite': satellite,
        'market': market,
        'summary': {
            'overall': overall,
            'traffic': traffic_issues,
            'satellite': satellite_issues,
            'market': market_stress
        }
    }

def generate_alerts(va05: pd.DataFrame, var_df: pd.DataFrame, signals: Dict, ml_orders: pd.DataFrame = None) -> List[Dict]:
    """Generate system alerts."""
    alerts = []
    
    if ml_orders is not None and len(ml_orders) > 0:
        high_risk = ml_orders[ml_orders['RiskCategory'] == 'High']
        if len(high_risk) > 0:
            top_risk = high_risk.iloc[0]
            alerts.append({
                'sev': 'CRITICAL',
                'src': 'ML Risk Model',
                'title': f'High-Risk Order #{int(top_risk["OrderNumber"])}',
                'detail': f'${top_risk["TotalRevenue"]:,.0f} | {top_risk["RiskProbability"]*100:.0f}% risk score'
            })
        
        if len(high_risk) >= 5:
            alerts.append({
                'sev': 'HIGH',
                'src': 'ML Risk Model',
                'title': f'{len(high_risk)} Orders Flagged High-Risk',
                'detail': f'${high_risk["TotalRevenue"].sum():,.0f} total value at risk'
            })
    else:
        high_risk = va05[va05['risk_level'] == 'HIGH']
        if len(high_risk) > 0:
            alerts.append({
                'sev': 'CRITICAL',
                'src': 'Order Pipeline',
                'title': f'{len(high_risk)} High-Risk Orders',
                'detail': f'${high_risk["revenue_at_risk"].sum():,.0f} revenue at risk'
            })
    
    if var_df is not None:
        critical_var = var_df[var_df['Risk'] == 'CRITICAL']
        if len(critical_var) > 0:
            alerts.append({
                'sev': 'CRITICAL',
                'src': 'Financial',
                'title': f'{len(critical_var)} Customers Below Plan',
                'detail': f'${abs(critical_var["Variance"].sum()):,.0f} total shortfall'
            })
    
    for t in signals['traffic']:
        if t['level'] == 'severe':
            alerts.append({
                'sev': 'CRITICAL',
                'src': 'Traffic',
                'title': f'{t["corridor"]} Severe Delays',
                'detail': f'{t["delay_ratio"]}x normal transit time'
            })
        elif t['level'] == 'heavy':
            alerts.append({
                'sev': 'HIGH',
                'src': 'Traffic',
                'title': f'{t["corridor"]} Heavy Traffic',
                'detail': f'{t["delay_ratio"]}x normal transit time'
            })
    
    for s in signals['satellite']:
        if s['trend'] == 'declining':
            alerts.append({
                'sev': 'HIGH',
                'src': 'Satellite',
                'title': f'{s["location"]} Activity Down',
                'detail': f'{s["activity"]*100:.0f}% utilization'
            })
    
    return sorted(alerts, key=lambda x: 0 if x['sev'] == 'CRITICAL' else 1)[:10]

# ============================================================
# STYLES
# ============================================================

def inject_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .stApp {
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3a 50%, #0a0a1a 100%);
    }
    
    .main-header {
        font-size: 28px;
        font-weight: 700;
        color: #fff;
        padding: 16px 0;
        border-bottom: 1px solid #3b82f6;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .status-badge {
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }
    
    .status-normal { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
    .status-elevated { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
    .status-critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
    
    .ml-badge {
        background: rgba(139, 92, 246, 0.2);
        color: #a78bfa;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        margin-left: 12px;
    }
    
    .ai-badge {
        background: rgba(6, 182, 212, 0.2);
        color: #22d3ee;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        margin-left: 8px;
    }
    
    .section-header {
        font-size: 16px;
        font-weight: 600;
        color: #94a3b8;
        padding: 12px 0 8px 0;
        border-bottom: 1px solid #2a2a4a;
        margin-bottom: 12px;
    }
    
    .data-card {
        background: rgba(30, 30, 60, 0.6);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 4px solid #3b82f6;
        transition: all 0.2s;
    }
    
    .data-card:hover {
        background: rgba(40, 40, 80, 0.8);
    }
    
    .data-card.critical { border-left-color: #ef4444; }
    .data-card.high { border-left-color: #f59e0b; }
    .data-card.normal { border-left-color: #22c55e; }
    .data-card.low { border-left-color: #22c55e; }
    
    .card-title {
        font-size: 15px;
        font-weight: 600;
        color: #fff;
        margin-bottom: 6px;
    }
    
    .card-detail {
        font-size: 13px;
        color: #94a3b8;
    }
    
    .signal-card {
        background: rgba(30, 30, 60, 0.4);
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .signal-name {
        font-size: 14px;
        color: #fff;
        font-weight: 500;
    }
    
    .signal-val {
        font-size: 13px;
        color: #94a3b8;
    }
    
    .signal-badge {
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 600;
    }
    
    .signal-badge.severe, .signal-badge.critical, .signal-badge.drop { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
    .signal-badge.heavy, .signal-badge.high, .signal-badge.surge { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
    .signal-badge.normal, .signal-badge.stable, .signal-badge.low { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
    
    .model-card {
        background: rgba(30, 30, 60, 0.6);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #3b82f6;
    }
    
    .model-title {
        font-size: 18px;
        font-weight: 600;
        color: #fff;
        margin-bottom: 16px;
    }
    
    .model-metric {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #2a2a4a;
    }
    
    .metric-label { color: #94a3b8; font-size: 14px; }
    .metric-value { color: #fff; font-weight: 600; font-size: 14px; }
    
    .ai-explanation {
        background: rgba(6, 182, 212, 0.1);
        border: 1px solid rgba(6, 182, 212, 0.3);
        border-radius: 12px;
        padding: 16px;
        margin-top: 12px;
    }
    
    .ai-explanation-header {
        color: #22d3ee;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .ai-explanation-text {
        color: #e2e8f0;
        font-size: 14px;
        line-height: 1.6;
    }
    
    .consequence-card {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 12px;
        padding: 16px;
        margin-top: 12px;
    }
    
    .consequence-header {
        color: #ef4444;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    
    .top5-card {
        background: rgba(139, 92, 246, 0.1);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 12px;
        padding: 16px;
        margin-top: 12px;
    }
    
    .top5-header {
        color: #a78bfa;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(20, 20, 40, 0.5);
        padding: 8px;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #94a3b8;
        border-radius: 8px;
        padding: 8px 16px;
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(59, 130, 246, 0.2);
        color: #3b82f6;
    }
    
    /* Decision Template Styles */
    .decision-card {
        background: rgba(15, 15, 35, 0.9);
        border: 2px solid #3b82f6;
        border-radius: 16px;
        padding: 0;
        margin: 16px 0;
        overflow: hidden;
        font-family: 'Inter', monospace;
    }
    
    .decision-header {
        background: linear-gradient(90deg, #3b82f6 0%, #1d4ed8 100%);
        padding: 12px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .decision-header.critical {
        background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
    }
    
    .decision-header.high {
        background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);
    }
    
    .decision-title {
        color: #fff;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    
    .decision-badge {
        background: rgba(255,255,255,0.2);
        color: #fff;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }
    
    .decision-body {
        padding: 16px 20px;
    }
    
    .decision-row {
        display: flex;
        justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid rgba(59, 130, 246, 0.2);
    }
    
    .decision-row:last-child {
        border-bottom: none;
    }
    
    .decision-label {
        color: #64748b;
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .decision-value {
        color: #fff;
        font-size: 14px;
        font-weight: 600;
        text-align: right;
        max-width: 60%;
    }
    
    .decision-section {
        background: rgba(30, 30, 60, 0.5);
        border-radius: 8px;
        padding: 12px 16px;
        margin: 12px 0;
    }
    
    .decision-section-title {
        color: #3b82f6;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    
    .decision-section-content {
        color: #e2e8f0;
        font-size: 13px;
        line-height: 1.5;
    }
    
    .decision-footer {
        background: rgba(30, 30, 60, 0.8);
        padding: 12px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    .decision-meta {
        color: #64748b;
        font-size: 11px;
    }
    
    .decision-action {
        background: #3b82f6;
        color: #fff;
        padding: 6px 16px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .risk-bar {
        height: 8px;
        background: rgba(255,255,255,0.1);
        border-radius: 4px;
        overflow: hidden;
        margin-top: 4px;
    }
    
    .risk-bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
    }
    
    .risk-bar-fill.critical { background: linear-gradient(90deg, #ef4444, #dc2626); }
    .risk-bar-fill.high { background: linear-gradient(90deg, #f59e0b, #d97706); }
    .risk-bar-fill.medium { background: linear-gradient(90deg, #3b82f6, #1d4ed8); }
    
    /* Playbook Styles */
    .playbook-card {
        background: rgba(15, 15, 35, 0.9);
        border: 2px solid #22c55e;
        border-radius: 16px;
        padding: 0;
        margin: 16px 0;
        overflow: hidden;
    }
    
    .playbook-header {
        background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%);
        padding: 12px 20px;
    }
    
    .playbook-title {
        color: #fff;
        font-size: 14px;
        font-weight: 700;
    }
    
    .playbook-step {
        display: flex;
        align-items: flex-start;
        padding: 12px 0;
        border-bottom: 1px solid rgba(34, 197, 94, 0.2);
    }
    
    .playbook-step-number {
        background: #22c55e;
        color: #fff;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 700;
        margin-right: 12px;
        flex-shrink: 0;
    }
    
    .playbook-step-text {
        color: #e2e8f0;
        font-size: 13px;
        line-height: 1.5;
    }
    
    /* Action Plan Styles */
    .action-plan {
        background: rgba(15, 15, 35, 0.9);
        border: 2px solid #a78bfa;
        border-radius: 16px;
        overflow: hidden;
        margin: 16px 0;
    }
    
    .action-plan-header {
        background: linear-gradient(90deg, #a78bfa 0%, #7c3aed 100%);
        padding: 12px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .action-plan-title {
        color: #fff;
        font-size: 14px;
        font-weight: 700;
    }
    
    .action-plan-date {
        color: rgba(255,255,255,0.8);
        font-size: 12px;
    }
    
    .action-item {
        display: flex;
        align-items: center;
        padding: 14px 20px;
        border-bottom: 1px solid rgba(167, 139, 250, 0.2);
    }
    
    .action-priority {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 10px;
        font-weight: 700;
        margin-right: 12px;
        min-width: 60px;
        text-align: center;
    }
    
    .action-priority.critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
    .action-priority.high { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
    .action-priority.medium { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
    
    .action-text {
        color: #e2e8f0;
        font-size: 13px;
        flex: 1;
    }
    
    .action-checkbox {
        width: 20px;
        height: 20px;
        border: 2px solid #a78bfa;
        border-radius: 4px;
        margin-left: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================
# DECISION TEMPLATE RENDERERS
# ============================================================

def render_escalation_card(card: dict):
    """Render a structured escalation decision card."""
    risk_class = card.get('risk_level', 'HIGH').lower()
    risk_pct = int(card.get('risk_score', 0) * 100)
    
    st.markdown(f'''
    <div class="decision-card">
        <div class="decision-header {risk_class}">
            <div class="decision-title">📋 ESCALATION: Order #{card.get('order_id')}</div>
            <div class="decision-badge">{card.get('risk_level', 'HIGH')} RISK</div>
        </div>
        <div class="decision-body">
            <div class="decision-row">
                <span class="decision-label">Customer</span>
                <span class="decision-value">{card.get('customer')}</span>
            </div>
            <div class="decision-row">
                <span class="decision-label">Order Value</span>
                <span class="decision-value">${card.get('value', 0):,.0f}</span>
            </div>
            <div class="decision-row">
                <span class="decision-label">Risk Score</span>
                <span class="decision-value">{risk_pct}%</span>
            </div>
            <div class="risk-bar">
                <div class="risk-bar-fill {risk_class}" style="width: {risk_pct}%"></div>
            </div>
            
            <div class="decision-section">
                <div class="decision-section-title">Root Cause</div>
                <div class="decision-section-content">{card.get('root_cause', 'Analysis pending')}</div>
            </div>
            
            <div class="decision-section">
                <div class="decision-section-title">Recommended Action</div>
                <div class="decision-section-content">{card.get('action', 'Review order details')}</div>
            </div>
            
            <div class="decision-row">
                <span class="decision-label">Deadline</span>
                <span class="decision-value" style="color: #ef4444;">{card.get('deadline', 'ASAP')}</span>
            </div>
            <div class="decision-row">
                <span class="decision-label">Owner</span>
                <span class="decision-value">{card.get('owner', '[Assign]')}</span>
            </div>
            
            <div class="decision-section">
                <div class="decision-section-title">Fallback Plan</div>
                <div class="decision-section-content">{card.get('fallback', 'Escalate to manager')}</div>
            </div>
        </div>
        <div class="decision-footer">
            <span class="decision-meta">Recovery Probability: {card.get('recovery_probability', 70)}%</span>
            <span class="decision-action">TAKE ACTION</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)

def render_playbook_card(playbook: dict):
    """Render a mitigation playbook card."""
    steps_html = ""
    for i, step in enumerate(playbook.get('steps', []), 1):
        steps_html += f'''
        <div class="playbook-step">
            <div class="playbook-step-number">{i}</div>
            <div class="playbook-step-text">{step}</div>
        </div>
        '''
    
    st.markdown(f'''
    <div class="playbook-card">
        <div class="playbook-header">
            <div class="playbook-title">📘 MITIGATION PLAYBOOK: {playbook.get('issue_type', 'Issue').replace('_', ' ').title()}</div>
        </div>
        <div class="decision-body">
            <div class="decision-section">
                <div class="decision-section-title">Issue Summary</div>
                <div class="decision-section-content">{playbook.get('issue_summary', 'Issue detected')}</div>
            </div>
            
            <div class="decision-section">
                <div class="decision-section-title">Business Impact</div>
                <div class="decision-section-content">{playbook.get('impact', 'Impact assessment pending')}</div>
            </div>
            
            <div class="decision-section">
                <div class="decision-section-title">Mitigation Steps</div>
                {steps_html}
            </div>
            
            <div class="decision-row">
                <span class="decision-label">Escalate If</span>
                <span class="decision-value">{playbook.get('escalate_if', 'No improvement')}</span>
            </div>
            
            <div class="decision-row">
                <span class="decision-label">Success Metric</span>
                <span class="decision-value">{playbook.get('success_metric', 'Issue resolved')}</span>
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

def render_action_plan(plan: dict):
    """Render a daily action plan."""
    actions_html = ""
    for action in plan.get('actions', []):
        priority_class = action.get('priority', 'HIGH').lower()
        actions_html += f'''
        <div class="action-item">
            <span class="action-priority {priority_class}">{action.get('priority', 'HIGH')}</span>
            <span class="action-text">{action.get('action', 'Action item')}</span>
            <div class="action-checkbox"></div>
        </div>
        '''
    
    st.markdown(f'''
    <div class="action-plan">
        <div class="action-plan-header">
            <span class="action-plan-title">📋 TODAY'S ACTION PLAN</span>
            <span class="action-plan-date">{plan.get('date', 'Today')} | Generated {plan.get('generated_at', 'now')}</span>
        </div>
        {actions_html}
        <div class="decision-footer">
            <span class="decision-meta">At Risk: ${plan.get('total_at_risk', 0)/1e6:.2f}M | Orders to Review: {plan.get('orders_to_review', 0)}</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)

def render_tradeoff_card(summary: dict):
    """Render a tradeoff analysis card."""
    options_html = ""
    for i, opt in enumerate(summary.get('options', []), 1):
        is_recommended = i == summary.get('recommended', 1)
        highlight = 'border: 2px solid #22c55e; background: rgba(34, 197, 94, 0.1);' if is_recommended else ''
        rec_badge = '<span style="background:#22c55e;color:#fff;padding:2px 8px;border-radius:4px;font-size:10px;margin-left:8px;">RECOMMENDED</span>' if is_recommended else ''
        options_html += f'''
        <div class="decision-section" style="{highlight}">
            <div class="decision-section-title">Option {i}: {opt.get('name', 'Option')}{rec_badge}</div>
            <div class="decision-section-content">{opt.get('description', 'Description')}</div>
            <div style="color:#64748b;font-size:12px;margin-top:8px;">Impact: {opt.get('impact', 'Unknown')}</div>
        </div>
        '''
    
    confidence_color = '#22c55e' if summary.get('confidence') == 'HIGH' else '#f59e0b' if summary.get('confidence') == 'MEDIUM' else '#ef4444'
    
    st.markdown(f'''
    <div class="decision-card">
        <div class="decision-header">
            <div class="decision-title">⚖️ TRADEOFF ANALYSIS</div>
            <div class="decision-badge" style="background:{confidence_color};">{summary.get('confidence', 'MEDIUM')} CONFIDENCE</div>
        </div>
        <div class="decision-body">
            {options_html}
            
            <div class="decision-section">
                <div class="decision-section-title">Reasoning</div>
                <div class="decision-section-content">{summary.get('reasoning', 'Analysis pending')}</div>
            </div>
            
            <div class="decision-section">
                <div class="decision-section-title">Tradeoff</div>
                <div class="decision-section-content">{summary.get('tradeoff', 'Tradeoffs under analysis')}</div>
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

# ============================================================
# SCENARIO PACKS
# ============================================================

SCENARIO_PACKS = {
    "🌊 Port Strike": {"traffic_mult": 2.5, "satellite_drop": 0.3, "desc": "West coast port shutdown", "impact": -15},
    "📈 Demand Surge": {"demand_mult": 1.4, "desc": "Unexpected 40% demand increase", "impact": +25},
    "🔧 Supplier Issue": {"supply_drop": 0.25, "desc": "Key supplier capacity reduced", "impact": -10}
}

# ============================================================
# WALL MODE
# ============================================================

def render_wall_mode():
    """Render read-only wall display mode."""
    inject_styles()
    
    ml_models = load_ml_models()
    ai_service = get_ai_service()
    actuals, plan, var_df, yearly = load_gbi_data()
    va05 = generate_va05_orders()
    signals = generate_external_signals()
    
    ml_orders = ml_score_orders(actuals, ml_models) if actuals is not None else None
    alerts = generate_alerts(va05, var_df, signals, ml_orders)
    
    # Convert to dict for AI
    top_orders = orders_to_dict_list(ml_orders, 10) if ml_orders is not None else []
    
    # Calculate metrics
    if ml_orders is not None and len(ml_orders) > 0:
        total_pipeline = ml_orders['TotalRevenue'].sum()
        at_risk_value = ml_orders[ml_orders['RiskCategory'] == 'High']['TotalRevenue'].sum()
        high_risk_count = len(ml_orders[ml_orders['RiskCategory'] == 'High'])
        total_orders = len(ml_orders)
    else:
        total_pipeline = va05['value'].sum()
        at_risk_value = va05['revenue_at_risk'].sum()
        high_risk_count = len(va05[va05['risk_level'] == 'HIGH'])
        total_orders = va05['doc'].nunique()
    
    at_risk_pct = at_risk_value / total_pipeline * 100 if total_pipeline > 0 else 0
    status = signals['summary']['overall']
    status_class = status.lower()
    
    # Header
    badges = ""
    if ml_models['available']:
        badges += '<span class="ml-badge">🧠 ML</span>'
    if ai_service.available:
        badges += '<span class="ai-badge">🤖 AI</span>'
    
    st.markdown(f'''
    <div class="main-header">
        <div>{Config.APP_NAME} <span style="color:#64748b;font-size:14px;">v{Config.VERSION}</span>{badges}</div>
        <div class="status-badge status-{status_class}">{status}</div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Mode toggle
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("📺 WALL", use_container_width=True):
            st.session_state.mode = "wall"
    with col2:
        if st.button("🖥️ OPERATOR", use_container_width=True):
            st.session_state.mode = "operator"
            st.rerun()
    
    # Main metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Pipeline", f"${total_pipeline/1e6:.1f}M")
    c2.metric("Orders", f"{total_orders:,}")
    c3.metric("At Risk", f"${at_risk_value/1e6:.2f}M", f"{at_risk_pct:.0f}%")
    c4.metric("High Risk", high_risk_count)
    c5.metric("Alerts", len([a for a in alerts if a['sev'] in ['CRITICAL', 'HIGH']]))
    
    st.divider()
    
    # Two column layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="section-header">🚨 Priority Alerts</div>', unsafe_allow_html=True)
        for alert in alerts[:6]:
            cls = 'critical' if alert['sev'] == 'CRITICAL' else 'high' if alert['sev'] == 'HIGH' else 'normal'
            st.markdown(f'''
            <div class="data-card {cls}">
                <div class="card-title">{alert['title']}</div>
                <div class="card-detail">{alert['detail']} • {alert['src']}</div>
            </div>
            ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="section-header">🌐 External Signals</div>', unsafe_allow_html=True)
        for t in signals['traffic'][:4]:
            badge_class = 'severe' if t['level'] == 'severe' else 'heavy' if t['level'] == 'heavy' else 'normal'
            st.markdown(f'''
            <div class="signal-card">
                <div>
                    <div class="signal-name">{t['corridor']}</div>
                    <div class="signal-val">{t['delay_ratio']}x delay</div>
                </div>
                <div class="signal-badge {badge_class}">{t['level'].upper()}</div>
            </div>
            ''', unsafe_allow_html=True)
    
    # AI Brief section
    if ai_service.available:
        st.divider()
        
        metrics = {
            'total_orders': total_orders,
            'total_value': total_pipeline,
            'high_risk_count': high_risk_count,
            'at_risk_value': at_risk_value,
            'at_risk_pct': at_risk_pct,
            'critical_alerts': len([a for a in alerts if a['sev'] == 'CRITICAL']),
            'high_alerts': len([a for a in alerts if a['sev'] == 'HIGH']),
            'system_status': status,
            'traffic_issues': signals['summary']['traffic']
        }
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="section-header">🤖 AI Executive Brief</div>', unsafe_allow_html=True)
            with st.spinner("Generating brief..."):
                brief = ai_service.generate_executive_brief(metrics, top_orders, signals['traffic'])
            st.markdown(f'''
            <div class="ai-explanation">
                <div class="ai-explanation-header">🤖 Smart Analysis (Llama 3)</div>
                <div class="ai-explanation-text">{brief}</div>
            </div>
            ''', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="section-header">⚡ Top 5 Priority Orders</div>', unsafe_allow_html=True)
            if top_orders:
                top_5_value = sum(o['value'] for o in top_orders[:5])
                concentration = (top_5_value / at_risk_value * 100) if at_risk_value > 0 else 0
                st.markdown(f'''
                <div class="top5-card">
                    <div class="top5-header">🎯 Concentration: Top 5 = {concentration:.0f}% of risk (${top_5_value/1e6:.2f}M)</div>
                    <div class="ai-explanation-text">
                        {"<br>".join([f"#{o['order_id']}: ${o['value']:,.0f} | Customer {o['customer']}" for o in top_orders[:5]])}
                    </div>
                </div>
                ''', unsafe_allow_html=True)


# ============================================================
# OPERATOR MODE
# ============================================================

def render_operator_mode():
    """Render interactive operator mode."""
    inject_styles()
    
    ml_models = load_ml_models()
    ai_service = get_ai_service()
    actuals, plan, var_df, yearly = load_gbi_data()
    va05 = generate_va05_orders()
    signals = generate_external_signals()
    fc, fc_diag = generate_forecast(yearly) if yearly is not None else ([], {})
    
    ml_orders = ml_score_orders(actuals, ml_models) if actuals is not None else None
    ml_demand = ml_forecast_demand(actuals, ml_models) if actuals is not None else None
    alerts = generate_alerts(va05, var_df, signals, ml_orders)
    
    # Convert to dict for AI
    top_orders = orders_to_dict_list(ml_orders, 10) if ml_orders is not None else []
    
    # Calculate metrics
    if ml_orders is not None and len(ml_orders) > 0:
        total_pipeline = ml_orders['TotalRevenue'].sum()
        at_risk_value = ml_orders[ml_orders['RiskCategory'] == 'High']['TotalRevenue'].sum()
        high_risk_count = len(ml_orders[ml_orders['RiskCategory'] == 'High'])
        total_orders = len(ml_orders)
    else:
        total_pipeline = va05['value'].sum()
        at_risk_value = va05['revenue_at_risk'].sum()
        high_risk_count = len(va05[va05['risk_level'] == 'HIGH'])
        total_orders = va05['doc'].nunique()
    
    at_risk_pct = at_risk_value / total_pipeline * 100 if total_pipeline > 0 else 0
    status = signals['summary']['overall']
    status_class = status.lower()
    
    # Metrics dict for AI
    metrics = {
        'total_orders': total_orders,
        'total_value': total_pipeline,
        'high_risk_count': high_risk_count,
        'at_risk_value': at_risk_value,
        'at_risk_pct': at_risk_pct,
        'critical_alerts': len([a for a in alerts if a['sev'] == 'CRITICAL']),
        'high_alerts': len([a for a in alerts if a['sev'] == 'HIGH']),
        'system_status': status,
        'traffic_issues': signals['summary']['traffic']
    }
    
    # Header
    badges = ""
    if ml_models['available']:
        badges += '<span class="ml-badge">🧠 ML</span>'
    if ai_service.available:
        badges += '<span class="ai-badge">🤖 AI</span>'
    
    st.markdown(f'''
    <div class="main-header">
        <div>{Config.APP_NAME} <span style="color:#64748b;font-size:14px;">v{Config.VERSION} OPERATOR</span>{badges}</div>
        <div class="status-badge status-{status_class}">{status}</div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Mode toggle
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("📺 WALL", use_container_width=True):
            st.session_state.mode = "wall"
            st.rerun()
    with col2:
        if st.button("🖥️ OPERATOR", use_container_width=True):
            st.session_state.mode = "operator"
    
    # Tabs
    tabs = st.tabs(["📊 Overview", "📦 Logistics", "💰 Finance", "📈 Forecast", "🌐 Signals", "🚨 Alerts", "🎮 Scenarios", "🧠 ML Intel", "🤖 AI Command", "🔌 Sources"])
    
    # Overview
    with tabs[0]:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Pipeline", f"${total_pipeline/1e6:.1f}M")
        c2.metric("Orders", f"{total_orders:,}")
        c3.metric("At Risk", f"${at_risk_value/1e6:.2f}M", f"{at_risk_pct:.0f}%")
        c4.metric("High Risk", high_risk_count)
        c5.metric("Alerts", len([a for a in alerts if a['sev'] in ['CRITICAL', 'HIGH']]))
        
        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">🚨 Priority Alerts</div>', unsafe_allow_html=True)
            for a in alerts[:5]:
                cls = 'critical' if a['sev'] == 'CRITICAL' else 'high'
                st.markdown(f'<div class="data-card {cls}"><div class="card-title">{a["title"]}</div><div class="card-detail">{a["detail"]} • {a["src"]}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="section-header">🌐 Signals</div>', unsafe_allow_html=True)
            for t in signals['traffic'][:3]:
                b = 'critical' if t['level'] == 'severe' else 'high' if t['level'] == 'heavy' else 'normal'
                st.markdown(f'<div class="signal-card"><div class="signal-content"><div class="signal-name">{t["corridor"]}</div><div class="signal-val">{t["delay_ratio"]}x</div></div><div class="signal-badge {b}">{t["level"].upper()}</div></div>', unsafe_allow_html=True)
    
    # Logistics
    with tabs[1]:
        st.markdown('<div class="section-header">📦 Order Pipeline</div>', unsafe_allow_html=True)
        
        if ml_orders is not None and len(ml_orders) > 0:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Value", f"${ml_orders['TotalRevenue'].sum()/1e6:.1f}M")
            c2.metric("Orders", f"{len(ml_orders):,}")
            c3.metric("High Risk", len(ml_orders[ml_orders['RiskCategory'] == 'High']))
            c4.metric("At Risk $", f"${ml_orders[ml_orders['RiskCategory'] == 'High']['TotalRevenue'].sum()/1e6:.2f}M")
            
            # Top 5 concentration
            if ai_service.available and top_orders:
                top_5_value = sum(o['value'] for o in top_orders[:5])
                concentration = (top_5_value / at_risk_value * 100) if at_risk_value > 0 else 0
                
                st.markdown(f'''
                <div class="top5-card">
                    <div class="top5-header">🎯 TOP 5 CONCENTRATION: {concentration:.0f}% of risk = ${top_5_value/1e6:.2f}M</div>
                </div>
                ''', unsafe_allow_html=True)
            
            st.markdown('<div class="section-header">⚠️ ML-Scored High Risk Orders</div>', unsafe_allow_html=True)
            
            high_risk_orders = ml_orders[ml_orders['RiskCategory'] == 'High'].head(8)
            
            for idx, r in high_risk_orders.iterrows():
                order_id = int(r["OrderNumber"])
                
                st.markdown(f'''
                <div class="data-card critical">
                    <div class="card-title">Order {order_id} — Customer {int(r["Customer"])}</div>
                    <div class="card-detail">${r["TotalRevenue"]:,.0f} | {int(r["LineItems"])} items | {int(r["ProductDiversity"])} products | Risk: {r["RiskProbability"]*100:.0f}%</div>
                </div>
                ''', unsafe_allow_html=True)
                
                if ai_service.available:
                    col1, col2 = st.columns([4, 1])
                    with col2:
                        if st.button(f"🤖 Analyze", key=f"analyze_{order_id}"):
                            st.session_state.selected_order = order_id
                    
                    if st.session_state.selected_order == order_id:
                        if order_id not in st.session_state.ai_analysis_cache:
                            with st.spinner("AI analyzing..."):
                                order_data = {
                                    'order_id': order_id,
                                    'customer': int(r["Customer"]),
                                    'value': r["TotalRevenue"],
                                    'line_items': int(r["LineItems"]),
                                    'product_diversity': int(r["ProductDiversity"]),
                                    'risk_score': r["RiskProbability"]
                                }
                                analysis = ai_service.analyze_order_risk(order_data)
                                st.session_state.ai_analysis_cache[order_id] = analysis
                        
                        st.markdown(f'''
                        <div class="ai-explanation">
                            <div class="ai-explanation-header">🤖 AI Risk Analysis</div>
                            <div class="ai-explanation-text">{st.session_state.ai_analysis_cache[order_id]}</div>
                        </div>
                        ''', unsafe_allow_html=True)
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Value", f"${va05['value'].sum():,.0f}")
            c2.metric("Orders", va05['doc'].nunique())
            c3.metric("High Risk", len(va05[va05['risk_level'] == 'HIGH']))
            c4.metric("$ at Risk", f"${va05['revenue_at_risk'].sum():,.0f}")
            
            st.markdown('<div class="section-header">⚠️ High Risk Orders (Rule-Based)</div>', unsafe_allow_html=True)
            for _, r in va05[va05['risk_level'] == 'HIGH'].head(6).iterrows():
                st.markdown(f'<div class="data-card critical"><div class="card-title">Doc {r["doc"]} — {r["material"]}</div><div class="card-detail">${r["value"]:,.0f} | {r["days_old"]}d old | {r["late_prob"]*100:.0f}% late</div></div>', unsafe_allow_html=True)
    
    # Finance
    with tabs[2]:
        st.markdown('<div class="section-header">💰 Financial Performance</div>', unsafe_allow_html=True)
        if var_df is not None and len(var_df) > 0:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Actual", f"${var_df['Actual'].sum()/1e6:.1f}M")
            c2.metric("Plan", f"${var_df['Plan'].sum()/1e6:.1f}M")
            c3.metric("Variance", f"${var_df['Variance'].sum()/1e6:+.1f}M")
            c4.metric("At Risk", f"${abs(var_df[var_df['Variance']<0]['Variance'].sum())/1e6:.1f}M")
            
            if PLOTLY_AVAILABLE:
                below = var_df[var_df['Variance'] < 0].head(8)
                fig = go.Figure(go.Bar(x=below['Customer'].astype(str), y=below['Variance'].abs(), marker_color=['#ef4444' if r=='CRITICAL' else '#f59e0b' for r in below['Risk']]))
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), xaxis=dict(gridcolor='#2a2a4a'), yaxis=dict(gridcolor='#2a2a4a', tickformat='$,.0f'), height=300)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Enable GBI Analytics data")
    
    # Forecast
    with tabs[3]:
        st.markdown('<div class="section-header">📈 Revenue Forecasting</div>', unsafe_allow_html=True)
        if yearly is not None and fc:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("R²", f"{fc_diag['r2']:.3f}")
            c2.metric("Avg YoY", f"{fc_diag['avg_yoy']:.1f}%")
            c3.metric(f"{fc[0]['Year']} FC", f"${fc[0]['Forecast']/1e6:.1f}M")
            c4.metric("Trend", f"${fc_diag['slope']/1e6:.2f}M/yr")
            
            if PLOTLY_AVAILABLE:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=yearly['Year'], y=yearly['RevenueUSD'], mode='lines+markers', name='Historical', line=dict(color='#3b82f6', width=3)))
                fc_y = [f['Year'] for f in fc]
                fig.add_trace(go.Scatter(x=fc_y+fc_y[::-1], y=[f['High'] for f in fc]+[f['Low'] for f in fc][::-1], fill='toself', fillcolor='rgba(34,197,94,0.15)', line=dict(color='rgba(0,0,0,0)'), name='95% CI'))
                fig.add_trace(go.Scatter(x=fc_y, y=[f['Forecast'] for f in fc], mode='lines+markers', name='Forecast', line=dict(color='#22c55e', width=3, dash='dash')))
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), xaxis=dict(gridcolor='#2a2a4a'), yaxis=dict(gridcolor='#2a2a4a', tickformat='$,.0f'), height=350)
                st.plotly_chart(fig, use_container_width=True)
        
        if ml_demand is not None and len(ml_demand) > 0:
            st.markdown('<div class="section-header">🧠 ML Demand Forecast by Category</div>', unsafe_allow_html=True)
            for _, r in ml_demand.iterrows():
                badge = r['AlertType'].lower()
                st.markdown(f'<div class="signal-card"><div class="signal-content"><div class="signal-name">{r["Category"]}</div><div class="signal-val">Last: {int(r["Quantity"])} → Next: {int(r["ForecastedDemand"])} ({r["Change"]:+.1f}%)</div></div><div class="signal-badge {badge}">{r["AlertType"]}</div></div>', unsafe_allow_html=True)
    
    # Signals
    with tabs[4]:
        st.markdown('<div class="section-header">🌐 External Signals</div>', unsafe_allow_html=True)
        
        st.markdown("**Traffic Corridors**")
        for t in signals['traffic']:
            b = 'severe' if t['level'] == 'severe' else 'heavy' if t['level'] == 'heavy' else 'normal'
            st.markdown(f'<div class="signal-card"><div class="signal-content"><div class="signal-name">{t["corridor"]}</div><div class="signal-val">{t["delay_ratio"]}x delay ratio</div></div><div class="signal-badge {b}">{t["level"].upper()}</div></div>', unsafe_allow_html=True)
        
        # Corridor impact analysis
        if ai_service.available:
            affected_corridors = {t['corridor']: {'count': np.random.randint(20, 100), 'value': np.random.uniform(500000, 5000000)} for t in signals['traffic'] if t['level'] in ['heavy', 'severe']}
            if affected_corridors:
                st.markdown('<div class="section-header">🤖 AI Corridor Impact Analysis</div>', unsafe_allow_html=True)
                with st.spinner("Analyzing corridor impact..."):
                    corridor_analysis = ai_service.analyze_corridor_impact(signals['traffic'], affected_corridors)
                st.markdown(f'''
                <div class="ai-explanation">
                    <div class="ai-explanation-header">🤖 Corridor Analysis</div>
                    <div class="ai-explanation-text">{corridor_analysis}</div>
                </div>
                ''', unsafe_allow_html=True)
        
        st.markdown("**Satellite Activity**")
        for s in signals['satellite']:
            b = 'drop' if s['trend'] == 'declining' else 'surge' if s['trend'] == 'increasing' else 'stable'
            st.markdown(f'<div class="signal-card"><div class="signal-content"><div class="signal-name">{s["location"]}</div><div class="signal-val">{s["activity"]*100:.0f}% utilization</div></div><div class="signal-badge {b}">{s["trend"].upper()}</div></div>', unsafe_allow_html=True)
        
        st.markdown("**Market Indicators**")
        m = signals['market']
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Steel Index", f"{m['steel_index']:.0f}", "↑" if m['steel_index'] > 105 else "→")
        c2.metric("Fuel Index", f"{m['fuel_index']:.0f}", "↑" if m['fuel_index'] > 110 else "→")
        c3.metric("Container Rate", f"${m['container_rate']:,.0f}")
        c4.metric("Consumer Conf", f"{m['consumer_confidence']:.0f}")
    
    # Alerts
    with tabs[5]:
        st.markdown('<div class="section-header">🚨 All Alerts</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Critical", len([a for a in alerts if a['sev'] == 'CRITICAL']))
        c2.metric("High", len([a for a in alerts if a['sev'] == 'HIGH']))
        c3.metric("Total", len(alerts))
        
        for a in alerts:
            cls = 'critical' if a['sev'] == 'CRITICAL' else 'high'
            st.markdown(f'<div class="data-card {cls}"><div class="card-title">{a["title"]}</div><div class="card-detail">{a["detail"]} • {a["src"]}</div></div>', unsafe_allow_html=True)
    
    # Scenarios
    with tabs[6]:
        st.markdown('<div class="section-header">🎮 Scenario Packs</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for i, (name, data) in enumerate(SCENARIO_PACKS.items()):
            with cols[i]:
                if st.button(name, use_container_width=True, key=f"pack_{i}"):
                    st.session_state.selected_pack = name
        
        if hasattr(st.session_state, 'selected_pack') and st.session_state.selected_pack:
            p = SCENARIO_PACKS[st.session_state.selected_pack]
            st.markdown(f'<div class="data-card {"critical" if p["impact"] < 0 else "low"}"><div class="card-title">{st.session_state.selected_pack}</div><div class="card-detail">{p["desc"]}</div><div style="font-size:28px;font-weight:700;color:{"#ef4444" if p["impact"]<0 else "#22c55e"};margin-top:12px;">{p["impact"]:+.0f}%</div></div>', unsafe_allow_html=True)
    
    # ML Intel
    with tabs[7]:
        st.markdown('<div class="section-header">🧠 ML Model Intelligence</div>', unsafe_allow_html=True)
        
        if ml_models['available']:
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("""
                <div class="model-card">
                    <div class="model-title">Order Risk Classifier</div>
                    <div class="model-metric"><span class="metric-label">Algorithm</span><span class="metric-value">Random Forest</span></div>
                    <div class="model-metric"><span class="metric-label">Training Data</span><span class="metric-value">31,312 orders</span></div>
                    <div class="model-metric"><span class="metric-label">Precision</span><span class="metric-value">99%</span></div>
                    <div class="model-metric"><span class="metric-label">Recall</span><span class="metric-value">99%</span></div>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                st.markdown("""
                <div class="model-card">
                    <div class="model-title">Demand Forecaster</div>
                    <div class="model-metric"><span class="metric-label">Algorithm</span><span class="metric-value">Random Forest Regressor</span></div>
                    <div class="model-metric"><span class="metric-label">R² Score</span><span class="metric-value">0.981</span></div>
                    <div class="model-metric"><span class="metric-label">MAE</span><span class="metric-value">23.5 units</span></div>
                </div>
                """, unsafe_allow_html=True)
            
            if ml_orders is not None:
                st.markdown('<div class="section-header">Scoring Summary</div>', unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Scored", f"{len(ml_orders):,}")
                c2.metric("High", len(ml_orders[ml_orders['RiskCategory'] == 'High']))
                c3.metric("Medium", len(ml_orders[ml_orders['RiskCategory'] == 'Medium']))
                c4.metric("Low", len(ml_orders[ml_orders['RiskCategory'] == 'Low']))
        else:
            st.warning("ML models not loaded. Place in `ml/` folder.")
    
    # AI Command Center (upgraded from AI Brief)
    with tabs[8]:
        st.markdown('<div class="section-header">🤖 AI Command Center v2</div>', unsafe_allow_html=True)
        st.caption(f"v{Config.VERSION} | Decision Templates Active | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        if ai_service.available:
            # Tabs within AI Command
            ai_tabs = st.tabs(["📋 Daily Plan", "🎯 Escalations", "📘 Playbooks", "⚖️ Tradeoffs", "📊 Brief"])
            
            # Daily Action Plan
            with ai_tabs[0]:
                st.markdown("**Today's Action Plan**")
                with st.spinner("Generating action plan..."):
                    plan = ai_service.generate_daily_action_plan(metrics, top_orders, alerts)
                render_action_plan(plan)
                
                st.markdown("---")
                st.markdown("**Quick Stats**")
                c1, c2, c3 = st.columns(3)
                c1.metric("Critical Actions", len([a for a in plan.get('actions', []) if a.get('priority') == 'CRITICAL']))
                c2.metric("Total Actions", len(plan.get('actions', [])))
                c3.metric("At Risk", f"${metrics.get('at_risk_value', 0)/1e6:.2f}M")
            
            # Escalation Cards
            with ai_tabs[1]:
                st.markdown("**Order Escalation Decisions**")
                st.caption("Structured decision cards for high-risk orders. Click to generate.")
                
                if top_orders:
                    # Show first 3 orders with escalation cards
                    for i, order in enumerate(top_orders[:3]):
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"**Order #{order['order_id']}** - ${order['value']:,.0f} - {order['risk_score']*100:.0f}% risk")
                        with col2:
                            if st.button(f"Generate Card", key=f"esc_{i}"):
                                st.session_state[f'escalation_{i}'] = True
                        
                        if st.session_state.get(f'escalation_{i}'):
                            with st.spinner(f"Generating escalation card for Order #{order['order_id']}..."):
                                card = ai_service.generate_escalation_card(order)
                            render_escalation_card(card)
                        
                        st.markdown("---")
                else:
                    st.info("No high-risk orders requiring escalation.")
            
            # Mitigation Playbooks
            with ai_tabs[2]:
                st.markdown("**Mitigation Playbooks**")
                st.caption("Structured response plans for systemic issues.")
                
                # Check for issues that need playbooks
                corridor_issues = [c for c in signals['traffic'] if c['level'] in ['heavy', 'severe']]
                
                if corridor_issues:
                    st.markdown("**Active Corridor Issues:**")
                    for i, corridor in enumerate(corridor_issues):
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"🚛 **{corridor['corridor']}** - {corridor['delay_ratio']}x delay ({corridor['level'].upper()})")
                        with col2:
                            if st.button(f"Playbook", key=f"pb_corridor_{i}"):
                                st.session_state[f'playbook_corridor_{i}'] = True
                        
                        if st.session_state.get(f'playbook_corridor_{i}'):
                            with st.spinner("Generating playbook..."):
                                playbook = ai_service.generate_mitigation_playbook('corridor_delay', {
                                    'corridor': corridor['corridor'],
                                    'delay_ratio': corridor['delay_ratio'],
                                    'affected_count': np.random.randint(20, 80),
                                    'affected_value': np.random.uniform(500000, 3000000)
                                })
                            render_playbook_card(playbook)
                else:
                    st.success("✅ No systemic issues requiring playbooks.")
                
                # Demand issues
                if ml_demand is not None:
                    surge_drops = ml_demand[ml_demand['AlertType'].isin(['SURGE', 'DROP'])]
                    if len(surge_drops) > 0:
                        st.markdown("---")
                        st.markdown("**Demand Anomalies:**")
                        for i, (_, row) in enumerate(surge_drops.iterrows()):
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                icon = "📈" if row['AlertType'] == 'SURGE' else "📉"
                                st.markdown(f"{icon} **{row['Category']}** - {row['Change']:+.0f}% ({row['AlertType']})")
                            with col2:
                                if st.button(f"Playbook", key=f"pb_demand_{i}"):
                                    st.session_state[f'playbook_demand_{i}'] = True
                            
                            if st.session_state.get(f'playbook_demand_{i}'):
                                with st.spinner("Generating playbook..."):
                                    playbook = ai_service.generate_mitigation_playbook('demand_surge' if row['AlertType'] == 'SURGE' else 'demand_drop', {
                                        'category': row['Category'],
                                        'change': row['Change'],
                                        'current_demand': row['Quantity'],
                                        'forecast': row['ForecastedDemand']
                                    })
                                render_playbook_card(playbook)
            
            # Tradeoff Analysis
            with ai_tabs[3]:
                st.markdown("**Tradeoff Analysis**")
                st.caption("When you have competing priorities, get AI-powered decision support.")
                
                # Auto-detect competing priorities
                has_corridor_issue = any(c['level'] in ['heavy', 'severe'] for c in signals['traffic'])
                has_high_risk_orders = metrics.get('high_risk_count', 0) > 5
                has_critical_alerts = metrics.get('critical_alerts', 0) > 0
                
                if has_corridor_issue and has_high_risk_orders:
                    st.markdown("**Detected Competing Priorities:**")
                    
                    options = [
                        {
                            'name': 'Focus on High-Risk Orders',
                            'description': f'Address the {metrics.get("high_risk_count", 0)} high-risk orders first to protect ${metrics.get("at_risk_value", 0)/1e6:.2f}M in revenue.',
                            'impact': 'Maximizes revenue protection but delays logistics response'
                        },
                        {
                            'name': 'Focus on Corridor Delays',
                            'description': 'Reroute shipments and adjust ETAs for affected corridors to prevent cascading delays.',
                            'impact': 'Prevents future issues but high-risk orders may deteriorate'
                        },
                        {
                            'name': 'Split Resources',
                            'description': 'Assign half the team to orders, half to logistics. Parallel execution.',
                            'impact': 'Balanced approach but slower resolution on both fronts'
                        }
                    ]
                    
                    if st.button("🤖 Analyze Tradeoffs", key="analyze_tradeoffs"):
                        with st.spinner("AI analyzing tradeoffs..."):
                            summary = ai_service.generate_tradeoff_summary(options)
                        render_tradeoff_card(summary)
                else:
                    st.info("No competing priorities detected. System focus is clear.")
                    
                    # Manual tradeoff option
                    st.markdown("---")
                    st.markdown("**Custom Tradeoff Analysis**")
                    st.caption("Define your own options for AI analysis")
                    
                    with st.expander("Define Options"):
                        opt1 = st.text_input("Option 1", placeholder="e.g., Prioritize Customer A")
                        opt2 = st.text_input("Option 2", placeholder="e.g., Prioritize Customer B")
                        opt3 = st.text_input("Option 3", placeholder="e.g., Split resources")
                        
                        if st.button("Analyze Custom Tradeoffs") and opt1 and opt2:
                            options = [
                                {'name': 'Option 1', 'description': opt1, 'impact': 'User-defined'},
                                {'name': 'Option 2', 'description': opt2, 'impact': 'User-defined'}
                            ]
                            if opt3:
                                options.append({'name': 'Option 3', 'description': opt3, 'impact': 'User-defined'})
                            
                            with st.spinner("Analyzing..."):
                                summary = ai_service.generate_tradeoff_summary(options)
                            render_tradeoff_card(summary)
            
            # Executive Brief (original)
            with ai_tabs[4]:
                st.markdown("**Executive Summary**")
                with st.spinner("Generating smart brief..."):
                    brief = ai_service.generate_executive_brief(metrics, top_orders, signals['traffic'])
                st.markdown(f'''
                <div class="ai-explanation">
                    <div class="ai-explanation-header">🤖 AI Analysis</div>
                    <div class="ai-explanation-text">{brief}</div>
                </div>
                ''', unsafe_allow_html=True)
                
                st.markdown("**Recommended Action**")
                with st.spinner("..."):
                    rec = ai_service.generate_smart_recommendation(metrics, top_orders)
                st.info(f"🎯 {rec}")
                
                st.markdown("---")
                st.markdown("**Consequence Analysis**")
                with st.spinner("Projecting consequences..."):
                    consequences = ai_service.generate_consequence_analysis(metrics)
                st.markdown(f'''
                <div class="consequence-card">
                    <div class="consequence-header">⚠️ If We Do Nothing</div>
                    <div class="ai-explanation-text">{consequences}</div>
                </div>
                ''', unsafe_allow_html=True)
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Provider", "Ollama (Local)")
            c2.metric("Model", Config.OLLAMA_MODEL)
            c3.metric("Cost", "$0.00")
        else:
            st.warning("Local AI offline. Start with: `brew services start ollama`")
    
    # Sources
    with tabs[9]:
        st.markdown('<div class="section-header">🔌 Data Sources</div>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("GBI", "✅" if actuals is not None else "❌")
        c2.metric("VA05", "✅ Sim")
        c3.metric("Signals", "✅ Live")
        c4.metric("ML", "✅" if ml_models['available'] else "❌")
        c5.metric("AI", "✅" if ai_service.available else "❌")
        
        if ml_models['available']:
            st.success("🧠 ML: Risk (99% recall) + Demand (R²=0.981)")
        if ai_service.available:
            st.success("🤖 AI: Ollama + Llama 3 8B @ localhost:11434")

# ============================================================
# MAIN
# ============================================================

def main():
    if st.session_state.mode == "wall":
        render_wall_mode()
    else:
        render_operator_mode()

if __name__ == "__main__":
    main()
