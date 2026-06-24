import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

st.set_page_config(page_title="CAPE Platform", page_icon="🌿", layout="wide")

pages = st.navigation([
    st.Page("pages/0_Home.py",                title="CAPE Dashboard",        icon="🌿", default=True),
    st.Page("pages/1_Carbon_Risk_Scores.py",  title="Training in ERPsim",    icon="📈"),
    st.Page("pages/7_LAX_Case_Study.py",      title="LAX Case Study",       icon="✈️"),
    st.Page("pages/3_Emissions_By_Route.py",  title="Emissions by Route",   icon="📊"),
    st.Page("pages/2_What_If_Simulator.py",   title="What-If Simulator",    icon="⚡"),
    st.Page("pages/4_Ask_A_Question.py",      title="Chatbot on CAPE",      icon="💬"),
    st.Page("pages/6_Key_Findings.py",        title="Conclusions",           icon="🔑"),
    st.Page("pages/5_Data_&_Downloads.py",    title="Data & Downloads",     icon="📁"),
])

pages.run()
