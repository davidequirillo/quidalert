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
  String get buttonReject => 'Rifiuta';

  @override
  String get labelDoNotHaveAccount => 'Non hai un account? Registrati';

  @override
  String get labelPasswordForgotten => 'Password dimenticata?';

  @override
  String get labelRegistration => 'Registrazione';

  @override
  String get labelShowPassword => 'Mostra password';

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
  String get textInvalidCredentials => 'Email o password non valide';

  @override
  String get textLoadingError => 'Errore di caricamento';

  @override
  String get textUnknownState => 'Stato sconosciuto';
}
