import re
import streamlit as st
import pandas as pd
import os
import json
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import date

st.set_page_config(page_title="Ask a Question", page_icon="💬", layout="wide")

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
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

try:
    if not GEMINI_API_KEY:
        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    if not GROQ_API_KEY:
        GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
    if not TAVILY_API_KEY:
        TAVILY_API_KEY = st.secrets.get("TAVILY_API_KEY", "")
except Exception:
    pass

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
_GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
_TAVILY_URL = "https://api.tavily.com/search"

# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_cape_context():
    data_dir = Path(__file__).parent.parent / "data"
    ctx = {"error": None}

    try:
        lax = pd.read_csv(data_dir / "lax_cargo.csv")
        lax['AirCargoTons'] = lax['AirCargoTons'].str.replace(',', '').astype(float)
        lax['date'] = pd.to_datetime(lax['ReportPeriod'], format='%b %Y')
    except Exception as e:
        return {"error": str(e)}

    freight = lax[lax['CargoType'] == 'Freight']
    mail = lax[lax['CargoType'] == 'Mail']

    yearly = freight.groupby(freight['date'].dt.year)['AirCargoTons'].sum()
    monthly = freight.groupby('ReportPeriod')['AirCargoTons'].sum()

    intl = freight[freight['Domestic_International'] == 'International']['AirCargoTons'].sum()
    dom = freight[freight['Domestic_International'] == 'Domestic']['AirCargoTons'].sum()
    arrivals = freight[freight['Arrival_Departure'] == 'Arrival']['AirCargoTons'].sum()
    departures = freight[freight['Arrival_Departure'] == 'Departure']['AirCargoTons'].sum()

    peak_month = freight.groupby('ReportPeriod')['AirCargoTons'].sum()
    peak_month_idx = peak_month.idxmax()
    peak_month_val = peak_month.max()

    total_freight = freight['AirCargoTons'].sum()
    total_mail = mail['AirCargoTons'].sum()

    first_year_total = yearly.iloc[0]
    last_year_total = yearly.iloc[-1]
    overall_change = (last_year_total / first_year_total - 1) * 100

    peak_year = yearly.idxmax()
    peak_year_val = yearly.max()
    low_year = yearly.idxmin()
    low_year_val = yearly.min()

    covid_2019 = yearly.get(2019, 0)
    covid_2021 = yearly.get(2021, 0)
    covid_surge = (covid_2021 / covid_2019 - 1) * 100 if covid_2019 > 0 else 0

    crisis_2006 = yearly.get(2006, 0)
    crisis_2009 = yearly.get(2009, 0)
    crisis_drop = (crisis_2009 / crisis_2006 - 1) * 100 if crisis_2006 > 0 else 0

    ctx.update({
        "lax_raw": lax,
        "freight": freight,
        "yearly": yearly,
        "total_freight": total_freight,
        "total_mail": total_mail,
        "intl_tons": intl,
        "dom_tons": dom,
        "arrivals_tons": arrivals,
        "departures_tons": departures,
        "peak_month": peak_month_idx,
        "peak_month_tons": peak_month_val,
        "peak_year": int(peak_year),
        "peak_year_tons": peak_year_val,
        "low_year": int(low_year),
        "low_year_tons": low_year_val,
        "first_year": int(yearly.index[0]),
        "last_year": int(yearly.index[-1]),
        "first_year_tons": first_year_total,
        "last_year_tons": last_year_total,
        "overall_change_pct": overall_change,
        "covid_surge_pct": covid_surge,
        "crisis_drop_pct": crisis_drop,
        "intl_pct": intl / total_freight * 100,
        "num_years": int(yearly.index[-1] - yearly.index[0] + 1),
    })

    # Load per-shipment LAX data if available
    try:
        lax_sales = pd.read_excel(data_dir / "LAX_Sales.xlsx")
        lax_carbon = pd.read_excel(data_dir / "LAX_Carbon_Emissions.xlsx", sheet_name="Carbon_Emissions")

        carriers = lax_carbon.groupby("Carrier")["Total_CO2e_kg"].sum().sort_values(ascending=False)
        routes = lax_carbon.groupby("Route")["Total_CO2e_kg"].sum().sort_values(ascending=False)
        products = lax_carbon.groupby("Material/Product")["Total_CO2e_kg"].sum().sort_values(ascending=False)
        delivery_status = lax_carbon.groupby("Delivery_Status")["Total_CO2e_kg"].sum()
        late_overstock = lax_carbon[lax_carbon["Overstock_CO2e_kg"] > 0]["Overstock_CO2e_kg"].sum()

        ctx["shipment_available"] = True
        ctx["num_shipments"] = len(lax_carbon)
        ctx["total_shipment_co2e"] = float(lax_carbon["Total_CO2e_kg"].sum())
        ctx["total_scope1"] = float(lax_carbon["Scope_1_CO2e_kg"].sum())
        ctx["total_scope2"] = float(lax_carbon["Scope_2_CO2e_kg"].sum())
        ctx["total_scope3"] = float(lax_carbon["Scope_3_CO2e_kg"].sum())
        ctx["total_overstock_co2e"] = float(late_overstock)
        ctx["total_carbon_cost_usd"] = float(lax_carbon["Carbon_Cost_USD"].sum())
        ctx["total_revenue"] = float(lax_sales["Revenue"].sum())
        ctx["carriers_co2e"] = {k: f"{v:,.0f}" for k, v in carriers.head(5).items()}
        ctx["routes_co2e"] = {k: f"{v:,.0f}" for k, v in routes.head(5).items()}
        ctx["products_co2e"] = {k: f"{v:,.0f}" for k, v in products.items()}
        ctx["delivery_co2e"] = {k: f"{v:,.0f}" for k, v in delivery_status.items()}

        try:
            validation = pd.read_excel(data_dir / "LAX_Carbon_Emissions.xlsx", sheet_name="LAWA_Annual_Validation")
            ctx["lawa_validation"] = True
            ctx["lawa_years"] = f"{validation['Year'].iloc[0]} to {validation['Year'].iloc[-1]}"
        except Exception:
            ctx["lawa_validation"] = False
    except Exception:
        ctx["shipment_available"] = False

    return ctx


# ── System prompt ─────────────────────────────────────────────────────────────
def _build_system_prompt(ctx, search_results=None):
    today = date.today().strftime("%B %d, %Y")

    yearly_str = "\n".join(f"  {y}: {v:,.0f} tons" for y, v in ctx["yearly"].items())

    prompt = f"""You are CAPE AI, an assistant for the Carbon-Aware Predictive Engine — an NSF-funded research project at CSULA (California State University, Los Angeles).

Today's date is {today}.

CAPE is an AI-Driven Analytics Platform that predicts carbon risk in supply chain logistics using LAX air freight data. The core insight: when ground supply chains get stressed, companies switch to air freight — which produces 47-50x more carbon per ton-mile. CAPE detects these mode-switching events before they happen.

PRIMARY DATA — LAX Air Freight ({ctx['num_years']} years, {ctx['first_year']}–{ctx['last_year']}):
- Total freight volume: {ctx['total_freight']:,.0f} tons across {ctx['num_years']} years
- Total mail volume: {ctx['total_mail']:,.0f} tons
- International freight: {ctx['intl_pct']:.1f}% of total
- Arrivals: {ctx['arrivals_tons']:,.0f} tons | Departures: {ctx['departures_tons']:,.0f} tons
- Peak month: {ctx['peak_month']} ({ctx['peak_month_tons']:,.0f} tons)
- Peak year: {ctx['peak_year']} ({ctx['peak_year_tons']:,.0f} tons)
- Lowest year: {ctx['low_year']} ({ctx['low_year_tons']:,.0f} tons)
- Overall change {ctx['first_year']}→{ctx['last_year']}: {ctx['overall_change_pct']:+.1f}%
- 2008 Financial Crisis drop (2006→2009): {ctx['crisis_drop_pct']:.1f}%
- COVID supply chain surge (2019→2021): +{ctx['covid_surge_pct']:.1f}%

YEARLY FREIGHT TOTALS:
{yearly_str}

KEY EVENTS IN THE DATA:
- 2006-2007: Pre-crisis baseline ~2M tons/year
- 2008-2009: Financial crisis caused 21% freight decline
- 2010-2019: Gradual recovery, reaching pre-crisis levels by 2015
- 2020-2021: COVID disrupted ground supply chains, air freight surged +22% (mode-switching)
- 2021 March: Peak month — 254,057 tons (supply chain crisis peak)
- 2022-2023: Sharp correction as supply chains normalized (-34% from 2021 peak)

CARBON CONTEXT:
- Air freight produces ~47-50x more CO2 per ton-mile than ground transport
- Each spike in LAX air cargo = proportional spike in carbon emissions
- The 2021 surge alone represents millions of additional tons of CO2
- CAPE's value: detecting conditions that trigger mode-switching BEFORE the switch happens"""

    if ctx.get("shipment_available"):
        carriers_str = "\n".join(f"  {k}: {v} kg CO2e" for k, v in ctx["carriers_co2e"].items())
        routes_str = "\n".join(f"  {k}: {v} kg CO2e" for k, v in ctx["routes_co2e"].items())
        products_str = "\n".join(f"  {k}: {v} kg CO2e" for k, v in ctx["products_co2e"].items())
        delivery_str = "\n".join(f"  {k}: {v} kg CO2e" for k, v in ctx["delivery_co2e"].items())
        prompt += f"""

PER-SHIPMENT LAX DATA ({ctx['num_shipments']} shipments, 2020–2023):
- Total CO2e: {ctx['total_shipment_co2e']:,.0f} kg
- Scope 1 (direct flight): {ctx['total_scope1']:,.0f} kg
- Scope 2 (facility electricity): {ctx['total_scope2']:,.0f} kg
- Scope 3 (upstream supply chain): {ctx['total_scope3']:,.0f} kg
- Overstock CO2e (late delivery penalty): {ctx['total_overstock_co2e']:,.0f} kg
- Total carbon cost: ${ctx['total_carbon_cost_usd']:,.0f}
- Total revenue: ${ctx['total_revenue']:,.0f}
- Emission factors: ICAO Carbon Emissions Calculator + UK DEFRA/BEIS GHG Conversion Factors

TOP CARRIERS BY CO2e:
{carriers_str}

TOP ROUTES BY CO2e:
{routes_str}

CO2e BY PRODUCT CATEGORY:
{products_str}

CO2e BY DELIVERY STATUS:
{delivery_str}

Data sources: LAWA Open Data Portal (tonnage), Freightos Air Index (pricing), ICAO/DEFRA (emission factors)."""

    prompt += f"""

RESEARCH CONTEXT:
- CAPE is an AI-Driven Analytics Platform for carbon-awareness of LAX logistics
- Team: Brian Ta, Daniel Ramirez | Advisor: Dr. Ming Wang (Faculty Advisor) | CSULA CIS
- NSF Grant Project | SAIES Research
- Novel contribution: connecting supply chain order patterns to real-world air freight carbon impact at LAX"""

    if search_results:
        results_text = "\n\n".join(
            f"Title: {r['title']}\nURL: {r['url']}\nDate: {r['date'] or 'not specified'}\nContent: {r['content']}"
            for r in search_results
        )
        prompt += f"""

CURRENT WEB SEARCH RESULTS (live data retrieved for this question):
{results_text}

Instructions for using search results:
- Use the search results as your primary source for any current or real-world information.
- Always connect findings back to what they mean for CAPE's focus areas: carbon risk, supply chain disruptions, freight costs, emissions regulations, or LAX air cargo.
- At the end of your response, list each source you used as a numbered reference in this exact format:
  [1] Title — URL (Date)
  [2] Title — URL (Date)
- Only include sources you actually referenced in the response."""

    prompt += """

RESPONSE GUIDELINES:
- LAX data questions: answer directly and authoritatively from the dataset above. No citation needed.
- Questions about CAPE: explain it as an AI-Driven Analytics Platform focused on LAX logistics carbon risk.
- Questions with search results: lead with the insight relevant to CAPE/supply chain, then cite sources as a numbered list at the end.
- General knowledge without search results: answer helpfully; note if the information is from training data and may not reflect the latest developments.
- Greetings and casual conversation: respond naturally and professionally; no citation needed.
- Never start a response with "I'm not sure" or "I don't know" — state what you do know, then note any limitations.
- When discussing ERPsim, always clarify it was used as training data for CAPE's model — the real analysis is on LAX data.
Keep all responses under 250 words."""

    return prompt


# ── Pattern matching (minimal — almost everything goes to the LLM) ───────────
def _pattern_answer(q, ctx):
    """Only match exact, short, definitional questions. Everything else goes to LLM."""
    ql = q.lower().strip().rstrip("?").strip()

    if ql in ("what is cape", "what does cape do", "explain cape"):
        return (
            "**CAPE (Carbon-Aware Predictive Engine)** is an AI-Driven Analytics Platform and NSF-funded "
            "research project at CSULA. It predicts carbon risk in supply chain logistics by analyzing "
            f"LAX air freight data spanning {ctx['num_years']} years ({ctx['first_year']}–{ctx['last_year']}). "
            "The core insight: when ground supply chains get stressed, companies switch to air freight — "
            "which produces 47-50x more carbon per ton-mile. CAPE detects these mode-switching events "
            "before they happen, enabling intervention before carbon costs spike."
        )

    return None


# ── Web search ───────────────────────────────────────────────────────────────
_SEARCH_TRIGGERS = [
    "right now", "this year", "this month", "this week",
    "latest news", "current events", "what is happening",
    "2024", "2025", "2026",
    "other companies", "other businesses",
    "affect our business", "impact our", "affect our risk",
    "affect our carbon", "affect our supply chain",
    "freight rate today", "current shipping cost", "current fuel price",
    "carbon tax", "emissions regulation",
]

def _should_search(question):
    ql = question.lower()
    return any(t in ql for t in _SEARCH_TRIGGERS)


_CAPE_SEARCH_BIAS = (
    "supply chain carbon emissions logistics freight shipping "
    "air cargo overstock inventory regulations LAX airport"
)

_BUSINESS_TRIGGERS = [
    "affect our business", "affect my business", "impact our", "impact my",
    "our supply chain", "our carbon", "our risk", "our company",
    "current events", "news", "what is happening", "what's happening",
]

def _build_search_query(question):
    ql = question.lower()
    if any(t in ql for t in _BUSINESS_TRIGGERS):
        return f"{question} {_CAPE_SEARCH_BIAS}"
    return question


def _tavily_search(question):
    if not TAVILY_API_KEY:
        return [], "TAVILY_API_KEY not loaded"
    query = _build_search_query(question)
    payload = json.dumps({
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": 3,
        "include_answer": False,
    }).encode("utf-8")
    req = Request(
        _TAVILY_URL, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for r in data.get("results", []):
            results.append({
                "title":   r.get("title", ""),
                "url":     r.get("url", ""),
                "date":    r.get("published_date", ""),
                "content": r.get("content", "")[:600],
            })
        return results, None
    except Exception as e:
        return [], f"Search: {type(e).__name__}: {e}"


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
        return None, f"Groq: {type(e).__name__}: {e}"


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
        return None, f"Gemini: {type(e).__name__}: {e}"


def _clean_response(text):
    text = re.sub(r'\s*(\[\d+\])', r'\n\1', text)
    text = re.sub(r'\s*\(not specified\)', '', text)
    text = re.sub(r'\n(\[1\])', r'\n\n\1', text)
    return text.strip()


def get_answer(question, ctx):
    answer = _pattern_answer(question, ctx)
    if answer:
        return answer, None, False

    search_results = []
    search_err = None
    searched = False
    if TAVILY_API_KEY and _should_search(question):
        search_results, search_err = _tavily_search(question)
        searched = True

    system_prompt = _build_system_prompt(ctx, search_results if search_results else None)

    answer, groq_err = _groq_answer(question, system_prompt)
    if answer:
        return _clean_response(answer), None, searched
    answer, gemini_err = _gemini_answer(question, system_prompt)
    if answer:
        return _clean_response(answer), None, searched

    errors = [e for e in [search_err, groq_err, gemini_err] if e]
    return (
        "I can answer questions about LAX air freight data, carbon emissions by carrier and route, "
        "supply chain mode-switching, delivery status impacts, and how CAPE predicts carbon risk. "
        "Try one of the suggested questions in the sidebar, or ask your own."
    ), errors or None, searched


# ── Page ──────────────────────────────────────────────────────────────────────
st.title("💬 Ask a Question")
st.markdown("**Ask anything about LAX air freight, carbon risk, supply chain logistics, or CAPE research.**")
st.caption("Answers are grounded in 18 years of LAX air freight data (2006–2023). Questions about current events use live web search with citations.")
st.divider()

ctx = load_cape_context()

if ctx.get("error"):
    st.error(f"Could not load data: {ctx['error']}. Ensure lax_cargo.csv is in the data/ folder.")
    st.stop()

SUGGESTIONS = [
    "What is CAPE?",
    "Which LAX air cargo carriers produce the most carbon?",
    "What are the highest-emitting routes from LAX?",
    "How did COVID affect LAX air freight volume and carbon?",
    "Which product categories have the highest carbon intensity?",
    "What is the carbon impact of late deliveries at LAX?",
    "How do Scope 1, 2, and 3 emissions break down for LAX freight?",
    "Does LAX air freight reduce carbon over time?",
    "What drives spikes in LAX air cargo volume?",
    "How does air freight carbon compare to ground transport?",
    "What was the peak month and year for LAX freight?",
    "What data sources does CAPE use?",
]

if "cape_messages" not in st.session_state:
    st.session_state.cape_messages = []

with st.sidebar:
    st.markdown("### Suggested questions")
    for s in SUGGESTIONS:
        if st.button(s, use_container_width=True, key=f"sug_{s}"):
            answer, _, _ = get_answer(s, ctx)
            st.session_state.cape_messages.append({"role": "user",      "content": s})
            st.session_state.cape_messages.append({"role": "assistant", "content": answer})
            st.rerun()
    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.cape_messages = []
        st.rerun()
    st.divider()
    if GROQ_API_KEY or GEMINI_API_KEY:
        search_status = " + Web Search" if TAVILY_API_KEY else ""
        st.success(f"AI Assistant: Online{search_status}")
    else:
        st.warning("AI Assistant: Offline\n\nAdd `GROQ_API_KEY` or `GEMINI_API_KEY` to Streamlit secrets to enable AI responses.")
    if not TAVILY_API_KEY and (GROQ_API_KEY or GEMINI_API_KEY):
        st.info("Add `TAVILY_API_KEY` to Streamlit secrets to enable live web search.")

for msg in st.session_state.cape_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask anything about LAX air freight, carbon risk, or CAPE research..."):
    st.session_state.cape_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        spinner_msg = "Searching the web..." if (TAVILY_API_KEY and _should_search(prompt)) else "Thinking..."
        with st.spinner(spinner_msg):
            answer, errors, searched = get_answer(prompt, ctx)
        st.markdown(answer)
        if errors:
            with st.expander("AI diagnostic"):
                for e in errors:
                    st.caption(e)
    st.session_state.cape_messages.append({"role": "assistant", "content": answer})

if not st.session_state.cape_messages:
    st.info("Ask a question below, or click a suggested question in the sidebar.")

st.caption("CAPE AI | AI-Driven Analytics Platform | SAIES Research | CSULA CIS | NSF Grant Project")
