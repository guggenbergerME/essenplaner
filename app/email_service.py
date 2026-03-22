"""E-Mail-Versand für Einmal-Passwörter."""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() == "true"


def send_password_email(to_email: str, password: str) -> bool:
    """Sendet das Einmal-Passwort per E-Mail."""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM]):
        print(f"[MAIL] SMTP nicht konfiguriert. Passwort für {to_email}: {password}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "essenplaner – Dein Zugangspasswort"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    text = f"""Hallo,

du hast dich beim essenplaner registriert.

Dein Passwort lautet: {password}

Bitte melde dich damit an. Du kannst das Passwort nach dem Login in den Einstellungen ändern.

Viele Grüße
essenplaner
"""

    html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1a1a2e; padding: 2rem;">
    <div style="max-width: 500px; margin: 0 auto; background: #f5f7fa; border-radius: 12px; padding: 2rem;">
        <h2 style="color: #0A2463; margin-bottom: 1rem;">essenplaner</h2>
        <p>Hallo,</p>
        <p>du hast dich beim essenplaner registriert.</p>
        <p style="margin: 1.5rem 0;">
            <strong>Dein Passwort:</strong>
            <span style="display: inline-block; background: #0A2463; color: white; padding: 0.5rem 1.5rem; border-radius: 8px; font-size: 1.2rem; font-family: monospace; letter-spacing: 0.1em; margin-left: 0.5rem;">{password}</span>
        </p>
        <p>Bitte melde dich damit an. Du kannst das Passwort nach dem Login in den Einstellungen ändern.</p>
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 1.5rem 0;">
        <p style="font-size: 0.85rem; color: #6b7280;">Viele Grüße<br>essenplaner</p>
    </div>
</body>
</html>"""

    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if SMTP_TLS:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)

        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, to_email, msg.as_string())
        server.quit()
        print(f"[MAIL] Passwort an {to_email} gesendet.")
        return True
    except Exception as e:
        print(f"[MAIL] Fehler beim Senden an {to_email}: {e}")
        print(f"[MAIL] Passwort für {to_email}: {password}")
        return False
