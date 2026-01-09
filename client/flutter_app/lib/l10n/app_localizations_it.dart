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
  String get errorGeneric => 'Errore';

  @override
  String get errorBadRequest => 'Richiesta non accettata';

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
  String get labelCompetenceTerritory => 'Territorio di competenza';

  @override
  String get labelDoNotHaveAccount => 'Non hai un account? Registrati';

  @override
  String get labelFirstname => 'Nome';

  @override
  String get labelPasswordForgotten => 'Password dimenticata?';

  @override
  String get labelRegistration => 'Registrazione';

  @override
  String get labelShowPassword => 'Mostra password';

  @override
  String get labelSurname => 'Cognome';

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
  String get successRegistration => 'Se l\'indirizzo email è valido, riceverai una mail con link di attivazione. In caso di mancata ricezione di essa, recarsi presso l\'autorità territoriale competente';

  @override
  String get successGeneric => 'Operazione effettuata';
}
