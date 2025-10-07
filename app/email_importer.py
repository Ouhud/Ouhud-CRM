# app/email_importer.py
import imaplib
import email
from email.header import decode_header
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Message, Customer

IMAP_SERVER = "mail.mehmalat.ch"  # z. B. von deinem Hoster
IMAP_USER = "info@mehmalat.ch"
IMAP_PASS = "DEIN_PASSWORT"

def fetch_emails():
    print("📬 Verbinde mit IMAP...")
    imap = imaplib.IMAP4_SSL(IMAP_SERVER)
    imap.login(IMAP_USER, IMAP_PASS)
    imap.select("INBOX")

    # Nur ungelesene Mails abrufen
    status, messages = imap.search(None, 'UNSEEN')
    if status != "OK":
        print("⚠️ Keine neuen Mails gefunden.")
        return

    mail_ids = messages[0].split()
    print(f"📨 {len(mail_ids)} neue E-Mail(s) gefunden.")

    db: Session = SessionLocal()

    for num in mail_ids:
        res, msg_data = imap.fetch(num, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8", errors="ignore")
        sender = msg.get("From")
        sender_name = sender
        sender_email = sender

        # E-Mail-Inhalt extrahieren
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        # Kunde automatisch verknüpfen
        customer = db.query(Customer).filter(Customer.email == sender_email).first()

        new_msg = Message(
            sender_name=sender_name,
            sender_email=sender_email,
            subject=subject,
            content=body.strip(),
            received_at=datetime.utcnow(),
            customer=customer
        )
        db.add(new_msg)
        db.commit()

        # Optional: Mail als gelesen markieren
        imap.store(num, '+FLAGS', '\\Seen')

        print(f"✅ Nachricht '{subject}' von {sender_email} gespeichert.")

    imap.logout()
    db.close()

if __name__ == "__main__":
    fetch_emails()