import streamlit as st

st.set_page_config(page_title="CAPE Platform", page_icon="🌿", layout="wide")

st.title("🌿 CAPE — Carbon-Aware Predictive Engine")
st.markdown("**Predictive Analytics on Carbon-Awareness of LAX Logistics**")
st.markdown("Dr. Ming Wang · Brian · Daniel Ramirez | CSULA CIS | SAIES Research | NSF Grant Project")
st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.success("### 🌿 CAPE Carbon\nCarbon risk scores, overstock penalties, LAX validation. Use the sidebar to navigate.")
with col2:
    st.info("### ⚡ Control Tower\nOrder risk intelligence, carbon alerts, plain English explanations.")
with col3:
    st.warning("### 📊 Sales Intelligence\nBrian's competitive pricing dashboard — coming soon.")

st.divider()
st.caption("Use the sidebar arrows to navigate between modules")
