# extractor.py
import os
import json
import re

OPENAI_KEY = os.getenv("OPENAI_API_KEY")

def call_llm_for_items(invoice_text: str):
    """
    If OPENAI_API_KEY is set, call OpenAI to parse invoice_text into JSON.
    Otherwise, use a simple fallback parser to extract numbers from lines.
    """
    if OPENAI_KEY:
        try:
            import openai
            openai.api_key = OPENAI_KEY
            prompt = (
                "Extract only a JSON array of line items from the following invoice text. "
                "Each item must be an object with keys: item_name, item_quantity, item_rate, item_amount. "
                "Return only valid JSON (no extra explanation).\n\n"
                "Invoice text:\n" + invoice_text + "\n\nJSON:"
            )
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":prompt}],
                max_tokens=800,
                temperature=0.0
            )
            content = resp['choices'][0]['message']['content'].strip()
            m = re.search(r'(\[.*\])', content, re.S)
            json_text = m.group(1) if m else content
            items = json.loads(json_text)
            out = []
            for it in items:
                if isinstance(it, dict):
                    out.append({
                        "item_name": it.get("item_name"),
                        "item_quantity": it.get("item_quantity", 1),
                        "item_rate": it.get("item_rate", None),
                        "item_amount": it.get("item_amount", None),
                    })
            return out
        except Exception:
            # fall through to fallback
            pass

    # Fallback (naive) parser: find lines with trailing number and treat that as amount
    items = []
    lines = [l.strip() for l in invoice_text.splitlines() if l.strip()]
    for l in lines:
        # try find last number in line (amount)
        parts = re.findall(r'([0-9]+(?:[.,][0-9]{1,2})?)', l.replace(',',''))
        if parts:
            # treat last match as amount
            amt_str = parts[-1]
            try:
                amt = float(amt_str)
            except:
                continue
            # item name is line minus the amount string
            name = re.sub(re.escape(amt_str) + r'\s*$', '', l).strip()
            if not name:
                name = "item"
            items.append({"item_name": name, "item_quantity": 1, "item_rate": None, "item_amount": amt})
    return items