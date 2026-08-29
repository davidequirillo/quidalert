# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from email.message import EmailMessage
from email.utils import formataddr
from core.settings import settings
from services.network import send_mail_message
from services.localization import (user_langmap, 
    localize_activation_code_mail, localize_reset_code_mail, 
    localize_reset_successful_mail, 
    localize_login_code_mail,
    localize_login_successful_mail
    )
from core.btask_events import (
    log_user_activation_code_mail_error,
    log_user_reset_code_mail_error,
    log_user_reset_successful_mail_error,
    log_user_login_code_mail_error,
    log_user_login_successful_mail_error
)

def send_activation_code_mail(email: str, token: str, lang: str, request_info: dict):
    prot = settings.protocol
    sname = settings.server_name
    sport = settings.server_port
    act_url = f"{prot}://{sname}:{sport}/api/activate?email={email}&token={token}"
    msg = EmailMessage()
    msg["Subject"] = user_langmap[lang]["reg_subject"]
    msg["From"] = formataddr((settings.smtp_from_name, settings.smtp_from))
    msg["To"] = email
    msg.set_content(localize_activation_code_mail(act_url, lang))
    try:
        send_mail_message(msg, request_info)
    except Exception as e:
        log_user_activation_code_mail_error(email, request_info, detail=str(e))

def send_reset_code_mail(email: str, code: str, lang: str, request_info: dict):
    msg = EmailMessage()
    msg["Subject"] = user_langmap[lang]["reset_code_subject"]
    msg["From"] = formataddr((settings.smtp_from_name, settings.smtp_from))
    msg["To"] = email
    msg.set_content(localize_reset_code_mail(code, lang))     
    try:
        send_mail_message(msg, request_info)
    except Exception as e:
        log_user_reset_code_mail_error(email, request_info, detail=str(e))

def send_reset_successful_mail(email: str, lang: str, request_info: dict):
    msg = EmailMessage()
    msg["Subject"] = user_langmap[lang]["reset_done_subject"]
    msg["From"] = formataddr((settings.smtp_from_name, settings.smtp_from))
    msg["To"] = email
    msg.set_content(localize_reset_successful_mail(lang))     
    try:
        send_mail_message(msg, request_info)
    except Exception as e:
        log_user_reset_successful_mail_error(email, request_info, detail=str(e))

def send_login_code_mail(email: str, code: str, lang: str, request_info: dict):
    msg = EmailMessage()
    msg["Subject"] = user_langmap[lang]["login_code_subject"]
    msg["From"] = formataddr((settings.smtp_from_name, settings.smtp_from))
    msg["To"] = email
    msg.set_content(localize_login_code_mail(code, lang))     
    try:
        send_mail_message(msg, request_info)
    except Exception as e:
        log_user_login_code_mail_error(email, request_info, detail=str(e))

def send_login_successful_mail(email: str, lang: str, request_info: dict):
    msg = EmailMessage()
    msg["Subject"] = user_langmap[lang]["login_successful_subject"]
    msg["From"] = formataddr((settings.smtp_from_name, settings.smtp_from))
    msg["To"] = email
    msg.set_content(localize_login_successful_mail(lang))
    try:
        send_mail_message(msg, request_info)
    except Exception as e:
        log_user_login_successful_mail_error(email, request_info, detail=str(e))
