# app/utils/camt_parser.py
import xml.etree.ElementTree as ET

def parse_camt053(file_path: str):
    """
    Liest eine CAMT.053-Datei (XML) ein und gibt eine Liste von Zahlungen zurück.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'ns': 'urn:iso:std:iso:20022:tech:xsd:camt.053.001.02'}

    payments = []
    for entry in root.findall('.//ns:Ntry', ns):
        amount_el = entry.find('ns:Amt', ns)
        credit_debit = entry.find('ns:CdtDbtInd', ns)
        info_el = entry.find('.//ns:Ustrd', ns)

        if amount_el is None or credit_debit is None:
            continue

        amount = float(amount_el.text)
        entry_type = credit_debit.text.strip()  # CRDT oder DBIT
        reference = info_el.text.strip() if info_el is not None else ""

        payments.append({
            "amount": amount,
            "type": entry_type,
            "reference": reference
        })

    return payments