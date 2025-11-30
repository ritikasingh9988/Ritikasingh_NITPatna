import re
from typing import List, Dict, Tuple
import pdfplumber

# Heuristic helper regexes
AMOUNT_RE = re.compile(r'([0-9]+(?:[,][0-9]{3})*(?:\.[0-9]{1,2})?)\b')
QUANTITY_RE = re.compile(r'(?:x|qty|qty:|quantity|no\.)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)', re.I)
SNO_PREFIX_RE = re.compile(r'^\s*\d+[\)\.\-]?\s*')  # remove leading numbering "1.", "2) ", etc.
TOTAL_LABELS = [
    r'grand\s*total', r'net\s*amount\s*payable', r'net\s*amount', r'total\s*amount',
    r'total\s*bill', r'final\s*total', r'total\s*of\s*pharmacy', r'total'
]
TOTAL_RE_LIST = [re.compile(rf'({label})\s*[:\-]?\s*([0-9]+(?:[,][0-9]{{3}})*(?:\.[0-9]+)?)', re.I) for label in TOTAL_LABELS]

def clean_text(t: str) -> str:
    if t is None:
        return ""
    # normalise whitespace and remove weird non-printables
    return re.sub(r'\s+', ' ', t).strip()

def extract_text_pages_pdfplumber(pdf_bytes: bytes) -> List[str]:
    pages_text = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            pages_text.append(clean_text(txt))
    return pages_text

# fallback minimal OCR approach (if needed) is omitted for brevity.
# We prefer pdfplumber for this datathon sample.

import io
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> List[str]:
    # try pdfplumber first
    try:
        return extract_text_pages_pdfplumber(pdf_bytes)
    except Exception:
        # fallback: return single block to avoid crash
        return [clean_text(pdf_bytes.decode('latin-1', errors='ignore'))]

def parse_items_from_page_text(page_text: str) -> List[Dict]:
    items = []
    if not page_text:
        return items

    # split text by newlines or by common separators if pages come as single line
    lines = re.split(r'\n|;|\r', page_text)
    if len(lines) == 1:
        # if page text is single line long string, try splitting by double spaces which often separate fields
        lines = re.split(r'\s{2,}', page_text)

    for raw in lines:
        t = clean_text(raw)
        if not t:
            continue

        # Skip lines that are likely header/footer
        low = t.lower()
        if any(x in low for x in ('invoice', 'bill', 'patient name', 'hospital', 'reg no', 'address', 'total', 'grand')):
            # still process lines that might be "Total ..." later in totals function
            # but skip full headers (heuristic)
            pass

        # find amounts in line (we pick the last numeric-looking token as item amount)
        amounts = AMOUNT_RE.findall(t)
        if not amounts:
            continue  # likely not a line-item if it has no number

        amount_str = amounts[-1]
        # convert to float safely
        amount_val = float(amount_str.replace(',', ''))

        # quantity detection
        qmatch = QUANTITY_RE.search(t)
        if qmatch:
            try:
                quantity_val = float(qmatch.group(1))
            except:
                quantity_val = 1.0
        else:
            # Try to detect patterns like "2 x" or "2x"
            m = re.search(r'(\d+(?:\.\d+)?)\s*[xX]\b', t)
            if m:
                quantity_val = float(m.group(1))
            else:
                quantity_val = 1.0

        # compute rate if possible (if qty>0 and amount looks like total)
        rate_val = 0.0
        if quantity_val and quantity_val != 0:
            # if there's a separate number before amount that looks like per-unit, we could derive, but to be safe:
            # we set rate == amount/quantity if amount was full line amount
            try:
                rate_val = round(amount_val / quantity_val, 2)
            except Exception:
                rate_val = 0.0

        # build name: remove amount and qty tokens and leading sno
        name = SNO_PREFIX_RE.sub('', t)
        # remove the amount token at end
        name = re.sub(re.escape(amount_str) + r'\s*$', '', name).strip()
        # remove quantity mentions
        name = re.sub(r'\b(x|qty|qty:|quantity|no\.)\b.*$', '', name, flags=re.I).strip()
        # further cleanup
        name = re.sub(r'[\:\-\*]{2,}', ' ', name).strip()

        if not name:
            # fallback to something sensible
            name = f"item_{len(items)+1}"

        # remove excessive trailing punctuation
        name = name.strip(' ,:-.')

        items.append({
            "item_name": name,
            "item_amount": round(amount_val, 2),
            "item_rate": round(rate_val, 2) if rate_val else 0.0,
            "item_quantity": int(quantity_val) if float(quantity_val).is_integer() else quantity_val,
            "raw": t
        })
    return items

def find_totals_and_reconcile(page_texts: List[str], items_all_pages: List[Dict]) -> Tuple[float, float]:
    grand_total = None
    # search across pages bottom-up for typical total labels
    combined_text = "\n".join(page_texts)
    for regex in TOTAL_RE_LIST:
        m = regex.search(combined_text[::-1])  # trick: search reversed? easier is search last occurrence.
        # but reversed regex is tricky; instead find last match
        all_matches = list(regex.finditer(combined_text))
        if all_matches:
            last = all_matches[-1]
            try:
                val = float(last.group(2).replace(',', ''))
                grand_total = round(val, 2)
                break
            except Exception:
                continue

    # if not found, try more generic last-number-labelled-line containing 'total' word
    if grand_total is None:
        for p in reversed(page_texts):
            for line in reversed(p.splitlines()):
                if 'total' in line.lower() or 'grand' in line.lower() or 'net amount' in line.lower() or 'final total' in line.lower():
                    m = AMOUNT_RE.search(line)
                    if m:
                        try:
                            grand_total = float(m.group(1).replace(',', ''))
                            break
                        except:
                            pass
            if grand_total is not None:
                break

    # compute sum extracted
    total_extracted = sum([i.get('item_amount', 0.0) for i in items_all_pages])
    total_extracted = round(total_extracted, 2)

    if grand_total is None:
        reconciled = 0.0
        grand_total = 0.0
    else:
        reconciled = round(grand_total - total_extracted, 2)

    return grand_total, reconciled

def run_full_extraction(pdf_bytes: bytes) -> Dict:
    pages = extract_text_from_pdf_bytes(pdf_bytes)
    pagewise_line_items = []
    all_items_flat = []
    for idx, ptxt in enumerate(pages):
        items = parse_items_from_page_text(ptxt)
        pagewise_line_items.append({
            "page_no": idx + 1,  # 1-indexed
            "page_type": "Bill Detail",
            "bill_items": items
        })
        all_items_flat.extend(items)

    grand, reconciled = find_totals_and_reconcile(pages, all_items_flat)

    response = {
        "is_success": True,
        "data": {
            "pagewise_line_items": pagewise_line_items,
            "total_item_count": sum(len(p["bill_items"]) for p in pagewise_line_items),
            "reconciled_amount": reconciled,
            "grand_total_found": grand
        }
    }
    return response