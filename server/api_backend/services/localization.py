# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from models.general import UserLanguage
from services.security import RESET_CODE_TTL_MINUTES

langmap = {
    "en": {
        "act_expired_title": "Activation expired",
        "act_expired": "Activation code expired, retry account registration",
        "act_already_title": "User already active",
        "act_already": "User already active. You can login using the app",
        "act_not_valid": "Activation code not valid",
        "act_done_title": "Activation done successfully",
        "act_done": "Activation done successfully. Now you can login using the app",
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
        "login_successful_subject": "Notifica di accesso (login) effettuato con successo",
        "mail_ignore": "Se hai ricevuto questo messaggio per errore, ignoralo",
        "reg_subject": "Attiva il tuo account",
        "reset_code_subject": "Codice di verifica del reset password",
        "reset_done_subject": "Modifica password effettuata"
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
    
def localize_reset_code_mail(code: str, lang: str):
    if (lang == UserLanguage.it):
        return f"""Ciao,

hai richiesto il reset della password.

Il tuo codice di verifica è:

{code}

Questo codice è valido per {RESET_CODE_TTL_MINUTES} minuti.
Se non hai richiesto tu il reset, puoi ignorare questo messaggio.
"""
    else: 
        return f"""Hello, 
        
you have requested a reset of your password.

Your verification code is:

{code}

This code is valid for {RESET_CODE_TTL_MINUTES} minutes.
If you haven't asked the reset, you can ignore this message.
"""
    
def localize_reset_successful_mail(lang: str):
    if (lang == UserLanguage.it):
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
    if (lang == UserLanguage.it):
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

def localize_empty_string(): # I'm including this for visual convenience.
    return ""
