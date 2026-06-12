import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="CAPE Data Upload", page_icon="📁", layout="wide")

st.title("📁 Data Upload")
st.markdown("**Test CAPE with your own ERPsim data**")
st.caption(
    "Every team that runs the ERPsim simulation makes different decisions — different pricing, "
    "different order quantities, different timing — so their carbon outcomes will differ. "
    "Upload your own ERPsim export files here to run the full CAPE analysis on your team's data. "
    "This makes CAPE a replicable framework, not just a one-time analysis of one dataset."
)
st.info(
    "📌 **For researchers:** CAPE was built and validated on SAP ERPsim data provided by "
    "Dr. Ming Wang via the SAP University Alliance. If you are running ERPsim at another "
    "institution, your exported files will work here as long as they contain the required columns "
    "listed below each upload field.",
    icon="🔬"
)
st.divider()

DATA_DIR = Path(__file__).parent.parent / "data"

# Each dataset: display name → filename, preferred sheet, required columns
DATASETS = {
    "Sales": {
        "filename": "Sales.xlsx",
        "sheet":    "Sales",
        "required": ["SIM_ROUND", "SIM_STEP", "NET_VALUE", "SALES_ORDER_NUMBER"],
    },
    "Carbon Emissions": {
        "filename": "Carbon Emissions.xlsx",
        "sheet":    "Carbon_Emissions",
        "required": ["SIM_ROUND", "SIM_STEP", "TOTAL_CO2E_EMISSIONS", "TYPE", "SCOPE"],
    },
    "Purchase Orders": {
        "filename": "Purchase Orders.xlsx",
        "sheet":    "Purchase_Orders",
        "required": ["SIM_ROUND", "SIM_STEP", "GOODS_RECEIPT_ROUND", "GOODS_RECEIPT_STEP"],
    },
    "Inventory": {
        "filename": "Inventory.xlsx",
        "sheet":    "Inventory",
        "required": ["SIM_ROUND", "SIM_STEP"],
    },
    "Financial Postings": {
        "filename": "Fianancial Postings.xlsx",
        "sheet":    "Financial_Postings",
        "required": ["SIM_ROUND", "SIM_STEP"],
    },
}


def _read_best_sheet(uploaded_file, required_cols, preferred_sheet):
    """Try preferred sheet first, then all others, returning the first that has all required columns."""
    xl = pd.ExcelFile(uploaded_file)
    sheets = (
        ([preferred_sheet] if preferred_sheet in xl.sheet_names else [])
        + [s for s in xl.sheet_names if s != preferred_sheet]
    )
    for sheet in sheets:
        df = pd.read_excel(xl, sheet_name=sheet)
        if all(c in df.columns for c in required_cols):
            return df, sheet
    return None, None


def _file_info(path: Path):
    if not path.exists():
        return None
    stat = path.stat()
    size_kb = stat.st_size / 1024
    return f"{size_kb:.0f} KB"


# ── Page ──────────────────────────────────────────────────────────────────────
st.title("📁 Data Upload")
st.markdown("**Replace or augment CAPE datasets with your own ERPsim export files.**")
st.caption(
    "Uploaded files are validated for required columns before replacing the existing data. "
    "All other CAPE pages reload automatically after a successful upload."
)
st.divider()

# ── Current data status ───────────────────────────────────────────────────────
st.subheader("Current Data")
cols = st.columns(len(DATASETS))
for i, (name, cfg) in enumerate(DATASETS.items()):
    info = _file_info(DATA_DIR / cfg["filename"])
    with cols[i]:
        if info:
            st.metric(name, info, help=cfg["filename"])
        else:
            st.metric(name, "Missing", help=f"{cfg['filename']} not found in data/")

st.divider()

# ── Upload section ────────────────────────────────────────────────────────────
st.subheader("Upload New Data")
st.info(
    "Files must be `.xlsx` format and contain the required columns. "
    "Use the ERPsim export format. Uploading a file replaces the existing one for all pages.",
    icon="ℹ️",
)

for name, cfg in DATASETS.items():
    with st.expander(f"**{name}** — `{cfg['filename']}`"):
        st.caption(f"Required columns: `{'`, `'.join(cfg['required'])}`")
        uploaded = st.file_uploader(
            f"Choose {name} file",
            type=["xlsx"],
            key=f"upload_{name}",
        )
        if uploaded:
            with st.spinner("Validating..."):
                df, matched_sheet = _read_best_sheet(uploaded, cfg["required"], cfg["sheet"])

            if df is None:
                st.error(
                    f"No sheet found with all required columns: `{'`, `'.join(cfg['required'])}`. "
                    f"Check that you're uploading the correct ERPsim export."
                )
            else:
                st.success(f"Valid — **{len(df):,} rows** found in sheet `{matched_sheet}`.")
                st.dataframe(df.head(3), use_container_width=True)

                if st.button(f"Save and replace {name}", key=f"save_{name}", type="primary"):
                    uploaded.seek(0)
                    dest = DATA_DIR / cfg["filename"]
                    dest.write_bytes(uploaded.read())
                    st.cache_data.clear()
                    st.success(
                        f"{name} saved to `data/{cfg['filename']}`. "
                        f"All CAPE pages will use the new data on next load."
                    )

st.divider()

# ── Notes ─────────────────────────────────────────────────────────────────────
with st.expander("Notes on data format"):
    st.markdown("""
**Minimum column requirements per file:**

| File | Required columns |
|------|-----------------|
| Sales.xlsx | `SIM_ROUND`, `SIM_STEP`, `NET_VALUE`, `SALES_ORDER_NUMBER` |
| Carbon Emissions.xlsx | `SIM_ROUND`, `SIM_STEP`, `TOTAL_CO2E_EMISSIONS`, `TYPE`, `SCOPE` |
| Purchase Orders.xlsx | `SIM_ROUND`, `SIM_STEP`, `GOODS_RECEIPT_ROUND`, `GOODS_RECEIPT_STEP` |
| Inventory.xlsx | `SIM_ROUND`, `SIM_STEP` |
| Financial Postings.xlsx | `SIM_ROUND`, `SIM_STEP` |

**Sheet names:** The uploader checks the preferred sheet name first (e.g. `Sales`, `Carbon_Emissions`),
then searches all sheets for the required columns — so non-standard sheet names will still work
as long as the columns are present.

**Deployment note:** On Streamlit Cloud, the filesystem is reset on each deployment.
Uploaded files persist for the current session only.
""")

st.caption("CAPE Data Upload | SAIES Research | CSULA CIS | NSF Grant Project")
