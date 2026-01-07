# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import smtplib
from email.message import EmailMessage
from lib.commons import AppSettings
from lib.localization import langmap, localize_activation_mail

def send_activation_mail(email: str, token: str, lang: str):
    prot = AppSettings.protocol
    sname = AppSettings.server_name
    sport = AppSettings.server_port
    act_url = f"{prot}://{sname}:{sport}/activate?email={email}&token={token}"
    msg = EmailMessage()
    msg["Subject"] = langmap[lang]["reg_subject"]
    msg["From"] = AppSettings.smtp_from
    msg["To"] = email
    msg.set_content(localize_activation_mail(act_url, lang))     
    send_mail_message(msg)

def send_mail_message(data):
    with smtplib.SMTP(AppSettings.smtp_host, AppSettings.smtp_port) as server:
        server.send_message(data)
