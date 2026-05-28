"""
AABS Control Tower v5.3
Enterprise Decision Intelligence Platform

v5.3 CHANGES (Workshop & Demo Upgrades):
- Scenario Packs: One-click preset scenarios (Supply Shock, Recession, etc.)
- Executive Brief Generator: One-page summary for leadership
- AABS Case Mode: Named case studies for teaching (Amazon Q4 Miss, etc.)
- All v5.2 features preserved (validation, safety toggles)
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION
# ============================================================

class Config:
    APP_NAME = "AABS Control Tower"
    VERSION = "5.3"
    # Use relative paths from app.py location
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    GBI_PATH = os.path.join(_BASE_DIR, 'uploads', 'GB_AnalyticsData.xlsx')
    ERPSIM_PATH = os.path.join(_BASE_DIR, 'uploads', 'ERPSIM.xlsx')
    AUTO_REFRESH_INTERVAL = 30
    CRITICAL_THRESHOLD = -20
    HIGH_THRESHOLD = -10
    MEDIUM_THRESHOLD = -5

# ============================================================
# SCENARIO PACKS (NEW in v5.3)
# ============================================================

SCENARIO_PACKS = {
    "-- Select Pack --": [],
    "🔥 Supply Shock": ["Steel +20%", "Fuel +30%"],
    "📉 Recession": ["Recession -15%"],
    "🚀 Expansion": ["Expansion +10%"],
    "⚠️ Perfect Storm": ["Steel +20%", "Fuel +30%", "Recession -15%"],
    "🎯 Stress Test": ["Steel +20%", "Fuel +30%", "Recession -15%", "Expansion +10%"],
}

# ============================================================
# AABS CASE MODE (NEW in v5.3)
# ============================================================

AABS_CASES = {
    "-- No Case Selected --": {
        "subtitle": "Enterprise Decision Intelligence Platform",
        "context": None,
        "signals_modifier": None,
    },
    "📦 Amazon Q4 Miss": {
        "subtitle": "Case Study: When forecasts diverge from fulfillment reality",
        "context": """**Scenario:** It's Q4 2024. Revenue forecasts show strong holiday demand, but 
        distribution center satellite data shows declining activity. Traffic data shows logistics 
        corridors are clear — suspiciously clear. What's really happening?""",
        "signals_modifier": {"satellite_bias": -15, "traffic_bias": -0.3},
    },
    "🚗 Auto Supply Chain Crisis": {
        "subtitle": "Case Study: Semiconductor shortage cascades through operations",
        "context": """**Scenario:** Steel prices surge 20%, fuel costs spike. Your customers are auto 
        manufacturers who can't get chips. Orders are on the books but fulfillment is stalled. 
        How do you advise leadership?""",
        "signals_modifier": {"market_bias": 15, "satellite_bias": -10},
    },
    "📈 CESIM Turnaround": {
        "subtitle": "Case Study: From 33% to 56% gross margin in one quarter",
        "context": """**Scenario:** Your team inherited a struggling operation — production geography 
        misaligned with demand, capacity allocated to wrong products. You have one quarter to 
        turn it around. What levers do you pull?""",
        "signals_modifier": None,
    },
    "🏪 Retail Demand Collapse": {
        "subtitle": "Case Study: When satellite data contradicts sales forecasts",
        "context": """**Scenario:** Finance shows plan achievement at 105%. But satellite monitoring 
        of key retail DCs shows parking lot activity down 20%. Consumer confidence is tanking. 
        Is the forecast wrong, or is reality about to catch up?""",
        "signals_modifier": {"satellite_bias": -20, "market_bias": -10},
    },
}

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title=f"{Config.APP_NAME} v{Config.VERSION}",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# IMPORTS WITH FALLBACK
# ============================================================

try:
    import plotly.express as px
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
    from api_integration import ExternalDataAggregator, get_external_data
    API_MODULE_AVAILABLE = True
except ImportError:
    API_MODULE_AVAILABLE = False

# ============================================================
# SESSION STATE
# ============================================================

if 'refresh_count' not in st.session_state:
    st.session_state.refresh_count = 0
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if 'va05_validated' not in st.session_state:
    st.session_state.va05_validated = None
if 'selected_case' not in st.session_state:
    st.session_state.selected_case = "-- No Case Selected --"
if 'scenario_pack' not in st.session_state:
    st.session_state.scenario_pack = "-- Select Pack --"

# ============================================================
# STYLING
# ============================================================

st.markdown("""
<style>
    .live-indicator {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 4px 12px; background: #dcfce7; border-radius: 20px;
        font-size: 12px; color: #166534;
    }
    .live-dot {
        width: 8px; height: 8px; background: #22c55e;
        border-radius: 50%; animation: pulse 2s infinite;
    }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    .validation-pass { background: #dcfce7; border: 1px solid #22c55e; padding: 10px; border-radius: 8px; }
    .validation-fail { background: #fee2e2; border: 1px solid #ef4444; padding: 10px; border-radius: 8px; }
    .data-quality-box { background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 8px; margin: 10px 0; }
    .case-context { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 0 8px 8px 0; margin: 16px 0; }
    .exec-brief { background: #f8fafc; border: 1px solid #e2e8f0; padding: 20px; border-radius: 8px; font-family: 'Georgia', serif; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# VA05 DATA - REAL (from SAP PDF) with VALIDATION
# ============================================================

VA05_EXPECTED = {
    "total_value": 746357.50,
    "total_qty": 258,
    "dxtr_qty": 191,
    "prtr_qty": 67,
}

VA05_REAL_ORDERS = [
    {"ref": "Z999", "date": "2016-05-27", "doc": 1, "customer": 5999, "material": "DXTR1999", "qty": 2, "value": 6000.00},
    {"ref": "Z998", "date": "2016-05-27", "doc": 2, "customer": 5998, "material": "DXTR1998", "qty": 5, "value": 15000.00},
    {"ref": "Z997", "date": "2016-05-27", "doc": 3, "customer": 5997, "material": "DXTR1997", "qty": 8, "value": 24000.00},
    {"ref": "163", "date": "2025-09-30", "doc": 4, "customer": 25005, "material": "DXTR1163", "qty": 5, "value": 14012.50},
    {"ref": "163", "date": "2025-09-30", "doc": 4, "customer": 25005, "material": "PRTR1163", "qty": 2, "value": 6080.00},
    {"ref": "152", "date": "2025-09-30", "doc": 5, "customer": 25006, "material": "DXTR1152", "qty": 5, "value": 14012.50},
    {"ref": "152", "date": "2025-09-30", "doc": 5, "customer": 25006, "material": "PRTR1152", "qty": 2, "value": 6080.00},
    {"ref": "148", "date": "2025-10-01", "doc": 6, "customer": 25007, "material": "DXTR1148", "qty": 5, "value": 14012.50},
    {"ref": "148", "date": "2025-10-01", "doc": 6, "customer": 25007, "material": "PRTR1148", "qty": 2, "value": 6080.00},
    {"ref": "101", "date": "2025-10-01", "doc": 7, "customer": 25008, "material": "DXTR1101", "qty": 5, "value": 14012.50},
    {"ref": "101", "date": "2025-10-01", "doc": 7, "customer": 25008, "material": "PRTR1101", "qty": 2, "value": 6080.00},
    {"ref": "811", "date": "2025-10-02", "doc": 8, "customer": 25010, "material": "PRTR1811", "qty": 2, "value": 6080.00},
    {"ref": "811", "date": "2025-10-02", "doc": 8, "customer": 25010, "material": "DXTR1811", "qty": 5, "value": 14012.50},
    {"ref": "811", "date": "2025-10-02", "doc": 9, "customer": 25010, "material": "PRTR1811", "qty": 2, "value": 6080.00},
    {"ref": "811", "date": "2025-10-02", "doc": 9, "customer": 25010, "material": "DXTR1811", "qty": 5, "value": 14012.50},
    {"ref": "144", "date": "2025-10-02", "doc": 10, "customer": 25012, "material": "PRTR1144", "qty": 2, "value": 6080.00},
    {"ref": "144", "date": "2025-10-02", "doc": 10, "customer": 25012, "material": "DXTR1144", "qty": 5, "value": 14012.50},
    {"ref": "161", "date": "2025-10-02", "doc": 11, "customer": 25014, "material": "PRTR1161", "qty": 2, "value": 6080.00},
    {"ref": "161", "date": "2025-10-02", "doc": 11, "customer": 25014, "material": "DXTR1161", "qty": 5, "value": 14012.50},
    {"ref": "160", "date": "2025-10-03", "doc": 12, "customer": 25013, "material": "PRTR1160", "qty": 2, "value": 6080.00},
    {"ref": "160", "date": "2025-10-03", "doc": 12, "customer": 25013, "material": "DXTR1160", "qty": 5, "value": 14012.50},
    {"ref": "140", "date": "2025-10-03", "doc": 13, "customer": 25011, "material": "PRTR1140", "qty": 2, "value": 6080.00},
    {"ref": "140", "date": "2025-10-03", "doc": 13, "customer": 25011, "material": "DXTR1140", "qty": 5, "value": 14012.50},
    {"ref": "151", "date": "2025-10-03", "doc": 14, "customer": 25015, "material": "DXTR1151", "qty": 5, "value": 14012.50},
    {"ref": "151", "date": "2025-10-03", "doc": 14, "customer": 25015, "material": "PRTR1151", "qty": 2, "value": 6080.00},
    {"ref": "158", "date": "2025-10-03", "doc": 15, "customer": 25016, "material": "DXTR1158", "qty": 5, "value": 14012.50},
    {"ref": "158", "date": "2025-10-03", "doc": 15, "customer": 25016, "material": "PRTR1158", "qty": 2, "value": 6080.00},
    {"ref": "147", "date": "2025-10-04", "doc": 16, "customer": 25018, "material": "DXTR1147", "qty": 5, "value": 14012.50},
    {"ref": "147", "date": "2025-10-04", "doc": 16, "customer": 25018, "material": "PRTR1147", "qty": 2, "value": 6080.00},
    {"ref": "167", "date": "2025-10-04", "doc": 17, "customer": 25019, "material": "DXTR1167", "qty": 5, "value": 14012.50},
    {"ref": "167", "date": "2025-10-04", "doc": 17, "customer": 25019, "material": "PRTR1167", "qty": 2, "value": 6080.00},
    {"ref": "142", "date": "2025-10-05", "doc": 18, "customer": 25021, "material": "DXTR1142", "qty": 2, "value": 6000.00},
    {"ref": "142", "date": "2025-10-05", "doc": 18, "customer": 25021, "material": "DXTR1142", "qty": 5, "value": 15000.00},
    {"ref": "156", "date": "2025-10-05", "doc": 19, "customer": 25022, "material": "DXTR1156", "qty": 5, "value": 14012.50},
    {"ref": "156", "date": "2025-10-05", "doc": 19, "customer": 25022, "material": "PRTR1156", "qty": 2, "value": 6080.00},
    {"ref": "145", "date": "2025-10-05", "doc": 20, "customer": 25020, "material": "DXTR1145", "qty": 5, "value": 14012.50},
    {"ref": "145", "date": "2025-10-05", "doc": 20, "customer": 25020, "material": "PRTR1145", "qty": 2, "value": 6080.00},
    {"ref": "141", "date": "2025-10-06", "doc": 21, "customer": 25017, "material": "PRTR1141", "qty": 2, "value": 6400.00},
    {"ref": "141", "date": "2025-10-06", "doc": 21, "customer": 25017, "material": "DXTR1141", "qty": 5, "value": 14750.00},
    {"ref": "168", "date": "2025-10-06", "doc": 22, "customer": 25026, "material": "DXTR1168", "qty": 5, "value": 14012.50},
    {"ref": "168", "date": "2025-10-06", "doc": 22, "customer": 25026, "material": "PRTR1168", "qty": 2, "value": 6080.00},
    {"ref": "149", "date": "2025-10-06", "doc": 23, "customer": 25025, "material": "DXTR1149", "qty": 2, "value": 6000.00},
    {"ref": "149", "date": "2025-10-06", "doc": 23, "customer": 25025, "material": "DXTR1149", "qty": 5, "value": 15000.00},
    {"ref": "154", "date": "2025-10-06", "doc": 24, "customer": 25027, "material": "DXTR1154", "qty": 5, "value": 14012.50},
    {"ref": "154", "date": "2025-10-06", "doc": 24, "customer": 25027, "material": "PRTR1154", "qty": 2, "value": 6080.00},
    {"ref": "165", "date": "2025-10-06", "doc": 25, "customer": 25028, "material": "DXTR1165", "qty": 5, "value": 14012.50},
    {"ref": "165", "date": "2025-10-06", "doc": 25, "customer": 25028, "material": "PRTR1165", "qty": 2, "value": 6080.00},
    {"ref": "162", "date": "2025-10-06", "doc": 26, "customer": 25029, "material": "PRTR1162", "qty": 2, "value": 6080.00},
    {"ref": "162", "date": "2025-10-06", "doc": 26, "customer": 25029, "material": "DXTR1162", "qty": 5, "value": 14012.50},
    {"ref": "143", "date": "2025-10-06", "doc": 27, "customer": 25023, "material": "PRTR1143", "qty": 2, "value": 6080.00},
    {"ref": "143", "date": "2025-10-06", "doc": 27, "customer": 25023, "material": "DXTR1143", "qty": 5, "value": 14012.50},
    {"ref": "150", "date": "2025-10-06", "doc": 28, "customer": 25033, "material": "PRTR1150", "qty": 2, "value": 6080.00},
    {"ref": "150", "date": "2025-10-06", "doc": 28, "customer": 25033, "material": "DXTR1150", "qty": 5, "value": 14012.50},
    {"ref": "157", "date": "2025-10-07", "doc": 29, "customer": 25024, "material": "DXTR1157", "qty": 5, "value": 14012.50},
    {"ref": "157", "date": "2025-10-07", "doc": 29, "customer": 25024, "material": "PRTR1157", "qty": 2, "value": 6080.00},
    {"ref": "166", "date": "2025-10-07", "doc": 30, "customer": 25035, "material": "DXTR1166", "qty": 5, "value": 14012.50},
    {"ref": "166", "date": "2025-10-07", "doc": 30, "customer": 25035, "material": "PRTR1166", "qty": 2, "value": 6080.00},
    {"ref": "169", "date": "2025-10-07", "doc": 31, "customer": 25037, "material": "DXTR1169", "qty": 5, "value": 14012.50},
    {"ref": "169", "date": "2025-10-07", "doc": 31, "customer": 25037, "material": "PRTR1169", "qty": 2, "value": 6080.00},
    {"ref": "159", "date": "2025-10-07", "doc": 32, "customer": 25038, "material": "DXTR1159", "qty": 5, "value": 14012.50},
    {"ref": "159", "date": "2025-10-07", "doc": 32, "customer": 25038, "material": "DXTR1159", "qty": 2, "value": 5700.00},
    {"ref": "153", "date": "2025-10-07", "doc": 33, "customer": 25034, "material": "DXTR1153", "qty": 5, "value": 14012.50},
    {"ref": "153", "date": "2025-10-07", "doc": 33, "customer": 25034, "material": "PRTR1153", "qty": 2, "value": 6080.00},
    {"ref": "110", "date": "2025-10-07", "doc": 34, "customer": 25039, "material": "DXTR1110", "qty": 5, "value": 15000.00},
    {"ref": "110", "date": "2025-10-07", "doc": 34, "customer": 25039, "material": "PRTR1110", "qty": 2, "value": 6400.00},
    {"ref": "Serena1", "date": "2025-10-20", "doc": 38, "customer": 25038, "material": "DXTR1110", "qty": 10, "value": 26000.00},
    {"ref": "Serena1", "date": "2025-10-20", "doc": 38, "customer": 25038, "material": "PRTR1110", "qty": 8, "value": 24240.00},
    {"ref": "Serena2", "date": "2025-10-20", "doc": 39, "customer": 25038, "material": "DXTR1110", "qty": 5, "value": 15150.00},
    {"ref": "Serena2", "date": "2025-10-20", "doc": 39, "customer": 25038, "material": "PRTR1110", "qty": 3, "value": 9300.00},
]

def validate_va05() -> Dict:
    """Validate VA05 data against expected totals from PDF."""
    try:
        total_value = sum(o['value'] for o in VA05_REAL_ORDERS)
        total_qty = sum(o['qty'] for o in VA05_REAL_ORDERS)
        dxtr_qty = sum(o['qty'] for o in VA05_REAL_ORDERS if 'DXTR' in o['material'])
        prtr_qty = sum(o['qty'] for o in VA05_REAL_ORDERS if 'PRTR' in o['material'])
        
        value_ok = abs(total_value - VA05_EXPECTED['total_value']) < 0.01
        qty_ok = total_qty == VA05_EXPECTED['total_qty']
        dxtr_ok = dxtr_qty == VA05_EXPECTED['dxtr_qty']
        prtr_ok = prtr_qty == VA05_EXPECTED['prtr_qty']
        
        all_valid = value_ok and qty_ok and dxtr_ok and prtr_ok
        dates = [o['date'] for o in VA05_REAL_ORDERS]
        unique_docs = len(set(o['doc'] for o in VA05_REAL_ORDERS))
        
        return {
            'valid': all_valid,
            'checks': {
                'total_value': {'actual': total_value, 'expected': VA05_EXPECTED['total_value'], 'pass': value_ok},
                'total_qty': {'actual': total_qty, 'expected': VA05_EXPECTED['total_qty'], 'pass': qty_ok},
                'dxtr_qty': {'actual': dxtr_qty, 'expected': VA05_EXPECTED['dxtr_qty'], 'pass': dxtr_ok},
                'prtr_qty': {'actual': prtr_qty, 'expected': VA05_EXPECTED['prtr_qty'], 'pass': prtr_ok},
            },
            'quality': {
                'line_items': len(VA05_REAL_ORDERS),
                'unique_docs': unique_docs,
                'date_min': min(dates),
                'date_max': max(dates),
                'legacy_orders': len([o for o in VA05_REAL_ORDERS if o['date'].startswith('2016')]),
            },
            'error': None
        }
    except Exception as e:
        return {'valid': False, 'checks': {}, 'quality': {}, 'error': str(e)}

def get_real_va05_data() -> pd.DataFrame:
    """Get validated real VA05 data as DataFrame with risk scoring."""
    df = pd.DataFrame(VA05_REAL_ORDERS)
    df['date'] = pd.to_datetime(df['date'])
    df['product_type'] = df['material'].apply(lambda x: 'DXTR' if 'DXTR' in x else 'PRTR')
    
    today = datetime(2025, 10, 25)
    df['days_old'] = (today - df['date']).dt.days
    df['age_risk'] = df['days_old'].apply(lambda d: 0.9 if d > 20 else 0.7 if d > 10 else 0.5 if d > 5 else 0.3)
    df['value_risk'] = df['value'].apply(lambda v: 0.8 if v > 20000 else 0.6 if v > 10000 else 0.4)
    df['late_prob'] = ((df['age_risk'] + df['value_risk']) / 2).round(2)
    df['risk_level'] = df['late_prob'].apply(lambda p: 'HIGH' if p >= 0.7 else 'MEDIUM' if p >= 0.5 else 'LOW')
    df['revenue_at_risk'] = (df['value'] * df['late_prob']).round(2)
    
    return df

def get_sample_va05_data() -> pd.DataFrame:
    """Generate sample VA05 data as fallback."""
    np.random.seed(42)
    n = 15
    df = pd.DataFrame({
        'ref': [f"SAMPLE-{i}" for i in range(1, n+1)],
        'date': pd.date_range(start='2025-10-01', periods=n, freq='D'),
        'doc': range(1, n+1),
        'customer': np.random.choice([25005, 25006, 25007, 25008, 25010], n),
        'material': np.random.choice(['DXTR1163', 'DXTR1152', 'PRTR1163', 'PRTR1152'], n),
        'qty': np.random.randint(2, 10, n),
        'value': np.random.uniform(5000, 20000, n).round(2),
    })
    df['product_type'] = df['material'].apply(lambda x: 'DXTR' if 'DXTR' in x else 'PRTR')
    df['days_old'] = np.random.randint(1, 15, n)
    df['late_prob'] = np.random.uniform(0.3, 0.8, n).round(2)
    df['risk_level'] = df['late_prob'].apply(lambda p: 'HIGH' if p >= 0.7 else 'MEDIUM' if p >= 0.5 else 'LOW')
    df['revenue_at_risk'] = (df['value'] * df['late_prob']).round(2)
    return df

# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data(ttl=300)
def load_gbi_data(path):
    try:
        if not os.path.exists(path):
            return None, None
        actuals = pd.read_excel(path, sheet_name='SalesdataAct')
        plan = pd.read_excel(path, sheet_name='SalesdataPlan')
        return actuals, plan
    except Exception as e:
        return None, None

@st.cache_data(ttl=300)
def load_erpsim_data(path):
    try:
        if not os.path.exists(path):
            return None
        df = pd.read_excel(path, sheet_name='Sheet1')
        if 'Team' in df.columns:
            df['Team'] = df['Team'].str.strip()
        return df
    except Exception as e:
        return None

# ============================================================
# EXTERNAL SIGNALS (with Case Mode modifier)
# ============================================================

def get_all_signals(case_modifier: Dict = None) -> Dict:
    """Get external signals with optional case-based modifications."""
    seed = int(datetime.now().timestamp()) % 10000
    np.random.seed(seed)
    
    satellite_bias = case_modifier.get('satellite_bias', 0) if case_modifier else 0
    traffic_bias = case_modifier.get('traffic_bias', 0) if case_modifier else 0
    market_bias = case_modifier.get('market_bias', 0) if case_modifier else 0
    
    corridors = [
        {'name': 'I-710 (LA Port)', 'region': 'West', 'baseline': 90},
        {'name': 'I-5 South (SD Border)', 'region': 'West', 'baseline': 120},
        {'name': 'I-10 East (AZ)', 'region': 'Southwest', 'baseline': 270},
        {'name': 'I-95 North (East Coast)', 'region': 'East', 'baseline': 360},
        {'name': 'I-80 (Midwest)', 'region': 'Central', 'baseline': 480},
        {'name': 'I-45 (Houston)', 'region': 'South', 'baseline': 180},
    ]
    
    traffic = []
    hour = datetime.now().hour
    for c in corridors:
        if 7 <= hour <= 9 or 16 <= hour <= 18:
            factor = 1.3 + np.random.uniform(0, 0.7)
        elif 22 <= hour or hour <= 5:
            factor = 0.8 + np.random.uniform(0, 0.2)
        else:
            factor = 1.0 + np.random.uniform(-0.1, 0.5)
        if np.random.random() < 0.1:
            factor *= 1.5
        factor += traffic_bias
        factor = max(0.5, factor)
        level = 'severe' if factor > 2.0 else 'heavy' if factor > 1.5 else 'moderate' if factor > 1.2 else 'normal'
        traffic.append({
            'corridor': c['name'], 'region': c['region'],
            'delay_ratio': round(factor, 2), 'level': level,
            'status': '🔴' if level == 'severe' else '🟠' if level == 'heavy' else '🟡' if level == 'moderate' else '🟢',
            'delay_min': round((factor - 1) * c['baseline'], 0),
        })
    
    locations = [
        {'name': 'Walmart DC - Ontario, CA', 'customer': 6000, 'baseline': 75},
        {'name': 'Target DC - Fontana, CA', 'customer': 1000, 'baseline': 70},
        {'name': 'Costco Regional - Phoenix', 'customer': 12000, 'baseline': 80},
        {'name': 'Amazon FC - San Bernardino', 'customer': 9000, 'baseline': 85},
        {'name': 'Home Depot DC - Dallas', 'customer': 4000, 'baseline': 65},
    ]
    satellite = []
    for loc in locations:
        delta = np.random.uniform(-25, 15) + satellite_bias
        current = max(20, min(98, loc['baseline'] + delta))
        signal = 'demand_drop' if delta < -15 else 'slight_decline' if delta < -5 else 'demand_surge' if delta > 10 else 'normal'
        satellite.append({
            'location': loc['name'], 'customer_id': loc['customer'],
            'current': round(current, 1), 'delta': round(delta, 1), 'signal': signal,
            'risk': 'HIGH' if signal == 'demand_drop' else 'MEDIUM' if signal == 'slight_decline' else 'LOW',
            'status': '🔴' if signal == 'demand_drop' else '🟡' if signal == 'slight_decline' else '🟢',
        })
    
    indicators = [
        {'name': 'Steel (HRC)', 'category': 'Commodity'},
        {'name': 'Diesel Fuel', 'category': 'Energy'},
        {'name': 'Container Rates', 'category': 'Shipping'},
        {'name': 'USD/EUR', 'category': 'Currency'},
        {'name': 'Consumer Confidence', 'category': 'Economic'},
    ]
    market = []
    for ind in indicators:
        change = np.random.uniform(-15, 20) + market_bias
        is_cost = ind['category'] in ['Commodity', 'Energy', 'Shipping']
        impact = 'negative' if (is_cost and change > 5) or (not is_cost and change < -5) else \
                 'positive' if (is_cost and change < -5) or (not is_cost and change > 5) else 'neutral'
        margin = -abs(change) * 0.25 if impact == 'negative' else abs(change) * 0.2 if impact == 'positive' else 0
        market.append({
            'indicator': ind['name'], 'category': ind['category'],
            'change_pct': round(change, 1), 'impact': impact, 'margin_impact': round(margin, 1),
            'status': '🔴' if impact == 'negative' else '🟢' if impact == 'positive' else '⚪',
        })
    
    t_alerts = len([t for t in traffic if t['level'] in ['severe', 'heavy']])
    s_alerts = len([s for s in satellite if s['signal'] in ['demand_drop', 'slight_decline']])
    m_alerts = len([m for m in market if m['impact'] == 'negative'])
    risk = 'CRITICAL' if t_alerts >= 2 or s_alerts >= 3 else 'ELEVATED' if t_alerts >= 1 or s_alerts >= 2 else 'NORMAL'
    
    return {
        'traffic': traffic, 'satellite': satellite, 'market': market,
        'summary': {'traffic_alerts': t_alerts, 'satellite_alerts': s_alerts, 'market_alerts': m_alerts, 'overall_risk': risk}
    }

# ============================================================
# ANALYTICS
# ============================================================

def compute_variance(actuals, plan, year):
    try:
        act = actuals[actuals['Year'] == year]
        pln = plan[plan['YEAR'] == year]
        if len(act) == 0 or len(pln) == 0:
            return pd.DataFrame()
        actual_agg = act.groupby('Customer')['RevenueUSD'].sum().reset_index()
        actual_agg.columns = ['Customer', 'Actual']
        plan_agg = pln.groupby('Customer')['RevenuePlan'].sum().reset_index()
        plan_agg.columns = ['Customer', 'Plan']
        merged = actual_agg.merge(plan_agg, on='Customer', how='outer').fillna(0)
        merged['Variance'] = merged['Actual'] - merged['Plan']
        merged['VarPct'] = merged.apply(lambda r: (r['Variance']/r['Plan']*100) if r['Plan'] > 0 else 0, axis=1)
        def risk(pct):
            if pct < Config.CRITICAL_THRESHOLD: return 'CRITICAL'
            if pct < Config.HIGH_THRESHOLD: return 'HIGH'
            if pct < Config.MEDIUM_THRESHOLD: return 'MEDIUM'
            return 'LOW'
        merged['Risk'] = merged['VarPct'].apply(risk)
        return merged.sort_values('Variance')
    except:
        return pd.DataFrame()

def compute_yearly(actuals):
    yearly = actuals.groupby('Year').agg({'RevenueUSD': 'sum', 'CostsUSD': 'sum'}).reset_index()
    yearly['Margin'] = (yearly['RevenueUSD'] - yearly['CostsUSD']) / yearly['RevenueUSD'] * 100
    yearly['YoY'] = yearly['RevenueUSD'].pct_change() * 100
    return yearly

def forecast(yearly, years_ahead=3):
    yrs = yearly['Year'].values
    revs = yearly['RevenueUSD'].values
    max_yr = int(yrs.max())
    
    if SCIPY_AVAILABLE:
        slope, intercept, r, _, _ = stats.linregress(yrs, revs)
        r2 = r ** 2
    else:
        slope = (revs[-1] - revs[0]) / (yrs[-1] - yrs[0])
        intercept = revs[-1] - slope * yrs[-1]
        r2 = 0.7
    
    linear_fc = [slope * (max_yr + i + 1) + intercept for i in range(years_ahead)]
    avg_growth = yearly['YoY'].dropna().mean() / 100 if 'YoY' in yearly.columns else 0.03
    growth_fc = [revs[-1] * (1 + avg_growth) ** (i + 1) for i in range(years_ahead)]
    
    results = []
    for i in range(years_ahead):
        fc = 0.6 * linear_fc[i] + 0.4 * growth_fc[i]
        std = np.std([linear_fc[i], growth_fc[i]]) * (1 + i * 0.2)
        results.append({
            'Year': max_yr + i + 1,
            'Forecast': fc,
            'Low': fc - 1.96 * std,
            'High': fc + 1.96 * std,
        })
    
    return results, {'r2': r2, 'slope': slope, 'avg_yoy': avg_growth * 100}

def analyze_erpsim(df):
    team = df.groupby('Team').agg({'Revenue': 'sum', 'Quantity': 'sum', 'Price': 'mean'}).reset_index()
    team.columns = ['Team', 'Revenue', 'Quantity', 'AvgPrice']
    team = team.sort_values('Revenue', ascending=False)
    product = df.groupby('Product').agg({'Revenue': 'sum', 'Quantity': 'sum'}).reset_index()
    product = product.sort_values('Revenue', ascending=False)
    return team, product

# ============================================================
# ALERTS
# ============================================================

def generate_alerts(variance_df, signals, va05_df):
    alerts = []
    
    if variance_df is not None and len(variance_df) > 0:
        for _, row in variance_df[variance_df['Risk'].isin(['CRITICAL', 'HIGH'])].iterrows():
            alerts.append({
                'type': 'Revenue', 'source': 'Finance', 'severity': row['Risk'],
                'title': f"Customer {int(row['Customer'])} Below Plan",
                'detail': f"${abs(row['Variance']):,.0f} ({row['VarPct']:.1f}%)",
                'action': 'Review customer account', 'score': 100 if row['Risk'] == 'CRITICAL' else 70
            })
    
    if va05_df is not None:
        for _, row in va05_df[va05_df['risk_level'] == 'HIGH'].head(3).iterrows():
            alerts.append({
                'type': 'Order Risk', 'source': 'VA05',
                'severity': 'HIGH',
                'title': f"Doc {row['doc']} - {row['material']}",
                'detail': f"${row['value']:,.0f} | {row['days_old']}d old | {row['late_prob']*100:.0f}% late",
                'action': 'Expedite order', 'score': 75
            })
    
    for t in signals['traffic']:
        if t['level'] in ['severe', 'heavy']:
            alerts.append({
                'type': 'Logistics', 'source': 'Traffic',
                'severity': 'CRITICAL' if t['level'] == 'severe' else 'HIGH',
                'title': f"{t['corridor']} Delays",
                'detail': f"{t['delay_ratio']}x normal",
                'action': f"Adjust {t['region']} ETAs",
                'score': 90 if t['level'] == 'severe' else 65
            })
    
    for s in signals['satellite']:
        if s['signal'] in ['demand_drop', 'slight_decline']:
            alerts.append({
                'type': 'Demand', 'source': 'Satellite',
                'severity': 'HIGH' if s['signal'] == 'demand_drop' else 'MEDIUM',
                'title': f"{s['location'][:20]}...",
                'detail': f"{s['current']}% ({s['delta']:+.0f}%)",
                'action': f"Check Customer {s['customer_id']}",
                'score': 80 if s['signal'] == 'demand_drop' else 50
            })
    
    return sorted(alerts, key=lambda x: x['score'], reverse=True)

# ============================================================
# EXECUTIVE BRIEF GENERATOR (NEW in v5.3)
# ============================================================

def generate_executive_brief(alerts, signals, forecast_data, variance_df, actuals, case_name=None):
    """Generate a comprehensive executive brief."""
    now = datetime.now().strftime("%B %d, %Y %H:%M")
    
    critical = len([a for a in alerts if a['severity'] == 'CRITICAL'])
    high = len([a for a in alerts if a['severity'] == 'HIGH'])
    
    top_alerts = alerts[:5]
    
    fin_summary = ""
    if actuals is not None:
        yearly = compute_yearly(actuals)
        if len(yearly) > 0:
            latest_year = yearly.iloc[-1]
            fin_summary = f"""
**Financial Position (FY{int(latest_year['Year'])})**
- Revenue: ${latest_year['RevenueUSD']/1e6:.1f}M
- Margin: {latest_year['Margin']:.1f}%
- YoY Growth: {latest_year['YoY']:.1f}%"""
    
    fc_summary = ""
    if forecast_data:
        fc = forecast_data[0]
        fc_summary = f"""
**Forecast Outlook ({fc['Year']})**
- Projected Revenue: ${fc['Forecast']/1e6:.1f}M
- Range: ${fc['Low']/1e6:.1f}M - ${fc['High']/1e6:.1f}M (95% CI)"""
    
    sig_summary = f"""
**External Intelligence**
- Traffic Corridors: {signals['summary']['traffic_alerts']} alerts
- Distribution Centers: {signals['summary']['satellite_alerts']} demand signals
- Market Indicators: {signals['summary']['market_alerts']} cost pressures
- Overall Risk Level: {signals['summary']['overall_risk']}"""
    
    risk_lines = "\n".join([f"- [{a['severity']}] {a['title']}: {a['detail']}" for a in top_alerts])
    
    recommendations = []
    if critical > 0:
        recommendations.append("IMMEDIATE: Escalate critical alerts to executive team")
    if signals['summary']['overall_risk'] == 'CRITICAL':
        recommendations.append("URGENT: Review logistics contingency plans")
    if high > 2:
        recommendations.append("HIGH PRIORITY: Schedule customer account reviews")
    if signals['summary']['market_alerts'] > 2:
        recommendations.append("MONITOR: Cost pressures may impact margins")
    if not recommendations:
        recommendations.append("STANDARD: Continue monitoring, no immediate action required")
    
    rec_lines = "\n".join([f"- {r}" for r in recommendations])
    
    case_header = f"\n**Case Study: {case_name}**\n" if case_name and case_name != "-- No Case Selected --" else ""
    
    brief = f"""
================================================================================
                        AABS CONTROL TOWER - EXECUTIVE BRIEF
================================================================================
Generated: {now}
Classification: INTERNAL USE ONLY
{case_header}
--------------------------------------------------------------------------------
                              SITUATION OVERVIEW
--------------------------------------------------------------------------------

**Alert Summary**
- Critical Alerts: {critical}
- High Priority: {high}
- Total Active: {len(alerts)}
{fin_summary}
{fc_summary}
{sig_summary}

--------------------------------------------------------------------------------
                              TOP RISKS
--------------------------------------------------------------------------------

{risk_lines}

--------------------------------------------------------------------------------
                           RECOMMENDED ACTIONS
--------------------------------------------------------------------------------

{rec_lines}

--------------------------------------------------------------------------------
                              PREPARED BY
--------------------------------------------------------------------------------

AABS Control Tower v{Config.VERSION}
Enterprise Decision Intelligence Platform

This brief provides a point-in-time snapshot. For real-time monitoring,
access the Control Tower dashboard directly.

================================================================================
"""
    return brief

# ============================================================
# MAIN APP
# ============================================================

def main():
    current_case = st.session_state.get('selected_case', "-- No Case Selected --")
    case_config = AABS_CASES.get(current_case, AABS_CASES["-- No Case Selected --"])
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"# 🎯 {Config.APP_NAME} v{Config.VERSION}")
        st.caption(case_config['subtitle'])
    with col2:
        st.markdown('<div class="live-indicator"><div class="live-dot"></div>LIVE</div>', unsafe_allow_html=True)
    with col3:
        st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
    
    if case_config['context']:
        st.markdown(f'<div class="case-context">{case_config["context"]}</div>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("### ⚙️ Control Panel")
        
        auto_refresh = st.checkbox("Auto-Refresh (30s)", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto_refresh
        
        if st.button("🔄 Refresh Now"):
            st.session_state.refresh_count += 1
            st.rerun()
        
        st.divider()
        
        st.markdown("### 🎓 AABS Case Mode")
        selected_case = st.selectbox(
            "Select Case Study",
            options=list(AABS_CASES.keys()),
            index=list(AABS_CASES.keys()).index(st.session_state.selected_case),
            help="Load a teaching case with preset scenarios"
        )
        if selected_case != st.session_state.selected_case:
            st.session_state.selected_case = selected_case
            st.rerun()
        
        st.divider()
        st.markdown("### 📂 Data Sources")
        use_gbi = st.checkbox("GBI Analytics", value=True)
        use_erpsim = st.checkbox("ERPSIM Data", value=True)
        
        st.divider()
        st.markdown("### 📦 VA05 Data")
        use_real_va05 = st.checkbox("Use Real VA05 Data", value=True, help="Toggle off to use sample data")
        
        if use_real_va05:
            validation = validate_va05()
            if validation['valid']:
                st.markdown('<div class="validation-pass">✓ Validated</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="validation-fail">✗ Validation Failed</div>', unsafe_allow_html=True)
        
        st.divider()
        st.caption(f"Refreshes: {st.session_state.refresh_count}")
        st.caption(f"Plotly: {'✅' if PLOTLY_AVAILABLE else '❌'}")
    
    actuals, plan = (None, None)
    if use_gbi:
        actuals, plan = load_gbi_data(Config.GBI_PATH)
    
    erpsim = None
    if use_erpsim:
        erpsim = load_erpsim_data(Config.ERPSIM_PATH)
    
    va05_df = None
    va05_source = "Sample"
    if use_real_va05:
        validation = validate_va05()
        if validation['valid']:
            va05_df = get_real_va05_data()
            va05_source = "SAP (Validated)"
        else:
            va05_df = get_sample_va05_data()
            va05_source = "Sample (Validation Failed)"
    else:
        va05_df = get_sample_va05_data()
        va05_source = "Sample"
    
    signals = get_all_signals(case_config.get('signals_modifier'))
    
    tabs = st.tabs(["📦 Logistics", "💰 Finance", "📈 Forecast", "🌐 Signals", "🚨 Alerts", "🎬 Scenarios", "📌 Sources", "🎯 Strategy"])
    
    # TAB 1: LOGISTICS
    with tabs[0]:
        st.header("Logistics Operations")
        st.caption(f"Data Source: {va05_source}")
        
        with st.expander("📊 Data Quality", expanded=False):
            if use_real_va05:
                validation = validate_va05()
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Line Items", validation['quality'].get('line_items', 'N/A'))
                c2.metric("Documents", validation['quality'].get('unique_docs', 'N/A'))
                c3.metric("Date Range", f"{validation['quality'].get('date_min', 'N/A')[:10]}...")
                c4.metric("Legacy Orders", validation['quality'].get('legacy_orders', 'N/A'))
                c5.metric("Validation", "✓ PASS" if validation['valid'] else "✗ FAIL")
                
                if st.checkbox("View Validation Details"):
                    for check, data in validation['checks'].items():
                        status = "✓" if data['pass'] else "✗"
                        st.text(f"{status} {check}: {data['actual']} (expected: {data['expected']})")
        
        if va05_df is not None:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Open Orders", len(va05_df))
            c2.metric("At Risk", len(va05_df[va05_df['risk_level'] == 'HIGH']))
            total_value = va05_df['value'].sum()
            at_risk_value = va05_df['revenue_at_risk'].sum()
            c3.metric("Total Value", f"${total_value:,.0f}")
            c4.metric("Revenue at Risk", f"${at_risk_value:,.0f}")
            
            st.divider()
            high_risk = va05_df[va05_df['risk_level'] == 'HIGH'].head(5)
            for _, row in high_risk.iterrows():
                st.markdown(f"""<div style='background:#fee2e2;padding:10px;border-radius:8px;margin-bottom:8px'>
                    <strong>🔴 Doc {row['doc']}</strong> - {row['material']}<br>
                    ${row['value']:,.0f} | {row['days_old']} days old | {row['late_prob']*100:.0f}% late probability
                </div>""", unsafe_allow_html=True)
    
    # TAB 2: FINANCE
    with tabs[1]:
        st.header("Finance Analytics")
        if actuals is not None and plan is not None:
            years = sorted(set(actuals['Year']) & set(plan['YEAR']))
            if years:
                year = st.selectbox("Year", years, index=len(years)-1)
                var_df = compute_variance(actuals, plan, year)
                
                if len(var_df) > 0:
                    total_actual = var_df['Actual'].sum()
                    total_plan = var_df['Plan'].sum()
                    total_var = var_df['Variance'].sum()
                    at_risk = var_df[var_df['Risk'].isin(['CRITICAL', 'HIGH'])]['Variance'].sum()
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Actual", f"${total_actual/1e6:.1f}M")
                    c2.metric("Plan", f"${total_plan/1e6:.1f}M")
                    c3.metric("Variance", f"${total_var/1e6:+.1f}M")
                    c4.metric("At Risk", f"${abs(at_risk)/1e6:.1f}M")
                    
                    if PLOTLY_AVAILABLE:
                        fig = go.Figure()
                        colors = ['#ef4444' if v < 0 else '#22c55e' for v in var_df['Variance']]
                        fig.add_trace(go.Bar(x=var_df['Customer'], y=var_df['Variance'], marker_color=colors))
                        fig.update_layout(height=300, yaxis_tickformat='$,.0f')
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Enable GBI Analytics in sidebar")
    
    # TAB 3: FORECAST
    with tabs[2]:
        st.header("Revenue Forecasting")
        if actuals is not None:
            yearly = compute_yearly(actuals)
            fc, metrics = forecast(yearly)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("R²", f"{metrics['r2']:.3f}")
            c2.metric("Avg YoY", f"{metrics['avg_yoy']:.1f}%")
            c3.metric(f"{fc[0]['Year']} FC", f"${fc[0]['Forecast']/1e6:.1f}M")
            c4.metric("Trend", f"${metrics['slope']/1e6:.2f}M/yr")
            
            if PLOTLY_AVAILABLE:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=yearly['Year'], y=yearly['RevenueUSD'], mode='lines+markers', name='Historical', line=dict(color='#3b82f6', width=3)))
                fc_years = [f['Year'] for f in fc]
                fc_vals = [f['Forecast'] for f in fc]
                fc_low = [f['Low'] for f in fc]
                fc_high = [f['High'] for f in fc]
                fig.add_trace(go.Scatter(x=fc_years + fc_years[::-1], y=fc_high + fc_low[::-1], fill='toself', fillcolor='rgba(34,197,94,0.2)', line=dict(color='rgba(0,0,0,0)'), name='95% CI'))
                fig.add_trace(go.Scatter(x=fc_years, y=fc_vals, mode='lines+markers', name='Forecast', line=dict(color='#22c55e', width=3, dash='dash')))
                fig.update_layout(height=350, yaxis_tickformat='$,.0f')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Enable GBI Analytics in sidebar")
    
    # TAB 4: SIGNALS
    with tabs[3]:
        st.header("External Signals")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Traffic", signals['summary']['traffic_alerts'])
        c2.metric("Demand", signals['summary']['satellite_alerts'])
        c3.metric("Cost", signals['summary']['market_alerts'])
        risk_icon = {'CRITICAL': '🔴', 'ELEVATED': '🟠', 'NORMAL': '🟢'}
        c4.metric("Risk", f"{risk_icon.get(signals['summary']['overall_risk'], '⚪')} {signals['summary']['overall_risk']}")
        
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("🚚 Traffic")
            for t in signals['traffic']:
                bg = '#fee2e2' if t['level'] == 'severe' else '#fef3c7' if t['level'] == 'heavy' else '#f0fdf4'
                st.markdown(f"<div style='background:{bg};padding:8px;border-radius:6px;margin-bottom:6px'>{t['status']} {t['corridor']}<br><small>{t['level']} • {t['delay_ratio']}x</small></div>", unsafe_allow_html=True)
        
        with col2:
            st.subheader("🛰️ Satellite")
            for s in signals['satellite']:
                bg = '#fee2e2' if s['risk'] == 'HIGH' else '#fef3c7' if s['risk'] == 'MEDIUM' else '#f0fdf4'
                st.markdown(f"<div style='background:{bg};padding:8px;border-radius:6px;margin-bottom:6px'>{s['status']} {s['location'][:18]}...<br><small>{s['current']}% ({s['delta']:+.0f}%)</small></div>", unsafe_allow_html=True)
        
        with col3:
            st.subheader("📊 Market")
            for m in signals['market']:
                bg = '#fee2e2' if m['impact'] == 'negative' else '#f0fdf4' if m['impact'] == 'positive' else '#f3f4f6'
                st.markdown(f"<div style='background:{bg};padding:8px;border-radius:6px;margin-bottom:6px'>{m['status']} {m['indicator']}<br><small>{m['change_pct']:+.1f}%</small></div>", unsafe_allow_html=True)
    
    # TAB 5: ALERTS
    with tabs[4]:
        st.header("🚨 Alert Center")
        var_df = None
        if actuals is not None and plan is not None:
            years = sorted(set(actuals['Year']) & set(plan['YEAR']))
            if years:
                var_df = compute_variance(actuals, plan, years[-1])
        
        alerts = generate_alerts(var_df, signals, va05_df)
        critical = len([a for a in alerts if a['severity'] == 'CRITICAL'])
        high = len([a for a in alerts if a['severity'] == 'HIGH'])
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔴 Critical", critical)
        c2.metric("🟠 High", high)
        c3.metric("Total", len(alerts))
        
        with c4:
            fc_data = None
            if actuals is not None:
                yearly = compute_yearly(actuals)
                fc_data, _ = forecast(yearly)
            
            brief = generate_executive_brief(
                alerts, signals, fc_data, var_df, actuals, 
                st.session_state.selected_case
            )
            st.download_button(
                "📋 Executive Brief",
                brief,
                "AABS_Executive_Brief.txt",
                mime="text/plain",
                help="Generate comprehensive leadership summary"
            )
        
        report = f"# AABS Alert Report\n{datetime.now()}\n\nCritical: {critical} | High: {high}\n\n" + "\n".join([f"- [{a['severity']}] {a['title']}: {a['detail']}" for a in alerts[:10]])
        st.download_button("📄 Quick Report", report, "aabs_report.md")
        
        st.divider()
        for a in alerts[:12]:
            bg = '#fee2e2' if a['severity'] == 'CRITICAL' else '#fef3c7' if a['severity'] == 'HIGH' else '#fefce8'
            icon = '🔴' if a['severity'] == 'CRITICAL' else '🟠' if a['severity'] == 'HIGH' else '🟡'
            st.markdown(f"""<div style='background:{bg};padding:12px;border-radius:8px;margin-bottom:8px'>
                <strong>{icon} {a['title']}</strong> <small>({a['source']})</small><br>
                {a['detail']}<br><span style='color:#1d4ed8'>→ {a['action']}</span>
            </div>""", unsafe_allow_html=True)
    
    # TAB 6: SCENARIOS
    with tabs[5]:
        st.header("🎬 Scenario Simulator")
        if actuals is not None:
            yearly = compute_yearly(actuals)
            base_fc, _ = forecast(yearly)
            
            scenarios = [
                {'name': 'Steel +20%', 'factor': -0.08},
                {'name': 'Fuel +30%', 'factor': -0.06},
                {'name': 'Recession -15%', 'factor': -0.15},
                {'name': 'Expansion +10%', 'factor': 0.10},
            ]
            
            st.markdown("#### 📦 Scenario Packs")
            pack_col1, pack_col2 = st.columns([1, 2])
            with pack_col1:
                selected_pack = st.selectbox(
                    "Quick Load",
                    options=list(SCENARIO_PACKS.keys()),
                    index=0,
                    help="One-click scenario combinations"
                )
            with pack_col2:
                if selected_pack != "-- Select Pack --":
                    pack_scenarios = SCENARIO_PACKS[selected_pack]
                    st.info(f"**{selected_pack}**: {', '.join(pack_scenarios) if pack_scenarios else 'No scenarios'}")
            
            st.divider()
            st.markdown("#### Manual Selection")
            
            selected = []
            cols = st.columns(4)
            for i, s in enumerate(scenarios):
                with cols[i]:
                    default_val = s['name'] in SCENARIO_PACKS.get(selected_pack, [])
                    if st.checkbox(s['name'], key=f"s_{i}", value=default_val):
                        selected.append(s)
            
            st.divider()
            
            if selected:
                st.markdown("#### Impact Analysis")
                base_total = sum(f['Forecast'] for f in base_fc)
                total_impact = 0
                for s in selected:
                    impact = base_total * s['factor']
                    total_impact += impact
                    bg = '#fee2e2' if impact < 0 else '#dcfce7'
                    icon = '📉' if impact < 0 else '📈'
                    st.markdown(f"<div style='background:{bg};padding:12px;border-radius:8px;margin-bottom:8px'><strong>{icon} {s['name']}</strong>: ${impact/1e6:+.1f}M 3-year impact</div>", unsafe_allow_html=True)
                
                if len(selected) > 1:
                    bg = '#fee2e2' if total_impact < 0 else '#dcfce7'
                    st.markdown(f"<div style='background:{bg};padding:16px;border-radius:8px;border:2px solid #374151'><strong>📊 COMBINED IMPACT</strong>: ${total_impact/1e6:+.1f}M 3-year impact</div>", unsafe_allow_html=True)
            else:
                st.info("Select scenarios above or choose a Scenario Pack to model impact")
        else:
            st.info("Enable GBI Analytics")
    
    # TAB 7: SOURCES
    with tabs[6]:
        st.header("📌 Data Sources")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("GBI", "✅" if actuals is not None else "❌")
        c2.metric("ERPSIM", "✅" if erpsim is not None else "❌")
        c3.metric("VA05", va05_source)
        c4.metric("Signals", "✅ Live")
        
        st.divider()
        st.code("""# Go Live
export GOOGLE_MAPS_API_KEY="your-key"
export ALPHA_VANTAGE_API_KEY="your-key"
streamlit run app.py""", language="bash")
    
    # TAB 8: STRATEGY
    with tabs[7]:
        st.header("🎯 Strategy Coach")
        if erpsim is not None:
            team, _ = analyze_erpsim(erpsim)
            c1, c2, c3 = st.columns(3)
            c1.metric("Teams", len(team))
            c2.metric("Top", team.iloc[0]['Team'])
            c3.metric("Revenue", f"${team['Revenue'].sum()/1e6:.1f}M")
            
            if PLOTLY_AVAILABLE:
                fig = go.Figure(go.Bar(y=team['Team'], x=team['Revenue'], orientation='h', marker_color='#3b82f6'))
                fig.update_layout(height=300, xaxis_tickformat='$,.0f', yaxis_autorange='reversed')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Enable ERPSIM")
    
    if st.session_state.auto_refresh:
        time.sleep(Config.AUTO_REFRESH_INTERVAL)
        st.rerun()

if __name__ == "__main__":
    main()
