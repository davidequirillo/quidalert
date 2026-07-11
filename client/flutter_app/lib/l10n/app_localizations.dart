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

  /// No description provided for @alertSender.
  ///
  /// In en, this message translates to:
  /// **'Sender'**
  String get alertSender;

  /// No description provided for @alertChief.
  ///
  /// In en, this message translates to:
  /// **'Chief'**
  String get alertChief;

  /// No description provided for @alertAlertedUsers.
  ///
  /// In en, this message translates to:
  /// **'Alerted users'**
  String get alertAlertedUsers;

  /// No description provided for @alertRadius.
  ///
  /// In en, this message translates to:
  /// **'Raggio'**
  String get alertRadius;

  /// No description provided for @alertStatusOpen.
  ///
  /// In en, this message translates to:
  /// **'Open'**
  String get alertStatusOpen;

  /// No description provided for @alertStatusClosed.
  ///
  /// In en, this message translates to:
  /// **'Closed'**
  String get alertStatusClosed;

  /// No description provided for @alertStatusPending.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get alertStatusPending;

  /// No description provided for @alertTypeGeneral.
  ///
  /// In en, this message translates to:
  /// **'General'**
  String get alertTypeGeneral;

  /// No description provided for @alertTypeLocal.
  ///
  /// In en, this message translates to:
  /// **'Local'**
  String get alertTypeLocal;

  /// No description provided for @alertTypeEmpty.
  ///
  /// In en, this message translates to:
  /// **'Empty'**
  String get alertTypeEmpty;

  /// No description provided for @alertTypeManaged.
  ///
  /// In en, this message translates to:
  /// **'Managed'**
  String get alertTypeManaged;

  /// No description provided for @buttonAccept.
  ///
  /// In en, this message translates to:
  /// **'Accept'**
  String get buttonAccept;

  /// No description provided for @buttonAdd.
  ///
  /// In en, this message translates to:
  /// **'Add'**
  String get buttonAdd;

  /// No description provided for @buttonBack.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get buttonBack;

  /// No description provided for @buttonCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get buttonCancel;

  /// No description provided for @buttonClear.
  ///
  /// In en, this message translates to:
  /// **'Clear'**
  String get buttonClear;

  /// No description provided for @buttonCopy.
  ///
  /// In en, this message translates to:
  /// **'Copy'**
  String get buttonCopy;

  /// No description provided for @buttonDelete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get buttonDelete;

  /// No description provided for @buttonModify.
  ///
  /// In en, this message translates to:
  /// **'Modify'**
  String get buttonModify;

  /// No description provided for @buttonObtain.
  ///
  /// In en, this message translates to:
  /// **'Obtain'**
  String get buttonObtain;

  /// No description provided for @buttonPromote.
  ///
  /// In en, this message translates to:
  /// **'Promote'**
  String get buttonPromote;

  /// No description provided for @buttonReject.
  ///
  /// In en, this message translates to:
  /// **'Reject'**
  String get buttonReject;

  /// No description provided for @buttonSearch.
  ///
  /// In en, this message translates to:
  /// **'Search'**
  String get buttonSearch;

  /// No description provided for @exceptionBadRequest.
  ///
  /// In en, this message translates to:
  /// **'Bad request'**
  String get exceptionBadRequest;

  /// No description provided for @exceptionForbiddenRequest.
  ///
  /// In en, this message translates to:
  /// **'Permissions not valid'**
  String get exceptionForbiddenRequest;

  /// No description provided for @exceptionGenericNotAuthorized.
  ///
  /// In en, this message translates to:
  /// **'Not authorized, retry login'**
  String get exceptionGenericNotAuthorized;

  /// No description provided for @exceptionNetwork.
  ///
  /// In en, this message translates to:
  /// **'Network error'**
  String get exceptionNetwork;

  /// No description provided for @exceptionServer.
  ///
  /// In en, this message translates to:
  /// **'Server error'**
  String get exceptionServer;

  /// No description provided for @exceptionNotFound.
  ///
  /// In en, this message translates to:
  /// **'Resource not found'**
  String get exceptionNotFound;

  /// No description provided for @exceptionFromJsonObj.
  ///
  /// In en, this message translates to:
  /// **'Json object reading error'**
  String get exceptionFromJsonObj;

  /// No description provided for @exceptionUnknown.
  ///
  /// In en, this message translates to:
  /// **'Unknown error'**
  String get exceptionUnknown;

  /// No description provided for @errorAccountBlocked.
  ///
  /// In en, this message translates to:
  /// **'Account blocked'**
  String get errorAccountBlocked;

  /// No description provided for @errorAddressNotFound.
  ///
  /// In en, this message translates to:
  /// **'Address not found'**
  String get errorAddressNotFound;

  /// No description provided for @errorAlertSimilarInZone.
  ///
  /// In en, this message translates to:
  /// **'A similar alert already exists in this zone'**
  String get errorAlertSimilarInZone;

  /// No description provided for @errorAlertSimilarInGeneral.
  ///
  /// In en, this message translates to:
  /// **'A similar general alert already exists'**
  String get errorAlertSimilarInGeneral;

  /// No description provided for @errorBadRequest.
  ///
  /// In en, this message translates to:
  /// **'Bad request'**
  String get errorBadRequest;

  /// No description provided for @errorCannotReadFile.
  ///
  /// In en, this message translates to:
  /// **'Cannot read file'**
  String get errorCannotReadFile;

  /// No description provided for @errorCodeNotValid.
  ///
  /// In en, this message translates to:
  /// **'Code not valid'**
  String get errorCodeNotValid;

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

  /// No description provided for @errorEmailNotFound.
  ///
  /// In en, this message translates to:
  /// **'Email not found'**
  String get errorEmailNotFound;

  /// No description provided for @errorEmailNotValid.
  ///
  /// In en, this message translates to:
  /// **'Email not valid'**
  String get errorEmailNotValid;

  /// No description provided for @errorEmailAlreadyExist.
  ///
  /// In en, this message translates to:
  /// **'Email already exists'**
  String get errorEmailAlreadyExist;

  /// No description provided for @errorEmailAlreadyRegistered.
  ///
  /// In en, this message translates to:
  /// **'Email already registered'**
  String get errorEmailAlreadyRegistered;

  /// No description provided for @errorError.
  ///
  /// In en, this message translates to:
  /// **'Error'**
  String get errorError;

  /// No description provided for @errorGeneric.
  ///
  /// In en, this message translates to:
  /// **'Generic error'**
  String get errorGeneric;

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

  /// No description provided for @errorLocationServicesDisabled.
  ///
  /// In en, this message translates to:
  /// **'Location services are disabled, go to settings and enable gps and location services'**
  String get errorLocationServicesDisabled;

  /// No description provided for @errorLocationPermissionDenied.
  ///
  /// In en, this message translates to:
  /// **'Location permissions are denied, go to settings to enable them'**
  String get errorLocationPermissionDenied;

  /// No description provided for @errorLocationPermissionDeniedForever.
  ///
  /// In en, this message translates to:
  /// **'You have permanently denied location permissions, go to settings and enable them'**
  String get errorLocationPermissionDeniedForever;

  /// No description provided for @errorLocationFetchTimeout.
  ///
  /// In en, this message translates to:
  /// **'Timeout error, I fetched the last know position'**
  String get errorLocationFetchTimeout;

  /// No description provided for @errorLoginLocked.
  ///
  /// In en, this message translates to:
  /// **'Too many attempts, login is locked for 24 hours'**
  String get errorLoginLocked;

  /// No description provided for @errorNoEntryToAdd.
  ///
  /// In en, this message translates to:
  /// **'No entry to add'**
  String get errorNoEntryToAdd;

  /// No description provided for @errorNoEntryFound.
  ///
  /// In en, this message translates to:
  /// **'No entry found'**
  String get errorNoEntryFound;

  /// No description provided for @errorNoFileSelected.
  ///
  /// In en, this message translates to:
  /// **'No file selected'**
  String get errorNoFileSelected;

  /// No description provided for @errorNotAuthorized.
  ///
  /// In en, this message translates to:
  /// **'Not authorized'**
  String get errorNotAuthorized;

  /// No description provided for @errorNotAuthorizedDoLogin.
  ///
  /// In en, this message translates to:
  /// **'Not authorized, retry login'**
  String get errorNotAuthorizedDoLogin;

  /// No description provided for @errorOpDeniedYouAreNotReliable.
  ///
  /// In en, this message translates to:
  /// **'Operation denied: you have been judged as not realiable'**
  String get errorOpDeniedYouAreNotReliable;

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

  /// No description provided for @errorPermissionsNotValid.
  ///
  /// In en, this message translates to:
  /// **'Permissions not valid'**
  String get errorPermissionsNotValid;

  /// No description provided for @errorPositionNotAvailable.
  ///
  /// In en, this message translates to:
  /// **'Position not available'**
  String get errorPositionNotAvailable;

  /// No description provided for @errorRegisteringDeviceForPushNotifications.
  ///
  /// In en, this message translates to:
  /// **'Failed to register device for push notification'**
  String get errorRegisteringDeviceForPushNotifications;

  /// No description provided for @errorSearchParamsNotSufficientToProceed.
  ///
  /// In en, this message translates to:
  /// **'Query parameters not sufficient to proceed'**
  String get errorSearchParamsNotSufficientToProceed;

  /// No description provided for @errorServer.
  ///
  /// In en, this message translates to:
  /// **'Server error'**
  String get errorServer;

  /// No description provided for @errorSomeEntriesNotAdded.
  ///
  /// In en, this message translates to:
  /// **'Some entries have not been added'**
  String get errorSomeEntriesNotAdded;

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

  /// No description provided for @labelActive.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get labelActive;

  /// No description provided for @labelAddNotes.
  ///
  /// In en, this message translates to:
  /// **'Add notes'**
  String get labelAddNotes;

  /// No description provided for @labelAddress.
  ///
  /// In en, this message translates to:
  /// **'Address'**
  String get labelAddress;

  /// No description provided for @labelAddEmailsToWhiteList.
  ///
  /// In en, this message translates to:
  /// **'Add email addressed to white list'**
  String get labelAddEmailsToWhiteList;

  /// No description provided for @labelAdvice.
  ///
  /// In en, this message translates to:
  /// **'Advice'**
  String get labelAdvice;

  /// No description provided for @labelAllMasculinePlural.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get labelAllMasculinePlural;

  /// No description provided for @labelAreYouSure.
  ///
  /// In en, this message translates to:
  /// **'Are you sure?'**
  String get labelAreYouSure;

  /// No description provided for @labelAuthorizedBy.
  ///
  /// In en, this message translates to:
  /// **'Authorized by'**
  String get labelAuthorizedBy;

  /// No description provided for @labelAuthorizer.
  ///
  /// In en, this message translates to:
  /// **'Authorizer'**
  String get labelAuthorizer;

  /// No description provided for @labelBirthdate.
  ///
  /// In en, this message translates to:
  /// **'Birthdate'**
  String get labelBirthdate;

  /// No description provided for @labelCity.
  ///
  /// In en, this message translates to:
  /// **'City'**
  String get labelCity;

  /// No description provided for @labelClickToSelectFile.
  ///
  /// In en, this message translates to:
  /// **'Click to select file'**
  String get labelClickToSelectFile;

  /// No description provided for @labelClickSearchToLoadEntries.
  ///
  /// In en, this message translates to:
  /// **'Click a search button to get entries'**
  String get labelClickSearchToLoadEntries;

  /// No description provided for @labelCompetenceTerritory.
  ///
  /// In en, this message translates to:
  /// **'Competence territory'**
  String get labelCompetenceTerritory;

  /// No description provided for @labelCompileToChangeAuthorizer.
  ///
  /// In en, this message translates to:
  /// **'Compile only if you need to change the authorizer'**
  String get labelCompileToChangeAuthorizer;

  /// No description provided for @labelCompleteProfile.
  ///
  /// In en, this message translates to:
  /// **'Complete profile'**
  String get labelCompleteProfile;

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

  /// No description provided for @labelCountry.
  ///
  /// In en, this message translates to:
  /// **'Country'**
  String get labelCountry;

  /// No description provided for @labelCurrentWhiteListEntries.
  ///
  /// In en, this message translates to:
  /// **'Current white list entries'**
  String get labelCurrentWhiteListEntries;

  /// No description provided for @labelDatetime.
  ///
  /// In en, this message translates to:
  /// **'Datetime'**
  String get labelDatetime;

  /// No description provided for @labelDatetimesAreInUTC.
  ///
  /// In en, this message translates to:
  /// **'Datetimes are in UTC format'**
  String get labelDatetimesAreInUTC;

  /// No description provided for @labelDescription.
  ///
  /// In en, this message translates to:
  /// **'Description'**
  String get labelDescription;

  /// No description provided for @labelDetails.
  ///
  /// In en, this message translates to:
  /// **'Details'**
  String get labelDetails;

  /// No description provided for @labelDismissAccountConfirmation.
  ///
  /// In en, this message translates to:
  /// **'Note: only in case you want to delete your account, type DELETE here and press ok'**
  String get labelDismissAccountConfirmation;

  /// No description provided for @labelDoNotHaveAccount.
  ///
  /// In en, this message translates to:
  /// **'Don\'t have an account? Sign Up'**
  String get labelDoNotHaveAccount;

  /// No description provided for @labelEmail.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get labelEmail;

  /// No description provided for @labelEmailSingle.
  ///
  /// In en, this message translates to:
  /// **'Single email address'**
  String get labelEmailSingle;

  /// No description provided for @labelEmailMany.
  ///
  /// In en, this message translates to:
  /// **'Many email addresses'**
  String get labelEmailMany;

  /// No description provided for @labelEmptyF.
  ///
  /// In en, this message translates to:
  /// **'Empty'**
  String get labelEmptyF;

  /// No description provided for @labelEntrySingle.
  ///
  /// In en, this message translates to:
  /// **'Single entry'**
  String get labelEntrySingle;

  /// No description provided for @labelEntriesAuthorizedByMe.
  ///
  /// In en, this message translates to:
  /// **'All entries authorized by me'**
  String get labelEntriesAuthorizedByMe;

  /// No description provided for @labelEntriesAll.
  ///
  /// In en, this message translates to:
  /// **'All entries'**
  String get labelEntriesAll;

  /// No description provided for @labelEnterVerificationMailCode.
  ///
  /// In en, this message translates to:
  /// **'Enter the verification code just sent to you by email'**
  String get labelEnterVerificationMailCode;

  /// No description provided for @labelEntriesDeleted.
  ///
  /// In en, this message translates to:
  /// **'Deleted entries'**
  String get labelEntriesDeleted;

  /// No description provided for @labelEntriesFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed entries'**
  String get labelEntriesFailed;

  /// No description provided for @labelEntriesSkipped.
  ///
  /// In en, this message translates to:
  /// **'Skipped entries'**
  String get labelEntriesSkipped;

  /// No description provided for @labelEntriesTotal.
  ///
  /// In en, this message translates to:
  /// **'Total entries'**
  String get labelEntriesTotal;

  /// No description provided for @labelEntriesAdded.
  ///
  /// In en, this message translates to:
  /// **'Added entries'**
  String get labelEntriesAdded;

  /// No description provided for @labelEntriesExisting.
  ///
  /// In en, this message translates to:
  /// **'Existing entries'**
  String get labelEntriesExisting;

  /// No description provided for @labelFileSelected.
  ///
  /// In en, this message translates to:
  /// **'File selected'**
  String get labelFileSelected;

  /// No description provided for @labelFirstname.
  ///
  /// In en, this message translates to:
  /// **'Firstname'**
  String get labelFirstname;

  /// No description provided for @labelGeneral.
  ///
  /// In en, this message translates to:
  /// **'General'**
  String get labelGeneral;

  /// No description provided for @labelGpsLocation.
  ///
  /// In en, this message translates to:
  /// **'GPS location'**
  String get labelGpsLocation;

  /// No description provided for @labelGpsLocationTest.
  ///
  /// In en, this message translates to:
  /// **'GPS location test'**
  String get labelGpsLocationTest;

  /// No description provided for @labelGpsPosition.
  ///
  /// In en, this message translates to:
  /// **'GPS position'**
  String get labelGpsPosition;

  /// No description provided for @labelGpsPositionTest.
  ///
  /// In en, this message translates to:
  /// **'GPS position test'**
  String get labelGpsPositionTest;

  /// No description provided for @labelLastRefreshAt.
  ///
  /// In en, this message translates to:
  /// **'Last refresh at'**
  String get labelLastRefreshAt;

  /// No description provided for @labelLanguage.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get labelLanguage;

  /// No description provided for @labelLatitude.
  ///
  /// In en, this message translates to:
  /// **'Latitude'**
  String get labelLatitude;

  /// No description provided for @labelLongitude.
  ///
  /// In en, this message translates to:
  /// **'Longitude'**
  String get labelLongitude;

  /// No description provided for @labelLocal.
  ///
  /// In en, this message translates to:
  /// **'Local'**
  String get labelLocal;

  /// No description provided for @labelManagedF.
  ///
  /// In en, this message translates to:
  /// **'Managed'**
  String get labelManagedF;

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

  /// No description provided for @labelNo.
  ///
  /// In en, this message translates to:
  /// **'No'**
  String get labelNo;

  /// No description provided for @labelNotes.
  ///
  /// In en, this message translates to:
  /// **'Notes'**
  String get labelNotes;

  /// No description provided for @labelOK.
  ///
  /// In en, this message translates to:
  /// **'OK'**
  String get labelOK;

  /// No description provided for @labelPasswordForgotten.
  ///
  /// In en, this message translates to:
  /// **'Forgot password?'**
  String get labelPasswordForgotten;

  /// No description provided for @labelPersonalInfo.
  ///
  /// In en, this message translates to:
  /// **'Personal Info'**
  String get labelPersonalInfo;

  /// No description provided for @labelPhoneNumber.
  ///
  /// In en, this message translates to:
  /// **'Phone'**
  String get labelPhoneNumber;

  /// No description provided for @labelPostalCode.
  ///
  /// In en, this message translates to:
  /// **'CAP/ZIP'**
  String get labelPostalCode;

  /// No description provided for @labelPressButtonToObtainPosition.
  ///
  /// In en, this message translates to:
  /// **'Press button to obtain the position'**
  String get labelPressButtonToObtainPosition;

  /// No description provided for @labelProvince.
  ///
  /// In en, this message translates to:
  /// **'Province'**
  String get labelProvince;

  /// No description provided for @labelQueryUsers.
  ///
  /// In en, this message translates to:
  /// **'Query users'**
  String get labelQueryUsers;

  /// No description provided for @labelRecents.
  ///
  /// In en, this message translates to:
  /// **'Recents'**
  String get labelRecents;

  /// No description provided for @labelRecentAlerts.
  ///
  /// In en, this message translates to:
  /// **'Recent alerts'**
  String get labelRecentAlerts;

  /// No description provided for @labelRegistration.
  ///
  /// In en, this message translates to:
  /// **'Registration'**
  String get labelRegistration;

  /// No description provided for @labelReloadPage.
  ///
  /// In en, this message translates to:
  /// **'Reload page'**
  String get labelReloadPage;

  /// No description provided for @labelReliability.
  ///
  /// In en, this message translates to:
  /// **'Reliability'**
  String get labelReliability;

  /// No description provided for @labelReliabilityScore.
  ///
  /// In en, this message translates to:
  /// **'Reliability score'**
  String get labelReliabilityScore;

  /// No description provided for @labelRole.
  ///
  /// In en, this message translates to:
  /// **'Role'**
  String get labelRole;

  /// No description provided for @labelRowsTotal.
  ///
  /// In en, this message translates to:
  /// **'Total rows'**
  String get labelRowsTotal;

  /// No description provided for @labelSearchByCSV.
  ///
  /// In en, this message translates to:
  /// **'Search by CSV'**
  String get labelSearchByCSV;

  /// No description provided for @labelSelect.
  ///
  /// In en, this message translates to:
  /// **'Select'**
  String get labelSelect;

  /// No description provided for @labelShowPassword.
  ///
  /// In en, this message translates to:
  /// **'Show password'**
  String get labelShowPassword;

  /// No description provided for @labelStatus.
  ///
  /// In en, this message translates to:
  /// **'Status'**
  String get labelStatus;

  /// No description provided for @labelStreet.
  ///
  /// In en, this message translates to:
  /// **'Street'**
  String get labelStreet;

  /// No description provided for @labelStreetAndNumber.
  ///
  /// In en, this message translates to:
  /// **'Street and civic number'**
  String get labelStreetAndNumber;

  /// No description provided for @labelSubmittingAlert.
  ///
  /// In en, this message translates to:
  /// **'Submitting alert'**
  String get labelSubmittingAlert;

  /// No description provided for @labelSurname.
  ///
  /// In en, this message translates to:
  /// **'Surname'**
  String get labelSurname;

  /// No description provided for @labelNoEntryFound.
  ///
  /// In en, this message translates to:
  /// **'No entry found'**
  String get labelNoEntryFound;

  /// No description provided for @labelTechnicalInfo.
  ///
  /// In en, this message translates to:
  /// **'Technical Info'**
  String get labelTechnicalInfo;

  /// No description provided for @labelType.
  ///
  /// In en, this message translates to:
  /// **'Type'**
  String get labelType;

  /// No description provided for @labelTypeDeleteToConfirm.
  ///
  /// In en, this message translates to:
  /// **'Type DELETE to confirm'**
  String get labelTypeDeleteToConfirm;

  /// No description provided for @labelVerificationCode.
  ///
  /// In en, this message translates to:
  /// **'Verification code'**
  String get labelVerificationCode;

  /// No description provided for @labelViewInTheMap.
  ///
  /// In en, this message translates to:
  /// **'View in the map'**
  String get labelViewInTheMap;

  /// No description provided for @labelWaitPlease.
  ///
  /// In en, this message translates to:
  /// **'Please, wait'**
  String get labelWaitPlease;

  /// No description provided for @labelWarning.
  ///
  /// In en, this message translates to:
  /// **'Warning'**
  String get labelWarning;

  /// No description provided for @labelYes.
  ///
  /// In en, this message translates to:
  /// **'Yes'**
  String get labelYes;

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

  /// No description provided for @menuRegisteredUsers.
  ///
  /// In en, this message translates to:
  /// **'Registered users'**
  String get menuRegisteredUsers;

  /// No description provided for @menuResetPrivileges.
  ///
  /// In en, this message translates to:
  /// **'Reset privileges'**
  String get menuResetPrivileges;

  /// No description provided for @menuUploadTerms.
  ///
  /// In en, this message translates to:
  /// **'Upload legal terms'**
  String get menuUploadTerms;

  /// No description provided for @menuUsers.
  ///
  /// In en, this message translates to:
  /// **'Users'**
  String get menuUsers;

  /// No description provided for @menuWhiteList.
  ///
  /// In en, this message translates to:
  /// **'Registration white list'**
  String get menuWhiteList;

  /// No description provided for @sectionUsers.
  ///
  /// In en, this message translates to:
  /// **'Users'**
  String get sectionUsers;

  /// No description provided for @successAccountDismissed.
  ///
  /// In en, this message translates to:
  /// **'Account dismissed successfully. If you change your mind and log in again within 30 days, your account will not be dismissed, and it will remain active'**
  String get successAccountDismissed;

  /// No description provided for @successAlertCreated.
  ///
  /// In en, this message translates to:
  /// **'Alert created successfully'**
  String get successAlertCreated;

  /// No description provided for @successAlertCreatedLocal.
  ///
  /// In en, this message translates to:
  /// **'Alert created successfully. Searching for nearby users and the chief'**
  String get successAlertCreatedLocal;

  /// No description provided for @successAlertCreatedManaged.
  ///
  /// In en, this message translates to:
  /// **'Managed alert created. Searching for users near the target zone'**
  String get successAlertCreatedManaged;

  /// No description provided for @successAlertCreatedEmpty.
  ///
  /// In en, this message translates to:
  /// **'Empty alert created. No need to search for any users to alert at the moment'**
  String get successAlertCreatedEmpty;

  /// No description provided for @successAlertCreatedGeneral.
  ///
  /// In en, this message translates to:
  /// **'General alert created. It\'s visible to all'**
  String get successAlertCreatedGeneral;

  /// No description provided for @successDeviceRegisteredForPushNotifications.
  ///
  /// In en, this message translates to:
  /// **'Device registered for push notification'**
  String get successDeviceRegisteredForPushNotifications;

  /// No description provided for @successEntryAdded.
  ///
  /// In en, this message translates to:
  /// **'Entry added'**
  String get successEntryAdded;

  /// No description provided for @successLogin.
  ///
  /// In en, this message translates to:
  /// **'Login successful'**
  String get successLogin;

  /// No description provided for @successLoginAdvice.
  ///
  /// In en, this message translates to:
  /// **'It is recommended to refresh at least once every 6 months to maintain the session (thus avoiding the needing of login)'**
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

  /// No description provided for @successUpload.
  ///
  /// In en, this message translates to:
  /// **'Upload done successfully'**
  String get successUpload;

  /// No description provided for @successUsersModified.
  ///
  /// In en, this message translates to:
  /// **'<count> users modified'**
  String get successUsersModified;

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
