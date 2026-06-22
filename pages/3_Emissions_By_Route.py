"""
CAPE: Sales & Carbon Intelligence
===================================
Analyzes LAX air freight data to reveal carbon exposure patterns across
carriers, routes, product categories, and delivery status.

Data required (in data/ folder):
  - lax_cargo.csv           - LAWA monthly freight volume (2006-2023)
  - LAX_Sales.xlsx           - Per-shipment LAX data with revenue/cost
  - LAX_Carbon_Emissions.xlsx - Per-shipment emissions (ICAO/DEFRA methodology)

Author: Brian Ta · Daniel Ramirez | Advisor: Dr. Ming Wang | SAIES Research | CSULA CIS | NSF Grant Project
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from data_loader import load_lax_aggregate, load_lax_shipments

TEAL   = "#1D9E75"
AMBER  = "#BA7517"
RED    = "#E24B4A"
BLUE   = "#185FA5"
CORAL  = "#D85A30"
PURPLE = "#7B4FA0"
GRAY   = "#888780"

AIR_CARBON_FACTOR = 1.13
GROUND_CARBON_FACTOR = 0.023
AVG_HAUL_MILES = 2500


# ── Page ──────────────────────────────────────────────────────────────────────

def main():
    try:
        lax = load_lax_aggregate()
        agg_ok = True
    except Exception:
        lax = None
        agg_ok = False

    try:
        sales, carbon = load_lax_shipments()
        ship_ok = True
    except Exception:
        sales, carbon = None, None
        ship_ok = False

    if not agg_ok and not ship_ok:
        st.error("Could not load LAX data. Ensure data files are in the `data/` folder.")
        st.stop()

    freight = lax[lax['CargoType'] == 'Freight'] if agg_ok else pd.DataFrame()
    mail = lax[lax['CargoType'] == 'Mail'] if agg_ok else pd.DataFrame()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("### 📊 Emissions by Route")
    st.markdown("##### Which airlines, routes, and cargo types produce the most carbon at LAX?")
    st.caption(
        "This page breaks down carbon emissions by carrier, route, product type, and delivery status — "
        "using 18 years of LAX air freight data and per-shipment analysis with ICAO/DEFRA emission factors. "
        "ICAO = International Civil Aviation Organization; DEFRA = UK Department for Environment, Food & Rural Affairs."
    )
    st.divider()

    # ── Compute metrics ──────────────────────────────────────────────────────
    total_freight = freight['AirCargoTons'].sum()
    total_mail = mail['AirCargoTons'].sum()

    intl_freight = freight[freight['Domestic_International'] == 'International']['AirCargoTons'].sum()
    dom_freight = freight[freight['Domestic_International'] == 'Domestic']['AirCargoTons'].sum()
    arrival_freight = freight[freight['Arrival_Departure'] == 'Arrival']['AirCargoTons'].sum()
    departure_freight = freight[freight['Arrival_Departure'] == 'Departure']['AirCargoTons'].sum()

    est_air_co2e = total_freight * AVG_HAUL_MILES * AIR_CARBON_FACTOR / 1e6  # million kg
    est_ground_co2e = total_freight * AVG_HAUL_MILES * GROUND_CARBON_FACTOR / 1e6
    carbon_multiplier = est_air_co2e / est_ground_co2e if est_ground_co2e > 0 else 49

    yearly_freight = freight.groupby('year')['AirCargoTons'].sum()
    peak_year = yearly_freight.idxmax()
    peak_year_val = yearly_freight.max()

    yearly_freight_2019 = yearly_freight.get(2019, 0)
    yearly_freight_2021 = yearly_freight.get(2021, 0)
    surge_pct = (yearly_freight_2021 / yearly_freight_2019 - 1) * 100 if yearly_freight_2019 > 0 else 0

    # ── Key Finding ──────────────────────────────────────────────────────────
    st.warning(
        f"🔍 **Key Finding:** LAX handled **{total_freight/1e6:.1f} million tons** of air freight "
        f"from 2006–2023. If this cargo had moved by ground instead of air, estimated carbon "
        f"emissions would have been **{carbon_multiplier:.0f}x lower** — a difference of approximately "
        f"**{(est_air_co2e - est_ground_co2e):,.0f} million kg CO2e**. International routes account for "
        f"{intl_freight/total_freight*100:.1f}% of all freight, making them the largest carbon exposure."
    )
    st.divider()

    # ── KPI cards ────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Freight", f"{total_freight/1e6:.1f}M tons",
                  help="Total LAX air freight volume 2006–2023")
    with c2:
        st.metric("Est. Air CO2e", f"{est_air_co2e:,.0f}M kg",
                  help=f"Estimated carbon from air transport ({AIR_CARBON_FACTOR} kg CO2e/ton-mile × {AVG_HAUL_MILES} avg miles)")
    with c3:
        st.metric("International Share", f"{intl_freight/total_freight*100:.1f}%",
                  help="Percentage of freight that is international (longer routes = more carbon)")
    with c4:
        st.metric("2021 Surge", f"+{surge_pct:.1f}%",
                  help="Year-over-year increase from 2019 to 2021 (COVID supply chain disruption)")

    st.markdown("")

    # ── Time series: Freight volume with estimated CO2e ──────────────────────
    yearly_df = freight.groupby('year')['AirCargoTons'].sum().reset_index()
    yearly_df.columns = ['Year', 'Freight_Tons']
    yearly_df['Est_CO2e_M_kg'] = yearly_df['Freight_Tons'] * AVG_HAUL_MILES * AIR_CARBON_FACTOR / 1e6

    from plotly.subplots import make_subplots
    fig_ts = make_subplots(specs=[[{"secondary_y": True}]])
    fig_ts.add_trace(
        go.Bar(x=yearly_df['Year'], y=yearly_df['Freight_Tons'],
               name='Freight (tons)', marker_color=TEAL, opacity=0.7,
               hovertemplate='<b>%{x}</b><br>%{y:,.0f} tons<extra></extra>'),
        secondary_y=False)
    fig_ts.add_trace(
        go.Scatter(x=yearly_df['Year'], y=yearly_df['Est_CO2e_M_kg'],
                   name='Est. CO2e (M kg)', mode='lines+markers',
                   line=dict(color=RED, width=2), marker=dict(size=6),
                   hovertemplate='<b>%{x}</b><br>%{y:,.0f}M kg CO2e<extra></extra>'),
        secondary_y=True)
    fig_ts.update_layout(
        height=350, margin=dict(t=30, b=40),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
    fig_ts.update_yaxes(title_text="Freight (tons)", secondary_y=False,
                        showgrid=True, gridcolor="rgba(128,128,128,0.1)")
    fig_ts.update_yaxes(title_text="Est. CO2e (M kg)", secondary_y=True, showgrid=False)
    st.markdown("**Annual Freight Volume vs Estimated Carbon Emissions**")
    st.caption("Bars show total freight tonnage. The red line shows estimated carbon emissions — they move in lockstep because more air freight = more carbon.")
    st.plotly_chart(fig_ts, use_container_width=True)

    # ── Row 2: Route breakdown + Direction breakdown ─────────────────────────
    col_route, col_dir = st.columns(2)

    with col_route:
        st.markdown("**Domestic vs International Freight**")
        st.caption(
            "International routes are longer and generate more carbon per shipment. "
            "This breakdown shows where the freight is going."
        )
        route_df = freight.groupby(['year', 'Domestic_International'])['AirCargoTons'].sum().reset_index()
        fig_route = px.bar(route_df, x='year', y='AirCargoTons',
                          color='Domestic_International',
                          color_discrete_map={'International': BLUE, 'Domestic': TEAL},
                          labels={'AirCargoTons': 'Freight (tons)', 'year': 'Year',
                                  'Domestic_International': 'Route'},
                          barmode='stack')
        fig_route.update_layout(
            height=300, margin=dict(t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
        st.plotly_chart(fig_route, use_container_width=True)

    with col_dir:
        st.markdown("**Arrivals vs Departures**")
        st.caption(
            "Are we importing more than we export? Imbalances mean empty return flights — "
            "wasted fuel and carbon on planes flying back without full loads."
        )
        dir_df = freight.groupby(['year', 'Arrival_Departure'])['AirCargoTons'].sum().reset_index()
        fig_dir = px.bar(dir_df, x='year', y='AirCargoTons',
                        color='Arrival_Departure',
                        color_discrete_map={'Arrival': CORAL, 'Departure': AMBER},
                        labels={'AirCargoTons': 'Freight (tons)', 'year': 'Year',
                                'Arrival_Departure': 'Direction'},
                        barmode='group')
        fig_dir.update_layout(
            height=300, margin=dict(t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
        st.plotly_chart(fig_dir, use_container_width=True)

    # ── Row 3: Carbon intensity by route type ────────────────────────────────
    st.markdown("**Estimated Carbon Exposure by Route Type**")
    st.caption(
        "International freight travels farther, so each ton generates more carbon. "
        "This chart estimates the carbon difference between domestic and international routes."
    )

    intl_yearly = freight[freight['Domestic_International'] == 'International'].groupby('year')['AirCargoTons'].sum()
    dom_yearly = freight[freight['Domestic_International'] == 'Domestic'].groupby('year')['AirCargoTons'].sum()
    intl_co2e = (intl_yearly * 4000 * AIR_CARBON_FACTOR / 1e6).reset_index()  # ~4000 mi avg intl
    dom_co2e = (dom_yearly * 1500 * AIR_CARBON_FACTOR / 1e6).reset_index()    # ~1500 mi avg domestic
    intl_co2e.columns = ['Year', 'CO2e_M_kg']
    dom_co2e.columns = ['Year', 'CO2e_M_kg']
    intl_co2e['Route'] = 'International'
    dom_co2e['Route'] = 'Domestic'
    combined_co2e = pd.concat([intl_co2e, dom_co2e])

    fig_carbon = px.bar(combined_co2e, x='Year', y='CO2e_M_kg',
                       color='Route',
                       color_discrete_map={'International': BLUE, 'Domestic': TEAL},
                       labels={'CO2e_M_kg': 'Est. CO2e (M kg)', 'Year': 'Year'},
                       barmode='stack')
    fig_carbon.update_layout(
        height=300, margin=dict(t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
    st.plotly_chart(fig_carbon, use_container_width=True)

    # ── Seasonal pattern ─────────────────────────────────────────────────────
    st.markdown("**Monthly Freight Pattern (averaged across all years)**")
    st.caption(
        "Air freight has a seasonal cycle. Understanding when volumes peak helps predict "
        "when carbon risk is highest and when mode-switching (companies shifting cargo from ground to air transport) is most likely."
    )
    month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    monthly_avg = freight.groupby('month')['AirCargoTons'].mean().reset_index()
    monthly_avg['Month'] = monthly_avg['month'].map(lambda m: month_names[m-1])

    fig_season = px.bar(monthly_avg, x='Month', y='AirCargoTons',
                       color='AirCargoTons', color_continuous_scale='Blues',
                       labels={'AirCargoTons': 'Avg Monthly Freight (tons)', 'Month': ''})
    fig_season.update_layout(
        height=280, margin=dict(t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(categoryorder='array', categoryarray=month_names),
        showlegend=False)
    st.plotly_chart(fig_season, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # PER-SHIPMENT ANALYSIS (from LAX_Sales.xlsx + LAX_Carbon_Emissions.xlsx)
    # ══════════════════════════════════════════════════════════════════════════
    if ship_ok:
        st.divider()
        st.header("🔬 Per-Shipment Carbon Analysis (2020–2023)")
        st.caption(
            "This section uses per-shipment data with emissions calculated using ICAO/DEFRA methodology. "
            "ICAO (International Civil Aviation Organization) and DEFRA (UK Dept for Environment, Food & Rural Affairs) "
            "publish the emission factors used by airlines and governments worldwide. "
            "Data sources: LAWA (Los Angeles World Airports) Open Data Portal (tonnage), Freightos Air Index (pricing), "
            "ICAO Carbon Emissions Calculator + UK DEFRA/BEIS GHG Conversion Factors (emission factors)."
        )
        st.warning(
            "📌 **What's real and what's modeled:** The freight tonnage comes from real LAWA public records. "
            "The airline names, product types, and delivery statuses are **example values we created for this analysis** — "
            "LAWA only publishes monthly totals, not details about individual shipments. "
            "Carbon emissions are calculated using internationally recognized methods (ICAO/DEFRA), not directly measured."
        )
        st.divider()

        total_co2e = carbon['Total_CO2e_kg'].sum()
        total_rev = sales['Revenue'].sum()
        total_cost_usd = carbon['Carbon_Cost_USD'].sum()

        # ── Scope breakdown ──────────────────────────────────────────────────
        st.markdown(
            "Carbon emissions are categorized into three **scopes**: "
            "**Scope 1** is direct emissions from the flight itself (jet fuel burned). "
            "**Scope 2** is electricity used at airport facilities and ground operations. "
            "**Scope 3** is everything upstream — fuel production, aircraft manufacturing, and support services. "
            "Scope 1 is by far the largest, which is why reducing flight distance or shifting to ground transport has the biggest impact."
        )
        scope_col1, scope_col2, scope_col3, scope_col4 = st.columns(4)
        with scope_col1:
            st.metric("Total CO2e", f"{total_co2e/1e9:.2f}B kg",
                      help="Total carbon emissions across all shipments (ICAO/DEFRA methodology)")
        with scope_col2:
            st.metric("Scope 1 (Direct)", f"{carbon['Scope_1_CO2e_kg'].sum()/1e9:.2f}B kg",
                      help="Direct flight emissions — fuel burned during transport")
        with scope_col3:
            st.metric("Scope 2 (Electricity)", f"{carbon['Scope_2_CO2e_kg'].sum()/1e6:.0f}M kg",
                      help="Facility and ground operations electricity at airports")
        with scope_col4:
            st.metric("Scope 3 (Supply Chain)", f"{carbon['Scope_3_CO2e_kg'].sum()/1e9:.2f}B kg",
                      help="Upstream supply chain emissions — fuel production, aircraft manufacturing, etc.")

        st.divider()

        # ── Top carriers and routes ──────────────────────────────────────────
        col_carrier, col_route = st.columns(2)

        with col_carrier:
            st.markdown("**Carbon Emissions by Carrier**")
            st.caption("Which airlines produce the most carbon on LAX routes? Longer routes and heavier loads drive higher emissions.")
            carrier_co2e = carbon.dropna(subset=["Carrier"]).groupby('Carrier')['Total_CO2e_kg'].sum().sort_values(ascending=True).reset_index()
            carrier_co2e['Total_CO2e_B'] = carrier_co2e['Total_CO2e_kg'] / 1e9
            fig_carrier = px.bar(carrier_co2e, x='Total_CO2e_B', y='Carrier',
                                orientation='h', color='Total_CO2e_B',
                                color_continuous_scale='Reds',
                                labels={'Total_CO2e_B': 'CO2e (Billion kg)', 'Carrier': ''})
            fig_carrier.update_layout(
                height=300, margin=dict(t=10, b=10, l=10, r=10),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False)
            st.plotly_chart(fig_carrier, use_container_width=True)

        with col_route:
            st.markdown("**Carbon Emissions by Route**")
            st.caption("Which LAX routes generate the most carbon? Longer international routes dominate.")
            route_co2e = carbon.dropna(subset=["Route"]).groupby('Route')['Total_CO2e_kg'].sum().sort_values(ascending=True).reset_index()
            route_co2e['Total_CO2e_B'] = route_co2e['Total_CO2e_kg'] / 1e9
            fig_route = px.bar(route_co2e, x='Total_CO2e_B', y='Route',
                              orientation='h', color='Total_CO2e_B',
                              color_continuous_scale='Oranges',
                              labels={'Total_CO2e_B': 'CO2e (Billion kg)', 'Route': ''})
            fig_route.update_layout(
                height=300, margin=dict(t=10, b=10, l=10, r=10),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False)
            st.plotly_chart(fig_route, use_container_width=True)

        # ── Product categories and delivery status ───────────────────────────
        col_prod, col_status = st.columns(2)

        with col_prod:
            st.markdown("**Carbon by Product Category**")
            st.caption("What types of cargo generate the most emissions at LAX?")
            prod_co2e = carbon.dropna(subset=["Material/Product"]).groupby('Material/Product')['Total_CO2e_kg'].sum().sort_values(ascending=True).reset_index()
            prod_co2e['Total_CO2e_B'] = prod_co2e['Total_CO2e_kg'] / 1e9
            fig_prod = px.bar(prod_co2e, x='Total_CO2e_B', y='Material/Product',
                             orientation='h', color='Total_CO2e_B',
                             color_continuous_scale='Blues',
                             labels={'Total_CO2e_B': 'CO2e (Billion kg)', 'Material/Product': ''})
            fig_prod.update_layout(
                height=300, margin=dict(t=10, b=10, l=10, r=10),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False)
            st.plotly_chart(fig_prod, use_container_width=True)

        with col_status:
            st.markdown("**Late Delivery Carbon Penalty**")
            st.caption(
                "Late and at-risk shipments incur extra carbon from re-routing and warehousing. "
                "This is the core CAPE thesis: late orders drive avoidable carbon."
            )
            status_co2e = carbon.dropna(subset=["Delivery_Status"]).groupby('Delivery_Status').agg(
                total_co2e=('Total_CO2e_kg', 'sum'),
                overstock=('Overstock_CO2e_kg', 'sum'),
                count=('Total_CO2e_kg', 'count')
            ).reset_index()
            fig_status = go.Figure()
            fig_status.add_trace(go.Bar(
                x=status_co2e['Delivery_Status'], y=status_co2e['total_co2e'] / 1e9,
                name='Shipment CO2e', marker_color=TEAL))
            fig_status.add_trace(go.Bar(
                x=status_co2e['Delivery_Status'], y=status_co2e['overstock'] / 1e6,
                name='Overstock Penalty (M kg)', marker_color=RED))
            fig_status.update_layout(
                height=300, margin=dict(t=10, b=10),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
            st.plotly_chart(fig_status, use_container_width=True)

        # ── Revenue vs Carbon Cost ───────────────────────────────────────────
        st.markdown("**Revenue vs Carbon Cost by Shipment**")
        st.caption("Each dot is a shipment. Dots higher up and to the right generate more carbon per dollar earned.")
        fig_scatter = px.scatter(
            carbon.merge(sales[['Date', 'Revenue']], on='Date', how='left').dropna(subset=['Revenue']),
            x='Revenue', y='Total_CO2e_kg',
            color='Delivery_Status',
            size='Weight_tonnes',
            color_discrete_map={'On-Time': TEAL, 'Late': RED, 'At-Risk': AMBER},
            hover_data=['Route', 'Material/Product', 'Carrier'],
            labels={'Revenue': 'Revenue ($)', 'Total_CO2e_kg': 'Total CO2e (kg)'})
        fig_scatter.update_layout(
            height=350, margin=dict(t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
        st.plotly_chart(fig_scatter, use_container_width=True)

    # ── Key takeaways ────────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### Key Takeaways")

    takeaways = []
    if agg_ok and len(freight) > 0:
        takeaways.extend([
            f"**International freight dominates carbon exposure** — {intl_freight/total_freight*100:.1f}% of volume but an even larger share of emissions due to longer distances",
            f"**Arrivals exceed departures** — LAX receives {arrival_freight/total_freight*100:.1f}% of freight as arrivals, indicating a trade imbalance that means partially empty return flights",
            f"**The 2021 spike was a carbon event** — the +{surge_pct:.0f}% surge in air freight during COVID wasn't just a logistics problem, it was a carbon problem",
        ])
    if ship_ok:
        late_count = len(carbon[carbon['Delivery_Status'] == 'Late'])
        overstock_total = carbon['Overstock_CO2e_kg'].sum()
        takeaways.extend([
            f"**Late deliveries create avoidable carbon** — {late_count} late shipments generated {overstock_total:,.0f} kg in overstock carbon penalties",
            "**Scope 1 (direct flight) is the dominant emission source** — reducing flight distance or shifting to ground transport has the biggest impact",
        ])
    takeaways.append("**Mode-switching is the key lever** — every ton shifted from air to ground reduces carbon by ~49x per ton-mile")

    st.markdown("\n".join(f"- {t}" for t in takeaways))

    st.divider()
    st.caption("Sales & Carbon Intelligence | AI-Driven Analytics Platform | SAIES Research | Cal State LA · CIS | NSF Grant Project")


main()
