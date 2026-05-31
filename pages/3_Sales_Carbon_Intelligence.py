"""
CAPE — Sales & Carbon Intelligence
===================================
Connects ERPsim sales performance to carbon outcomes at the product-type
and sales-org level. Answers: which product types and orgs earn the most
while emitting the least?

Place this file in: pages/3_Sales_Carbon_Intelligence.py

Data required (in data/ folder):
  - Sales.xlsx             — ERPsim sales transactions
  - Carbon Emissions.xlsx  — ERPsim carbon records (Scope 1/2/3)

Column names confirmed via validate_data.py on 2026-05-31.

Author: SAIES Research Team · CSULA CIS · NSF Grant Project
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

# ── Color palette ─────────────────────────────────────────────────────────────
TEAL   = "#1D9E75"
AMBER  = "#BA7517"
RED    = "#E24B4A"
BLUE   = "#185FA5"
CORAL  = "#D85A30"
PURPLE = "#7B4FA0"
GRAY   = "#888780"

RISK_THRESHOLD = 0.6

# ── Confirmed column names ────────────────────────────────────────────────────
COL_ROUND        = "SIM_ROUND"
COL_STEP         = "SIM_STEP"
COL_REVENUE      = "NET_VALUE"
COL_COST         = "COST"
COL_QTY          = "QUANTITY"
COL_PRODUCT      = "MATERIAL_NUMBER"
COL_PRODUCT_DESC = "MATERIAL_DESCRIPTION"
COL_SALES_ORG    = "SALES_ORGANIZATION"
COL_REGION       = "REGION"
COL_CO2E         = "TOTAL_CO2E_EMISSIONS"
COL_TYPE         = "TYPE"

# German state → geographic group (for color coding)
REGION_GROUP = {
    "Hamburg":               "North",
    "Bremen":                "North",
    "Berlin":                "North",
    "Nrth Rhine Westfalia":  "Central",
    "Hessen":                "Central",
    "Saarland":              "Central",
    "Bavaria":               "South/East",
    "Baden-Wurttemberg":     "South/East",
    "Saxony":                "South/East",
}
GROUP_COLOR = {"North": BLUE, "Central": TEAL, "South/East": CORAL}


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    data_dir = Path(__file__).parent.parent / "data"
    try:
        sales  = pd.read_excel(data_dir / "Sales.xlsx")
        carbon = pd.read_excel(data_dir / "Carbon Emissions.xlsx")
        return sales, carbon, True
    except FileNotFoundError:
        return None, None, False
    except Exception as e:
        st.warning(f"Data load error: {e}")
        return None, None, False


def extract_product_type(material_number: pd.Series) -> pd.Series:
    """
    Convert material number (e.g. 'OO-T01') → product type ('T01').
    Falls back to the raw value if the pattern doesn't match.
    """
    return material_number.str.extract(r"-?(T\d+)$", expand=False).fillna(
        material_number
    )


def make_synthetic():
    """Reference data matching CAPE research summary numbers."""
    rows = [
        ("R1",1,6.2,0.18),("R1",2,7.8,0.22),("R1",3,8.4,0.19),
        ("R1",4,7.1,0.25),("R1",5,9.2,0.31),
        ("R2",1,8.8,0.28),("R2",2,9.4,0.35),("R2",3,10.1,0.42),
        ("R2",4,8.7,0.38),("R2",5,11.2,0.45),
        ("R3",1,9.8,0.41),("R3",2,10.4,0.48),("R3",3,11.1,0.52),
        ("R3",4,10.8,0.55),("R3",5,9.6,0.757),("R3",6,11.8,0.834),
        ("R3",7,11.6,0.749),("R3",8,8.6,0.783),("R3",9,12.5,0.708),
        ("R3",10,7.1,0.764),
        ("R4",1,14.3,0.635),("R4",2,8.9,0.633),("R4",3,12.1,0.58),
        ("R4",4,10.5,0.52),
    ]
    period_df = pd.DataFrame(rows, columns=["round","step","revenue_m","risk"])
    period_df["label"] = period_df["round"] + "-S" + period_df["step"].astype(str)

    product_df = pd.DataFrame({
        "product_type": ["T01","T02","T03","T04","T05","T06"],
        "product":      ["Type 01","Type 02","Type 03","Type 04","Type 05","Type 06"],
        "revenue_m":    [8.9,7.6,9.2,6.8,8.1,7.2],
        "intensity":    [0.079,0.118,0.092,0.171,0.082,0.143],
        "units_k":      [4.2,3.1,3.8,2.4,3.6,2.1],
        "risk_level":   ["low","medium","low","high","low","medium"],
    })

    org_df = pd.DataFrame({
        "org":    ["O3","P3","Q3","R3","S3","T3","U3"],
        "eff":    [41.0,37.2,29.7,27.5,24.9,23.7,19.4],
    })

    region_df = pd.DataFrame({
        "region": list(REGION_GROUP.keys()),
        "group":  list(REGION_GROUP.values()),
        "eff":    [38.5,33.2,29.8,27.1,24.6,22.3,31.4,28.9,25.7],
    })

    return period_df, product_df, org_df, region_df


# ── Metric computation ────────────────────────────────────────────────────────

@st.cache_data
def compute_metrics(sales: pd.DataFrame, carbon: pd.DataFrame):
    try:
        # Period key
        sales  = sales.copy()
        carbon = carbon.copy()
        sales["period"]  = sales[COL_ROUND].astype(str)  + "-S" + sales[COL_STEP].astype(str)
        carbon["period"] = carbon[COL_ROUND].astype(str) + "-S" + carbon[COL_STEP].astype(str)

        # ── 1. Period level ───────────────────────────────
        rev_p = (sales.groupby(["period",COL_ROUND,COL_STEP])[COL_REVENUE]
                 .sum().reset_index().rename(columns={COL_REVENUE:"revenue"}))
        co2_p = (carbon.groupby([COL_ROUND,COL_STEP])[COL_CO2E]
                 .sum().reset_index().rename(columns={COL_CO2E:"total_co2e"}))
        period_df = rev_p.merge(co2_p, on=[COL_ROUND,COL_STEP], how="left")
        period_df["co2e_intensity"] = period_df["total_co2e"] / period_df["revenue"]

        os_mask = carbon[COL_TYPE].astype(str).str.lower().str.contains("overstock", na=False)
        os_p = (carbon[os_mask].groupby([COL_ROUND,COL_STEP])[COL_CO2E]
                .sum().reset_index().rename(columns={COL_CO2E:"overstock_co2e"}))
        period_df = period_df.merge(os_p, on=[COL_ROUND,COL_STEP], how="left")
        period_df["overstock_co2e"] = period_df["overstock_co2e"].fillna(0)

        ci = period_df["co2e_intensity"]
        os = period_df["overstock_co2e"]
        ci_s = (ci - ci.min()) / (ci.max() - ci.min() + 1e-9)
        os_s = (os - os.min()) / (os.max() - os.min() + 1e-9)
        period_df["risk"] = ci_s * 0.70 + os_s * 0.30
        period_df["revenue_m"] = period_df["revenue"] / 1_000_000
        period_df["label"] = period_df["period"]
        period_df = period_df.sort_values([COL_ROUND, COL_STEP]).reset_index(drop=True)

        # ── 2. Product-TYPE level (group T01–T06 across all teams) ────────────
        sales["product_type"] = extract_product_type(sales[COL_PRODUCT])
        # Description: pick the most common description for each type
        desc_map = (sales.groupby("product_type")[COL_PRODUCT_DESC]
                    .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0])
                    .reset_index().rename(columns={COL_PRODUCT_DESC:"product"}))

        prod_p = (sales.groupby(["period", COL_ROUND, COL_STEP, "product_type"])[COL_REVENUE]
                  .sum().reset_index().rename(columns={COL_REVENUE:"prod_revenue"}))
        prod_p = prod_p.merge(period_df[["period","revenue","total_co2e"]], on="period", how="left")
        prod_p["rev_share"] = prod_p["prod_revenue"] / prod_p["revenue"]
        prod_p["attributed_co2e"] = prod_p["rev_share"] * prod_p["total_co2e"]

        qty_pt = (sales.groupby("product_type")[COL_QTY]
                  .sum().reset_index().rename(columns={COL_QTY:"units"}))

        product_df = (prod_p.groupby("product_type")
                      .agg(revenue_m=("prod_revenue","sum"),
                           attributed_co2e=("attributed_co2e","sum"))
                      .reset_index())
        product_df = product_df.merge(desc_map,    on="product_type", how="left")
        product_df = product_df.merge(qty_pt,      on="product_type", how="left")
        product_df["revenue_m"] /= 1_000_000
        product_df["intensity"]  = product_df["attributed_co2e"] / (product_df["revenue_m"] * 1_000_000)
        product_df["units_k"]    = product_df["units"] / 1000
        med = product_df["intensity"].median()
        product_df["risk_level"] = product_df["intensity"].apply(
            lambda x: "high" if x > med*1.3 else ("medium" if x > med*0.85 else "low"))

        # ── 3. Sales-org level ───────────────────────────────────────────
        org_p = (sales.groupby(["period",COL_ROUND,COL_STEP,COL_SALES_ORG])[COL_REVENUE]
                 .sum().reset_index().rename(columns={COL_REVENUE:"org_revenue"}))
        org_p = org_p.merge(period_df[["period","revenue","total_co2e"]], on="period", how="left")
        org_p["rev_share"] = org_p["org_revenue"] / org_p["revenue"]
        org_p["attributed_co2e"] = org_p["rev_share"] * org_p["total_co2e"]

        org_df = (org_p.groupby(COL_SALES_ORG)
                  .agg(revenue=("org_revenue","sum"),
                       attributed_co2e=("attributed_co2e","sum"))
                  .reset_index())
        org_df["eff"] = org_df["revenue"] / org_df["attributed_co2e"]
        org_df = org_df.sort_values("eff", ascending=False).reset_index(drop=True)
        org_df.rename(columns={COL_SALES_ORG:"org"}, inplace=True)

        # ── 4. Region level ───────────────────────────────────────────────
        reg_p = (sales.groupby(["period",COL_ROUND,COL_STEP,COL_REGION])[COL_REVENUE]
                 .sum().reset_index().rename(columns={COL_REVENUE:"reg_revenue"}))
        reg_p = reg_p.merge(period_df[["period","revenue","total_co2e"]], on="period", how="left")
        reg_p["rev_share"] = reg_p["reg_revenue"] / reg_p["revenue"]
        reg_p["attributed_co2e"] = reg_p["rev_share"] * reg_p["total_co2e"]

        region_df = (reg_p.groupby(COL_REGION)
                     .agg(revenue=("reg_revenue","sum"),
                          attributed_co2e=("attributed_co2e","sum"))
                     .reset_index())
        region_df["eff"] = region_df["revenue"] / region_df["attributed_co2e"]
        region_df["group"] = region_df[COL_REGION].map(REGION_GROUP).fillna("Other")
        region_df = region_df.sort_values("eff", ascending=False).reset_index(drop=True)
        region_df.rename(columns={COL_REGION:"region"}, inplace=True)

        return period_df, product_df, org_df, region_df

    except KeyError as e:
        st.error(f"Column not found: {e}. Re-run validate_data.py to diagnose.")
        return None, None, None, None
    except Exception as e:
        st.error(f"Metric error: {e}")
        return None, None, None, None


# ── Charts ────────────────────────────────────────────────────────────────────

def chart_time_series(period_df):
    from plotly.subplots import make_subplots
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=period_df["label"], y=period_df["revenue_m"],
            name="Revenue ($M)",
            mode="lines+markers",
            line=dict(color=TEAL, width=2),
            fill="tozeroy", fillcolor="rgba(29,158,117,0.07)",
            marker=dict(size=4),
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:.3f}M<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=period_df["label"], y=period_df["risk"],
            name="CAPE Risk Score",
            mode="lines+markers",
            line=dict(color=RED, width=1.5, dash="dot"),
            marker=dict(
                size=[8 if r >= RISK_THRESHOLD else 3 for r in period_df["risk"]],
                color=[RED if r >= RISK_THRESHOLD else "rgba(226,75,74,0.3)"
                       for r in period_df["risk"]],
            ),
            hovertemplate="<b>%{x}</b><br>Risk: %{y:.3f}<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=period_df["label"], y=[RISK_THRESHOLD] * len(period_df),
            name="Threshold",
            mode="lines",
            line=dict(color="rgba(226,75,74,0.22)", width=1, dash="dash"),
            hoverinfo="skip", showlegend=False,
        ),
        secondary_y=True,
    )

    fig.update_yaxes(
        title_text="Revenue ($M)",
        title_font=dict(color=TEAL, size=11),
        tickfont=dict(color=TEAL, size=10),
        tickprefix="$", ticksuffix="M",
        showgrid=True, gridcolor="rgba(128,128,128,0.1)",
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Risk Score",
        title_font=dict(color=RED, size=11),
        tickfont=dict(color=RED, size=10),
        range=[0, 1.05],
        showgrid=False,
        secondary_y=True,
    )
    fig.update_layout(
        height=230, margin=dict(t=10, b=45, l=55, r=55),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickangle=45, tickfont=dict(size=9), automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="left", x=0, font=dict(size=11)),
        hovermode="x unified",
    )
    return fig


def chart_bubble(product_df):
    fig = px.scatter(
        product_df,
        x="revenue_m", y="intensity",
        size="units_k",
        color="risk_level",
        color_discrete_map={"low": TEAL, "medium": AMBER, "high": RED},
        hover_name="product",
        hover_data={
            "product_type": True,
            "revenue_m":    ":.3f",
            "intensity":    ":.4f",
            "units_k":      ":.1f",
            "risk_level":   False,
        },
        labels={
            "revenue_m":    "Revenue ($M)",
            "intensity":    "Carbon intensity (kg CO₂e / $)",
            "units_k":      "Units (thousands)",
            "product_type": "Type",
            "risk_level":   "Risk",
        },
        size_max=32,
    )
    fig.update_layout(
        height=270,
        margin=dict(t=10,b=10,l=10,r=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickprefix="$", ticksuffix="M",
                   showgrid=True, gridcolor="rgba(128,128,128,0.1)",
                   title_font=dict(size=11), tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.1)",
                   title_font=dict(size=11), tickfont=dict(size=10)),
        legend=dict(title="Risk level", font=dict(size=11)),
    )
    return fig


def chart_org_bar(org_df):
    org_sorted = org_df.sort_values("eff", ascending=True).copy()
    n = len(org_sorted)
    # Green→red gradient: best org = teal, worst = red
    palette = [RED, CORAL, "#C96530", AMBER, AMBER, "#2DB882", TEAL]
    colors = palette[:n] if n <= 7 else [TEAL] * n

    fig = go.Figure(go.Bar(
        x=org_sorted["eff"],
        y=org_sorted["org"],
        orientation="h",
        marker_color=colors,
        hovertemplate="<b>%{y}</b><br>$%{x:.1f} revenue / kg CO₂e<extra></extra>",
    ))
    fig.update_layout(
        height=270,
        margin=dict(t=10,b=10,l=10,r=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="$ per kg CO₂e", tickprefix="$",
                   showgrid=True, gridcolor="rgba(128,128,128,0.1)",
                   title_font=dict(size=11), tickfont=dict(size=10)),
        yaxis=dict(showgrid=False, tickfont=dict(size=11)),
        showlegend=False,
    )
    return fig


def chart_region_bar(region_df):
    region_sorted = region_df.sort_values("eff", ascending=True).copy()
    region_sorted["color"] = region_sorted["group"].map(GROUP_COLOR).fillna(GRAY)

    fig = go.Figure(go.Bar(
        x=region_sorted["eff"],
        y=region_sorted["region"],
        orientation="h",
        marker_color=region_sorted["color"].tolist(),
        customdata=region_sorted["group"],
        hovertemplate="<b>%{y}</b> (%{customdata})<br>$%{x:.1f} revenue / kg CO₂e<extra></extra>",
    ))
    fig.update_layout(
        height=270,
        margin=dict(t=10,b=10,l=10,r=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="$ per kg CO₂e", tickprefix="$",
                   showgrid=True, gridcolor="rgba(128,128,128,0.1)",
                   title_font=dict(size=11), tickfont=dict(size=10)),
        yaxis=dict(showgrid=False, tickfont=dict(size=10)),
        showlegend=False,
    )
    return fig


# ── Page ──────────────────────────────────────────────────────────────────────

def main():
    # ── Load data ──────────────────────────────────────────────────────────────
    sales, carbon, data_ok = load_data()
    if data_ok:
        period_df, product_df, org_df, region_df = compute_metrics(sales, carbon)
        using_live = period_df is not None
    else:
        using_live = False

    if not using_live:
        period_df, product_df, org_df, region_df = make_synthetic()
        st.info(
            "**Reference mode** — showing research summary values. "
            "Add `Sales.xlsx` and `Carbon Emissions.xlsx` to `data/` to load live data.",
            icon="ℹ️",
        )

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("### 📊 Sales & Carbon Intelligence")
    st.caption(
        "Which product types and organizations earn the most while emitting the least? "
        "This page bridges sales performance with carbon outcomes — the missing layer "
        "between revenue reporting and carbon compliance."
    )
    st.divider()

    # ── KPI cards ─────────────────────────────────────────────────────────────
    total_rev     = product_df["revenue_m"].sum()
    avg_intensity = (product_df["intensity"] * product_df["revenue_m"]).sum() / product_df["revenue_m"].sum()
    best_region   = region_df.iloc[0]["region"] if not region_df.empty else "—"
    best_reg_eff  = region_df.iloc[0]["eff"]    if not region_df.empty else 0
    high_risk_n   = (product_df["risk_level"] == "high").sum()
    total_types   = len(product_df)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Revenue", f"${total_rev:.3f}M",
                  help="Sum across all simulation periods and product types")
    with c2:
        st.metric("Avg Carbon Intensity", f"{avg_intensity:.4f}",
                  help="kg CO₂e per $ revenue (revenue-weighted)")
    with c3:
        st.metric("Most Efficient Region", best_region,
                  help=f"${best_reg_eff:.1f} revenue per kg CO₂e")
    with c4:
        st.metric("High-Risk Product Types", f"{high_risk_n} of {total_types}",
                  help="Product types above 1.3× the median carbon intensity")

    st.markdown("")

    # ── Time series ───────────────────────────────────────────────────────────
    st.markdown("**Revenue vs. CAPE Carbon Risk Score — by simulation period**")
    st.caption(
        "Revenue growth and carbon risk moved together in Round 3. "
        "High-risk periods (score > 0.6) are marked with larger dots."
    )
    st.plotly_chart(chart_time_series(period_df), use_container_width=True)

    # ── Bottom row: Bubble + two bars ─────────────────────────────────────────
    col_bub, col_org, col_reg = st.columns([0.40, 0.30, 0.30])

    with col_bub:
        st.markdown("**Product type vs. carbon intensity**")
        st.caption(
            "Each bubble = one product type (T01–T06) aggregated across all teams. "
            "Bubble size = total units sold. Hover for exact values."
        )
        st.plotly_chart(chart_bubble(product_df), use_container_width=True)

    with col_org:
        st.markdown("**Carbon efficiency by team**")
        st.caption("$ revenue per kg CO₂e — higher is better. Green = most efficient.")
        st.plotly_chart(chart_org_bar(org_df), use_container_width=True)

    with col_reg:
        st.markdown("**Carbon efficiency by region**")
        # Region group legend
        lc = st.columns(3)
        lc[0].markdown(f"<span style='color:{BLUE};font-size:11px;'>■ North</span>", unsafe_allow_html=True)
        lc[1].markdown(f"<span style='color:{TEAL};font-size:11px;'>■ Central</span>", unsafe_allow_html=True)
        lc[2].markdown(f"<span style='color:{CORAL};font-size:11px;'>■ South/East</span>", unsafe_allow_html=True)
        st.plotly_chart(chart_region_bar(region_df), use_container_width=True)

    # ── Key finding ───────────────────────────────────────────────────────────
    st.divider()

    r2 = period_df[period_df["label"].str.startswith("R2")]
    r3 = period_df[period_df["label"].str.startswith("R3")]
    r2_rev  = r2["revenue_m"].sum()
    r3_rev  = r3["revenue_m"].sum()
    r2_risk = r2["risk"].mean()
    r3_risk = r3["risk"].mean()
    rev_delta  = ((r3_rev  - r2_rev)  / r2_rev  * 100) if r2_rev  else 0
    risk_delta = ((r3_risk - r2_risk) / r2_risk * 100) if r2_risk else 0

    best_type = product_df.loc[product_df["intensity"].idxmin(), "product_type"]
    worst_type = product_df.loc[product_df["intensity"].idxmax(), "product_type"]
    ratio = product_df["intensity"].max() / product_df["intensity"].min()

    st.info(
        f"**Key finding — revenue growth and carbon risk are not independent.** "
        f"Round 3 revenue rose **{rev_delta:.0f}%** vs Round 2, but average carbon risk "
        f"increased **{risk_delta:.0f}%**. "
        f"At the product level, **{best_type}** is the most carbon-efficient type "
        f"and **{worst_type}** the least — a **{ratio:.1f}×** difference in carbon intensity "
        f"for products that may have similar revenue profiles. "
        f"Shifting sales mix toward lower-intensity product types is a lever "
        f"for reducing carbon exposure without sacrificing revenue.",
        icon="🔍",
    )


main()
