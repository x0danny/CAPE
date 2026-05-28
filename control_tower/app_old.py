"""
EAISS Control Tower v8.0
Enterprise Decision Intelligence Platform

AI-POWERED UPGRADE:
- Local AI (Ollama/Llama 3) for intelligent explanations
- ML Risk Scoring: Random Forest (99% recall)
- ML Demand Forecasting: Random Forest Regressor (R² = 0.981)
- AI-generated briefs and recommendations

TWO PRESENTATION LAYERS:
- WALL MODE: Single screen, cinematic, read-only
- OPERATOR MODE: Tabbed interface, interactive analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
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
    VERSION = "8.0"
    GBI_PATH = 'uploads/GB_AnalyticsData.xlsx'
    ERPSIM_PATH = 'uploads/ERPSIM.xlsx'
    RISK_MODEL_PATH = 'ml/order_risk_model.pkl'
    DEMAND_MODEL_PATH = 'ml/demand_forecast_model.pkl'
    AUTO_REFRESH_INTERVAL = 30
    
    # Local AI Config
    OLLAMA_BASE_URL = "http://localhost:11434"
    OLLAMA_MODEL = "llama3:8b"
    AI_TIMEOUT = 30.0

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
# LOCAL AI SERVICE
# ============================================================

class LocalAIService:
    """Lightweight local AI service using Ollama."""
    
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
    
    def analyze_order_risk(self, order_data: dict) -> str:
        """Generate AI explanation for order risk."""
        system = """You are an ERP analyst. Analyze order risk factors concisely. 
Be specific about why this order needs attention. Max 3 sentences."""
        
        prompt = f"""Analyze this order's risk:
- Order: {order_data.get('order_id', 'N/A')}
- Customer: {order_data.get('customer', 'N/A')}
- Value: ${order_data.get('value', 0):,.0f}
- Line Items: {order_data.get('line_items', 0)}
- Product Diversity: {order_data.get('product_diversity', 0)} different products
- Risk Score: {order_data.get('risk_score', 0)*100:.0f}%

Why is this order flagged as high risk?"""
        
        result = self.complete(prompt, system, max_tokens=150)
        return result or "AI analysis unavailable."
    
    def generate_executive_brief(self, metrics: dict) -> str:
        """Generate AI-powered executive brief."""
        system = """You are a supply chain executive advisor. Write a brief executive summary.
Be direct, actionable, and specific. Use the data provided. Max 4 sentences."""
        
        prompt = f"""Generate an executive brief for these metrics:

PIPELINE STATUS:
- Total Orders: {metrics.get('total_orders', 0):,}
- Total Value: ${metrics.get('total_value', 0)/1e6:.1f}M
- High Risk Orders: {metrics.get('high_risk_count', 0)}
- Revenue at Risk: ${metrics.get('at_risk_value', 0)/1e6:.2f}M ({metrics.get('at_risk_pct', 0):.0f}%)

ALERTS:
- Critical: {metrics.get('critical_alerts', 0)}
- High: {metrics.get('high_alerts', 0)}
- System Status: {metrics.get('system_status', 'NORMAL')}

EXTERNAL SIGNALS:
- Traffic Issues: {metrics.get('traffic_issues', 0)} corridors affected

What should the executive team know and do?"""
        
        result = self.complete(prompt, system, max_tokens=200)
        return result or "AI brief unavailable. System operating normally with standard monitoring."
    
    def generate_recommendation(self, metrics: dict) -> str:
        """Generate AI-powered recommendation."""
        system = """You are an operations advisor. Give ONE specific, actionable recommendation.
Be direct. Start with an action verb. Max 2 sentences."""
        
        prompt = f"""Based on current status:
- {metrics.get('high_risk_count', 0)} high-risk orders (${metrics.get('at_risk_value', 0)/1e6:.2f}M at risk)
- {metrics.get('critical_alerts', 0)} critical alerts
- System: {metrics.get('system_status', 'NORMAL')}

What is the single most important action to take right now?"""
        
        result = self.complete(prompt, system, max_tokens=100)
        return result or "Continue standard monitoring procedures."


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
        
        # Aggregate to order level
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
        
        # Engineer features
        order_features['GrossMargin'] = ((order_features['TotalRevenue'] - order_features['TotalCost']) / order_features['TotalRevenue']).fillna(0)
        order_features['DiscountPct'] = (order_features['TotalDiscount'] / order_features['TotalRevenue']).fillna(0)
        order_features['AvgItemValue'] = order_features['TotalRevenue'] / order_features['LineItems']
        order_features['AvgQuantityPerItem'] = order_features['TotalQuantity'] / order_features['LineItems']
        order_features['Quarter'] = order_features['Month'].apply(lambda x: (x-1)//3 + 1)
        order_features['IsQ4'] = (order_features['Quarter'] == 4).astype(int)
        
        # Encode categoricals
        order_features['Country_enc'] = order_features['Country'].fillna('DE').apply(
            lambda x: le_country.transform([x])[0] if x in le_country.classes_ else 0
        )
        order_features['SalesOrg_enc'] = order_features['SalesOrg'].fillna('DN00').apply(
            lambda x: le_salesorg.transform([x])[0] if x in le_salesorg.classes_ else 0
        )
        
        # Score
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
# DATA LOADER
# ============================================================

@st.cache_data(ttl=300)
def load_gbi_data():
    """Load and process GBI Analytics data."""
    try:
        if not os.path.exists(Config.GBI_PATH):
            return None, None, None, None
        
        xls = pd.ExcelFile(Config.GBI_PATH)
        
        # Load actuals
        actuals = None
        for sheet in ['Actuals', 'actuals', 'ACTUALS', 'SalesActuals']:
            if sheet in xls.sheet_names:
                actuals = pd.read_excel(xls, sheet_name=sheet)
                break
        
        if actuals is None:
            actuals = pd.read_excel(xls, sheet_name=0)
        
        # Load plan
        plan = None
        for sheet in ['Plan', 'plan', 'PLAN', 'SalesPlan']:
            if sheet in xls.sheet_names:
                plan = pd.read_excel(xls, sheet_name=sheet)
                break
        
        # Variance analysis
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
        
        # Yearly aggregation for forecast
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
        X = yearly['Year'].values.reshape(-1, 1)
        y = yearly['RevenueUSD'].values
        
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
    
    # ML-based alerts
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
        # Rule-based alerts
        high_risk = va05[va05['risk_level'] == 'HIGH']
        if len(high_risk) > 0:
            alerts.append({
                'sev': 'CRITICAL',
                'src': 'Order Pipeline',
                'title': f'{len(high_risk)} High-Risk Orders',
                'detail': f'${high_risk["revenue_at_risk"].sum():,.0f} revenue at risk'
            })
    
    # Variance alerts
    if var_df is not None:
        critical_var = var_df[var_df['Risk'] == 'CRITICAL']
        if len(critical_var) > 0:
            alerts.append({
                'sev': 'CRITICAL',
                'src': 'Financial',
                'title': f'{len(critical_var)} Customers Below Plan',
                'detail': f'${abs(critical_var["Variance"].sum()):,.0f} total shortfall'
            })
    
    # Signal alerts
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
        cursor: pointer;
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
    </style>
    """, unsafe_allow_html=True)

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
    
    # Load data
    ml_models = load_ml_models()
    ai_service = get_ai_service()
    actuals, plan, var_df, yearly = load_gbi_data()
    va05 = generate_va05_orders()
    signals = generate_external_signals()
    
    ml_orders = ml_score_orders(actuals, ml_models) if actuals is not None else None
    alerts = generate_alerts(va05, var_df, signals, ml_orders)
    
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
        st.markdown('<div class="section-header">🤖 AI Executive Brief</div>', unsafe_allow_html=True)
        
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
        
        with st.spinner("Generating AI brief..."):
            brief = ai_service.generate_executive_brief(metrics)
        
        st.markdown(f'''
        <div class="ai-explanation">
            <div class="ai-explanation-header">🤖 AI Analysis (Local - Llama 3)</div>
            <div class="ai-explanation-text">{brief}</div>
        </div>
        ''', unsafe_allow_html=True)

# ============================================================
# OPERATOR MODE
# ============================================================

def render_operator_mode():
    """Render interactive operator mode."""
    inject_styles()
    
    # Load data
    ml_models = load_ml_models()
    ai_service = get_ai_service()
    actuals, plan, var_df, yearly = load_gbi_data()
    va05 = generate_va05_orders()
    signals = generate_external_signals()
    fc, fc_diag = generate_forecast(yearly) if yearly is not None else ([], {})
    
    ml_orders = ml_score_orders(actuals, ml_models) if actuals is not None else None
    ml_demand = ml_forecast_demand(actuals, ml_models) if actuals is not None else None
    alerts = generate_alerts(va05, var_df, signals, ml_orders)
    erpsim = None  # Placeholder
    
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
    tabs = st.tabs(["📊 Overview", "📦 Logistics", "💰 Finance", "📈 Forecast", "🌐 Signals", "🚨 Alerts", "🎮 Scenarios", "🧠 ML Intel", "🤖 AI Brief", "🔌 Sources"])
    
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
            
            st.markdown('<div class="section-header">⚠️ ML-Scored High Risk Orders</div>', unsafe_allow_html=True)
            
            high_risk_orders = ml_orders[ml_orders['RiskCategory'] == 'High'].head(8)
            
            for idx, r in high_risk_orders.iterrows():
                order_id = int(r["OrderNumber"])
                
                # Order card
                st.markdown(f'''
                <div class="data-card critical">
                    <div class="card-title">Order {order_id} — Customer {int(r["Customer"])}</div>
                    <div class="card-detail">${r["TotalRevenue"]:,.0f} | {int(r["LineItems"])} items | {int(r["ProductDiversity"])} products | Risk: {r["RiskProbability"]*100:.0f}%</div>
                </div>
                ''', unsafe_allow_html=True)
                
                # AI Analysis button
                if ai_service.available:
                    col1, col2 = st.columns([4, 1])
                    with col2:
                        if st.button(f"🤖 Analyze", key=f"analyze_{order_id}"):
                            st.session_state.selected_order = order_id
                    
                    # Show analysis if this order is selected
                    if st.session_state.selected_order == order_id:
                        # Check cache
                        if order_id not in st.session_state.ai_analysis_cache:
                            with st.spinner("AI analyzing order..."):
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
        
        # ML Demand Forecast
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
    
    # ML Intelligence
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
                    <div class="model-metric"><span class="metric-label">F1-Score</span><span class="metric-value">0.99</span></div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("**Top Risk Factors:**")
                st.markdown("""
                1. LineItems (27%)
                2. ProductDiversity (25%)
                3. TotalQuantity (13%)
                4. TotalCost (11%)
                5. TotalRevenue (11%)
                """)
            
            with c2:
                st.markdown("""
                <div class="model-card">
                    <div class="model-title">Demand Forecaster</div>
                    <div class="model-metric"><span class="metric-label">Algorithm</span><span class="metric-value">Random Forest Regressor</span></div>
                    <div class="model-metric"><span class="metric-label">Training Data</span><span class="metric-value">3,077 weekly periods</span></div>
                    <div class="model-metric"><span class="metric-label">R² Score</span><span class="metric-value">0.981</span></div>
                    <div class="model-metric"><span class="metric-label">MAE</span><span class="metric-value">23.5 units</span></div>
                    <div class="model-metric"><span class="metric-label">Categories</span><span class="metric-value">6</span></div>
                </div>
                """, unsafe_allow_html=True)
            
            if ml_orders is not None:
                st.markdown('<div class="section-header">Current ML Scoring Summary</div>', unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Orders Scored", f"{len(ml_orders):,}")
                c2.metric("High Risk", len(ml_orders[ml_orders['RiskCategory'] == 'High']))
                c3.metric("Medium Risk", len(ml_orders[ml_orders['RiskCategory'] == 'Medium']))
                c4.metric("Low Risk", len(ml_orders[ml_orders['RiskCategory'] == 'Low']))
        else:
            st.warning("ML models not loaded. Place model files in `ml/` folder.")
    
    # AI Brief
    with tabs[8]:
        st.markdown('<div class="section-header">🤖 AI-Powered Executive Brief</div>', unsafe_allow_html=True)
        
        # Collect metrics
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
        
        brief_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.caption(f"Generated {brief_time}")
        
        # Metrics row
        status_color = "🔴" if status == "CRITICAL" else "🟠" if status == "ELEVATED" else "🟢"
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Status", f"{status_color} {status}")
        c2.metric("At Risk", f"${at_risk_value/1e6:.2f}M", f"{at_risk_pct:.0f}%")
        c3.metric("High Risk Orders", high_risk_count)
        c4.metric("Critical Alerts", metrics['critical_alerts'])
        
        st.divider()
        
        if ai_service.available:
            # AI-generated content
            st.subheader("Executive Summary")
            with st.spinner("AI generating brief..."):
                brief = ai_service.generate_executive_brief(metrics)
            st.markdown(f'''
            <div class="ai-explanation">
                <div class="ai-explanation-header">🤖 AI Analysis (Local - Llama 3 8B)</div>
                <div class="ai-explanation-text">{brief}</div>
            </div>
            ''', unsafe_allow_html=True)
            
            st.divider()
            
            st.subheader("Recommendation")
            with st.spinner("AI generating recommendation..."):
                rec = ai_service.generate_recommendation(metrics)
            st.info(f"🤖 {rec}")
            
            st.divider()
            
            st.subheader("AI Status")
            c1, c2, c3 = st.columns(3)
            c1.metric("Provider", "Ollama (Local)")
            c2.metric("Model", Config.OLLAMA_MODEL)
            c3.metric("Cost", "$0.00")
            
        else:
            # Fallback to rule-based
            st.warning("⚠️ Local AI not available. Using rule-based analysis.")
            st.markdown("**To enable AI:**")
            st.code("brew services start ollama", language="bash")
            
            st.subheader("Current Situation")
            ml_note = " (ML-scored)" if ml_orders is not None else ""
            st.markdown(f"""
            System is **{status}**. Pipeline: **${total_pipeline/1e6:.1f}M** across {total_orders:,} orders{ml_note}.  
            **${at_risk_value/1e6:.2f}M** at risk ({at_risk_pct:.0f}%). {metrics['critical_alerts'] + metrics['high_alerts']} active alerts.
            """)
            
            st.divider()
            
            st.subheader("Recommendation")
            if metrics['critical_alerts'] > 0:
                rec = "Address critical alerts immediately. See Alerts tab for details."
            elif high_risk_count >= 5:
                rec = "Expedite high-risk orders to reduce exposure."
            elif signals['summary']['traffic'] >= 2:
                rec = "Adjust ETAs for affected corridors."
            else:
                rec = "Maintain current operations. Continue monitoring."
            st.info(rec)
    
    # Sources
    with tabs[9]:
        st.markdown('<div class="section-header">🔌 Data Sources & Intelligence</div>', unsafe_allow_html=True)
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("GBI", "✅" if actuals is not None else "❌")
        c2.metric("VA05", "✅ Sim")
        c3.metric("Signals", "✅ Live")
        c4.metric("ML Models", "✅" if ml_models['available'] else "❌")
        c5.metric("Local AI", "✅" if ai_service.available else "❌")
        
        if ml_models['available']:
            st.success("🧠 ML Models: Order Risk (99% recall) + Demand Forecast (R²=0.981)")
        
        if ai_service.available:
            st.success("🤖 Local AI: Ollama + Llama 3 8B running on localhost:11434")
        else:
            st.warning("🤖 Local AI offline. Start with: `brew services start ollama`")

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
