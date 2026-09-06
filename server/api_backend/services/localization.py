# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from models.general import UserLanguage, Alert, User
from services.security import OTP_CODE_TTL_MINUTES

user_langmap = {
    "en": {
        "act_expired_title": "Activation expired",
        "act_expired": "Activation code expired, retry account registration",
        "act_already_title": "User already active",
        "act_already": "User already active. You can login using the app",
        "act_not_valid": "Activation code not valid",
        "act_done_title": "Activation done successfully",
        "act_done": "Activation done successfully. Now you can login using the app",
        "login_code_subject": "Login verification code",
        "login_successful_subject": "Successful login notification",
        "mail_ignore": "If you have received this message for an error, please ignore it",
        "reg_subject": "Activate your account",
        "reset_code_subject": "Password reset verification code",
        "reset_done_subject": "Password change done"
    },
    "it": {
        "act_expired_title": "Attivazione scaduta",
        "act_expired": "Codice di attivazione scaduto, ritenta la registrazione tramite app",
        "act_already_title": "Utente già attivato",
        "act_already": "Utente già attivato, puoi fare l'accesso (login) tramite app",
        "act_not_valid": "Codice di attivazione non valido",
        "act_done_title": "Attivazione completata con successo",
        "act_done": "Attivazione completata con successo. Ora puoi fare l'accesso (login) mediante app",
        "login_code_subject": "Codice di verifica per l'accesso (login)",
        "login_successful_subject": "Notifica di accesso (login) effettuato con successo",
        "mail_ignore": "Se hai ricevuto questo messaggio per errore, ignoralo",
        "reg_subject": "Attiva il tuo account",
        "reset_code_subject": "Codice di verifica del reset password",
        "reset_done_subject": "Modifica password effettuata"
    }
}

alert_langmap = {
    "en": {
        "new_alert_mail_subject": "Alert notification",
        "new_alert_mail_body_summary": "An alert has been sent by a user in your area. Please check the app for details.",
        "new_alert_title": "New alert",
        "new_alert_prefix": "{name} has created a new alert:",
        "new_alert_action_label": "View",
        "new_alert_notification_to_sender": "You have created a new alert. Notifications have been sent as follows.\nChief included in alert: {chief_included_in_alert}\nChief notified via FCM (push): {chief_notified_via_fcm}\nChief notified via email: {chief_notified_via_email}\nNearby users included in alert: {nearby_users_included_in_alert}\nNearby users notified: {nearby_users_notified}",
        "new_alert_notification_to_sender_manager": "You have created a new alert. Notifications have been sent as follows.\nNearby users included in alert: {nearby_users_included_in_alert}\nNearby users notified: {nearby_users_notified}",
        "new_alert_contact_emergency_if_no_response": "Contact emergency services by phone if you do not receive a response in a short time.",
        "new_alert_no_chief_available": "No chief found. Contact emergency services by phone if the situation is serious.",
        "close_alert_title": "Alert closed",
        "close_alert_text": "The alert created on date {date} hour {hour}, has been closed by the chief manager. Closure type: {closing_type}",
        "close_alert_action_label": "View",
        "close_alert_positive_closure": "Positive",
        "close_alert_negative_closure": "Negative",
        "close_alert_neutral_closure": "Neutral",
        "close_alert_punitive_closure": "Punitive",
        "expand_alert_title": "Alert expanded",
        "expand_alert_text": "The alert created on date {date} hour {hour}, has been extended (by the chief manager)",
        "expand_alert_to_role_text": "The alert created on date {date} hour {hour}, has been extended (by the chief manager) to role: {role}, with radius: {radius}. Found {users_num} specialists in the area",
        "expand_alert_to_all_text": "The alert created on date {date} hour {hour}, has been extended (by the chief manager) to all nearby users, with radius: {radius}. Found {users_num} users in the area",
        "expand_alert_action_label": "View",
        "new_message_title": "New message",
        "new_message_text": "{name} sent a new message regarding the alert created on date {date}, hour {hour}: {content}",
        "new_message_action_label": "View"
    },
    "it": {
        "new_alert_mail_subject": "Notifica di allerta",
        "new_alert_mail_body_summary": "Un utente della tua zona ha inviato un'allerta. Controlla l'app per i dettagli.",
        "new_alert_title": "Nuova allerta",
        "new_alert_prefix": "{name} ha creato una nuova allerta:",
        "new_alert_action_label": "Vedi",
        "new_alert_notification_to_sender": "Hai creato una nuova allerta. Le notifiche sono state inviate come segue.\nCapo incluso nell'allerta: {chief_included_in_alert}\nCapo notificato via FCM (push): {chief_notified_via_fcm}\nCapo notificato via email: {chief_notified_via_email}\nUtenti nelle vicinanze inclusi nell'allerta: {nearby_users_included_in_alert}\nUtenti nelle vicinanze notificati: {nearby_users_notified}",
        "new_alert_notification_to_sender_manager": "Hai creato una nuova allerta. Le notifiche sono state inviate come segue.\nUtenti nelle vicinanze inclusi nell'allerta: {nearby_users_included_in_alert}\nUtenti nelle vicinanze notificati: {nearby_users_notified}",
        "new_alert_contact_emergency_if_no_response": "Contatta telefonicamente i soccorsi se non ricevi una risposta in tempi brevi.",
        "new_alert_no_chief_available": "Nessun capo trovato. Contatta telefonicamente i soccorsi se la situazione è grave.",
        "close_alert_title": "Allerta chiusa",
        "close_alert_text": "L'allerta creata in data {date} ora {hour}, è stata chiusa dal capo responsabile. Tipo di chiusura: {closing_type}",
        "close_alert_action_label": "Vedi",
        "close_alert_positive_closure": "Positiva",
        "close_alert_negative_closure": "Negativa",
        "close_alert_neutral_closure": "Neutrale",
        "close_alert_punitive_closure": "Punitiva",
        "expand_alert_title": "Allerta espansa",
        "expand_alert_text": "L'allerta creata in data {date} ora {hour}, è stata estesa (dal capo responsabile).",
        "expand_alert_to_role_text": "L'allerta creata in data {date} ora {hour}, è stata estesa (dal capo responsabile) al ruolo {role}, con raggio: {radius}. Trovati {users_num} specialisti nell'area",
        "expand_alert_to_all_text": "L'allerta creata in data {date} ora {hour}, è stata estesa (dal capo responsabile) a tutti gli utenti vicini, con raggio: {radius}. Trovati {users_num} utenti nell'area",
        "expand_alert_action_label": "Vedi",
        "new_message_title": "Nuovo messaggio",
        "new_message_text": "{name} ha inviato un nuovo messaggio riguardo all'allerta creata in data {date}, ora {hour}: {content}",
        "new_message_action_label": "Vedi"
    }
}

## General localizations

def localize_boolean(value: bool, lang: str):
    if (lang == UserLanguage.it.value):
        return "sì" if (value is True) else "no"
    else:
        return "yes" if (value is True) else "no"

## Mail body localization for users (activation, reset, login)

def localize_activation_code_mail(activation_url: str, lang: str):
    if (lang == UserLanguage.it.value):
        return f"""Ciao, 
        
per attivare il tuo account clicca sul seguente link:

{activation_url}

Se non hai richiesto questa registrazione, puoi ignorare questa email.
"""
    else: 
        return f"""Hello, 

to activate your account click on the following link:

{activation_url}

If you haven't asked this mail message, you can ignore it.
"""
    
def localize_reset_code_mail(code: str, lang: str):
    if (lang == UserLanguage.it.value):
        return f"""Ciao,

hai richiesto il reset della password.

Il tuo codice di verifica è:

{code}

Questo codice è valido per {OTP_CODE_TTL_MINUTES} minuti.
Se non hai richiesto tu il reset, puoi ignorare questo messaggio.
"""
    else: 
        return f"""Hello, 
        
you have requested a reset of your password.

Your verification code is:

{code}

This code is valid for {OTP_CODE_TTL_MINUTES} minutes.
If you haven't asked the reset, you can ignore this message.
"""
    
def localize_reset_successful_mail(lang: str):
    if (lang == UserLanguage.it.value):
        return f"""Ciao,

hai modificato la password con successo.

Se non sei stato tu, si raccomanda di effettuare al più presto un nuovo reset della password (nell'app, schermata di login, "password dimenticata").

Se il problema persiste, contattare l'autorità territoriale competente.
"""
    else: 
        return f"""Hello, 
        
you have changed your password successfully.

If it wasn't you, we recommend to do a new password reset immediately (in the app, login page, "forgot password").

If the problem persists, please contact the competent territorial authority
"""
    
def localize_login_successful_mail(lang: str):
    if (lang == UserLanguage.it.value):
        return f"""Ciao,

hai effettuato l'accesso (login) con successo.

Se non sei stato tu, si raccomanda di modificare al più presto la password (nell'app, schermata di login, "password dimenticata").

Se il problema persiste, contattare l'autorità territoriale competente.
"""
    else: 
        return f"""Hello,

you have logged in successfully.

If it wasn't you, we recommend to change your password immediately (in the app, login page, "forgot password").

If the problem persists, please contact the competent territorial authority.
"""

def localize_login_code_mail(code: str, lang: str):
    if (lang == UserLanguage.it.value):
        return f"""Ciao,

Per completare l'accesso (login), inserisci il codice di verifica.

Il tuo codice di verifica è:

{code}

Questo codice è valido per {OTP_CODE_TTL_MINUTES} minuti.
Se non hai richiesto tu l'accesso (login), ti raccomandiamo di modificare al più presto la password (nell'app, schermata di login, "password dimenticata").
"""
    else: 
        return f"""Hello, 
        
To complete the login, enter the verification code.

Your verification code is:

{code}

This code is valid for {OTP_CODE_TTL_MINUTES} minutes.
If you haven't asked the login, we recommend to change your password immediately (in the app, login page, "forgot password").
"""

## Mail body localization for alerts (new alert)

def localize_new_alert_mail(alert: Alert, sender: User, chief_email: str, lang: str):
    if (lang == UserLanguage.it.value):
        return f"""Ciao, 

{alert_langmap[lang]['new_alert_mail_body_summary']}

Dati allerta:
- ID: {alert.id}
- Descrizione: {alert.description}
- Coordinate: {alert.latitude}, {alert.longitude}
- Indirizzo approssimativo: {alert.address}
- Data creazione: {alert.created_at} (Nota importante: l'orario è in UTC. Convertilo nella tua ora locale)

Capo responsabile (chief manager):
{chief_email}

Dati mittente allerta: 
- Nome: {sender.firstname}
- Cognome: {sender.surname}
- Email: {sender.email}
- Telefono: {sender.phone}
- Via: {sender.street}
- Città: {sender.city}
- CAP: {sender.postal_code}
- Provincia: {sender.province}
- Nazione: {sender.country}
- Data di nascita: {sender.birthdate}
"""
    else:
        return f"""Hello, 
        
{alert_langmap[lang]['new_alert_mail_body_summary']}

Alert data:
- ID: {alert.id}
- Description: {alert.description}
- Coordinates: {alert.latitude}, {alert.longitude}
- Approximate address: {alert.address}
- Creation date: {alert.created_at} (Important note: the time is in UTC. Please, convert it to your local time)

Chief manager:
{chief_email}

Alert sender data:
- Name: {sender.firstname}
- Surname: {sender.surname}
- Email: {sender.email}
- Phone: {sender.phone}
- Street: {sender.street}, 
- City: {sender.city}
- Postal code: {sender.postal_code}
- Province: {sender.province}
- Country: {sender.country}
- Birth date: {sender.birthdate}
"""
