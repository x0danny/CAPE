import streamlit as st

st.title("🌿 CAPE — Carbon-Aware Predictive Engine")
st.markdown("**AI-Driven Analytics Application for LAX**")

col_team, col_advisor = st.columns(2)
with col_team:
    st.markdown("##### Team")
    st.markdown("**Brian Ta**, Co-Lead & Software Developer\n\n**Daniel Ramirez**, Co-Lead & Financial Analyst")
with col_advisor:
    st.markdown("##### Advisor")
    st.markdown("Dr. Ming Wang")
st.caption("Cal State LA · CIS | SAIES Research | NSF Grant Project")
st.divider()

st.markdown("#### What is CAPE?")
st.markdown("""
CAPE (Carbon-Aware Predictive Engine) is a predictive carbon intelligence platform that analyzes air freight data
at LAX (Los Angeles International Airport), one of the busiest cargo airports in the United States.
Most enterprise carbon tools tell you what you already emitted — like a bill after you spent the money.
**CAPE tells you how much carbon shipping and freight vehicles will emit — before the shipping decision is made.**

Using a machine learning model, CAPE achieves **94.2% accuracy** predicting which
supply chain conditions will generate harmful carbon exposure.
The key finding: **carbon emissions are the #1 predictor of order lateness** — carbon risk and delivery risk move together.

The CAPE project predicts carbon risk using **18 years of real LAX air freight data** and **Port of LA shipping records**,
confirming that the patterns CAPE detects match what actually happened during the 2021 supply chain crisis.
""")

st.markdown(
    "**Why does this matter?** LAX is a critical hub for the Los Angeles community and the broader economy. "
    "Every time a package gets rushed by airplane instead of ground transport, "
    "it produces roughly **49 times more carbon pollution**. During the COVID-19 pandemic, "
    "global supply chains were severely disrupted — ports were backed up, ground shipping was delayed, "
    "and companies were forced to rely on air freight to keep goods moving. "
    "As a result, LAX air freight surged 31% between 2019 and 2021, generating millions of extra tons of CO₂ "
    "that could have been avoided with earlier intervention. "
    "The increase happened because the pandemic caused a massive shift from ground to air shipping "
    "as companies scrambled to meet demand despite ground transportation bottlenecks. "
    "CAPE is designed to provide that early warning — confirming that the patterns CAPE detects "
    "match what actually happened during the 2021 supply chain crisis."
)
st.divider()

st.markdown("#### Explore More Details")

col1, col2, col3 = st.columns(3)
with col1:
    st.page_link("pages/1_Carbon_Risk_Scores.py", label="Which periods were high risk?", icon="📈", use_container_width=True)
    st.success(
        "**Training in ERPsim**\n\n"
        "See which time periods had the highest carbon risk and why they were flagged, "
        "using data from a supply chain training simulation."
    )
with col2:
    st.page_link("pages/7_LAX_Case_Study.py", label="How does it compare to real LAX data?", icon="✈️", use_container_width=True)
    st.warning(
        "**LAX Case Study**\n\n"
        "18 years of real LAX air freight data (2006–2023) compared to CAPE's predictions. "
        "Includes Port of LA container volume analysis."
    )
with col3:
    st.page_link("pages/3_Emissions_By_Route.py", label="Which routes emit the most?", icon="📊", use_container_width=True)
    st.info(
        "**Emissions by Route**\n\n"
        "Which airlines, routes, and cargo types produce the most carbon at LAX? "
        "Per-shipment analysis with real emission factors."
    )

st.markdown("")
col4, col5, col6 = st.columns(3)
with col4:
    st.page_link("pages/2_What_If_Simulator.py", label="What if we changed our approach?", icon="⚡", use_container_width=True)
    st.info(
        "**What-If Simulator**\n\n"
        "Drag sliders to simulate supply chain changes — fewer late orders, smaller orders, "
        "more ground shipping — and see how carbon risk would change."
    )
with col5:
    st.page_link("pages/4_Ask_A_Question.py", label="Have a question? Ask CAPE AI", icon="💬", use_container_width=True)
    st.success(
        "**Chatbot on CAPE**\n\n"
        "Type any question about LAX air freight, carbon risk, or supply chain logistics. "
        "Get answers grounded in real data."
    )
with col6:
    st.page_link("pages/5_Data_&_Downloads.py", label="Download the data", icon="📁", use_container_width=True)
    st.error(
        "**Data & Downloads**\n\n"
        "Download all CAPE datasets for your own analysis, "
        "or upload updated LAX data."
    )

st.markdown("")
col7, col8, _col9 = st.columns(3)
with col7:
    st.page_link("pages/6_Key_Findings.py", label="What did CAPE find?", icon="🔑", use_container_width=True)
    st.warning(
        "**Conclusions**\n\n"
        "The project's conclusions: what CAPE found, why it matters, "
        "and what LAX and logistics operators should do about it."
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
              help="Air freight produces approximately 49 times more CO₂ per ton-mile than ground transport (based on ICAO/DEFRA emission factors). See the Emissions by Route page for the full calculation.")

st.divider()
st.caption("CAPE — AI-Driven Analytics Application | SAIES Research | Cal State LA · CIS | NSF Grant Project")
