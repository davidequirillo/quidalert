import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_it.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale) : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate = _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates = <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('it')
  ];

  /// No description provided for @buttonAccept.
  ///
  /// In en, this message translates to:
  /// **'Accept'**
  String get buttonAccept;

  /// No description provided for @buttonCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get buttonCancel;

  /// No description provided for @buttonReject.
  ///
  /// In en, this message translates to:
  /// **'Reject'**
  String get buttonReject;

  /// No description provided for @errorGeneric.
  ///
  /// In en, this message translates to:
  /// **'Generic error'**
  String get errorGeneric;

  /// No description provided for @errorBadRequest.
  ///
  /// In en, this message translates to:
  /// **'Bad request'**
  String get errorBadRequest;

  /// No description provided for @errorCodeOrEmailNotValid.
  ///
  /// In en, this message translates to:
  /// **'Code or email not valid'**
  String get errorCodeOrEmailNotValid;

  /// No description provided for @errorDigitOnly.
  ///
  /// In en, this message translates to:
  /// **'Only digits are admitted'**
  String get errorDigitOnly;

  /// No description provided for @errorEmailAlreadyRegistered.
  ///
  /// In en, this message translates to:
  /// **'Email already registered'**
  String get errorEmailAlreadyRegistered;

  /// No description provided for @errorInvalidCredentials.
  ///
  /// In en, this message translates to:
  /// **'Email or password not valid'**
  String get errorInvalidCredentials;

  /// No description provided for @errorLoading.
  ///
  /// In en, this message translates to:
  /// **'Loading error'**
  String get errorLoading;

  /// No description provided for @errorNetwork.
  ///
  /// In en, this message translates to:
  /// **'Network error'**
  String get errorNetwork;

  /// No description provided for @errorRegNotAuthorized.
  ///
  /// In en, this message translates to:
  /// **'Registration not authorized: ask to competent territorial authority'**
  String get errorRegNotAuthorized;

  /// No description provided for @errorPasswordsDoNotMatch.
  ///
  /// In en, this message translates to:
  /// **'Passwords do not match'**
  String get errorPasswordsDoNotMatch;

  /// No description provided for @errorPasswordMissingUppercase.
  ///
  /// In en, this message translates to:
  /// **'Password must contain at least an uppercase character'**
  String get errorPasswordMissingUppercase;

  /// No description provided for @errorPasswordMissingLowercase.
  ///
  /// In en, this message translates to:
  /// **'Password must contain at least a lowercase character'**
  String get errorPasswordMissingLowercase;

  /// No description provided for @errorPasswordMissingDigit.
  ///
  /// In en, this message translates to:
  /// **'Password must contain at least a digit'**
  String get errorPasswordMissingDigit;

  /// No description provided for @errorPasswordMissingSpecial.
  ///
  /// In en, this message translates to:
  /// **'Password must contain at least a special character'**
  String get errorPasswordMissingSpecial;

  /// No description provided for @errorStringNotValid.
  ///
  /// In en, this message translates to:
  /// **'String not valid'**
  String get errorStringNotValid;

  /// No description provided for @errorStringTooLong.
  ///
  /// In en, this message translates to:
  /// **'String too long'**
  String get errorStringTooLong;

  /// No description provided for @errorStringTooShort.
  ///
  /// In en, this message translates to:
  /// **'String too short'**
  String get errorStringTooShort;

  /// No description provided for @errorUnknownState.
  ///
  /// In en, this message translates to:
  /// **'Unknown state'**
  String get errorUnknownState;

  /// No description provided for @errorSessionNotValidOrExpired.
  ///
  /// In en, this message translates to:
  /// **'Session not valid or expired'**
  String get errorSessionNotValidOrExpired;

  /// No description provided for @labelCompetenceTerritory.
  ///
  /// In en, this message translates to:
  /// **'Competence territory'**
  String get labelCompetenceTerritory;

  /// No description provided for @labelConfirmPassword.
  ///
  /// In en, this message translates to:
  /// **'Confirm password'**
  String get labelConfirmPassword;

  /// No description provided for @labelConfirmNewPassword.
  ///
  /// In en, this message translates to:
  /// **'Confirm new password'**
  String get labelConfirmNewPassword;

  /// No description provided for @labelDoNotHaveAccount.
  ///
  /// In en, this message translates to:
  /// **'Don\'t have an account? Sign Up'**
  String get labelDoNotHaveAccount;

  /// No description provided for @labelFirstname.
  ///
  /// In en, this message translates to:
  /// **'Firstname'**
  String get labelFirstname;

  /// No description provided for @labelLastRefreshAt.
  ///
  /// In en, this message translates to:
  /// **'Last refresh at'**
  String get labelLastRefreshAt;

  /// No description provided for @labelNewAlert.
  ///
  /// In en, this message translates to:
  /// **'New alert'**
  String get labelNewAlert;

  /// No description provided for @labelNewPassword.
  ///
  /// In en, this message translates to:
  /// **'New password'**
  String get labelNewPassword;

  /// No description provided for @labelPasswordForgotten.
  ///
  /// In en, this message translates to:
  /// **'Forgot password?'**
  String get labelPasswordForgotten;

  /// No description provided for @labelRecents.
  ///
  /// In en, this message translates to:
  /// **'Recents'**
  String get labelRecents;

  /// No description provided for @labelRegistration.
  ///
  /// In en, this message translates to:
  /// **'Registration'**
  String get labelRegistration;

  /// No description provided for @labelShowPassword.
  ///
  /// In en, this message translates to:
  /// **'Show password'**
  String get labelShowPassword;

  /// No description provided for @labelSurname.
  ///
  /// In en, this message translates to:
  /// **'Surname'**
  String get labelSurname;

  /// No description provided for @labelVerificationCode.
  ///
  /// In en, this message translates to:
  /// **'Verification code'**
  String get labelVerificationCode;

  /// No description provided for @menuRequest.
  ///
  /// In en, this message translates to:
  /// **'Request'**
  String get menuRequest;

  /// No description provided for @menuRecents.
  ///
  /// In en, this message translates to:
  /// **'Recents'**
  String get menuRecents;

  /// No description provided for @menuSettings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get menuSettings;

  /// No description provided for @menuTerms.
  ///
  /// In en, this message translates to:
  /// **'Legal terms'**
  String get menuTerms;

  /// No description provided for @menuProfile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get menuProfile;

  /// No description provided for @successLogin.
  ///
  /// In en, this message translates to:
  /// **'Login successful'**
  String get successLogin;

  /// No description provided for @successLoginAdvice.
  ///
  /// In en, this message translates to:
  /// **'It is recommended to refresh at least once every 6 months to maintain the session (thus avoiding the needing of logging in)'**
  String get successLoginAdvice;

  /// No description provided for @successRegistration.
  ///
  /// In en, this message translates to:
  /// **'If email address is valid, you will receive an activation mail message. If you don\'t receive it, ask to the competent territorial authority'**
  String get successRegistration;

  /// No description provided for @successResetRequest.
  ///
  /// In en, this message translates to:
  /// **'If email address is valid, you will receive a verification code to your email address. The code must be inserted here with the new password'**
  String get successResetRequest;

  /// No description provided for @successPasswordChanged.
  ///
  /// In en, this message translates to:
  /// **'Password changed successfully'**
  String get successPasswordChanged;

  /// No description provided for @successGeneric.
  ///
  /// In en, this message translates to:
  /// **'Operation done'**
  String get successGeneric;
}

class _AppLocalizationsDelegate extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) => <String>['en', 'it'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {


  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en': return AppLocalizationsEn();
    case 'it': return AppLocalizationsIt();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.'
  );
}
