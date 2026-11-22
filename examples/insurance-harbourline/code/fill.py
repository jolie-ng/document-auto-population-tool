from docx import Document  # imports Document — opens and saves a Word .docx file
from docx.oxml.ns import qn  # imports qn — builds the XML names Word uses, e.g. w:sdt for a content control
from docx.shared import RGBColor  # imports RGBColor — sets a run's font colour (used for the black fix in the fallback)
 
 
def _force_run_black(run):  # defines _force_run_black — forces ONE run (w:r element) to black, RGB 0,0,0
    rPr = run.find(qn("w:rPr"))  # finds the run's formatting block (w:rPr) — colour and style live there
    if rPr is None:  # if the run has no formatting block yet:
        rPr = run.makeelement(qn("w:rPr"), {})  # creates an empty formatting block for this run
        run.insert(0, rPr)  # inserts it as the run's first child — Word requires it in that position
    rStyle = rPr.find(qn("w:rStyle"))  # finds the run's character style, if any
    if rStyle is not None:  # if a character style is set:
        style_val = rStyle.get(qn("w:val")) or ""  # reads the style's name
        if "Placeholder" in style_val:  # if it is the grey Placeholder style:
            rPr.remove(rStyle)  # removes it — a filled value must not keep placeholder formatting
    color = rPr.find(qn("w:color"))  # finds the run's colour setting, if any
    if color is None:  # if no colour is set yet:
        color = run.makeelement(qn("w:color"), {})  # creates a colour element
        rPr.append(color)  # adds it to the run's formatting block
    for attr in list(color.attrib):  # loops through the colour's existing attributes (e.g. a theme colour)
        if attr != qn("w:val"):  # keeps only w:val — a theme colour could override the black
            del color.attrib[attr]  # deletes every other colour attribute
    color.set(qn("w:val"), "000000")  # sets the colour to 000000 = black, RGB 0,0,0 — THE BLACK-FONT FIX
 
 
def _set_sdt_text(sdt, value):  # defines _set_sdt_text — writes a value into ONE content control (w:sdt element)
    content = sdt.find(qn("w:sdtContent"))  # finds the control's content area — the text lives inside it
    if content is None:  # if the control has no content area:
        return False  # returns False = could not fill this control
    texts = content.findall(".//" + qn("w:t"))  # finds every text node inside the control
    if not texts:  # if the control holds no text node:
        return False  # returns False = could not fill this control
    sdtPr = sdt.find(qn("w:sdtPr"))  # finds the control's properties block
    if sdtPr is not None:  # if a properties block exists:
        showing = sdtPr.find(qn("w:showingPlcHdr"))  # finds the "showing placeholder" marker — while it is set, Word renders the text grey
        if showing is not None:  # if that marker is present:
            sdtPr.remove(showing)  # removes it — THE BLACK-FONT FIX: the control is no longer a placeholder
    lines = value.split("\n")  # splits the value into lines — addresses arrive as several lines
    texts[0].text = lines[0]  # writes the first line into the control's first text node
    for extra in texts[1:]:  # loops through any remaining text nodes in the control:
        extra.text = ""  # clears them — old placeholder text must not survive next to the new value
    for run in content.findall(".//" + qn("w:r")):  # loops through every run inside the control:
        _force_run_black(run)  # forces each run to black — THE BLACK-FONT FIX, applied to the whole control
    if len(lines) > 1:  # if the value has more lines (an address):
        run = texts[0].getparent()  # finds the run that holds the first text node
        for line in lines[1:]:  # loops through the remaining address lines:
            br = run.makeelement(qn("w:br"), {})  # creates a line-break element
            run.append(br)  # adds the line break to the run
            t = run.makeelement(qn("w:t"), {})  # creates a text element for this address line
            t.text = line  # puts this address line into it
            run.append(t)  # adds it after the break — no part of the address is lost
    return True  # returns True = this control was filled
 
 
def fill_letter(input_path, output_path, fill):  # defines fill_letter — fill: {ControlTag: value}; saves a NEW file; returns tags NOT found
    doc = Document(input_path)  # opens the partly-filled letter — the input file itself is never overwritten
    missing = []  # starts an empty list — tags not found in the letter go in here
    for tag, value in fill.items():  # loops through each Tag -> value pair to fill
        filled = False  # starts as not filled for this tag
        for sdt in doc.element.iter(qn("w:sdt")):  # loops through EVERY content control in the document, tables included
            tag_el = sdt.find(".//" + qn("w:tag"))  # finds this control's Tag element
            if tag_el is not None and tag_el.get(qn("w:val")) == tag:  # if this control's Tag matches the tag being filled:
                filled = _set_sdt_text(sdt, value) or filled  # writes the value in — every control with this Tag is filled (e.g. Approved Amount twice)
        if not filled:  # if no content control matched — try the fallback:
            placeholder = "{{" + tag + "}}"  # builds the typed placeholder text, e.g. {{ClaimReference}}
            for para in doc.paragraphs:  # loops through the document's paragraphs (fallback route)
                if placeholder in para.text:  # if this paragraph contains the placeholder:
                    for run in para.runs:  # loops through the paragraph's runs
                        if placeholder in run.text:  # if this run contains the placeholder:
                            run.text = run.text.replace(placeholder, value)  # replaces the placeholder with the value
                            run.font.color.rgb = RGBColor(0, 0, 0)  # forces the filled run to black, RGB 0,0,0 — BLACK FIX (fallback)
                            filled = True  # marks this tag as filled
            for table in doc.tables:  # loops through the document's tables (fallback route, e.g. the settlement summary table)
                for row in table.rows:  # loops through each table row
                    for cell in row.cells:  # loops through each cell in the row
                        for para in cell.paragraphs:  # loops through each paragraph in the cell
                            if placeholder in para.text:  # if this cell paragraph contains the placeholder:
                                for run in para.runs:  # loops through the paragraph's runs
                                    if placeholder in run.text:  # if this run contains the placeholder:
                                        run.text = run.text.replace(placeholder, value)  # replaces the placeholder with the value
                                        run.font.color.rgb = RGBColor(0, 0, 0)  # forces the filled run to black, RGB 0,0,0 — BLACK FIX (fallback)
                                        filled = True  # marks this tag as filled
        if not filled:  # if NEITHER route filled this tag:
            missing.append(tag)  # records it — main.py warns you; nothing is filled silently into the wrong place
    doc.save(output_path)  # saves the filled letter as a NEW draft at output_path — the input letter is untouched
    return missing  # returns the list of tags that were not found (empty list = every tag filled)