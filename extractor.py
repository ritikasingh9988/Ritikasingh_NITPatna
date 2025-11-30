# extractor.py
import re
from typing import List, Dict, Tuple
from decimal import Decimal, InvalidOperation

# helper to parse numeric strings like "1,234.56" -> float
def parse_number(s: str) -> float:
    if s is None:
        return 0.0
    s = s.replace(',', '').strip()
    try:
        return float(Decimal(s))
    except (InvalidOperation, ValueError):
        # remove non-numeric (except dot)
        s2 = re.sub(r'[^\d.\-]', '', s)
        try:
            return float(Decimal(s2)) if s2 not in ("", ".", "-") else 0.0
        except Exception:
            return 0.0

# find candidate grand total by looking for keywords near numbers
TOTAL_PATTERNS = [
    r'grand\s*total[:\s]*([0-9,\.]+)',
    r'net\s*amount\s*payable[:\s]*([0-9,\.]+)',
    r'net\s*total[:\s]*([0-9,\.]+)',
    r'balance\s*payable[:\s]*([0-9,\.]+)',
    r'total\s*amount[:\s]*([0-9,\.]+)',
    r'total[:\s]*([0-9,\.]{2,})'
]

def find_grand_total_from_text(text: str) -> float:
    t = text.lower()
    for pat in TOTAL_PATTERNS:
        m = re.search(pat, t)
        if m:
            return parse_number(m.group(1))
    # fallback: last large number in page as grand total (heuristic)
    nums = re.findall(r'([0-9][0-9,]*\.\d{2})', text)
    if nums:
        # return the largest numeric (likely total)
        vals = [parse_number(x) for x in nums]
        return max(vals)
    return None

def parse_items_from_page_text(page_text: str) -> List[Dict]:
    """
    Heuristic parsing:
    - split lines
    - for each line: if it contains at least one number -> treat as candidate line-item
    - map last number as item_amount, second-last as item_rate (if present), third-last as qty
    - item_name is the left side (text before first numeric group)
    """
    items = []
    lines = page_text.splitlines()
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        # find numbers with decimals or comma-format
        nums = re.findall(r'(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.\d{1,2}|\d+)', ln)
        if not nums:
            continue
        # ignore lines that look like phone numbers or dates? Basic filter: if only one short integer < 4 digits and line length small -> skip
        # choose last as amount
        item_amount = parse_number(nums[-1])
        item_rate = 0.0
        item_quantity = 1
        if len(nums) >= 2:
            # choose second last as rate candidate (but if it's extremely large maybe it's qty; heuristics)
            item_rate = parse_number(nums[-2])
        if len(nums) >= 3:
            item_quantity = parse_number(nums[-3])
            if item_quantity == 0:
                item_quantity = 1
        # item name: part of line before first numeric token
        first_num = re.search(r'(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.\d{1,2}|\d+)', ln)
        if first_num:
            name = ln[:first_num.start()].strip(' .:-,')
        else:
            name = ln
        name = re.sub(r'\s{2,}', ' ', name)
        # guard: if name is empty, put whole line but we'll try to clean trailing numbers
        if not name:
            # remove numeric tokens from end
            name = re.sub(r'[-\d,.\s]+$', '', ln).strip()
        if not name:
            name = ln  # give something

        items.append({
            "item_name": name,
            "item_amount": round(item_amount, 2),
            "item_rate": round(item_rate, 2) if item_rate else 0.0,
            "item_quantity": int(item_quantity) if float(item_quantity).is_integer() else item_quantity,
            "raw": ln
        })
    return items

def find_totals_and_reconcile(page_texts: List[str]) -> Tuple[float, float]:
    """
    Find grand total across pages (search each page). Compute reconciled amount = grand - sum(extracted).
    Returns (grand_total_found_or_None, reconciled_amount)
    """
    grand_found = None
    for p in page_texts:
        val = find_grand_total_from_text(p)
        if val:
            grand_found = val
            break
    return grand_found

def run_full_extraction(page_texts: List[str]) -> Dict:
    pagewise_line_items = []
    total_extracted = 0.0
    for idx, ptxt in enumerate(page_texts, start=1):
        items = parse_items_from_page_text(ptxt)
        # filter out spurious items where amount is 0 and the raw doesn't look like a product line:
        filtered = []
        for it in items:
            # If amount zero and raw is very short or looks like heading, skip
            if it['item_amount'] == 0 and len(it['raw']) < 10:
                continue
            filtered.append(it)
        pagewise_line_items.append({
            "page_no": idx,
            "page_type": "Bill Detail",
            "bill_items": filtered
        })
        total_extracted += sum(i.get('item_amount', 0.0) for i in filtered)

    grand_found = find_totals_and_reconcile([p['page_type'] + "\n" + ("\n".join(pt for pt in []) for p in [])]) if False else None
    # simpler: find grand from page_texts using helper
    grand_found = find_grand_total_from_text("\n".join(page_texts)) or None

    reconciled = None
    if grand_found is not None:
        reconciled = round(grand_found - round(total_extracted, 2), 2)
    else:
        reconciled = round(0.0 - round(total_extracted, 2), 2)  # if no grand known, negative indicates mismatch

    response = {
        "is_success": True,
        "data": {
            "pagewise_line_items": pagewise_line_items,
            "total_item_count": sum(len(p["bill_items"]) for p in pagewise_line_items),
            "reconciled_amount": reconciled,
            "grand_total_found": grand_found if grand_found is not None else 0.0
        }
    }
    return response