import pdfplumber
import re
import hashlib
import io
from datetime import datetime
from typing import Optional

def detect_payment_method(label: str) -> Optional[str]:
    label_upper = label.upper()
    if "PAIEMENT CB" in label_upper or "PAIEMENT PSC" in label_upper:
        return "cb"
    if "PRLV SEPA" in label_upper or "PRELEVEMENT" in label_upper:
        return "prelevement"
    if "VIR" in label_upper:
        return "virement"
    return None

def parse_amount(value: str) -> Optional[float]:
    if not value or not value.strip():
        return None
    try:
        cleaned = value.strip().replace(" ", "").replace("\xa0", "").replace(",", ".")
        return float(cleaned)
    except ValueError:
        return None

def parse_date(value: str) -> Optional[str]:
    if not value or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None

def is_date(value: str) -> bool:
    if not value:
        return False
    return bool(re.match(r'^\d{2}/\d{2}/\d{4}$', value.strip()))

def extract_account_name(page_text: str) -> Optional[str]:
    match = re.search(r'(C/C [^\n]+|LIVRET [^\n]+)', page_text)
    if match:
        return match.group(1).split("N°")[0].strip()
    return None

def hash_pdf(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def parse_credit_mutuel_pdf(file_bytes: bytes) -> dict:
    transactions = []
    current_account = None
    pending_row = None

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            account = extract_account_name(page_text)
            if account:
                current_account = account

            table = page.extract_table({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
            })

            if not table:
                continue

            for row in table:
                if not row or len(row) < 3:
                    continue

                cells = [str(c).strip() if c else "" for c in row]

                if is_date(cells[0]):
                    if pending_row:
                        transactions.append(pending_row)

                    transaction_date = parse_date(cells[0])
                    value_date = parse_date(cells[1]) if len(cells) > 1 else None
                    label = cells[2] if len(cells) > 2 else ""
                    debit = parse_amount(cells[3]) if len(cells) > 3 else None
                    credit = parse_amount(cells[4]) if len(cells) > 4 else None

                    if "SOLDE" in label.upper():
                        pending_row = None
                        continue

                    if debit:
                        amount = debit
                        tx_type = "debit"
                    elif credit:
                        amount = credit
                        tx_type = "credit"
                    else:
                        pending_row = None
                        continue

                    pending_row = {
                        "transaction_date": transaction_date,
                        "value_date": value_date,
                        "label": label,
                        "label_detail": None,
                        "amount": amount,
                        "type": tx_type,
                        "payment_method": detect_payment_method(label),
                        "account_name": current_account,
                        "matched": False,
                    }

                elif pending_row and cells[2] and not is_date(cells[0]):
                    detail = cells[2].strip()
                    if detail and "SOLDE" not in detail.upper() and "Date" not in detail:
                        pending_row["label_detail"] = detail
                        if not pending_row["payment_method"]:
                            pending_row["payment_method"] = detect_payment_method(detail)

            if pending_row:
                transactions.append(pending_row)
                pending_row = None

    # Déduplique
    seen = set()
    unique = []
    for tx in transactions:
        key = (tx["transaction_date"], tx["label"], tx["amount"])
        if key not in seen:
            seen.add(key)
            unique.append(tx)

    # Calcule la plage de dates et le compte principal
    dates = [tx["transaction_date"] for tx in unique if tx["transaction_date"]]
    accounts = [tx["account_name"] for tx in unique if tx["account_name"]]
    main_account = max(set(accounts), key=accounts.count) if accounts else None

    return {
        "transactions": unique,
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "account_name": main_account,
        "transaction_count": len(unique),
    }