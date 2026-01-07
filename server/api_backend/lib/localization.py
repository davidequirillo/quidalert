# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from lib.models import UserLanguage

langmap = {
    "en": {
        "act_expired_title": "Activation expired",
        "act_expired": "Activation code expired, retry account registration",
        "act_already_title": "User already active",
        "act_already": "User already active. You can login using the app",
        "act_not_valid": "Activation code not valid",
        "act_title": "Activation done successfully",
        "act_message": "Activation done successfully. Now you can login using the app",
        "mail_ignore": "If you have received this message for an error, please ignore it",
        "reg_subject": "Activate your account"
    },
    "it": {
        "act_expired_title": "Attivazione scaduta",
        "act_expired": "Codice di attivazione scaduto, ritenta la registrazione tramite app",
        "act_already_title": "Utente già attivato",
        "act_already": "Utente già attivato, puoi fare l'accesso (login) tramite app",
        "act_not_valid": "Codice di attivazione non valido",
        "act_success_title": "Attivazione completata con successo",
        "act_success": "Attivazione completata con successo. Ora puoi fare l'accesso (login) mediante app",
        "mail_ignore": "Se hai ricevuto questo messaggio per errore, ignoralo",
        "reg_subject": "Attiva il tuo account"
    }
}

def localize_activation_mail(activation_url: str, lang: str):
    if (lang == UserLanguage.it):
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

def localize_empty_string(): # I'm including this for visual convenience.
    return ""
