# app/utils/qrcode_utils.py

"""
QR-Code Utility Modul für verschiedene Zahlungsarten:
🌐 Online-Zahlungslink
🇪🇺 SEPA-Überweisung (EPC-Standard)
🇨🇭 TWINT / Schweizer QR-Rechnung (vereinfachte Version)
"""

import qrcode
from pathlib import Path


# 🛠 Hilfsfunktion zum Speichern
def _save_qr(img, filename: str) -> str:
    """
    Speichert ein QR-Bild im Verzeichnis app/static/qrcodes und gibt den Dateipfad zurück.
    """
    output_dir = Path("app/static/qrcodes")
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / f"{filename}.png"
    img.save(file_path)
    return str(file_path)


# 🌐 --- Online-Zahlungslink ---
def generate_link_qr(payment_url: str, filename: str) -> str:
    """
    Erstellt einen einfachen QR-Code mit einem Online-Zahlungslink (z. B. https://ouhud.com/pay/1234).
    """
    img = qrcode.make(payment_url)
    return _save_qr(img, filename)


# 🇪🇺 --- SEPA QR-Code ---
def generate_sepa_qr(iban: str, name: str, amount: float, purpose: str, filename: str) -> str:
    """
    Erstellt einen SEPA EPC QR-Code nach dem offiziellen europäischen Standard.
    Format:
    BCD
    001
    1
    SCT
    <Name>
    <IBAN>
    EUR<Amount>
    <Purpose>
    """
    data = f"""BCD
001
1
SCT
{name}
{iban}
EUR{amount:.2f}
{purpose}"""
    img = qrcode.make(data)
    return _save_qr(img, filename)


# 🇨🇭 --- TWINT / Swiss QR ---
def generate_twint_qr(
    iban: str,
    reference: str,
    amount: float,
    currency: str,
    filename: str,
    company_name: str = "Hamza Dev GmbH",
    company_address: str = "Musterstrasse 1",
    company_zip_city: str = "8000 Zürich",
    company_country: str = "CH",
) -> str:
    """
    Erstellt einen TWINT / Swiss QR Code (vereinfachte Struktur).
    Format basiert auf dem Swiss QR-Standard (SPC-Version).

    ⚠️ Hinweis: Für produktive Nutzung sollte der exakte Swiss QR-Standard
    verwendet werden: https://www.paymentstandards.ch
    """
    data = f"""SPC
0200
1
{iban}
K
{company_name}
{company_address}
{company_zip_city}
{company_country}

{currency}{amount:.2f}
Kunde Name
Adresse
Ort
CH

{reference}
NON
"""
    img = qrcode.make(data)
    return _save_qr(img, filename)


# 🔹 Optional: Allgemeiner QR-Code (z. B. für Debugging oder andere Zwecke)
def generate_payment_qr(data: str, filename: str) -> str:
    """
    Erstellt einen QR-Code mit beliebigen Daten (Fallback / Debug).
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    return _save_qr(img, filename)