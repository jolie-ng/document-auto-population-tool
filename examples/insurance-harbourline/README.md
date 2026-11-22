# Document Auto-Population Tool — Harbourline pilot

The insurance version of the document auto-population tool. It reads
mapped values out of system-generated claim PDFs and fills them into
Word acknowledgement and settlement letters.

Everything in here is fictional. "Harbourline General Insurance"
doesn't exist, and there's no real personal data, tenant URL,
credential or work document in this pack.

## What's in here

- `code/` — the four Python files, plus the test report for this code.
- `guides/` — the two Python build guides (reference guide and
  actions-only guide).
- `letters/` — the 7 Word letter templates: acknowledgement, settlement,
  supporting document, LOG request, reservation of rights, ex gratia,
  and private settlement.
- `sample_pdfs/v3_plus_matched_pairs/` — 29 sample PDFs, the v3 set with
  the matched-pair PDFs folded in.
- `sample_pdfs/ex_gratia/` — 25 Ex Gratia PDFs: 5 Adjustment Reports
  plus the 20 supporting PDFs for the same 5 people (FNOL, Policy
  Declaration, Repair Estimate, Medical Bill), including the 3 fixed
  files.

## Read this before using it

**The `main.py` in `code/` is not the newest version.** It's the one
tested on 22 Nov 2026 at 05:04. After that, a review found 7 real
issues, and the fixes (missing companion, same-policy different claim,
wrong Tag, wrong source PDF, duplicate function, companion text cache,
and a draft-name length fix) were applied and tested on the laptop the
tool runs on. That fixed `main.py` lives only on that laptop — swap it
in here before using or publishing this code as current.

**The letters use their original file names**
(`Harbourline_AcknowledgmentLetter_Template.docx` and so on), while the
guides' `letters.csv` expects the renamed ones
(`FNOLAcknowledgmentLetter_Template.docx`,
`SettlementDecisionLetter_Template.docx`, ...). Rename the letters to
match, or edit the `letters.csv` rows.

## Running it

```bash
pip install pdfplumber python-docx pandas
python main.py ACKNOWLEDGMENT FNOL
python main.py SETTLEMENT "Adjustment Report"
python main.py EX_GRATIA "Adjustment Report"
python main.py SUPPORTING_ACK FNOL
python main.py ROR_ACK FNOL
python main.py LOG_ACK "Policy Declaration"
python main.py PRIVATE_SETTLEMENT FNOL
```

One draft per case is saved for a person to vet, and every run is
logged (`requests.csv`, `exceptions.csv`). A field that can't be filled
cleanly is flagged with `[[CHECK: Field Name]]`, never guessed.

## Mapped fields

Only these — everything else in the letter is filled in by hand.

- FNOL: Claim Reference, Policy Number, Date of Loss, Date Reported
- Policy Declaration: Policy Number, Effective Date, Expiry Date,
  Deductible, Total Annual Premium
- Adjustment Report: Claim Reference, Policy Number, Claim Status,
  Assessment Date, Amount Claimed, Approved Amount
- Repair Estimate: Insurer Claim Reference, Estimate Date, Subtotal,
  GST (9%), Total Amount Due
- Medical Bill: Previous Address, New Address, Statement Date,
  Total Charges, Balance Due

## Known limits

- A currency code written after an amount (e.g. `100.00 EUR`) isn't
  detected.
- It runs locally, one person at a time.
