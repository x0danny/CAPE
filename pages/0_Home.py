import streamlit as st

st.title("🌿 CAPE — Carbon-Aware Predictive Engine")
st.markdown("**AI-Driven Analytics Platform for Carbon-Awareness of LAX (Los Angeles International Airport) Air Freight**")

col_team, col_advisor = st.columns(2)
with col_team:
    st.markdown("##### Team")
    st.markdown("Brian Ta · Daniel Ramirez")
with col_advisor:
    st.markdown("##### Advisor")
    st.markdown("Dr. Ming Wang")
st.caption("CSULA (Cal State LA) · CIS (College of Information Systems) | SAIES Research | NSF (National Science Foundation) Grant Project")
st.divider()

st.markdown("#### What is CAPE?")
st.markdown("""
CAPE is a predictive carbon intelligence platform that analyzes LAX air freight data.
Most enterprise carbon tools tell you what you already emitted — like a bill after you spent the money.
**CAPE tells you what you are about to emit before the decision is made.**

Using a machine learning model, CAPE achieves **94.2% accuracy** predicting which
supply chain conditions will generate dangerous carbon exposure.
The key finding: **carbon emissions are the #1 predictor of order lateness** — carbon risk and delivery risk move together.

CAPE's predictions are supported by **18 years of real LAX air freight data** and **Port of LA shipping records**,
confirming that the patterns CAPE detects match what actually happened during the 2021 supply chain crisis.
""")

st.markdown(
    "**Why does this matter?** Every time a package gets rushed by air instead of ground, "
    "it produces roughly **49 times more carbon pollution**. During the 2021 shipping crisis, "
    "LAX air freight surged 31% — millions of extra tons of CO₂ that could have been avoided "
    "with earlier intervention. CAPE is designed to provide that early warning."
)
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
col4, col5, col6 = st.columns(3)
with col4:
    st.page_link("pages/6_Key_Findings.py", label="What did CAPE find?", icon="🔑", use_container_width=True)
    st.error(
        "**Key Findings**\n\n"
        "The project's conclusions: what CAPE found, why it matters, "
        "and what LAX and logistics operators should do about it."
    )
with col5:
    st.page_link("pages/4_Ask_A_Question.py", label="Have a question? Ask CAPE AI", icon="💬", use_container_width=True)
    st.info(
        "**Ask a Question**\n\n"
        "Type any question about LAX air freight, carbon risk, or supply chain logistics. "
        "Get answers grounded in real data."
    )
with col6:
    st.page_link("pages/5_Data_&_Downloads.py", label="Download the data", icon="📁", use_container_width=True)
    st.success(
        "**Data & Downloads**\n\n"
        "Download all CAPE datasets for your own analysis, "
        "or upload updated LAX data."
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
st.caption("CAPE — AI-Driven Analytics Platform | SAIES Research | Cal State LA · CIS | NSF Grant Project")
