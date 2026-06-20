import streamlit as st

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
    st.page_link("pages/1_Carbon_Risk_Scores.py", label="Which periods were high risk?", icon="🌿", use_container_width=True)
    st.success(
        "**Carbon Risk Scores**\n\n"
        "See which time periods had the highest carbon risk, why they were flagged, "
        "and how the findings connect to 18 years of real LAX air freight data."
    )
with col2:
    st.page_link("pages/2_What_If_Simulator.py", label="What if we changed our approach?", icon="⚡", use_container_width=True)
    st.info(
        "**What-If Simulator**\n\n"
        "Drag sliders to simulate supply chain changes — fewer late orders, smaller orders, "
        "more ground shipping — and see how carbon risk would change."
    )
with col3:
    st.page_link("pages/3_Emissions_By_Route.py", label="Which routes emit the most?", icon="📊", use_container_width=True)
    st.warning(
        "**Emissions by Route**\n\n"
        "Which airlines, routes, and cargo types produce the most carbon at LAX? "
        "Per-shipment analysis with real emission factors."
    )

st.markdown("")
col4, col5 = st.columns(2)
with col4:
    st.page_link("pages/4_Ask_A_Question.py", label="Have a question? Ask CAPE AI", icon="💬", use_container_width=True)
    st.info(
        "**Ask a Question**\n\n"
        "Type any question about LAX air freight, carbon risk, or supply chain logistics. "
        "Get answers grounded in real data — with live web search for current events."
    )
with col5:
    st.page_link("pages/5_Data_&_Downloads.py", label="Download the data", icon="📁", use_container_width=True)
    st.success(
        "**Data & Downloads**\n\n"
        "Download all CAPE datasets for your own analysis, "
        "or upload updated LAX data to extend the research."
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
