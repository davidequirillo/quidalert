// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get buttonAccept => 'Accept';

  @override
  String get buttonReject => 'Reject';

  @override
  String get labelDoNotHaveAccount => 'Don\'t have an account? Sign Up';

  @override
  String get labelPasswordForgotten => 'Forgot password?';

  @override
  String get labelRegistration => 'Registration';

  @override
  String get labelShowPassword => 'Show password';

  @override
  String get menuRequest => 'Request';

  @override
  String get menuRecents => 'Recents';

  @override
  String get menuSettings => 'Settings';

  @override
  String get menuTerms => 'Legal terms';

  @override
  String get menuProfile => 'Profile';

  @override
  String get textInvalidCredentials => 'Email or password not valid';

  @override
  String get textLoadingError => 'Loading error';

  @override
  String get textUnknownState => 'Unknown state';
}
