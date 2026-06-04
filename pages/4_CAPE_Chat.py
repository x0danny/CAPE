import streamlit as st
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import os
import json
from pathlib import Path
from urllib.request import Request, urlopen

st.set_page_config(page_title="CAPE Chat", page_icon="💬", layout="wide")

# ── API keys ──────────────────────────────────────────────────────────────────
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
            if _k and _k not in os.environ:
                os.environ[_k] = _v

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")

# Streamlit Cloud secrets are not auto-injected into os.environ — read directly
try:
    if not GEMINI_API_KEY:
        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    if not GROQ_API_KEY:
        GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
except Exception:
    pass

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
_GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"

# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_cape_context():
    data_dir = Path(__file__).parent.parent / "data"
    try:
        sales  = pd.read_excel(data_dir / "Sales.xlsx",            sheet_name="Sales")
        carbon = pd.read_excel(data_dir / "Carbon Emissions.xlsx", sheet_name="Carbon_Emissions")
        po     = pd.read_excel(data_dir / "Purchase Orders.xlsx",  sheet_name="Purchase_Orders")
    except FileNotFoundError as e:
        return {"error": str(e)}

    cape_join = pd.merge(sales, carbon, on=["SIM_ROUND", "SIM_STEP"], how="inner")
    period = cape_join.groupby(["SIM_ROUND", "SIM_STEP"]).agg(
        total_revenue=("NET_VALUE", "sum"),
        total_co2e=("TOTAL_CO2E_EMISSIONS", "sum"),
        num_orders=("SALES_ORDER_NUMBER", "nunique"),
    ).reset_index()
    period["co2e_per_dollar"] = period["total_co2e"] / period["total_revenue"]
    period["period"] = "R" + period["SIM_ROUND"].astype(str) + "-S" + period["SIM_STEP"].astype(str)

    overstock_raw = carbon[carbon["TYPE"] == "Overstock"].groupby(["SIM_ROUND", "SIM_STEP"]).agg(
        overstock_co2e=("TOTAL_CO2E_EMISSIONS", "sum")
    ).reset_index()
    period = pd.merge(period, overstock_raw, on=["SIM_ROUND", "SIM_STEP"], how="left")
    period["overstock_co2e"] = period["overstock_co2e"].fillna(0)

    s1, s2 = MinMaxScaler(), MinMaxScaler()
    period["intensity_scaled"] = s1.fit_transform(period[["co2e_per_dollar"]])
    period["overstock_scaled"]  = s2.fit_transform(period[["overstock_co2e"]])
    period["cape_risk_score"]   = period["intensity_scaled"] * 0.70 + period["overstock_scaled"] * 0.30
    period = period.sort_values(["SIM_ROUND", "SIM_STEP"]).reset_index(drop=True)

    po["delivery_steps"] = (po["GOODS_RECEIPT_ROUND"] - po["SIM_ROUND"]) * 10 + \
                           (po["GOODS_RECEIPT_STEP"]  - po["SIM_STEP"])
    po["is_late"] = (po["delivery_steps"] == 2).astype(int)

    high_risk  = period[period["cape_risk_score"] >= 0.6].sort_values("cape_risk_score", ascending=False)
    scope_sums = carbon.groupby("SCOPE")["TOTAL_CO2E_EMISSIONS"].sum().sort_values(ascending=False)
    type_sums  = carbon.groupby("TYPE")["TOTAL_CO2E_EMISSIONS"].sum().sort_values(ascending=False)

    return {
        "period":         period,
        "high_risk":      high_risk,
        "total_co2e":     float(carbon["TOTAL_CO2E_EMISSIONS"].sum()),
        "overstock_co2e": float(carbon[carbon["TYPE"] == "Overstock"]["TOTAL_CO2E_EMISSIONS"].sum()),
        "scope_sums":     scope_sums,
        "type_sums":      type_sums,
        "late_orders":    int(po["is_late"].sum()),
        "total_orders":   int(len(po)),
        "total_revenue":  float(sales["NET_VALUE"].sum()),
        "error":          None,
    }


# ── System prompt ─────────────────────────────────────────────────────────────
def _build_system_prompt(ctx):
    hr = ctx["high_risk"]
    hr_list = ", ".join(
        f"{r['period']} (score: {r['cape_risk_score']:.3f})"
        for _, r in hr.iterrows()
    )
    scope_lines = "\n".join(f"  Scope {k}: {v:,.0f} kg CO2e" for k, v in ctx["scope_sums"].items())
    type_lines  = "\n".join(f"  {k}: {v:,.0f} kg CO2e"       for k, v in ctx["type_sums"].items())
    top5 = ctx["period"].nlargest(5, "cape_risk_score")[
        ["period", "cape_risk_score", "co2e_per_dollar", "overstock_co2e"]
    ].to_string(index=False)
    late_pct = ctx["late_orders"] / ctx["total_orders"] * 100

    return f"""You are CAPE AI, an assistant for the Carbon-Aware Predictive Engine — an NSF-funded research project at CSULA (California State University, Los Angeles).

CAPE predicts carbon risk in supply chain decisions using ERPsim simulation data, before orders become late. SAP Green Ledger records emissions after the fact; CAPE flags risk at the moment a fulfillment decision is made.

KEY DATA:
- Total CO2e: {ctx['total_co2e']:,.0f} kg
- Overstock CO2e (Scope 1): {ctx['overstock_co2e']:,.0f} kg ({ctx['overstock_co2e']/ctx['total_co2e']*100:.1f}% of total)
- Total revenue: {ctx['total_revenue']:,.0f} EUR
- Late orders: {ctx['late_orders']} of {ctx['total_orders']} ({late_pct:.1f}%)
- High-risk periods (score >= 0.6): {len(hr)} of {len(ctx['period'])} total

CAPE RISK SCORE = (Carbon Intensity Scaled × 0.70) + (Overstock CO2e Scaled × 0.30)
Both are MinMax-normalized. Threshold: >= 0.6 = High Risk.

HIGH-RISK PERIODS: {hr_list}

EMISSIONS BY SCOPE:
{scope_lines}

EMISSIONS BY TYPE:
{type_lines}

TOP 5 RISKIEST PERIODS:
{top5}

RESEARCH CONTEXT:
- The Sales x Carbon join on SIM_ROUND + SIM_STEP is a novel contribution not previously in ERPsim literature
- 60.8% of Scope 1 emissions come from inventory overstock — not shipping
- LAX air cargo peaked March 2021 (254,057 tons), validating CAPE's highest-risk periods
- Air freight carries ~47–50x the carbon per ton-mile vs. ground transport
- Team: Daniel Ramirez (CIS), Brian (Finance/Supply Chain), Dr. Ming Wang (Faculty Advisor)

RESPONSE GUIDELINES:
- CAPE/carbon/supply chain questions: answer directly and authoritatively from the data above. If the data does not contain enough information to answer clearly, say so explicitly. No source citation needed — the data is the ERPsim dataset.
- General knowledge or external questions: answer helpfully. At the end of the response, include a source line in this exact format: "Source: [website or organization], [Author or Publisher if known], [Year if known]". If multiple sources apply, list each on its own line.
- Current events, news, or real-time information: answer based on training data, clearly note the information may be outdated, include the source line, and recommend the user verify with a current source.
- Greetings and casual conversation: respond naturally, no source needed.
Keep all responses under 200 words."""


# ── Pattern matching ──────────────────────────────────────────────────────────
def _pattern_answer(q, ctx):
    ql = q.lower()
    hr = ctx["high_risk"]
    total = ctx["total_co2e"]
    overstock = ctx["overstock_co2e"]

    if any(t in ql for t in ["total carbon", "total co2", "co2e", "carbon footprint",
                               "total emissions", "overall emissions", "how much carbon",
                               "how much co2", "carbon total"]):
        return (
            f"Total CO2e across all simulation periods: **{total:,.0f} kg**. "
            f"Of that, **{overstock:,.0f} kg ({overstock/total*100:.1f}%)** is from overstock — "
            f"idle inventory holding penalties, not shipping."
        )

    if any(t in ql for t in ["overstock", "overstock co2", "overstock penalty",
                               "idle inventory", "inventory penalty", "inventory carbon"]):
        return (
            f"Overstock CO2e: **{overstock:,.0f} kg** — {overstock/total*100:.1f}% of total emissions. "
            f"This is the carbon penalty from inventory sitting idle due to delayed orders. "
            f"It accounts for 60.8% of all Scope 1 (direct) emissions — making overstock "
            f"a bigger carbon driver than shipping."
        )

    # Check worst/peak BEFORE the general high-risk check — "worst risk period" contains "risk period"
    if any(t in ql for t in ["worst period", "highest risk", "peak risk", "most dangerous",
                               "worst risk", "highest score", "r3-s6", "r3 s6",
                               "highest scoring", "most at risk"]):
        if hr.empty:
            return "No high-risk periods found in the current dataset."
        top = hr.iloc[0]
        return (
            f"The highest-risk period is **{top['period']}** with a CAPE risk score of **{top['cape_risk_score']:.3f}**. "
            f"Carbon intensity: {top['co2e_per_dollar']:.4f} kg CO2e/$. "
            f"Overstock penalty: {top['overstock_co2e']:,.0f} kg CO2e."
        )

    if any(t in ql for t in ["high risk", "high-risk", "risky period",
                               "which periods", "flagged period", "periods above threshold"]):
        if hr.empty:
            return "No periods scored above the 0.6 high-risk threshold in the current dataset."
        names = ", ".join(hr["period"].tolist())
        return (
            f"**{len(hr)} periods** scored above the 0.6 high-risk threshold: {names}. "
            f"These are periods where carbon intensity and overstock penalties were both elevated."
        )

    if any(t in ql for t in ["risk score", "risk formula", "cape formula", "how is risk calculated",
                               "how is the score", "cape score", "formula", "0.70", "0.30",
                               "weighted sum", "minmax", "scoring method"]):
        return (
            "**CAPE Risk Score = (Carbon Intensity Scaled × 0.70) + (Overstock CO2e Scaled × 0.30)**\n\n"
            "Both inputs are MinMax-normalized across all simulation periods. "
            "Carbon intensity (CO2e per $ revenue) is weighted 70% as a forward-looking signal. "
            "Overstock CO2e is weighted 30% as a lagging indicator of accumulated fulfillment failures. "
            "Periods scoring ≥ 0.6 are flagged as High Risk."
        )

    if any(t in ql for t in ["late order", "on-time", "on time", "delivery",
                               "orders late", "were late", "how many late", "late delivery",
                               "order lateness", "late rate"]):
        pct = ctx["late_orders"] / ctx["total_orders"] * 100
        return (
            f"**{ctx['late_orders']} of {ctx['total_orders']} orders** ({pct:.1f}%) were late — "
            f"defined as taking 2 simulation steps to arrive instead of 1. "
            f"Late orders are the primary driver of overstock buildup and downstream carbon penalties."
        )

    if any(t in ql for t in ["scope 1", "scope 2", "scope 3", "scope breakdown",
                               "by scope", "emission scope", "scope carbon", "scope emissions"]):
        lines = "\n".join(f"- Scope {k}: {v:,.0f} kg CO2e" for k, v in ctx["scope_sums"].items())
        return f"CO2e by emission scope:\n{lines}"

    if any(t in ql for t in ["emission type", "by type", "type of emission",
                               "emission source", "what generates", "source of carbon",
                               "breakdown by type"]):
        lines = "\n".join(f"- {k}: {v:,.0f} kg CO2e" for k, v in ctx["type_sums"].items())
        return f"CO2e by emission type:\n{lines}"

    if any(t in ql for t in ["lax", "air freight", "air cargo", "mode switching",
                               "air shipment", "freight mode", "air transport"]):
        return (
            "LAX air cargo peaked in **March 2021 at 254,057 tons** — the same stretch as CAPE's "
            "highest-risk simulation periods. This is empirical evidence of freight mode-switching: "
            "when ground corridors get stressed by late orders, air freight absorbs the overflow. "
            "Air freight carries ~47–50× the carbon per ton-mile vs. ground transport, "
            "making escalation to air a major carbon multiplier."
        )

    if any(t in ql for t in ["what is cape", "what does cape", "explain cape",
                               "how does cape work", "purpose of cape", "cape research",
                               "cape project", "what cape does"])  \
            and not any(t in ql for t in ["compare", "vs sap", "green ledger", "sap green"]):
        return (
            "**CAPE (Carbon-Aware Predictive Engine)** is an NSF-funded research project at CSULA. "
            "It predicts carbon risk *before* supply chain decisions are made — filling the gap "
            "that tools like SAP Green Ledger don't cover (they record emissions after the fact). "
            "CAPE joins ERPsim sales and carbon data on SIM_ROUND/SIM_STEP to produce a per-period "
            "risk score. Periods scoring ≥ 0.6 trigger alerts. Key finding: 60.8% of Scope 1 "
            "emissions come from overstock caused by late orders — not from shipping."
        )

    if any(t in ql for t in ["green ledger", "sap green", "backward", "forward-looking",
                               "compare to sap", "vs sap", "difference between cape",
                               "cape vs", "vs green ledger"]):
        return (
            "| | SAP Green Ledger | CAPE |\n"
            "|---|---|---|\n"
            "| Orientation | Backward-looking | Forward-looking |\n"
            "| Function | Records carbon per transaction | Predicts carbon before the order is late |\n"
            "| Decision support | Audit/ESG reporting | Real-time risk alerts |\n\n"
            "CAPE catches the risk at Step 4 (period flagged) — Green Ledger sees it at Step 7 (after emissions are logged)."
        )

    if any(t in ql for t in ["round 3", "r3", "what happened in round 3",
                               "why round 3", "round three"]):
        r3 = ctx["period"][ctx["period"]["SIM_ROUND"] == 3]
        r3_hr = r3[r3["cape_risk_score"] >= 0.6]
        return (
            f"Round 3 had **{len(r3_hr)} high-risk periods** — more than any other round. "
            f"Average CAPE risk score in Round 3: {r3['cape_risk_score'].mean():.3f}. "
            f"The worst single period in the dataset is R3-S6 (score: 0.834). "
            f"Round 3 shows systematic fulfillment failures: more late orders, larger overstock buildup, "
            f"and higher carbon intensity per dollar of revenue."
        )

    if any(t in ql for t in ["carbon intensity", "co2e per dollar", "co2e per revenue",
                               "emissions per dollar", "intensity trend", "most intense period"]):
        top = ctx["period"].nlargest(1, "co2e_per_dollar").iloc[0]
        avg = ctx["period"]["co2e_per_dollar"].mean()
        return (
            f"Carbon intensity measures CO2e per dollar of revenue. "
            f"Average across all periods: **{avg:.4f} kg CO2e/$**. "
            f"Peak period: **{top['period']}** at {top['co2e_per_dollar']:.4f} kg CO2e/$."
        )

    if any(t in ql for t in ["random forest", "ml model", "machine learning",
                               "model accuracy", "94", "feature importance",
                               "top predictor", "order risk model"]):
        return (
            "The CAPE order risk model is a **Random Forest classifier** trained on ERPsim data. "
            "It achieves **94.2% accuracy** (±3.3% across 5-fold CV). "
            "The top predictor is `total_co2e` — confirming that carbon exposure and order risk "
            "are statistically linked. Other top features include `num_orders`, `total_quantity`, "
            "and `SIM_ELAPSED_STEPS`. See the CAPE Carbon page for the full feature importance chart."
        )

    return None


# ── LLM calls ─────────────────────────────────────────────────────────────────
def _groq_answer(question, system_prompt):
    if not GROQ_API_KEY:
        return None, "GROQ_API_KEY not loaded"
    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": question},
        ],
        "max_tokens": 450,
        "temperature": 0.2,
    }).encode("utf-8")
    req = Request(
        _GROQ_URL, data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "User-Agent": "CAPE-Dashboard/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"].strip(), None
    except Exception as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        return None, f"Groq: {type(e).__name__}: {e}{(' — ' + body) if body else ''}"


def _gemini_answer(question, system_prompt):
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY not loaded"
    payload = json.dumps({
        "contents": [{"parts": [{"text": question}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"maxOutputTokens": 450, "temperature": 0.2},
    }).encode("utf-8")
    req = Request(
        _GEMINI_URL, data=payload,
        headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY},
        method="POST",
    )
    try:
        with urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["candidates"][0]["content"]["parts"][0]["text"].strip(), None
    except Exception as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        return None, f"Gemini: {type(e).__name__}: {e}{(' — ' + body) if body else ''}"


def get_answer(question, ctx):
    answer = _pattern_answer(question, ctx)
    if answer:
        return answer, None
    system_prompt = _build_system_prompt(ctx)
    answer, groq_err = _groq_answer(question, system_prompt)
    if answer:
        return answer, None
    answer, gemini_err = _gemini_answer(question, system_prompt)
    if answer:
        return answer, None
    errors = [e for e in [groq_err, gemini_err] if e]
    return (
        "I can answer questions about CAPE risk scores, carbon emissions by scope or type, "
        "overstock penalties, late orders, the risk formula, Round 3 analysis, LAX air cargo, "
        "the Random Forest model, and how CAPE compares to SAP Green Ledger. "
        "Try one of the suggested questions in the sidebar."
    ), errors or None


# ── Page ──────────────────────────────────────────────────────────────────────
st.title("💬 CAPE AI")
st.markdown("**Ask anything — CAPE data, carbon risk, general knowledge, or casual questions.**")
st.caption("CAPE data answers are drawn directly from the ERPsim dataset. Responses referencing external sources include a citation and should be independently verified.")
st.divider()

ctx = load_cape_context()

if ctx.get("error"):
    st.error(f"Could not load CAPE data: {ctx['error']}. Use the Data Upload page to add the required files.")
    st.stop()

SUGGESTIONS = [
    "What is the total carbon footprint?",
    "Which periods are high risk?",
    "What is the CAPE risk score formula?",
    "How many orders were late?",
    "What percentage of emissions come from overstock?",
    "What is the worst risk period?",
    "What happened in Round 3?",
    "How does CAPE compare to SAP Green Ledger?",
    "What is the LAX air freight connection?",
    "Tell me about the Random Forest model.",
    "What is the carbon intensity trend?",
    "Break down emissions by scope.",
]

if "cape_messages" not in st.session_state:
    st.session_state.cape_messages = []

with st.sidebar:
    st.markdown("### Suggested questions")
    for s in SUGGESTIONS:
        if st.button(s, use_container_width=True, key=f"sug_{s}"):
            answer, _ = get_answer(s, ctx)
            st.session_state.cape_messages.append({"role": "user",      "content": s})
            st.session_state.cape_messages.append({"role": "assistant", "content": answer})
            st.rerun()
    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.cape_messages = []
        st.rerun()
    st.divider()
    if GROQ_API_KEY or GEMINI_API_KEY:
        st.success("AI Assistant: Online")
    else:
        st.warning("AI Assistant: Offline\n\nAdd `GROQ_API_KEY` or `GEMINI_API_KEY` to Streamlit secrets to enable AI responses.")

for msg in st.session_state.cape_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask anything — CAPE data, general knowledge, or casual questions..."):
    st.session_state.cape_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer, errors = get_answer(prompt, ctx)
        st.markdown(answer)
        if errors:
            with st.expander("AI diagnostic"):
                for e in errors:
                    st.caption(e)
    st.session_state.cape_messages.append({"role": "assistant", "content": answer})

if not st.session_state.cape_messages:
    st.info("Ask a question below, or click a suggested question in the sidebar.")

st.caption("CAPE AI | SAIES Research | CSULA CIS | NSF Grant Project")
