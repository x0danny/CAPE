import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="CAPE Data Upload", page_icon="📁", layout="wide")

st.title("📁 Data Upload")
st.markdown("**Upload LAX air freight data or ERPsim training data for CAPE analysis**")
st.markdown("##### Team")
st.markdown("Brian Ta · Daniel Ramirez")
st.markdown("##### Advisor")
st.markdown("Dr. Ming Wang")
st.caption("CSULA CIS | SAIES Research | NSF Grant Project")

st.caption(
    "CAPE analyzes LAX air freight data to predict carbon risk from supply chain mode-switching. "
    "Upload updated LAX cargo data to extend the analysis, or upload ERPsim files to retrain "
    "CAPE's predictive model with different simulation scenarios."
)
st.divider()

DATA_DIR = Path(__file__).parent.parent / "data"

DATASETS = {
    "LAX Cargo (Monthly Aggregate)": {
        "filename": "lax_cargo.csv",
        "type": "csv",
        "required": ["ReportPeriod", "Arrival_Departure", "Domestic_International", "CargoType", "AirCargoTons"],
        "description": "LAWA Open Data — monthly air freight and mail volumes at LAX (2006–2023). Source: data.lacity.org.",
    },
    "LAX Sales (Per-Shipment)": {
        "filename": "LAX_Sales.xlsx",
        "type": "xlsx",
        "sheet": "Sheet1",
        "required": ["Date", "Revenue", "Carrier", "Origin_Airport", "Destination_Airport", "Weight_kg"],
        "description": "Per-shipment LAX cargo data with LAWA tonnage, Freightos Air Index pricing, and carrier/route detail.",
    },
    "LAX Carbon Emissions (Per-Shipment)": {
        "filename": "LAX_Carbon_Emissions.xlsx",
        "type": "xlsx",
        "sheet": "Carbon_Emissions",
        "required": ["Date", "Route", "Total_CO2e_kg", "Scope_1_CO2e_kg", "Delivery_Status"],
        "description": "Per-shipment carbon emissions using ICAO/DEFRA methodology. Includes Scope 1/2/3 and overstock penalties.",
    },
    "LAX Prices": {
        "filename": "LAX_Prices.xlsx",
        "type": "xlsx",
        "sheet": "Sheet1",
        "required": ["Date", "Price_USD_per_kg"],
        "description": "Freightos Air Index (FAX) air cargo pricing by route and date.",
    },
}


def _read_best_sheet(uploaded_file, required_cols, preferred_sheet):
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


# ── Current data status ───────────────────────────────────────────────────────
st.subheader("Current Data")

cols = st.columns(len(DATASETS))
for i, (name, cfg) in enumerate(DATASETS.items()):
    info = _file_info(DATA_DIR / cfg["filename"])
    short_name = name.split(" (")[0]
    with cols[i]:
        if info:
            st.metric(short_name, info, help=cfg["filename"])
        else:
            st.metric(short_name, "Missing", help=f"{cfg['filename']} not found in data/")

st.divider()

# ── Upload section ────────────────────────────────────────────────────────────
st.subheader("Upload New Data")
st.info(
    "Upload updated LAX cargo data (CSV) or ERPsim training files (XLSX). "
    "Files are validated for required columns before replacing existing data.",
    icon="ℹ️",
)

for name, cfg in DATASETS.items():
    with st.expander(f"**{name}** — `{cfg['filename']}`"):
        st.caption(cfg["description"])
        st.caption(f"Required columns: `{'`, `'.join(cfg['required'])}`")

        file_types = ["csv"] if cfg["type"] == "csv" else ["xlsx"]
        uploaded = st.file_uploader(
            f"Choose {name} file",
            type=file_types,
            key=f"upload_{name}",
        )
        if uploaded:
            with st.spinner("Validating..."):
                if cfg["type"] == "csv":
                    try:
                        df = pd.read_csv(uploaded)
                        if all(c in df.columns for c in cfg["required"]):
                            matched = True
                        else:
                            matched = False
                            df = None
                    except Exception:
                        df = None
                        matched = False
                else:
                    df, sheet = _read_best_sheet(uploaded, cfg["required"], cfg.get("sheet", "Sheet1"))
                    matched = df is not None

            if not matched:
                st.error(
                    f"File missing required columns: `{'`, `'.join(cfg['required'])}`. "
                    f"Check that you're uploading the correct file."
                )
            else:
                st.success(f"Valid — **{len(df):,} rows** found.")
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

with st.expander("Notes on data format and sources"):
    st.markdown("""
**LAX Cargo (Monthly Aggregate) — `lax_cargo.csv`**
Source: [LAWA Open Data Portal](https://data.lacity.org/Transportation/Los-Angeles-International-Airport-Air-Cargo-Volume/tx7r-x3hp).
Monthly freight and mail tonnage at LAX, broken down by arrival/departure and domestic/international.

**LAX Sales (Per-Shipment) — `LAX_Sales.xlsx`**
LAWA tonnage combined with Freightos Air Index pricing. Revenue and cost are calculated from published pricing data.
Carrier and product categories are representative values assigned for research demonstration.

**LAX Carbon Emissions (Per-Shipment) — `LAX_Carbon_Emissions.xlsx`**
Emissions calculated using ICAO Carbon Emissions Calculator methodology + UK DEFRA/BEIS GHG Conversion Factors.
Includes a LAWA_Annual_Validation sheet with real airport-wide emissions (2013–2022) from LAWA Sustainability Reports.

**LAX Prices — `LAX_Prices.xlsx`**
Freightos Air Index (FAX) published air cargo pricing benchmark. Licensed as Freightos Data.

**Deployment note:** On Streamlit Cloud, the filesystem is reset on each deployment.
Uploaded files persist for the current session only.
""")

st.caption("CAPE Data Upload | AI-Driven Analytics Platform | SAIES Research | CSULA CIS | NSF Grant Project")
