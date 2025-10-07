# app/utils/email_utils.py
import smtplib
from email.message import EmailMessage
from pathlib import Path
import os
import ssl

# 📌 SMTP-Konfiguration über Umgebungsvariablen (⚡ Sicherer als Hardcoding!)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "deine_email@example.com")
SMTP_PASS = os.getenv("SMTP_PASS", "dein_app_passwort")


# 📎 -------------------------------------------------------------
# 📤 Rechnung als PDF per E-Mail versenden
# 📎 -------------------------------------------------------------
def send_invoice_email(recipient: str, subject: str, pdf_path: str, customer_name: str):
    """
    Versendet eine Rechnung als PDF-Anhang per SMTP-E-Mail.
    """
    if not recipient:
        print("❌ Kein Empfänger — E-Mail wird nicht gesendet.")
        return

    # 📨 E-Mail-Nachricht erstellen
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = recipient
    msg["Subject"] = subject

    # 📄 Nachrichtentext
    msg.set_content(f"""\
Sehr geehrte/r {customer_name},

anbei erhalten Sie Ihre aktuelle Rechnung als PDF-Dokument.

Mit freundlichen Grüßen
Ihr Unternehmen
""")

    # 📎 PDF anhängen (Datei prüfen)
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ PDF-Datei nicht gefunden: {pdf_path}")
        return

    msg.add_attachment(
        pdf_file.read_bytes(),
        maintype="application",
        subtype="pdf",
        filename=pdf_file.name
    )

    # 🔐 Sichere Verbindung (STARTTLS)
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        print(f"✅ Rechnung erfolgreich an {recipient} gesendet.")
    except Exception as e:
        print(f"❌ Fehler beim Senden der E-Mail an {recipient}: {e}")


# 📌 -------------------------------------------------------------
# 📧 Passwort-Zurücksetzen E-Mail
# 📌 -------------------------------------------------------------
def send_password_reset_email(recipient: str, reset_link: str):
    """
    Sendet eine E-Mail mit einem Link zum Zurücksetzen des Passworts.
    """
    if not recipient:
        print("❌ Kein Empfänger — Passwort-Reset-E-Mail wird nicht gesendet.")
        return

    # 📨 E-Mail-Nachricht erstellen
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = recipient
    msg["Subject"] = "🔑 Passwort zurücksetzen – Ouhud CRM"

    # 📄 Nachrichtentext
    msg.set_content(f"""\
Hallo,

du hast eine Anfrage zum Zurücksetzen deines Passworts gestellt.
Klicke auf den folgenden Link, um ein neues Passwort festzulegen:

{reset_link}

⚠️ Dieser Link ist 30 Minuten gültig.
Wenn du diese Anfrage nicht gestellt hast, kannst du diese E-Mail ignorieren.

Mit freundlichen Grüßen
Dein Ouhud CRM Team
""")

    # 🔐 SMTP-Versand
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        print(f"✅ Passwort-Reset-E-Mail erfolgreich an {recipient} gesendet.")
    except Exception as e:
        print(f"❌ Fehler beim Senden der Passwort-Reset-E-Mail an {recipient}: {e}")