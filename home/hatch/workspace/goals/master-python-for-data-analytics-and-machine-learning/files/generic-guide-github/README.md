# Document Auto-Population Tool

A small Python tool that reads values out of PDFs and fills them into a
Word letter. I built it so the same tool can be reused for a different
kind of document — enrolment forms, tax forms, onboarding packets, RFPs —
without rewriting it each time.

## Downloads

There are two zips on the Releases page. Grab whichever one you need:

- **generic-tool.zip** — the reusable tool itself: the four `.py` files,
  the build guide, and the enrolment test set. This is the one to use if
  you want to run it on your own documents.
- **harbourline-example.zip** — a worked insurance example in
  `examples/insurance-harbourline/`, for seeing the tool run on a full
  set of letters and PDFs. Every person, policy and claim number in it
  is made up.

## How it works

1. Put your Word letter template in `01_input_letters` and your PDFs in
   `02_input_pdfs`.
2. Run `main.py`. It pulls the mapped fields out of the PDFs, tidies
   them up (amounts become `$1,234.00`, dates become `DD/MM/YYYY`) and
   fills the matching content controls in the letter.
3. The filled drafts go to `03_output_drafts`. Nothing is sent anywhere —
   a person reviews every draft before it goes out.
4. Each run is logged in `04_logs`: `requests.csv` has one row per draft,
   `exceptions.csv` has one row per field that couldn't be filled.
5. If a value can't be filled cleanly, the tool flags it instead of
   guessing. The draft gets `[[CHECK: Field Name]]` and the case is
   marked Needs review.

## Files

- `Generic_Document_Auto-Population_Tool_Replication_Guide.docx` — the
  full build guide: what you need, the two CSVs, the Word controls, all
  the code, and a test checklist.
- `extract.py` — reads the text out of a PDF.
- `clean.py` — normalises amounts, dates and statuses, and flags what
  it can't clean.
- `fill.py` — fills the letter's content controls. Filled text comes out
  black.
- `main.py` — runs the whole thing: finds the letter by exact file name,
  goes through the PDFs, matches companion PDFs to the same case, fills
  one draft per case, and writes the logs.
- `enrolment_test_set/` — a complete example (education enrolment): 6
  cases, the template, the PDFs, the drafts it produced, and the logs.
- `TEST-REPORT-generic-2026-11-22.md` — what was tested and what came out.

## Making it yours

The code is generic, but it has FILL IN parts (highlighted yellow in the
guide) that belong to your use case. Replace these before it will work:

- field names, source labels and letter codes in `letters.csv` and
  `field_mapping.csv`
- the valid statuses, currency prefixes, and amount/date formats in
  `clean.py`
- the fill colour in `fill.py` (black, `000000`, by default)
- the draft file-name format and the companion-matching keys in `main.py`

Until you replace them, the tool still runs — but it flags everything
and fills nothing silently. The test report shows what that looks like.

## The rules it follows

- A letter is found by its exact file name in `letters.csv`. No guessing
  from similar names.
- Companion PDFs are matched to a case by its main reference number. The
  secondary reference is only a fallback when one side has no main
  reference, and a companion with no reference at all is matched by file
  name.
- If a needed companion PDF is missing, its required fields flag as Not
  found instead of staying blank with no explanation.
- If a content control's Tag is missing from the letter, that's logged as
  "Tag not in letter" and counts as a flag.
- A blank value, an unexpected status, a negative amount in brackets, or
  a value that can't be normalised is flagged, never filled.

## Quick start (enrolment example)

```bash
pip install pdfplumber python-docx pandas
cd enrolment_test_set/doc_tool
# first replace the FILL IN values in clean.py (see TEST-REPORT §2), then:
python main.py ENROL_CONFIRM "Enrolment Form"
```

You should get 6 drafts and 4 flags: Ben's blank Date Submitted,
Elena's unexpected status and negative discount, and Finn's EUR amount.

## Data

All test data is synthetic. Every person, reference number, amount and
address in the enrolment test set is fictional.

## Known limits

- A currency code written after an amount (e.g. `100.00 EUR`) isn't
  detected.
- It runs locally, one person at a time. There's no shared queue or
  multi-user review flow.
- An amount whose currency prefix isn't in your list flags as "Could not
  normalise", not as a blank value.
