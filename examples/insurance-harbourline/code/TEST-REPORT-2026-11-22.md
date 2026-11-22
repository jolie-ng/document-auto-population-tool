# Full code — test report (22 Nov 2026)

Code taken from the actions-only build guide (extract.py, clean.py,
fill.py, main.py), with the Medical Bill companion fix in `main.py` —
source types with no Claim Reference or Policy Number are matched by
file name instead.

Tested in a fresh folder with synthetic Word letters (content controls
already added) and the real sample PDFs: v3, the matched pairs, and the
Ex Gratia set. All synthetic data.

## Results

- **extract.py** — Tan's FNOL reads cleanly: 701 characters, Claim
  Reference CLM-2026-004512, Policy POL-2026-001, Date of Loss
  21/11/2026, Date Reported 22/11/2026.
- **clean.py** — `SGD 4,990.55` becomes `$4,990.55`; `123,456` becomes
  `$123,456.00`; `340.00` becomes `$340.00`. `29 Nov 2026` becomes
  `29/11/2026`, `3 Dec 2026` becomes `03/12/2026`.
- **clean.py, statuses** — all 6 valid statuses fill unchanged; a bogus
  one flags as `[[CHECK: Claim Status]]`.
- **clean.py, negatives** — a bracketed amount on a mapped field,
  `(262.66)`, flags as "Negative amount — verify credit" instead of
  being filled.
- **fill.py** — all 4 controls filled, nothing missing, filled values
  in black.
- **main.py, ACKNOWLEDGMENT** — 8 drafts, 1 flag: Rajesh's blank Date
  Reported.
- **main.py, SUPPORTING_ACK** — 2 drafts (Priya Sharma, Tan Wei Ming),
  each with both a Repair Estimate and a Medical Bill companion merged.
  Priya's Statement Date 20/11/2026 and Total Charges $980.00 filled;
  Tan's Statement Date 29/11/2026 filled. This is the Medical Bill fix
  working.
- **main.py, EX_GRATIA** — 5 drafts, 1 flag: Farah's blank Approved
  Amount.

## Files

`extract.py`, `clean.py`, `fill.py`, `main.py` — the full code, with a
`#` comment beside every key line, as in the guide. `main.py` includes
the Medical Bill companion fix; nothing else differs from the guide
version.

## Reusing this code

In the generic replication guide, the yellow-highlighted parts are the
bits to replace with your own field names, labels, statuses, date and
amount formats, fill colour, draft naming, and companion-matching keys.
The rest of these four files can be used as-is after those replacements.
