# app/email_sender.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from fastapi.templating import Jinja2Templates

# Jinja2 Template Loader
templates = Jinja2Templates(directory="templates")


# ------------------------------------------------------------
# 1) HTML Rendern mit DEINEM EINEN Template
# ------------------------------------------------------------
def build_email_html(subject: str, body: str, action_url=None, action_text=None):
    """
    Rendert dein globales HTML-E-Mail Template.
    """
    return templates.get_template("email/base_email.html").render({
        "subject": subject,
        "body": body,
        "action_url": action_url,
        "action_text": action_text,
    })


# ------------------------------------------------------------
# 2) SMTP SENDEN
# ------------------------------------------------------------
def send_via_smtp(provider, subject, html_body, to_email):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = provider.smtp_user
        msg["To"] = to_email

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(provider.smtp_host, provider.smtp_port) as server:
            server.starttls()
            server.login(provider.smtp_user, provider.smtp_password)
            server.sendmail(provider.smtp_user, [to_email], msg.as_string())

        return True, "SMTP erfolgreich"
    except Exception as e:
        return False, f"SMTP Fehler: {str(e)}"


# ------------------------------------------------------------
# 3) SENDGRID SENDEN
# ------------------------------------------------------------
def send_via_sendgrid(provider, subject, html_body, to_email):
    try:
        url = "https://api.sendgrid.com/v3/mail/send"

        payload = {
            "personalizations": [{
                "to": [{"email": to_email}]
            }],
            "from": {"email": provider.smtp_user or "no-reply@ouhud.com"},
            "subject": subject,
            "content": [{
                "type": "text/html",
                "value": html_body
            }]
        }

        headers = {
            "Authorization": f"Bearer {provider.sendgrid_key}",
            "Content-Type": "application/json",
        }

        r = requests.post(url, json=payload, headers=headers)

        if 200 <= r.status_code < 300:
            return True, "SendGrid erfolgreich"
        return False, f"SendGrid API Fehler: {r.text}"

    except Exception as e:
        return False, f"SendGrid Fehler: {str(e)}"


# ------------------------------------------------------------
# 4) MAILGUN SENDEN
# ------------------------------------------------------------
def send_via_mailgun(provider, subject, html_body, to_email):
    try:
        url = f"https://api.mailgun.net/v3/{provider.smtp_host}/messages"

        r = requests.post(
            url,
            auth=("api", provider.mailgun_key),
            data={
                "from": provider.smtp_user or "Ouhud CRM <no-reply@ouhud.com>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            },
        )

        if 200 <= r.status_code < 300:
            return True, "Mailgun erfolgreich"
        return False, f"Mailgun API Fehler: {r.text}"

    except Exception as e:
        return False, f"Mailgun Fehler: {str(e)}"


# ------------------------------------------------------------
# 5) AWS SES SENDEN
# ------------------------------------------------------------
def send_via_ses(provider, subject, html_body, to_email):
    try:
        client = boto3.client(
            "ses",
            aws_access_key_id=provider.ses_key,
            aws_secret_access_key=provider.ses_secret,
            region_name=provider.ses_region,
        )

        response = client.send_email(
            Source=provider.smtp_user,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Html": {"Data": html_body}},
            },
        )

        return True, "SES erfolgreich"

    except ClientError as e:
        return False, f"SES Fehler: {e.response['Error']['Message']}"
    except BotoCoreError as e:
        return False, f"SES Core Fehler: {str(e)}"
    except Exception as e:
        return False, f"SES Fehler: {str(e)}"


# ------------------------------------------------------------
# 6) UNIVERSAL SEND-FUNKTION
# ------------------------------------------------------------
def send_email(provider, subject, body, to_email, action_url=None, action_text=None):
    """
    Nutzt dein HTML Template + sendet über den aktiven Provider.
    """
    html = build_email_html(subject, body, action_url, action_text)

    if provider.provider == "smtp":
        return send_via_smtp(provider, subject, html, to_email)

    if provider.provider == "sendgrid":
        return send_via_sendgrid(provider, subject, html, to_email)

    if provider.provider == "mailgun":
        return send_via_mailgun(provider, subject, html, to_email)

    if provider.provider == "ses":
        return send_via_ses(provider, subject, html, to_email)

    return False, "Unbekannter Provider"


# ------------------------------------------------------------
# 7) TEST-E-MAIL (nutzt auch HTML)
# ------------------------------------------------------------
def send_test_email(provider, to_email):
    subject = "Test-E-Mail – Ouhud CRM"
    body = "<p>Dies ist eine <strong>Testnachricht</strong>. Dein Provider funktioniert!</p>"

    return send_email(provider, subject, body, to_email)


