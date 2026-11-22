import re  # imports re — pattern matching, used to find and clean amounts and dates
 
STATUSES = [  # the ONLY Claim Status values that may be filled — anything else is flagged
    "Partial Settlement",  # valid status 1 of 6
    "Full Settlement",  # valid status 2 of 6
    "Declined",  # valid status 3 of 6
    "Supplementary - Partial Settlement",  # valid status 4 of 6
    "Ex Gratia",  # valid status 5 of 6 — NEW: goodwill payment, no admission of liability
    "Declined - Ex Gratia Offer",  # valid status 6 of 6 — NEW: declined, with an ex gratia offer
]  # end of the valid-status list
 
MONTHS = {  # month name (first 3 letters) -> month number, for dates like 29 Nov 2026
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",  # Jan-Apr
    "may": "05", "jun": "06", "jul": "07", "aug": "08",  # May-Aug
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",  # Sep-Dec
}  # end of the month table
 
 
def _pad(x):  # defines _pad — turns 9 into 09 so dates always come out DD/MM/YYYY
    return x if len(x) == 2 else "0" + x  # returns the value unchanged if already 2 characters, else adds a leading 0
 
 
def normalise_amount(raw):  # defines normalise_amount — turns any amount format into $ with two decimals
    digits = re.sub(r"[^\d.]", "", raw)  # removes $, SGD, S$, commas and spaces — keeps digits and the decimal point only
    if not re.fullmatch(r"\d+(\.\d{1,2})?", digits or ""):  # checks what is left is a plain number — if not, it cannot be trusted
        return None  # returns None = could not clean — the caller flags this field, never guesses
    n = float(digits)  # converts the cleaned digits into a number — 0 is valid: $0.00 stays $0.00
    return f"${n:,.2f}"  # returns e.g. $4,990.55 — $ sign, commas, exactly two decimals, even if the PDF had no $
 
 
def normalise_date(raw):  # defines normalise_date — turns any date format into DD/MM/YYYY
    s = raw.strip()  # removes spaces at both ends of the raw date
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)  # matches 21/11/2026 — already DD/MM/YYYY
    if m:  # if that pattern matched:
        return f"{_pad(m.group(1))}/{_pad(m.group(2))}/{m.group(3)}"  # returns it padded as DD/MM/YYYY
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)  # matches 2026-11-14 — year first
    if m:  # if that pattern matched:
        return f"{_pad(m.group(3))}/{_pad(m.group(2))}/{m.group(1)}"  # reorders it to DD/MM/YYYY
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(\d{2})", s)  # matches 21-11-26 — two-digit year
    if m:  # if that pattern matched:
        return f"{_pad(m.group(1))}/{_pad(m.group(2))}/20{m.group(3)}"  # expands the year to 20xx, returns DD/MM/YYYY
    m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)  # matches 29 Nov 2026 or 21 November 2026
    if m and m.group(2)[:3].lower() in MONTHS:  # if it matched AND the month name is a real month:
        mo = MONTHS[m.group(2)[:3].lower()]  # looks up the month number, e.g. nov -> 11
        return f"{_pad(m.group(1))}/{mo}/{m.group(3)}"  # returns DD/MM/YYYY
    m = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", s)  # matches Nov 21, 2026 — month first
    if m and m.group(1)[:3].lower() in MONTHS:  # if it matched AND the month name is a real month:
        mo = MONTHS[m.group(1)[:3].lower()]  # looks up the month number
        return f"{_pad(m.group(2))}/{mo}/{m.group(3)}"  # returns DD/MM/YYYY
    return None  # no pattern matched — returns None = could not parse — the caller flags this field
def label_present(lines, label):  # defines label_present — checks whether a label appears anywhere in the text
    lbl = label.lower()  # lowercases the label so matching ignores capital letters
    return any(lbl in line.lower() for line in lines)  # returns True if any line contains the label, else False
 
 
def find_after_label(lines, label, data_type, all_labels):  # defines find_after_label — finds the value after the EXACT full label, same line only
    found = []  # starts an empty list — every value found for this label goes in here
    lbl = label.lower()  # lowercases the label for matching
    for i, line in enumerate(lines):  # loops through the PDF text line by line, keeping the line number
        idx = line.lower().find(lbl)  # finds where the label starts in this line — -1 means not on this line
        if idx < 0:  # if the label is not on this line:
            continue  # skips to the next line
        rest = re.sub(r"^[\s:\-]+", "", line[idx + len(label):])  # takes only what comes AFTER the full label, stripping leading spaces/colons
        if data_type == "Address":  # addresses are the one exception — they continue as a block over several lines
            block = [rest] if rest else []  # starts the address block with the rest of the label's line (if any)
            stops = all_labels + ["provider"]  # stop lines: any next mapped label, OR Provider (not mapped, but follows Medical Bill addresses)
            for j in range(i + 1, len(lines)):  # looks at the lines after the label line, one by one
                nxt = lines[j]  # the next line
                if not nxt:  # if the next line is blank:
                    break  # stops the address block at the blank line
                if any(nxt.lower().startswith(a) for a in stops):  # if the next line starts a new field (or Provider):
                    break  # stops the address block — that line is NOT part of this address
                block.append(nxt)  # adds this line to the address block
                if len(block) >= 6:  # safety limit — an address block never runs past 6 lines
                    break  # stops the address block at the limit
            if block:  # if any address lines were collected:
                found.append("\n".join(block))  # adds the whole address, lines joined, as one value
        elif data_type == "Amount":  # amounts must start immediately after the label
            if not rest:  # if nothing follows the label — the value is BLANK:
                continue  # skips it — NEVER reads the next line as the value; the caller flags it as Blank value
            m = re.match(r"\(?\s?(SGD|S\$|\$)?\s?\d[\d,]*(\.\d{1,2})?\)?", rest)  # matches an amount at the START of rest — a later sentence mentioning the label is not a value
            if m:  # if an amount starts there:
                found.append(m.group(0).strip())  # adds that amount, exactly as written in the PDF
        elif data_type == "Date":  # dates must start immediately after the label
            if not rest:  # if nothing follows the label — the value is BLANK:
                continue  # skips it — NEVER reads the next line; the caller flags it as Blank value
            m = re.match(r"(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{1,2}-\d{1,2}"  # matches a date at the START of rest, in any accepted format
                         r"|\d{1,2}-\d{1,2}-\d{2}|\d{1,2}\s+[A-Za-z]+\s+\d{4}"
                         r"|[A-Za-z]+\s+\d{1,2},\s*\d{4})", rest)  # end of the date patterns
            if m:  # if a date starts there:
                found.append(m.group(0).strip())  # adds that date, exactly as written in the PDF
        else:  # all other types (Text, Status) — take what follows the label on the same line
            if not rest:  # if nothing follows the label — the value is BLANK:
                continue  # skips it — NEVER reads the next line; the caller flags it as Blank value
            found.append(rest)  # adds the rest of the line as the value
    return found  # returns every value found for this label (usually one — more than one different value = conflict flag)
def extract_and_clean(pdf_text, rows):  # defines extract_and_clean — runs find + clean + flag for every mapping row of ONE source type
    lines = [ln.strip() for ln in pdf_text.splitlines()]  # splits the PDF text into trimmed lines
    all_labels = [r["SourceLabel"].lower() for r in rows]  # lists every label in these rows — used as address-block stop lines
    results = []  # starts an empty list — one result per mapping row
    for r in rows:  # loops through the mapping rows, one field at a time
        res = {"title": r["Title"], "tag": r["ControlTag"], "value": "",  # starts this field's result — value begins empty
               "raw": "", "flagged": False, "reason": ""}  # raw = as found in PDF; flagged/reason begin as no flag
        hits = find_after_label(lines, r["SourceLabel"],  # searches the text for this row's exact label
                                r["DataType"], all_labels)  # using this row's data type and the stop-label list
        if not hits:  # if NO value was found — label absent, OR label present with a blank value:
            res["flagged"] = r["Required"].strip().lower() == "yes"  # flags it if the field is Required — never invents a value
            res["reason"] = ("Blank value" if label_present(lines, r["SourceLabel"])  # reason = Blank value if the label IS there but empty
                             else "Not found")  # reason = Not found if the label never appears
        else:  # a value WAS found:
            unique = list(dict.fromkeys(hits))  # removes duplicate copies of the same value, keeping order
            res["raw"] = " | ".join(unique)  # stores the raw value(s) as found — this is what goes in exceptions.csv
            if len(unique) > 1:  # if two DIFFERENT values were found for one field:
                res["flagged"] = True  # flags it — a person must decide which is right
                res["reason"] = "Conflicting values"  # records the reason
            elif r["DataType"] == "Amount":  # cleans an amount:
                if re.fullmatch(r"\(.*\)", unique[0].strip()):  # if the amount is in (parentheses) — that means NEGATIVE:
                    res["flagged"] = True  # flags it — never fills it, positive or negative
                    res["reason"] = "Negative amount - verify credit"  # records the reason for a person to verify
                else:  # a normal amount:
                    cleaned = normalise_amount(unique[0])  # normalises it to $ with two decimals
                    if cleaned is None:  # if it could not be cleaned:
                        res["flagged"] = True  # flags it
                        res["reason"] = "Could not normalise"  # records the reason
                    else:  # cleaned successfully:
                        res["value"] = cleaned  # stores the cleaned $ value as the value to fill
            elif r["DataType"] == "Date":  # cleans a date:
                cleaned = normalise_date(unique[0])  # normalises it to DD/MM/YYYY
                if cleaned is None:  # if it could not be parsed:
                    res["flagged"] = True  # flags it
                    res["reason"] = "Could not parse date"  # records the reason
                else:  # parsed successfully:
                    res["value"] = cleaned  # stores the DD/MM/YYYY value to fill
            elif r["DataType"] == "Status":  # checks a Claim Status:
                if unique[0] not in STATUSES:  # if the status is NOT one of the 6 valid values above:
                    res["flagged"] = True  # flags it
                    res["reason"] = "Unexpected claim status"  # records the reason
                else:  # a valid status (including Ex Gratia / Declined - Ex Gratia Offer):
                    res["value"] = unique[0]  # stores the status exactly as written
            else:  # Text and Address values need no cleaning:
                res["value"] = unique[0]  # stores the value exactly as found
        if res["flagged"]:  # if this field was flagged at any point above:
            res["value"] = f"[[CHECK: {r['Title']}]]"  # replaces the fill value with the [[CHECK: ...]] marker — flagged values are NEVER filled
        results.append(res)  # adds this field's result to the list
    return results  # returns one result per mapping row — main.py turns these into the fill values and the log rows