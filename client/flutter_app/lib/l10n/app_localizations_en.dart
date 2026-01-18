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
  String get buttonCancel => 'Cancel';

  @override
  String get buttonReject => 'Reject';

  @override
  String get errorGeneric => 'Generic error';

  @override
  String get errorBadRequest => 'Bad request';

  @override
  String get errorCodeOrEmailNotValid => 'Code or email not valid';

  @override
  String get errorDigitOnly => 'Only digits are admitted';

  @override
  String get errorEmailAlreadyRegistered => 'Email already registered';

  @override
  String get errorInvalidCredentials => 'Email or password not valid';

  @override
  String get errorLoading => 'Loading error';

  @override
  String get errorNetwork => 'Network error';

  @override
  String get errorRegNotAuthorized => 'Registration not authorized: ask to competent territorial authority';

  @override
  String get errorPasswordsDoNotMatch => 'Passwords do not match';

  @override
  String get errorPasswordMissingUppercase => 'Password must contain at least an uppercase character';

  @override
  String get errorPasswordMissingLowercase => 'Password must contain at least a lowercase character';

  @override
  String get errorPasswordMissingDigit => 'Password must contain at least a digit';

  @override
  String get errorPasswordMissingSpecial => 'Password must contain at least a special character';

  @override
  String get errorStringNotValid => 'String not valid';

  @override
  String get errorStringTooLong => 'String too long';

  @override
  String get errorStringTooShort => 'String too short';

  @override
  String get errorUnknownState => 'Unknown state';

  @override
  String get labelCompetenceTerritory => 'Competence territory';

  @override
  String get labelConfirmPassword => 'Confirm password';

  @override
  String get labelConfirmNewPassword => 'Confirm new password';

  @override
  String get labelDoNotHaveAccount => 'Don\'t have an account? Sign Up';

  @override
  String get labelFirstname => 'Firstname';

  @override
  String get labelLastRefreshAt => 'Last refresh at';

  @override
  String get labelNewPassword => 'New password';

  @override
  String get labelPasswordForgotten => 'Forgot password?';

  @override
  String get labelRegistration => 'Registration';

  @override
  String get labelShowPassword => 'Show password';

  @override
  String get labelSurname => 'Surname';

  @override
  String get labelVerificationCode => 'Verification code';

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
  String get successLogin => 'Login successful';

  @override
  String get successRegistration => 'If email address is valid, you will receive an activation mail message. If you don\'t receive it, ask to the competent territorial authority';

  @override
  String get successResetRequest => 'If email address is valid, you will receive a verification code to your email address. The code must be inserted here with the new password';

  @override
  String get successPasswordChanged => 'Password changed successfully';

  @override
  String get successGeneric => 'Operation done';
}
