# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import smtplib
from email.message import EmailMessage
from firebase_admin import messaging as firebase_messaging
from sqlmodel import select, update
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
    log_notify_many_clients_error
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

def get_user_fcm_token(user_id, db_session):
    fcm_token = None
    statement = select(RefreshToken).where(
        RefreshToken.user_id == user_id).where(
            RefreshToken.fcm_token != None)
    rtoken = db_session.exec(statement).first()
    if rtoken:
        fcm_token = rtoken.fcm_token
    return fcm_token

def notify_single_client(
        user_id, fcm_token, 
        msg_title: str, msg_body: str, msg_data: dict, 
        request_info, db_session):
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
        log_notify_single_client_unregistered_error(request_info, detail=f"FCM token associated with user_id {user_id} is unregistered, deleting it...")
        # We clean unregistered FCM token from database
        try:
            user_id_as_uuid = string_as_uuid(user_id)
        except Exception as e_sub:
            log_notify_single_client_unregistered_error(request_info, detail=f"Error converting user_id {user_id} from database: {e_sub}")
        try:
            statement = select(RefreshToken).where(
                RefreshToken.user_id == user_id_as_uuid).where(
                    RefreshToken.fcm_token == fcm_token)
            rtoken = db_session.exec(statement).first()
            if rtoken:
                rtoken.fcm_token = None
                rtoken.fcm_token_updated_at = None
                db_session.add(rtoken)
                db_session.commit()
                log_notify_single_client_unregistered_error(request_info, detail=f"FCM token associated with user_id {user_id} deleted from database")
        except Exception as e_sub:
            db_session.rollback()
            log_notify_single_client_unregistered_error(request_info, detail=f"Error deleting FCM token associated with user_id {user_id} from database: {e_sub}")
        raise(e)
    except Exception as e:
        log_notify_single_client_error(request_info, detail=f"Error notifying single client: {e}")
        raise(e)

def notify_many_clients(
        user_ids, fcm_tokens, 
        msg_title: str, msg_body: str, msg_data: dict, 
        request_info, db_session):
    success_count = 0
    failure_count = 0
    # Note: chunk size can be 500 at max
    chunk_size = 10 if settings.app_mode == 'development' else 500
    for i in range(0, len(fcm_tokens), chunk_size):
        chunk_tokens = fcm_tokens[i:i+chunk_size]
        chunk_user_ids = user_ids[i:i+chunk_size]
        push_msg = firebase_messaging.MulticastMessage(
            notification=firebase_messaging.Notification(
                title=msg_title,
                body=msg_body
            ),
            data=msg_data,
            tokens=chunk_tokens
        )
        try:
            response = firebase_messaging.send_each_for_multicast(push_msg)
            if response.failure_count > 0:
                tokens_to_delete_by_ids = []
                tokens_to_delete = []
                for index, res in enumerate(response.responses):
                    if not res.success:
                        if str(res.exception) == 'NotRegistered':
                            tokens_to_delete_by_ids.append(chunk_user_ids[index])
                            tokens_to_delete.append(chunk_tokens[index])
                if tokens_to_delete_by_ids:
                    log_notify_many_clients_unregistered_warning(request_info, detail=f"Chunk {i // chunk_size + 1}: FCM token unregistered for user_ids {tokens_to_delete_by_ids}, deleting wrong fcm tokens...")
                    tokens_to_delete_by_uuids = []
                    for uid in tokens_to_delete_by_ids:
                        try:
                            tokens_to_delete_by_uuids.append(string_as_uuid(uid))
                        except Exception as e_sub:
                            log_notify_many_clients_unregistered_warning(request_info, detail=f"Chunk {i // chunk_size + 1}: Error converting user_id string to UUID: {e_sub}")
                    try:
                        # We clean unregistered FCM tokens (by ids in...) from database
                        statement = update(RefreshToken).where(
                        RefreshToken.user_id.in_(tokens_to_delete_by_uuids) # type:ignore
                            ).where(RefreshToken.fcm_token.in_(tokens_to_delete) # type:ignore
                            ).values(
                            fcm_token=None, fcm_token_updated_at=None)
                        db_session.exec(statement)
                        db_session.commit()
                        log_notify_many_clients_unregistered_warning(request_info, detail=f"Chunk {i // chunk_size + 1}: {len(tokens_to_delete)} wrong fcm tokens deleted from database")
                    except Exception as e_sub:
                        db_session.rollback()
                        log_notify_many_clients_unregistered_warning(request_info, detail=f"Chunk {i // chunk_size + 1}: error deleting wrong fcm tokens from database: {e_sub}")
            log_notify_many_clients_info(request_info, detail=f"Chunk {i // chunk_size + 1}: {response.success_count} success, {response.failure_count} failures")
            success_count += response.success_count
            failure_count += response.failure_count
        except Exception as e:
            log_notify_many_clients_error(request_info, detail=f"Chunk {i // chunk_size + 1}: error notifying clients: {e}")
            failure_count += len(chunk_tokens)
    log_notify_many_clients_info(request_info, detail=f"{success_count} success, {failure_count} failures")
    return success_count
