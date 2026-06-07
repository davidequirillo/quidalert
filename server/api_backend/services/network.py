# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import smtplib
from email.message import EmailMessage
from firebase_admin import messaging as firebase_messaging
from sqlmodel import Session, select, update
from models.general import string_as_uuid, RefreshToken
from core.settings import settings
from services.localization import (langmap, 
    localize_activation_mail, localize_reset_code_mail, 
    localize_reset_successful_mail, 
    localize_login_successful_mail,
    localize_login_code_mail
    )
from core.common_events import (
    log_notify_single_client_unregistered_error,
    log_notify_single_client_error,
    log_notify_single_client_success,
    log_notify_many_clients_unregistered_warning,
    log_notify_many_clients_info,
)

def send_mail_message(data):
    if not settings.send_emails: # in testing mode we can disable sending emails
        return
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

def send_login_code_mail(email: str, code: str, lang: str):
    msg = EmailMessage()
    msg["Subject"] = langmap[lang]["login_code_subject"]
    msg["From"] = settings.smtp_from
    msg["To"] = email
    msg.set_content(localize_login_code_mail(code, lang))     
    send_mail_message(msg)

def notify_single_client(
        user_id, fcm_token, 
        msg_title: str, msg_body: str, msg_data: dict, 
        request_info, db_engine):
    push_msg = firebase_messaging.Message(
        notification=firebase_messaging.Notification(
            title=msg_title,
            body=msg_body
        ),
        data=msg_data,
        token=fcm_token,
    )
    try:
        response = firebase_messaging.send(push_msg)
        log_notify_single_client_success(request_info, detail=f"Notification sent successfully to user_id {user_id}")
        return response
    except firebase_messaging.UnregisteredError as e:
        log_notify_single_client_unregistered_error(request_info, detail="FCM token unregistered, deleting it...")
        with Session(db_engine) as db_session:
            # We clean unregistered FCM token from database
            try:
                user_id_as_uuid = string_as_uuid(user_id)
            except Exception as e:
                raise Exception(f"Error converting user_id string to UUID: {e}")
            statement = select(RefreshToken).where(
                RefreshToken.user_id == user_id_as_uuid).where(
                    RefreshToken.fcm_token == fcm_token)
            rtoken = db_session.exec(statement).first()
            if rtoken:
                rtoken.fcm_token = None
                rtoken.fcm_token_updated_at = None
                db_session.add(rtoken)
                db_session.commit()
        raise(e)
    except Exception as e:
        log_notify_single_client_error(request_info, detail=f"Error notifying single client: {e}")
        raise(e)

def notify_many_clients(
        user_ids, fcm_tokens, 
        msg_title: str, msg_body: str, msg_data: dict, 
        request_info, db_engine):
    success_count = 0
    failure_count = 0
    # Firebase allows sending notifications to a maximum of 500 tokens at a time
    for i in range(0, len(fcm_tokens), 500):
        chunk_tokens = fcm_tokens[i:i+500]
        chunk_user_ids = user_ids[i:i+500]
        push_msg = firebase_messaging.MulticastMessage(
            notification=firebase_messaging.Notification(
                title=msg_title,
                body=msg_body
            ),
            data=msg_data,
            tokens=chunk_tokens
        )
        response = firebase_messaging.send_each_for_multicast(push_msg)
        if response.failure_count > 0:
            tokens_to_delete_by_ids = []
            tokens_to_delete = []
            for index, res in enumerate(response.responses):
                if not res.success:
                    if res.exception.code == 'messaging/registration-token-not-registered':
                        tokens_to_delete_by_ids.append(chunk_user_ids[index])
                        tokens_to_delete.append(chunk_tokens[index])
            if tokens_to_delete_by_ids:
                log_notify_many_clients_unregistered_warning(request_info, detail=f"FCM token unregistered for user_ids {tokens_to_delete_by_ids}, deleting wrong fcm tokens")
                tokens_to_delete_by_uuids = []
                for uid in tokens_to_delete_by_ids:
                    try:
                        tokens_to_delete_by_uuids.append(string_as_uuid(uid))
                    except Exception as e:
                        log_notify_many_clients_unregistered_warning(request_info, detail=f"Error converting user_id string to UUID: {e}")
                with Session(db_engine) as db_session:
                # We clean unregistered FCM tokens (by ids in...) from database
                    statement = update(RefreshToken).where(
                        RefreshToken.user_id.in_(tokens_to_delete_by_uuids) # type:ignore
                        ).where(RefreshToken.fcm_token.in_(tokens_to_delete) # type:ignore
                        ).values(
                            fcm_token=None, fcm_token_updated_at=None)
                    db_session.exec(statement)
                    db_session.commit()
                log_notify_many_clients_unregistered_warning(request_info, detail=f"Invalid FCM tokens deleted from db: {tokens_to_delete}")
        success_count += response.success_count
        failure_count += response.failure_count
    log_notify_many_clients_info(request_info, detail=f"{success_count} success, {failure_count} failures")
    return success_count