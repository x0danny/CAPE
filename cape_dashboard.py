import streamlit as st

st.set_page_config(page_title="CAPE Platform", page_icon="🌿", layout="wide")

pages = st.navigation([
    st.Page("pages/0_Home.py",                title="CAPE Dashboard",      icon="🌿", default=True),
    st.Page("pages/1_Carbon_Risk_Scores.py",  title="Carbon Risk Scores",  icon="📈"),
    st.Page("pages/2_What_If_Simulator.py",   title="What-If Simulator",   icon="⚡"),
    st.Page("pages/3_Emissions_By_Route.py",  title="Emissions by Route",  icon="📊"),
    st.Page("pages/6_Key_Findings.py",        title="Key Findings",        icon="🔑"),
    st.Page("pages/4_Ask_A_Question.py",      title="Ask a Question",      icon="💬"),
    st.Page("pages/5_Data_&_Downloads.py",    title="Data & Downloads",    icon="📁"),
])

pages.run()
