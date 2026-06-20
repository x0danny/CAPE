import streamlit as st

st.set_page_config(page_title="CAPE Platform", page_icon="🌿", layout="wide")

st.title("🌿 CAPE — Carbon-Aware Predictive Engine")
st.markdown("**AI-Driven Analytics Platform for Carbon-Awareness of LAX Logistics**")

st.markdown("##### Team")
st.markdown("Brian Ta · Daniel Ramirez")
st.markdown("##### Advisor")
st.markdown("Dr. Ming Wang")
st.caption("CSULA CIS | SAIES Research | NSF Grant Project")
st.divider()

st.markdown("#### What is CAPE?")
st.markdown("""
CAPE is a predictive carbon intelligence platform that analyzes LAX air freight data.
Most enterprise carbon tools tell you what you already emitted — like a bill after you spent the money.
**CAPE tells you what you are about to emit before the decision is made.**

Using a machine learning model trained on supply chain simulation data, CAPE achieves **94.2% cross-validation accuracy**
predicting which fulfillment periods will generate elevated carbon exposure.
The key finding: **carbon emissions are the #1 predictor of order lateness** — carbon and operational risk are statistically linked.

The platform is validated against **18 years of LAX air freight data** and **Port of LA container volume** from the 2021 supply chain surge,
grounding the findings in the real-world logistics corridor most relevant to this research.
""")
st.divider()

st.markdown("#### Explore the Platform")

col1, col2, col3 = st.columns(3)
with col1:
    st.page_link("pages/1_Carbon_Risk_Analysis.py", label="Open Carbon Risk Analysis", icon="🌿", use_container_width=True)
    st.success(
        "**Carbon Risk Analysis**\n\n"
        "Carbon risk scores across 38 simulation periods, validated against 18 years of real LAX air freight data. "
        "See which periods were high risk and why."
    )
with col2:
    st.page_link("pages/2_Risk_Control_Tower.py", label="Open Risk Control Tower", icon="⚡", use_container_width=True)
    st.info(
        "**Risk Control Tower**\n\n"
        "Interactive what-if sliders to simulate supply chain changes. "
        "Plain English recommendations for every high-risk period."
    )
with col3:
    st.page_link("pages/3_Freight_&_Carbon.py", label="Open Freight & Carbon", icon="📊", use_container_width=True)
    st.warning(
        "**Freight & Carbon Intelligence**\n\n"
        "Per-shipment carbon analysis by carrier, route, and product category. "
        "Scope 1/2/3 breakdown using ICAO/DEFRA methodology."
    )

st.markdown("")
col4, col5 = st.columns(2)
with col4:
    st.page_link("pages/4_Ask_CAPE_AI.py", label="Open Ask CAPE AI", icon="💬", use_container_width=True)
    st.info(
        "**Ask CAPE AI**\n\n"
        "Ask any question about LAX air freight, carbon risk, or supply chain logistics. "
        "Answers grounded in real data with live web search for current events."
    )
with col5:
    st.page_link("pages/5_Data_&_Downloads.py", label="Open Data & Downloads", icon="📁", use_container_width=True)
    st.success(
        "**Data & Downloads**\n\n"
        "Download all CAPE datasets (LAWA, Freightos, ICAO/DEFRA) "
        "or upload your own LAX data to extend the analysis."
    )

st.divider()

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric("LAX Freight Data", "18 Years",
              help="2006–2023 monthly air cargo tonnage from LAWA Open Data Portal")
with col_b:
    st.metric("ML Model Accuracy", "94.2% ±3.3%",
              help="Random Forest classifier, 5-fold cross-validation")
with col_c:
    st.metric("Air vs Ground Carbon", "~49x",
              help="Air freight produces approximately 49 times more CO₂ per ton-mile than ground transport")

st.divider()
st.caption("CAPE — AI-Driven Analytics Platform | SAIES Research | CSULA CIS | NSF Grant Project")
