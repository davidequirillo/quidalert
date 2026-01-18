# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import smtplib
from email.message import EmailMessage
from core.settings import settings
from services.localization import (langmap, 
    localize_activation_mail, localize_reset_code_mail, 
    localize_reset_successful_mail, 
    localize_login_successful_mail
    )

def send_mail_message(data):
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.send_message(data)

def send_activation_mail(email: str, token: str, lang: str):
    prot = settings.protocol
    sname = settings.server_name
    sport = settings.server_port
    act_url = f"{prot}://{sname}:{sport}/api/activate?email={email}&token={token}"
    msg = EmailMessage()
    msg["Subject"] = langmap[lang]["reg_subject"]
    msg["From"] = settings.smtp_from
    msg["To"] = email
    msg.set_content(localize_activation_mail(act_url, lang))     
    send_mail_message(msg)

def send_reset_code_mail(email: str, code: str, lang: str):
    msg = EmailMessage()
    msg["Subject"] = langmap[lang]["reset_code_subject"]
    msg["From"] = settings.smtp_from
    msg["To"] = email
    msg.set_content(localize_reset_code_mail(code, lang))     
    send_mail_message(msg)

def send_reset_successful_mail(email: str, lang: str):
    msg = EmailMessage()
    msg["Subject"] = langmap[lang]["reset_done_subject"]
    msg["From"] = settings.smtp_from
    msg["To"] = email
    msg.set_content(localize_reset_successful_mail(lang))     
    send_mail_message(msg)

def send_login_successful_mail(email: str, lang: str):
    msg = EmailMessage()
    msg["Subject"] = langmap[lang]["login_successful_subject"]
    msg["From"] = settings.smtp_from
    msg["To"] = email
    msg.set_content(localize_login_successful_mail(lang))
    send_mail_message(msg)