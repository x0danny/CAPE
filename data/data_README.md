# CAPE Data Folder — What Each File Actually Is

CAPE uses **three different kinds of data** that look similar but play very
different roles. Mixing them up is the easiest way to overstate a claim by
accident, so read this before citing any number from this folder in a paper,
slide, or dashboard caption.

| Layer | Files | What it actually is | What it proves |
|---|---|---|---|
| **1. Real LAX cargo** | `lax_cargo.csv` | Real monthly freight/mail tonnage at LAX, 2006–2023. Published by LAWA via the City of LA Open Data Portal. | The real-world disruption (2021 surge) actually happened. **No carbon or order data of any kind is in this file.** |
| **2. ERPsim simulation** | `Sales.xlsx`, `Carbon Emissions.xlsx`, `Inventory.xlsx`, `Purchase Orders.xlsx`, `Purchase Orders[1].xlsx`, `Stock Transfer.xlsx`, `Fianancial Postings.xlsx`, `Company Valuation.xlsx`, `Market.xlsx`, `Supplier Prices.xlsx` | SAP's own ERP simulation output. The only dataset where orders, inventory, and carbon are linked together. | **The CAPE mechanism** — that inventory overstock is a real, sizeable, independently-generated carbon cost (≈34% of total simulated emissions). This is where any statistical claim should come from. |
| **3. LAX illustrative overlay** | `LAX_Sales.xlsx`, `LAX_Carbon_Emissions.xlsx`, `LAX_Prices.xlsx` | Real LAX tonnage and standard emission factors, combined with **assigned, not measured**, delivery-status and overstock fields. Documented in `CAPE_Data_Sources_Methodology.docx`. | A worked illustration of what the CAPE logic looks like applied to LAX. **Does not prove a statistical relationship** — the overstock penalty is a fixed rule applied to a hand-assigned status, so any correlation here is true by construction. |

## The one rule that matters

> **Any claim that lateness "predicts," "drives," or "is a leading indicator of"
> carbon must come from Layer 2 (ERPsim), and even there the honest result is
> a weak period-level relationship — not a strong predictive one.**
> Layer 3 cannot support that claim at all, because the relationship is built
> into how the file was constructed, not discovered in it.

Layer 3 is still useful — it's what makes the dashboard and the story
LAX-specific and tangible. Just present it as **illustrative**, the way the
methodology doc already does, not as a measured finding.

## Known cleanup items (not yet fixed, flagging for whoever picks this up)

- `Purchase Orders[1].xlsx` looks like an accidental duplicate of
  `Purchase Orders.xlsx` (probably a re-download that kept the browser's
  "(1)" suffix). Worth confirming and deleting the redundant one.
- File names are inconsistent (`Carbon Emissions.xlsx` vs
  `Fianancial Postings.xlsx` — note the typo — vs `LAX_Carbon_Emissions.xlsx`).
  Not worth a mass rename right now since the dashboard code
  (`data_loader.py`, `pages/3_Emissions_By_Route.py`,
  `pages/4_Ask_A_Question.py`, `pages/5_Data_&_Downloads.py`) references
  several of these by exact filename — renaming would break the live app.
  Leave names as-is; this README is the fix for now.

## Methodology reference

For full column-by-column provenance (what's directly sourced, what's
calculated, what's representative) see `CAPE_Data_Sources_Methodology.docx`
in this folder.
