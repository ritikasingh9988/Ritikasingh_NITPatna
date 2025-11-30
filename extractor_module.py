# extractor_module.py
import re
from typing import List, Dict, Tuple, Optional

AMOUNT_RE = re.compile(r'([0-9]+(?:[,\s][0-9]{3})*(?:\.\d+)?)')  # matches amounts with commas or decimals
# common separators used often in invoices between name and amounts
LINE_SPLIT_RE = re.compile(r'\s{2,}|\t|\s*\|\s*')  # multiple spaces or pipe separators

def parse_amount(text: str) -> Optional[float]:
    """
    Parse first numeric amount-like token in text and return float (commas removed).
    """
    if text is None:
        return None
    m = AMOUNT_RE.search(text.replace('₹', '').replace('INR', ''))
    if not m:
        return None
    num = m.group(1)
    num = num.replace(' ', '').replace(',', '')
    try:
        return float(num)
    except Exception:
        return None

def parse_line_item(line: str) -> Dict:
    """
    Try to parse an item line and return dict with keys: item_name, item_amount, item_rate, item_quantity, raw
    Heuristics:
      - Look for last amount tokens as item amounts/rates.
      - If only one number found -> treat as amount.
      - If multiple numbers found, treat last as amount, previous maybe rate/qty.
    """
    raw = line.strip()
    # split by long spaces or pipes if present to separate columns
    parts = LINE_SPLIT_RE.split(raw)
    # if parted into columns and last column contains numbers -> use that
    if len(parts) >= 2:
        # try from last column backwards to find an amount
        for i in range(len(parts)-1, 0, -1):
            amt = parse_amount(parts[i])
            if amt is not None:
                # name = join of columns before this one
                name = ' '.join(parts[:i]).strip()
                # attempt to find rate/quantity on the right side as extra numbers
                right_nums = AMOUNT_RE.findall(' '.join(parts[i:]))
                rate = None
                qty = 1
                if len(right_nums) >= 2:
                    # assume second last is rate, last is amount OR last is amount and earlier could be qty
                    try:
                        rate = float(right_nums[-2].replace(',','').replace(' ',''))
                    except:
                        rate = None
                return {
                    "item_name": name if name else raw,
                    "item_amount": float(amt),
                    "item_rate": float(rate) if rate is not None else 0.0,
                    "item_quantity": 1,
                    "raw": raw
                }
    # fallback: search all numeric tokens
    all_nums = AMOUNT_RE.findall(raw)
    if all_nums:
        # treat last as amount
        amt = all_nums[-1]
        try:
            amount_val = float(amt.replace(',','').replace(' ', ''))
        except:
            amount_val = 0.0
        # name = line without the last matched numeric token
        # remove last occurrence of matched string
        idx = raw.rfind(all_nums[-1])
        name = raw[:idx].strip() if idx!=-1 else raw
        return {
            "item_name": name if name else raw,
            "item_amount": amount_val,
            "item_rate": 0.0,
            "item_quantity": 1,
            "raw": raw
        }
    # no number found at all -> treat as description (amount 0)
    return {
        "item_name": raw,
        "item_amount": 0.0,
        "item_rate": 0.0,
        "item_quantity": 1,
        "raw": raw
    }

def find_items_from_page_text(page_text: str) -> List[Dict]:
    """
    Given a page text, split into lines and attempt to parse line items.
    This uses heuristics: only lines with at least one numeric token are considered
    likely line-items; also try to skip header lines (containing 'bill', 'invoice', 'patient') heuristically.
    """
    items = []
    if not page_text:
        return items
    lines = [l.strip() for l in page_text.splitlines() if l.strip()]
    for line in lines:
        low = line.lower()
        # skip header-like lines
        if any(h in low for h in ('bill', 'invoice', 'patient name', 'reg no', 'age/sex', 'date', 'page')):
            # but sometimes headers contain amounts — we skip only pure header like lines
            # keep only if there is an amount token
            if not AMOUNT_RE.search(line):
                continue
        # heuristics: consider as line item if at least one number present OR pattern like ITEM NAME + amount
        if AMOUNT_RE.search(line):
            parsed = parse_line_item(line)
            # skip lines where the parsed name is obviously the header
            if parsed and parsed.get('item_name'):
                items.append(parsed)
    return items

def find_totals_and_reconcile(page_texts: List[str]) -> Tuple[Optional[float], float]:
    """
    Look for a grand total in pages (search for keywords 'grand total', 'net amount', 'net payable', 'total').
    Returns (grand_total_found_or_None, reconciled_amount=grand - sum(items) if grand exists else 0)
    """
    grand = None
    # search from last page backwards for totals
    key_patterns = [
        r'grand total[:\s]*([0-9,.\s]+)',
        r'net amount payable[:\s]*([0-9,.\s]+)',
        r'net payable[:\s]*([0-9,.\s]+)',
        r'grand total found[:\s]*([0-9,.\s]+)',
        r'\btotal of\b[:\s]*([0-9,.\s]+)',
        r'total[:\s]*([0-9,.\s]+)$'
    ]
    for t in reversed(page_texts):
        lower = t.lower()
        for pat in key_patterns:
            m = re.search(pat, lower, flags=re.IGNORECASE)
            if m:
                val_text = m.group(1)
                val = parse_amount(val_text)
                if val is not None:
                    grand = val
                    return grand, 0.0  # reconciliation will be computed outside once items sum known
    return None, 0.0