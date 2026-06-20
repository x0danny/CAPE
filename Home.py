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
st.markdown(
    "CAPE predicts carbon risk in supply chain decisions **before** orders become late. "
    "Traditional tools like SAP Green Ledger record emissions after the fact — CAPE catches "
    "the risk at the moment a fulfillment decision is made, giving operations teams time to act."
)
st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.success("### 🌿 CAPE Carbon\nCarbon risk scores, overstock penalties, and LAX air freight validation across 18 years of data.")
with col2:
    st.info("### ⚡ AI Supply Chain Control Tower\nOrder risk intelligence with interactive what-if sliders and plain English explanations.")
with col3:
    st.warning("### 📊 Sales & Carbon Intelligence\nWhich products earn the most while emitting the least? Revenue vs. carbon trade-offs by product, team, and region.")

st.divider()
st.caption("Use the sidebar to navigate between modules")
