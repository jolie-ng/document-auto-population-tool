# Generic replication pack: test report (22 Nov 2026)

The third round of fixes, ported from the insurance version's `main.py`
— missing companion, same-policy-different-case, wrong Tag, duplicate
function, and the companion text cache. The full run logs are in the
test set's `04_logs` folder; this report is the short version.

## What changed

Five fixes went into `main.py` (214 lines → 223). Everything else is
untouched — `extract.py`, `clean.py` and `fill.py` are identical to the
last version, and the guide's appendices match the code line for line.

1. **Missing companion PDF.** If a case needs a companion type and none
   matches, the run prints a warning and every required field of that
   type flags as Not found.
2. **Same policy, different case.** When both PDFs carry a main reference
   number, that number alone decides whether they're the same case. The
   secondary reference is only a fallback when one side has none.
3. **Wrong Tag in Word.** Each Tag the letter doesn't have gets a row in
   `exceptions.csv` ("Tag not in letter") and counts toward the flag
   total, so the case becomes Needs review.
4. **Duplicate function.** `person_from_text` now just calls
   `_value_after` instead of repeating it.
5. **Companion text cache.** Each companion PDF is read once per run and
   reused, instead of once per case. Measured: 19 reads for 19 PDFs.

Two things were deliberately not ported: the source-PDF logging (the
generic version already had it) and the shorter draft name (the draft
name format stays a FILL IN setting). Nothing was copied from the
insurance reference file.

## The enrolment run

Setup: education enrolment, 6 cases plus 1 decoy, 19 synthetic PDFs.
FILL IN values used — statuses Accepted / Conditional Offer /
Waitlisted; currency prefixes USD, US$, $; amounts as `${amount}`;
dates as `{dd}/{mm}/{yyyy}`; address stop label "issued by".

Result: **6 drafts, 4 flags**, same as the last run.

- Ana — 0 flags. Ben — 1 (blank Date Submitted). Chloe — 0 (her
  multi-page Amount Due, $7,695.00, came from page 3; her Fee
  Statement has no reference number, so it still matched on the
  secondary reference). Dev — 0. Elena — 2 (unexpected status, negative
  discount). Finn — 1 (EUR amount the prefix list doesn't cover).
- The decoy (ZaraQuinn, ENR-1999) was never merged into any case, and
  the `_old` letter was ignored.
- All 60 draft controls are byte-for-byte identical to the last run, in
  value and in black fill colour. The full `exceptions.csv` and
  `requests.csv` are in `enrolment_test_set/doc_tool/04_logs/`.

## The three fixes, tested on their own

The enrolment set can't trigger fixes 1–3, so each was tested on a
throwaway copy:

- Delete Finn's Aid Award → the warning prints, two "(no Aid Award
  PDF)" Not found rows appear, Finn goes from 1 flag to 3. The other
  five cases don't change.
- Give the decoy Ana's secondary reference but keep its own reference
  number → it doesn't merge into her case. Her Amount Due stays her
  own $1,120.00.
- Rename a Tag wrong in `field_mapping.csv` → 6 "Tag not in letter"
  rows, 10 flags in total, every case Needs review.

## As delivered (FILL IN parts not replaced)

Still fails safely: 6 drafts, 23 flags, every case Needs review. The
only Blank value is Ben's, which really is blank. Dates come out as
`<REPLACE: 03/11/2026>` and so on.

## Guide checks

Appendices A–D match the four `.py` files exactly. The yellow
highlights (36 in total) sit on the FILL IN lines only, and no
insurance, claim, policy, FNOL or recruitment wording appears before
Appendix E.

## Left as is

- An unknown LetterCode reports "No mapping rows found" before "not in
  letters.csv".
- `pandas` is in the install line but the code doesn't use it.
- A currency code after an amount (e.g. `100.00 EUR`) isn't detected.
- When a companion is missing, a field of that type that isn't required
  (e.g. Discount Applied) fills blank with no flag. That's the existing
  Required = No rule working as designed.
