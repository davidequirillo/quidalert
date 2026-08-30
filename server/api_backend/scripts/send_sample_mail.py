# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import argparse
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from core.settings import settings, build_public_baseurl

FROM_EMAIL = settings.smtp_from
FROM_NAME = settings.smtp_from_name
HOST = settings.smtp_host
PORT = settings.smtp_port
USER = settings.smtp_user
PASSWORD = settings.smtp_pass
USE_TLS = settings.smtp_use_tls

def run_test(email_recipient: str):
    print(f"Trying to connect to {HOST}:{PORT}...")
    msg = EmailMessage()
    msg["From"] = formataddr((FROM_NAME, FROM_EMAIL))
    msg["To"] = email_recipient
    msg["Subject"] = "Test email delivery"
    baseurl = build_public_baseurl(settings.protocol, settings.server_name, settings.server_port)
    # Plain text body for the email
    text_body = (
        "Hello!\n\n"
        f"This is a test message sent from {FROM_NAME} ({FROM_EMAIL}) to verify email delivery.\n\n"
        f"Sample activation link: {baseurl}/api/activate?email={email_recipient}&token=sampletoken\n\n"
        "Thank you for testing our email system.\n"
    )
    msg.set_content(text_body)
    try:
        with smtplib.SMTP(host=HOST, port=PORT, timeout=10) as server:
            server.ehlo()
            if USE_TLS.lower() in ("true", "1", "yes"):
                print("Starting STARTTLS handshake...")
                server.starttls()
                server.ehlo()
            if USER and PASSWORD:
                print("Authenticating on SMTP server...")
                server.login(user=USER, password=PASSWORD)
            print(f"Sending email to {email_recipient}...")
            server.send_message(msg)        
        print(f"Email successfully sent to {email_recipient}!")        
    except Exception as e:
        print(f"Failed to send email to {email_recipient}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a test email to verify SMTP settings.")
    parser.add_argument("--to_email", type=str, required=True, help="The recipient email address for the test email.")
    args = parser.parse_args()
    to_email = args.to_email
    run_test(to_email)
