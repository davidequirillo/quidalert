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
  String get buttonAdd => 'Add';

  @override
  String get buttonBack => 'Back';

  @override
  String get buttonCancel => 'Cancel';

  @override
  String get buttonDelete => 'Delete';

  @override
  String get buttonReject => 'Reject';

  @override
  String get buttonSearch => 'Search';

  @override
  String get errorGeneric => 'Generic error';

  @override
  String get errorBadRequest => 'Bad request';

  @override
  String get errorCannotReadFile => 'Cannot read file';

  @override
  String get errorCodeNotValid => 'Code not valid';

  @override
  String get errorCodeOrEmailNotValid => 'Code or email not valid';

  @override
  String get errorDigitOnly => 'Only digits are admitted';

  @override
  String get errorEmailNotFound => 'Email not found';

  @override
  String get errorEmailAlreadyExist => 'Email already exists';

  @override
  String get errorEmailAlreadyRegistered => 'Email already registered';

  @override
  String get errorEntriesNotAdded => 'Some entries have not been added';

  @override
  String get errorError => 'Error';

  @override
  String get errorInvalidCredentials => 'Email or password not valid';

  @override
  String get errorLoading => 'Loading error';

  @override
  String get errorLoginLocked => 'Too many attempts, login is locked for 24 hours';

  @override
  String get errorNetwork => 'Network error';

  @override
  String get errorNoEntryToAdd => 'No entry to add';

  @override
  String get errorNotAuthorized => 'Not authorized';

  @override
  String get errorNotAuthorizedDoLogin => 'Not authorized, do logout and retry login';

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
  String get errorPermissionsNotValid => 'Permissions not valid';

  @override
  String get errorStringNotValid => 'String not valid';

  @override
  String get errorStringTooLong => 'String too long';

  @override
  String get errorStringTooShort => 'String too short';

  @override
  String get errorUnknownState => 'Unknown state';

  @override
  String get errorSessionNotValidOrExpired => 'Session not valid or expired';

  @override
  String get labelAddEmailsToWhiteList => 'Add email addressed to white list';

  @override
  String get labelAdvice => 'Advice';

  @override
  String get labelAllMasculinePlural => 'All';

  @override
  String get labelAuthorizedBy => 'Authorized by';

  @override
  String get labelClickToSelectFile => 'Click to select file';

  @override
  String get labelClickSearchToLoadEntries => 'Click search to get entries';

  @override
  String get labelCompetenceTerritory => 'Competence territory';

  @override
  String get labelCompleteProfile => 'Complete profile';

  @override
  String get labelConfirmPassword => 'Confirm password';

  @override
  String get labelConfirmNewPassword => 'Confirm new password';

  @override
  String get labelCurrentWhiteListEntries => 'Current white list entries';

  @override
  String get labelDetails => 'Details';

  @override
  String get labelDoNotHaveAccount => 'Don\'t have an account? Sign Up';

  @override
  String get labelEmailSingle => 'Single email address';

  @override
  String get labelEmailMany => 'Many email addresses';

  @override
  String get labelEntrySingle => 'Single entry';

  @override
  String get labelEntriesAuthorizedByMe => 'All entries authorized by me';

  @override
  String get labelEntriesAll => 'All entries';

  @override
  String get labelEnterVerificationMailCode => 'Enter the verification code just sent to you by email';

  @override
  String get labelEntriesDeleted => 'Deleted entries';

  @override
  String get labelEntriesFailed => 'Failed entries';

  @override
  String get labelEntriesTotal => 'Total entries';

  @override
  String get labelEntriesAdded => 'Added entries';

  @override
  String get labelEntriesExisting => 'Existing entries';

  @override
  String get labelFileSelected => 'File selected';

  @override
  String get labelFirstname => 'Firstname';

  @override
  String get labelGpsPosition => 'GPS position';

  @override
  String get labelGpsPositionTest => 'GPS position test';

  @override
  String get labelLastRefreshAt => 'Last refresh at';

  @override
  String get labelLanguage => 'Language';

  @override
  String get labelNewAlert => 'New alert';

  @override
  String get labelNewPassword => 'New password';

  @override
  String get labelPasswordForgotten => 'Forgot password?';

  @override
  String get labelRecents => 'Recents';

  @override
  String get labelRegistration => 'Registration';

  @override
  String get labelRowsTotal => 'Total rows';

  @override
  String get labelSelect => 'Select';

  @override
  String get labelShowPassword => 'Show password';

  @override
  String get labelSurname => 'Surname';

  @override
  String get labelNoEntryFound => 'No entry found';

  @override
  String get labelTypeDeleteToConfirm => 'Type DELETE to confirm';

  @override
  String get labelVerificationCode => 'Verification code';

  @override
  String get labelWaitPlease => 'Please, wait';

  @override
  String get menuSettings => 'Settings';

  @override
  String get menuTerms => 'Legal terms';

  @override
  String get menuProfile => 'Profile';

  @override
  String get menuRegisteredUsers => 'Registered users';

  @override
  String get menuResetPrivileges => 'Reset privileges';

  @override
  String get menuUploadTerms => 'Upload legal terms';

  @override
  String get menuUsers => 'Users';

  @override
  String get menuWhiteList => 'Registration white list';

  @override
  String get successLogin => 'Login successful';

  @override
  String get successLoginAdvice => 'It is recommended to refresh at least once every 6 months to maintain the session (thus avoiding the needing of login)';

  @override
  String get successRegistration => 'If email address is valid, you will receive an activation mail message. If you don\'t receive it, ask to the competent territorial authority';

  @override
  String get successResetRequest => 'If email address is valid, you will receive a verification code to your email address. The code must be inserted here with the new password';

  @override
  String get successPasswordChanged => 'Password changed successfully';

  @override
  String get successUpload => 'Upload done successfully';

  @override
  String get successGeneric => 'Operation done';
}
