// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Italian (`it`).
class AppLocalizationsIt extends AppLocalizations {
  AppLocalizationsIt([String locale = 'it']) : super(locale);

  @override
  String get buttonAccept => 'Accetta';

  @override
  String get buttonCancel => 'Annulla';

  @override
  String get buttonReject => 'Rifiuta';

  @override
  String get errorGeneric => 'Errore generico';

  @override
  String get errorBadRequest => 'Richiesta non accettata';

  @override
  String get errorCodeOrEmailNotValid => 'Codice o indirizzo email non valido';

  @override
  String get errorDigitOnly => 'Sono ammesse solo cifre';

  @override
  String get errorEmailAlreadyRegistered => 'Email già registrata';

  @override
  String get errorInvalidCredentials => 'Email o password non valide';

  @override
  String get errorLoading => 'Errore di caricamento';

  @override
  String get errorNetwork => 'Errore di rete';

  @override
  String get errorRegNotAuthorized => 'Registrazione non autorizzata: chiedere all\'autorità territoriale competente';

  @override
  String get errorPasswordsDoNotMatch => 'Le password non corrispondono';

  @override
  String get errorPasswordMissingUppercase => 'La password deve contenere almeno una lettera maiuscola';

  @override
  String get errorPasswordMissingLowercase => 'La password deve contenere almeno una lettera minuscola';

  @override
  String get errorPasswordMissingDigit => 'La password deve contenere almeno una cifra';

  @override
  String get errorPasswordMissingSpecial => 'La password deve contenere almeno un carattere speciale';

  @override
  String get errorStringNotValid => 'Stringa non valida';

  @override
  String get errorStringTooLong => 'Stringa troppo lunga';

  @override
  String get errorStringTooShort => 'Stringa troppo corta';

  @override
  String get errorUnknownState => 'Stato sconosciuto';

  @override
  String get errorSessionNotValidOrExpired => 'Sessione non valida o scaduta';

  @override
  String get labelCompetenceTerritory => 'Territorio di competenza';

  @override
  String get labelConfirmPassword => 'Conferma password';

  @override
  String get labelConfirmNewPassword => 'Conferma nuova password';

  @override
  String get labelDoNotHaveAccount => 'Non hai un account? Registrati';

  @override
  String get labelFirstname => 'Nome';

  @override
  String get labelLastRefreshAt => 'Data dell\'ultima refresh';

  @override
  String get labelNewAlert => 'Nuova allerta';

  @override
  String get labelNewPassword => 'Nuova password';

  @override
  String get labelPasswordForgotten => 'Password dimenticata?';

  @override
  String get labelRecents => 'Recenti';

  @override
  String get labelRegistration => 'Registrazione';

  @override
  String get labelShowPassword => 'Mostra password';

  @override
  String get labelSurname => 'Cognome';

  @override
  String get labelVerificationCode => 'Codice di verifica';

  @override
  String get menuRequest => 'Richiesta';

  @override
  String get menuRecents => 'Recenti';

  @override
  String get menuSettings => 'Impostazioni';

  @override
  String get menuTerms => 'Termini legali';

  @override
  String get menuProfile => 'Profilo';

  @override
  String get successLogin => 'Login effettuato con successo';

  @override
  String get successLoginAdvice => 'Si consiglia di fare un refresh almeno una volta ogni 6 mesi per mantenere la sessione (evitando così la necessità di effettuare il login)';

  @override
  String get successRegistration => 'Se l\'indirizzo email è valido, riceverai una mail con link di attivazione. In caso di mancata ricezione di essa, recarsi presso l\'autorità territoriale competente';

  @override
  String get successResetRequest => 'Se l\'indirizzo email è valido, riceverai un codice di verifica via email, da riportare qui con la nuova password';

  @override
  String get successPasswordChanged => 'Password modificata con successo';

  @override
  String get successGeneric => 'Operazione effettuata';
}
