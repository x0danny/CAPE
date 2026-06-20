# Proposed Changes (Pending Danny's Approval)

These changes were identified during a review session but require team discussion before implementing.

## 1. Reorganize Page Order (LAX Data First)

**Problem:** The first page after home shows training exercise charts with abstract "round" labels that confuse non-technical users. The real LAX data (which everyone can understand) is buried on page 3.

**Proposed new order:**
1. CAPE Dashboard (home) — no change
2. **LAX Air Freight** — move current "Emissions by Route" to position 2 (real data first)
3. **What-If Simulator** — keep as is
4. **How CAPE Was Built** — rename current "Carbon Risk Scores" and move to position 4 (methodology page)
5. Key Findings — no change
6. Ask a Question — no change
7. Data & Downloads — no change

**Why:** Leads with real, relatable LAX data. The training exercise rounds only appear on a page explicitly about methodology, eliminating confusion about what "Round 14" means.

**Risk:** Significant restructuring — could introduce bugs. Danny's Carbon Risk Scores page would be renamed and repositioned.

## 2. Training Exercise "Rounds" Labeling

**Problem:** The x-axis labels "1-38" on Carbon Risk Scores and What-If Simulator are abstract. Users don't know what they represent. We've tried "R3-S6", "Period 24", "Week 24", and just "24" — none are intuitive without context.

**Proposed fix:** On whichever page shows the round-by-round charts, add a clear callout:
> "CAPE was trained on 38 rounds of a supply chain exercise — like a business simulation game — where orders were placed, shipped, and sometimes delayed. CAPE learned from these rounds what conditions lead to carbon waste. Then we checked: does the same pattern show up in real LAX airport data? It does."

Label x-axis as "Round 1" through "Round 38" — everyone understands "rounds" in a game context.

## 3. Clarify ERPsim Timing with Dr. Wang

**Question:** How long did each ERPsim round/step represent? Was it one class session? One week? Abstract game turns? This affects how we label the time axis accurately.

**Action:** Ask Dr. Wang before changing labels further.

## 4. Consider Splitting Emissions Page

**Current:** "Emissions by Route" has both aggregate LAX trends (18 years) and per-shipment analysis (carriers, routes, scopes). It's a long page.

**Option:** Split into "LAX Freight Trends" (aggregate) and "Carbon by Carrier & Route" (per-shipment). Would make each page more focused.

---

*Notes created 2026-06-19. Discuss with Danny before implementing any of these.*
