# 🌿 CAPE — Carbon-Aware Predictive Engine

**Predictive Analytics on Carbon-Awareness of LAX Logistics**

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-cape--dashboard.streamlit.app-brightgreen)](https://cape-dashboard.streamlit.app)
[![NSF Research](https://img.shields.io/badge/NSF-Undergraduate%20Research-blue)](https://www.nsf.gov)
[![CSULA](https://img.shields.io/badge/CSULA-CIS%20Department-gold)](https://www.calstatela.edu)

> Dr. Ming Wang · Brian · Daniel Ramirez  
> CSULA Department of CIS | SAIES Research Organization | NSF Grant Project

---

## What Is CAPE?

Most enterprise carbon accounting tools — including SAP Green Ledger (GA December 2024) — are compliance tools. They tell you what you *already* emitted. The gap nobody has filled: when a supply chain decision is being made in real time — hold this order, reroute it, or expedite it — **carbon is completely invisible at that moment.**

CAPE changes that. When an order is flagged as high risk for late delivery, CAPE calculates the downstream carbon cost of that delay *before* the fulfillment decision is made, not after.

**Research question:** Can integrating ERP transactional data with carbon emissions records produce a leading indicator of carbon exposure — surfacing risk before it becomes emissions?

**Short answer:** Yes. Late order risk is a statistically meaningful predictor of CO₂e penalties. 60.8% of all direct (Scope 1) emissions in the ERPsim dataset come from inventory overstock — not from moving goods. That's the carbon cost of delayed decisions.

---

## Key Findings

| Metric | Value | Significance |
|---|---|---|
| Total CO₂e | 421,694 kg | Full simulation carbon footprint |
| Scope 1 Direct | 234,250 kg | 55.5% of total emissions |
| Overstock CO₂e | 142,500 kg | **60.8% of all Scope 1 — not from shipping** |
| Avg Overstock Penalty | 1,827 kg/period | Carbon cost of late order buildup |
| High Risk Periods | 8 of 38 | Periods scoring above 0.6 threshold |
| Highest Risk Period | R3-S6 (score: 0.834) | Carbon intensity: 0.146 kg CO₂e/$ |
| LAX Peak Month | March 2021 | 254,057 tons — real-world validation anchor |

---

## CAPE Risk Score

```
CAPE Risk Score = (Carbon Intensity Scaled × 0.70) + (Overstock CO₂e Scaled × 0.30)
```

Periods scoring above **0.6** are flagged as High Risk and surfaced as alerts in the dashboard. Carbon intensity is weighted more heavily (70%) as a forward-looking signal; overstock penalty (30%) is a lagging indicator of accumulated fulfillment failures.

---

## Data Sources

### Internal — ERPsim (SAP University Alliance)

Provided by Dr. Ming Wang through SAP University Alliance access.

| Dataset | Rows | Key Fields |
|---|---|---|
| Sales.xlsx | 2,568 | SIM_ROUND, SIM_STEP, NET_VALUE, COST, QUANTITY |
| Carbon Emissions.xlsx | 2,397 | SCOPE, TYPE, TOTAL_CO2E_EMISSIONS, ORIGIN, DESTINATION |
| Inventory.xlsx | 6,888 | INVENTORY_OPENING_BALANCE, PLANT, STORAGE_LOCATION |
| Financial Postings.xlsx | 2,424 | GL_ACCOUNT_NAME, AMOUNT, DEBIT_CREDIT_INDICATOR |
| Purchase Orders.xlsx | — | Order-to-receipt timing, lateness proxy |
| Stock Transfer.xlsx | — | Inter-DC movements, Scope 1 emissions trigger |
| ERPSIM.xlsx | — | Competitive pricing rounds, market share by team |

The core technical contribution is joining Sales and Carbon Emissions on `SIM_ROUND` + `SIM_STEP` — a join not previously performed in ERPsim academic literature. This produces **160,132 rows** connecting every sales transaction to its corresponding carbon record across 38 matching simulation periods.

### External — LAX Air Cargo (LA Open Data Portal)

1,712 records of monthly air freight tonnage at LAX from 2006–2023 (data.lacity.org). Serves as real-world empirical grounding for the freight mode-switching logic: when ground shipments are delayed, some percentage escalate to air freight, which carries significantly higher carbon intensity per ton-mile. LAX peak (March 2021: 254,057 tons) aligns with CAPE's highest-risk simulation periods.

---

## Tech Stack

| Component | Technology |
|---|---|
| Data processing | Python, pandas |
| Analytical queries | DuckDB |
| ML models | scikit-learn (Random Forest) |
| Dashboard | Streamlit |
| Visualization | Plotly |
| Deployment | Streamlit Cloud |

---

## Project Structure

```
CAPE/
├── Home.py                  # App entry point
├── pages/
│   ├── 1_CAPE_Carbon.py     # Carbon risk scores, overstock analysis, LAX validation
│   ├── 2_Control_Tower.py   # Order risk intelligence, carbon alerts
│   └── 3_Sales_Intelligence.py  # Brian's dashboard (in progress)
├── data/                    # ERPsim datasets and LAX cargo data
├── ml/                      # Pre-trained Random Forest models
├── control_tower/           # Order risk scoring module
├── requirements.txt
└── CAPE_Analysis.ipynb      # Exploratory analysis and data join notebook
```

---

## Roadmap

| Phase | Status | Description |
|---|---|---|
| 1 — Data join + carbon risk scores | ✅ Complete | Sales × Carbon join confirmed; CAPE Risk Score implemented; LAX validation done |
| 2 — Sales Intelligence | 🔄 In progress | Merging Brian's competitive pricing dashboard as a Sales tab |
| 3 — Control Tower integration | 🔄 In progress | Integrating Random Forest order risk model as ML input to CAPE scores |
| 4 — Behavioral study | ⏳ Planned | Human-AI feedback loop study with ERPsim game participants |
| 5 — Paper + SAP presentation | ⏳ Planned | NSF research presentation (late June/early July 2026); SAP University Alliance submission |

---

## Relationship to SAP Green Ledger

| | SAP Green Ledger | CAPE |
|---|---|---|
| Orientation | Backward-looking | Forward-looking |
| Function | Records carbon per financial transaction | Predicts carbon before the order is late |
| Scope tracking | Scope 1/2/3 compliance reporting | Carbon intensity as a real-time risk signal |
| Decision support | Audit-ready ESG reporting | Alerts at the moment a fulfillment decision is made |

CAPE is the predictive layer that feeds what Green Ledger will eventually need. They are complementary, not competing.

---

## Research Gap

A 2025 systematic literature review identified ERP-native carbon prediction at the operational decision level as critically under-researched. SAP holds a patent on carbon-aware inventory optimization at the *planning* level — a different problem. No published paper has used the ERPsim carbon emissions table for ML-based predictive scoring. The combination of order risk scoring, carbon exposure forecasting, and human-AI behavioral analytics does not exist in the current literature.

---

## Team

| Name | Role |
|---|---|
| Daniel Ramirez | CIS — app development, ML, data engineering, LAX domain expertise |
| Brian | Finance/Supply Chain — sales dashboard, business framing, competitive analysis |
| Dr. Ming Wang | Faculty advisor — CIS Dept. Chair, CSULA; SAP University Alliance access |

**Affiliated with:** CSULA MBDS · SAIES Research Organization · NSF Undergraduate Research Program (Spring/Summer 2026)

---

*Live Dashboard: https://cape-dashboard.streamlit.app*
