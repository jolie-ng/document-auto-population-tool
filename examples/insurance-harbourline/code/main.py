import csv  # imports csv — reads letters.csv and field_mapping.csv, writes the two log files
import re  # imports re — cleans file-name parts and matches Claim Reference / Policy Number
import sys  # imports sys — reads the two words typed after: python main.py <LETTER_CODE> <SOURCE_TYPE>
from datetime import datetime  # imports datetime — stamps each draft's file name and each log row
from pathlib import Path  # imports Path — builds folder paths that work on Windows and Mac
 
from extract import pdf_to_text  # imports pdf_to_text from extract.py — PDF -> plain text
from clean import extract_and_clean  # imports extract_and_clean from clean.py — find, clean and flag each value
from fill import fill_letter  # imports fill_letter from fill.py — write values into the letter's controls, in black
 
BASE = Path(__file__).parent  # the doc_tool folder — the folder main.py itself sits in
LETTERS = BASE / "01_input_letters"  # folder holding the partly-filled letters — exact file names only
PDFS = BASE / "02_input_pdfs"  # folder holding the source PDFs for the run
DRAFTS = BASE / "03_output_drafts"  # folder the drafts are saved to — one draft per claim
LOGS = BASE / "04_logs"  # folder holding requests.csv and exceptions.csv
 
 
def load_letter_file(letter_code):  # defines load_letter_file — LetterCode -> exact letter file name, from letters.csv ONLY
    with open(BASE / "letters.csv", newline="", encoding="utf-8") as f:  # opens letters.csv — the LetterCode mapping table
        for r in csv.DictReader(f):  # loops through letters.csv one row at a time
            if r["LetterCode"] == letter_code:  # if this row's LetterCode matches the code you typed:
                return r["LetterFile"]  # returns that row's EXACT file name — no keyword search, no guessing
    return None  # returns None if the code is not in letters.csv — the run stops and tells you
 
 
def load_mapping(letter_code):  # defines load_mapping — ALL Extract rows for this letter, grouped by source type
    with open(BASE / "field_mapping.csv", newline="", encoding="utf-8") as f:  # opens field_mapping.csv
        rows = [r for r in csv.DictReader(f)  # keeps only rows that belong to this letter AND are Extract rows
                if r["LetterCode"] == letter_code and r["SourceType"] == "Extract"]  # Manual rows are skipped — the tool never fills them
    grouped = {}  # starts an empty dict — {SourceDocType: [rows for that type]}
    for r in sorted(rows, key=lambda r: int(r["SortOrder"])):  # sorts rows by SortOrder, then loops through them
        grouped.setdefault(r["SourceDocType"], []).append(r)  # adds each row under its source type — multi-source letters get several groups
    return grouped  # returns the grouped rows — one group per source PDF type this letter needs
 
 
def _clean_filename_part(text):  # defines _clean_filename_part — removes characters Windows bans from file names
    return re.sub(r'[\\/:*?"<>|]', "", text).strip()  # deletes \ / : * ? " < > | and trims spaces
 
 
def _normalise_name(text):  # defines _normalise_name — lowercase letters/digits only, for matching PDF file names
    return re.sub(r"[^a-z0-9]", "", text.lower())  # 'Adjustment Report' and 'AdjustmentReport' both become 'adjustmentreport'
 
 
def find_letter(letter_code):  # defines find_letter — finds the letter by EXACT file name from letters.csv
    expected = load_letter_file(letter_code)  # looks up the exact file name for this LetterCode in letters.csv
    if expected is None:  # if the LetterCode is not in letters.csv:
        print(f"Letter code {letter_code} is not in letters.csv.")  # tells you the code is unknown
        print("Add one row to letters.csv for it, then run again. No drafts were made.")  # tells you the fix — one new row, no code change
        return None  # returns None — the run stops, having made nothing
    for p in sorted(LETTERS.glob("*.docx")):  # loops through every .docx in 01_input_letters
        if p.name.lower() == expected.lower():  # EXACT name match ONLY — FNOLAcknowledgmentLetter_Template_old.docx / _v2.docx never match
            return p  # returns the exact letter file — old/_v2 copies in the same folder are ignored completely
    print(f"No letter found for {letter_code} in 01_input_letters.")  # tells you the exact letter was not found
    print(f"This letter code needs a file named exactly: {expected}")  # prints the EXACT file name expected — rename your letter to this
    print("No drafts were made.")  # confirms nothing was made
    return None  # returns None — the run stops
 
 
def find_pdfs(source_doc_type):  # defines find_pdfs — every PDF in 02_input_pdfs for ONE source type
    tag = _normalise_name(source_doc_type)  # normalises the type, e.g. Adjustment Report -> adjustmentreport
    return sorted(  # returns the matching PDFs in file-name order
        p for p in PDFS.glob("*.pdf")  # looks at every .pdf in 02_input_pdfs
        if _normalise_name(p.stem).endswith(tag))  # keeps only names ending with the type — _FNOL.pdf, _AdjustmentReport.pdf; other types ignored
 
 
def claimant_from_text(text):  # defines claimant_from_text — claimant name from the PDF, spaces removed, for the draft file name
    name = _value_after(text, "Claimant Name")  # the name after the label, same line only — None if blank or missing; main.py then falls back to the PDF file name
    return (_clean_filename_part(re.sub(r"\s+", "", name)) or None) if name else None  # removes all spaces — Tan Wei Ming becomes TanWeiMing
 
 
def _value_after(text, label):  # defines _value_after — raw value after a label, same line only — used to match companion PDFs to a claim
    for line in text.splitlines():  # loops through the text line by line
        idx = line.strip().lower().find(label.lower())  # finds the label on this line
        if idx >= 0:  # if the label is on this line:
            rest = re.sub(r"^[\s:\-]+", "", line.strip()[idx + len(label):]).strip()  # takes what follows the label
            return rest or None  # returns it — or None if blank (never the next line)
    return None  # returns None if the label never appears
 
 
def _claim_part(fill, results):  # defines _claim_part — the Claim Reference used inside the draft's file name
    for tag in ("ClaimReference", "InsurerClaimReference"):  # tries Claim Reference first, then the Repair Estimate tag
        flagged = any(r["flagged"] and r["tag"] == tag for r in results)  # checks whether that field was flagged for THIS claim
        value = (fill.get(tag) or "").strip()  # reads the filled value for that tag, if any
        if value and not flagged and not value.startswith("[[CHECK"):  # if a clean, unflagged value exists:
            return _clean_filename_part(value) or "UNKNOWN"  # returns it, file-name safe
    return "UNKNOWN"  # flagged or blank — returns UNKNOWN, never [[CHECK: ...]], in a file name
 
 
def main():  # defines main — the whole run: find letter, loop PDFs, fill one draft per claim, log each claim
    if len(sys.argv) != 3:  # if the command does NOT have exactly 2 words after main.py:
        print("Run it like this — letter code and source document type only, no file names:")  # prints the correct command shape
        print("    python main.py ACKNOWLEDGMENT FNOL")  # example 1 — FNOL Acknowledgement from FNOL PDFs
        print('    python main.py SETTLEMENT "Adjustment Report"')  # example 2 — Settlement from Adjustment Report PDFs (quotes: the type has a space)
        return  # stops — a typed file name lands here and makes nothing
    letter_code, primary_type = sys.argv[1], sys.argv[2]  # word 1 = LetterCode (letters.csv), word 2 = the PRIMARY source type to loop over
    grouped = load_mapping(letter_code)  # loads every Extract row for this letter, grouped by source type
    if primary_type not in grouped:  # if this letter has no mapping rows for the primary type you typed:
        print("No mapping rows found — check LetterCode and SourceDocType in field_mapping.csv.")  # tells you where to check
        return  # stops, having made nothing
    letter_path = find_letter(letter_code)  # finds the letter by EXACT file name via letters.csv — old/_v2 copies are never picked
    if letter_path is None:  # if the exact letter file is missing:
        return  # stops — find_letter already printed the exact file name expected
    pdf_paths = find_pdfs(primary_type)  # finds EVERY PDF of the primary type in 02_input_pdfs — you type no PDF name
    if not pdf_paths:  # if no PDF of that type is in the folder:
        tag = re.sub(r"\s+", "", primary_type)  # builds the expected suffix, e.g. FNOL or AdjustmentReport
        print(f"No PDFs matching {primary_type} found in 02_input_pdfs.")  # tells you none were found
        print(f"PDF file names for this run must end with _{tag}.pdf — for example TanWeiMing_{tag}.pdf.")  # prints the exact suffix expected
        print("No drafts were made.")  # confirms nothing was made
        return  # stops
    print(f"Letter: {letter_path.name}")  # prints the exact letter file being used — check it is not an _old/_v2 copy
    print(f"Found {len(pdf_paths)} PDF(s) matching {primary_type} in 02_input_pdfs.")  # prints how many primary PDFs the loop will process
    other_types = [t for t in grouped if t != primary_type]  # lists the letter's OTHER source types — companions for multi-source letters (none for single-source letters)
    LOGS.mkdir(exist_ok=True)  # creates 04_logs if it does not exist yet
    DRAFTS.mkdir(exist_ok=True)  # creates 03_output_drafts if it does not exist yet
    exc_is_new = not (LOGS / "exceptions.csv").exists()  # True if exceptions.csv does not exist yet — it needs a header row
    req_is_new = not (LOGS / "requests.csv").exists()  # True if requests.csv does not exist yet — it needs a header row
    exc_file = open(LOGS / "exceptions.csv", "a", newline="", encoding="utf-8")  # opens exceptions.csv in APPEND mode — old rows are never overwritten
    req_file = open(LOGS / "requests.csv", "a", newline="", encoding="utf-8")  # opens requests.csv in APPEND mode — one new row per claim per run
    exc_writer = csv.writer(exc_file)  # writer for exception rows — one row per flagged field per claim
    req_writer = csv.writer(req_file)  # writer for request rows — one row per claim per run
    if exc_is_new:  # if exceptions.csv was just created:
        exc_writer.writerow(["RunStamp", "SourceFile", "FieldName", "RawValue", "Reason", "Resolved"])  # writes its header row
    if req_is_new:  # if requests.csv was just created:
        req_writer.writerow(["RunStamp", "LetterCode", "SourceDocType", "LetterFile", "DraftFile", "FlagCount", "Status"])  # writes its header row
    total_flags = 0  # starts the flag total for the whole run at 0
    drafts_made = 0  # starts the draft total for the whole run at 0
    companion_texts = {}  # {PDF file name: text} — each companion PDF is read once and reused for every case
    try:  # everything in this block runs with both log files open — the finally block below always closes them
        for pdf_path in pdf_paths:  # THE LOOP — one primary PDF at a time; each claim is finished completely before the next begins
            print(f"Processing {pdf_path.name} ...")  # prints which PDF is being processed now
            text = pdf_to_text(pdf_path)  # extracts this PDF's text, every page
            if not text.strip():  # if the PDF produced NO text (scanned image):
                print(f"WARNING: {pdf_path.name} produced no text — is it a scanned image? Its fields will flag.")  # warns you — its fields will flag, never guess
            results = extract_and_clean(text, grouped[primary_type])  # finds, cleans and flags this PDF's fields for the primary source type
            claim_ref = _value_after(text, "Claim Reference") or _value_after(text, "Insurer Claim Reference")  # this claim's reference — used to find companion PDFs
            policy_no = _value_after(text, "Policy Number")  # this claim's policy number — the second matching key for companions
            for other_type in other_types:  # MULTI-SOURCE: for each other source type this letter needs (e.g. Repair Estimate + Medical Bill for Supporting)
                matched = False  # becomes True once a companion PDF of this type is found for this claim
                for cand in find_pdfs(other_type):  # loops through every PDF of that other type in 02_input_pdfs
                    if cand == pdf_path:  # if this candidate IS the primary PDF:
                        continue  # skips it — a PDF is never used as its own companion
                    if cand.name not in companion_texts:  # if this candidate has not been read yet in this run:
                        companion_texts[cand.name] = pdf_to_text(cand)  # extracts its text once and stores it
                    cand_text = companion_texts[cand.name]  # the candidate PDF's text — reused, never read twice
                    cand_ref = _value_after(cand_text, "Claim Reference") or _value_after(cand_text, "Insurer Claim Reference")  # the candidate's claim reference
                    cand_pol = _value_after(cand_text, "Policy Number")  # the candidate's policy number
                    if claim_ref and cand_ref:  # if BOTH PDFs carry a claim reference:
                        same_claim = claim_ref == cand_ref  # the claim reference decides alone — one policy can have several claims
                    else:  # if either PDF has no claim reference (e.g. Policy Declaration):
                        same_claim = bool(policy_no and cand_pol and policy_no == cand_pol)  # falls back to the Policy Number
                    if not same_claim and not cand_ref and not cand_pol:  # Medical Bill has NO Claim Reference or Policy Number, so the match above can never pass for it
                        cand_stem = cand.stem.rsplit("_", 1)[0]  # candidate's filename without its type suffix, e.g. PriyaSharma_MedicalBill -> PriyaSharma
                        primary_stem = pdf_path.stem.rsplit("_", 1)[0]  # primary PDF's filename without its type suffix, e.g. PriyaSharma_FNOL -> PriyaSharma
                        same_claim = cand_stem == primary_stem  # same claim if the filenames match on the person's name — PriyaSharma with PriyaSharma
                    if not same_claim:  # if the candidate belongs to a DIFFERENT claim:
                        continue  # skips it — another claim's values must never enter this draft
                    matched = True  # a companion of this type was found
                    have_tags = {r["tag"] for r in results}  # tags already filled from the primary PDF — the primary wins
                    for r in extract_and_clean(cand_text, grouped[other_type]):  # cleans the companion's fields for its source type
                        if r["tag"] not in have_tags:  # if the primary PDF did not already supply this field:
                            r["source"] = cand.name  # remembers which PDF this field came from — exceptions.csv names it
                            results.append(r)  # adds the companion's result — this is how one draft fills from 2-3 PDFs of the same claim
                    print(f"  + companion {cand.name} ({other_type}) — same claim")  # prints which companion PDF was merged into this claim's draft
                if not matched:  # if NO companion of this type exists for this claim:
                    print(f"WARNING: no {other_type} PDF found for this claim — its fields will flag.")  # warns you
                    have_tags = {r["tag"] for r in results}  # tags already filled — the primary wins
                    for r in extract_and_clean("", grouped[other_type]):  # blank text: every required field of this type flags as Not found
                        if r["tag"] not in have_tags:  # if no other PDF already supplied this field:
                            r["source"] = f"(no {other_type} PDF)"  # exceptions.csv shows the PDF is missing
                            results.append(r)  # adds the flagged field — the draft shows [[CHECK: ...]] and the claim Needs review
            results.sort(key=lambda r: r["title"])  # sorts the merged results by field name — log order only; fill order does not matter
            fill = {r["tag"]: r["value"] for r in results}  # builds the fill dict {ControlTag: value} — flagged fields hold their [[CHECK: ...]] marker
            flags = [r for r in results if r["flagged"]]  # collects THIS claim's flagged fields only
            claimant_part = claimant_from_text(text) or (_clean_filename_part(pdf_path.stem.rsplit("_", 1)[0]) or pdf_path.stem)  # claimant for the file name — from the PDF, else the PDF's file name without its type suffix (AhmadZulkifli_AdjustmentReport -> AhmadZulkifli; a name with no _ keeps its full name)
            claim_part = _claim_part(fill, results)  # claim reference for the file name — UNKNOWN if that field was flagged/blank
            now = datetime.now()  # takes the time NOW — at the moment THIS claim is processed
            stamp = now.strftime("%Y%m%d-%H%M")  # log stamp for this claim's rows: YYYYMMDD-HHMM
            file_stamp = now.strftime("%Y%m%d-%H%M-%S")  # draft-name stamp WITH seconds — two drafts in one minute never overwrite each other
            draft_name = (f"{claimant_part}_DRAFT_{file_stamp}"  # draft name part 1: ClaimantName_DRAFT_date-time-seconds
                          f"_ClaimReference={claim_part}_{letter_path.name}")  # draft name part 2: _ClaimReference=<ref>_<exact letter file name>
            missing = fill_letter(letter_path, DRAFTS / draft_name, fill)  # fills a FRESH copy of the letter with only THIS claim's values and saves this draft
            for tag in missing:  # for each Tag the letter does not contain:
                print(f"WARNING: tag {tag} was not found in the letter — check the control's Tag in Word.")  # warns you — fix the Tag in Word, do not ignore it
            for r in flags:  # logs THIS claim's flags — one exceptions.csv row per flagged field
                exc_writer.writerow([stamp, r.get("source", pdf_path.name), r["title"], r["raw"], r["reason"], "No"])  # row: run, source PDF, field, raw value, reason, Resolved=No
            titles = {r["tag"]: r["title"] for r in results}  # Tag -> field name, for the missing-tag rows below
            for tag in missing:  # logs each Tag the letter lacks — that field stayed unfilled in the draft
                exc_writer.writerow([stamp, letter_path.name, titles.get(tag, tag), "", "Tag not in letter", "No"])  # row: run, letter file, field, no raw value, reason, Resolved=No
            flag_count = len(flags) + len(missing)  # THIS claim's flags — flagged fields plus unfilled tags
            status = "Needs review" if flag_count else "Ready for review"  # THIS claim's status — any flag means Needs review
            req_writer.writerow([stamp, letter_code, primary_type, letter_path.name, draft_name, flag_count, status])  # logs THIS claim's requests.csv row
            exc_file.flush()  # writes this claim's exception rows to disk NOW — a crash mid-loop loses nothing already done
            req_file.flush()  # writes this claim's request row to disk NOW
            drafts_made += 1  # adds 1 to the draft total
            total_flags += flag_count  # adds this claim's flag count to the run total
            print(f"Draft saved: 03_output_drafts/{draft_name}")  # prints where THIS claim's draft was saved
            print(f"Flags: {flag_count} (see 04_logs/exceptions.csv)")  # prints THIS claim's flag count
    finally:  # runs whether the loop finished or stopped on an error:
        exc_file.close()  # closes exceptions.csv
        req_file.close()  # closes requests.csv
    print(f"Done: {drafts_made} draft(s) saved to 03_output_drafts, {total_flags} flag(s) in total (see 04_logs/exceptions.csv).")  # prints the run total
    print("A person still reviews every draft. Nothing has been sent.")  # reminder — the tool never sends a letter
 
 
if __name__ == "__main__":  # runs only when you run main.py directly from the Terminal
    main()  # starts the run


