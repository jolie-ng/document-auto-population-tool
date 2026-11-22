import pdfplumber  # imports pdfplumber — the free library that reads selectable text out of a PDF
 
 
def pdf_to_text(pdf_path):  # defines pdf_to_text — takes one PDF file path, returns all its text as one string
    pages = []  # starts an empty list — one text block will be added per page
    with pdfplumber.open(pdf_path) as pdf:  # opens the PDF safely — it closes itself when this block ends
        for page in pdf.pages:  # loops through EVERY page — mapped values can sit on page 2 or 3
            pages.append(page.extract_text() or "")  # adds this page's text — or "" if the page has no selectable text
    return "\n".join(pages)  # joins all pages into one string, one page after another
 
 
if __name__ == "__main__":  # runs only when you run extract.py directly — not when main.py imports it
    import sys  # imports sys — lets this test read the file path typed after the command
    text = pdf_to_text(sys.argv[1])  # extracts text from the PDF path typed after: python extract.py <path>
    print(text)  # prints the extracted text — check each label and value sit on the same line
    print(f"\n--- {len(text)} characters extracted ---")  # prints the character count — 0 means scanned image, no text