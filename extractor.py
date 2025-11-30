# extractor.py
import io
import re
from typing import List, Dict
import logging

logger = logging.getLogger("extractor")

# Amount regex: matches 1,234.56 or 1234.56 or 1000
AMOUNT_RE = re.compile(r'(?:\d{1,3}(?:[,\s]\d{3})+|\d+)(?:\.\d{1,2})?')

# lines containing these keywords should NOT be considered items
NON_ITEM_KEYWORDS = re.compile(
    r'\b(total|subtotal|grand total|net amount|balance due|amount due|gst|cgst|sgst|tax|roundoff|discount)\b',
    flags=re.I
)

def _clean_amount_token(tok: str):
    if tok is None: 
        return None
    s = str(tok).replace(",", "").replace(" ", "").strip()
    try:
        return float(s)
    except:
        return None

def parse_lines_to_items(lines: List[str]) -> List[Dict]:
    items = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        # ignore heading-like lines that contain only letters and no numbers
        if not re.search(r'\d', line):
            continue
        # skip very likely non-item lines
        if NON_ITEM_KEYWORDS.search(line):
            # still capture totals separately (if needed) in main logic
            continue
        # Try structured pattern: name  qty  rate  amount (numbers separated)
        m = re.match(r'^(?P<name>.+?)\s+(\b(?P<qty>\d+(?:\.\d+)?)\b)\s+(\b(?P<rate>\d{1,3}(?:[,\s]\d{3})(?:\.\d{1,2})?)\b)\s+(\b(?P<amt>\d{1,3}(?:[,\s]\d{3})(?:\.\d{1,2})?)\b)\s*$', line)
        if m:
            name = m.group('name').strip()
            qty = float(m.group('qty')) if m.group('qty') else 1
            rate = _clean_amount_token(m.group('rate')) or 0.0
            amt = _clean_amount_token(m.group('amt')) or (rate * qty)
            items.append({"item_name": name, "item_amount": round(amt,2), "item_rate": round(rate,2), "item_quantity": int(qty)})
            continue

        # fallback: find all amount tokens and pick the last as item_amount
        amounts = AMOUNT_RE.findall(line)
        if amounts:
            amt_tok = amounts[-1]
            amt = _clean_amount_token(amt_tok) or 0.0
            # name is text before last amount token
            idx = line.rfind(amt_tok)
            name = line[:idx].strip(' -:,.') or line
            # try to see if another numeric token before last could be rate/qty
            rate = None
            qty = 1
            if len(amounts) >= 2:
                # second last may be rate/qty - we choose not to assume; set rate=None => will be 0
                second = amounts[-2]
                # if second numeric appears before amount and separated likely qty or rate; use heuristic
                # if it's small integer (<=10) treat as qty
                try:
                    val = float(second.replace(',','').replace(' ',''))
                    if val.is_integer() and val <= 100:
                        qty = int(val)
                    else:
                        rate = val
                except:
                    rate = None
            if rate is None:
                rate_val = 0.0
            else:
                rate_val = float(rate)
            items.append({"item_name": name, "item_amount": round(amt,2), "item_rate": round(rate_val,2) if rate_val else 0.0, "item_quantity": int(qty)})
            continue
        # if nothing matched, skip
    return items

def extract_bill_from_text_pages(pages_text: List[str]) -> List[Dict]:
    """
    Input: list of page text strings
    Output: list of pages: {"page_no": n, "page_type": "Bill Detail", "bill_items": [...]}
    """
    results = []
    for i, text in enumerate(pages_text, start=1):
        lines = [ln for ln in (text.splitlines() if text else [])]
        # if PDF's page extraction produced empty lines, try to keep pages empty
        items = parse_lines_to_items(lines)
        results.append({"page_no": str(i), "page_type": "Bill Detail", "bill_items": items})
    return results