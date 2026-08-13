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

  /// No description provided for @addressStreet.
  ///
  /// In en, this message translates to:
  /// **'Street'**
  String get addressStreet;

  /// No description provided for @addressStreetAndNumber.
  ///
  /// In en, this message translates to:
  /// **'Street and civic number'**
  String get addressStreetAndNumber;

  /// No description provided for @addressCity.
  ///
  /// In en, this message translates to:
  /// **'City'**
  String get addressCity;

  /// No description provided for @addressPostalCode.
  ///
  /// In en, this message translates to:
  /// **'CAP/ZIP'**
  String get addressPostalCode;

  /// No description provided for @addressProvince.
  ///
  /// In en, this message translates to:
  /// **'Province'**
  String get addressProvince;

  /// No description provided for @addressCountry.
  ///
  /// In en, this message translates to:
  /// **'Country'**
  String get addressCountry;

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

  /// No description provided for @alertManager.
  ///
  /// In en, this message translates to:
  /// **'Manager'**
  String get alertManager;

  /// No description provided for @alertDescription.
  ///
  /// In en, this message translates to:
  /// **'Description'**
  String get alertDescription;

  /// No description provided for @alertInvolvedUsers.
  ///
  /// In en, this message translates to:
  /// **'Alerted users'**
  String get alertInvolvedUsers;

  /// No description provided for @alertAlertedUsers.
  ///
  /// In en, this message translates to:
  /// **'Alerted users'**
  String get alertAlertedUsers;

  /// No description provided for @alertAlertedSpecialists.
  ///
  /// In en, this message translates to:
  /// **'Alerted specialists'**
  String get alertAlertedSpecialists;

  /// No description provided for @alertPositiveVotesNum.
  ///
  /// In en, this message translates to:
  /// **'n. confirmation votes'**
  String get alertPositiveVotesNum;

  /// No description provided for @alertNegativeVotesNum.
  ///
  /// In en, this message translates to:
  /// **'n. denial votes'**
  String get alertNegativeVotesNum;

  /// No description provided for @alertMessages.
  ///
  /// In en, this message translates to:
  /// **'Messages'**
  String get alertMessages;

  /// No description provided for @alertRadius.
  ///
  /// In en, this message translates to:
  /// **'Radius'**
  String get alertRadius;

  /// No description provided for @alertRadiusKm.
  ///
  /// In en, this message translates to:
  /// **'Radius (km)'**
  String get alertRadiusKm;

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

  /// No description provided for @alertExtend.
  ///
  /// In en, this message translates to:
  /// **'Extend alert'**
  String get alertExtend;

  /// No description provided for @alertExtendedAndVoteTerminated.
  ///
  /// In en, this message translates to:
  /// **'The alert has been extended by the chief manager, so vote is terminated'**
  String get alertExtendedAndVoteTerminated;

  /// No description provided for @alertSpreadingInfo.
  ///
  /// In en, this message translates to:
  /// **'The alert is spreading, wait please...'**
  String get alertSpreadingInfo;

  /// No description provided for @alertSpreadCountInfo.
  ///
  /// In en, this message translates to:
  /// **'Spread count: {count} of {max}'**
  String alertSpreadCountInfo(Object count, Object max);

  /// No description provided for @alertNew.
  ///
  /// In en, this message translates to:
  /// **'New alert'**
  String get alertNew;

  /// No description provided for @alertRecents.
  ///
  /// In en, this message translates to:
  /// **'Recent alerts'**
  String get alertRecents;

  /// No description provided for @alertYou.
  ///
  /// In en, this message translates to:
  /// **'You'**
  String get alertYou;

  /// No description provided for @alertedUserVote.
  ///
  /// In en, this message translates to:
  /// **'Vote'**
  String get alertedUserVote;

  /// No description provided for @alertedUserMyVote.
  ///
  /// In en, this message translates to:
  /// **'My vote'**
  String get alertedUserMyVote;

  /// No description provided for @alertedUserClosingVote.
  ///
  /// In en, this message translates to:
  /// **'Closing vote'**
  String get alertedUserClosingVote;

  /// No description provided for @alertedUserManager.
  ///
  /// In en, this message translates to:
  /// **'Chief'**
  String get alertedUserManager;

  /// No description provided for @alertedUserDistance.
  ///
  /// In en, this message translates to:
  /// **'Distance'**
  String get alertedUserDistance;

  /// No description provided for @alertedUserVotePositive.
  ///
  /// In en, this message translates to:
  /// **'Positive'**
  String get alertedUserVotePositive;

  /// No description provided for @alertedUserVoteNegative.
  ///
  /// In en, this message translates to:
  /// **'Negative'**
  String get alertedUserVoteNegative;

  /// No description provided for @alertedUserVoteNeutral.
  ///
  /// In en, this message translates to:
  /// **'Neutral'**
  String get alertedUserVoteNeutral;

  /// No description provided for @alertedUserVotePunitive.
  ///
  /// In en, this message translates to:
  /// **'Punitive'**
  String get alertedUserVotePunitive;

  /// No description provided for @alertedUserVoteNeutralInfo.
  ///
  /// In en, this message translates to:
  /// **'If you want you can still vote to confirm or deny the alert'**
  String get alertedUserVoteNeutralInfo;

  /// No description provided for @alertedUserYouHaveNotVoted.
  ///
  /// In en, this message translates to:
  /// **'You have not voted'**
  String get alertedUserYouHaveNotVoted;

  /// No description provided for @booleanTrue.
  ///
  /// In en, this message translates to:
  /// **'Yes'**
  String get booleanTrue;

  /// No description provided for @booleanFalse.
  ///
  /// In en, this message translates to:
  /// **'No'**
  String get booleanFalse;

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

  /// No description provided for @buttonExtend.
  ///
  /// In en, this message translates to:
  /// **'Extend'**
  String get buttonExtend;

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

  /// No description provided for @buttonWrite.
  ///
  /// In en, this message translates to:
  /// **'Write'**
  String get buttonWrite;

  /// No description provided for @buttonView.
  ///
  /// In en, this message translates to:
  /// **'View'**
  String get buttonView;

  /// No description provided for @buttonTest.
  ///
  /// In en, this message translates to:
  /// **'Test'**
  String get buttonTest;

  /// No description provided for @buttonVotePositive.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get buttonVotePositive;

  /// No description provided for @buttonVoteNegative.
  ///
  /// In en, this message translates to:
  /// **'Deny'**
  String get buttonVoteNegative;

  /// No description provided for @buttonVoteNeutral.
  ///
  /// In en, this message translates to:
  /// **'I don\'t know'**
  String get buttonVoteNeutral;

  /// No description provided for @buttonClosingPositive.
  ///
  /// In en, this message translates to:
  /// **'Confirm and close'**
  String get buttonClosingPositive;

  /// No description provided for @buttonClosingNegative.
  ///
  /// In en, this message translates to:
  /// **'Deny and close'**
  String get buttonClosingNegative;

  /// No description provided for @buttonClosingNeutral.
  ///
  /// In en, this message translates to:
  /// **'Normal close'**
  String get buttonClosingNeutral;

  /// No description provided for @buttonClosingPunitive.
  ///
  /// In en, this message translates to:
  /// **'Punitive close'**
  String get buttonClosingPunitive;

  /// No description provided for @entriesAll.
  ///
  /// In en, this message translates to:
  /// **'All entries'**
  String get entriesAll;

  /// No description provided for @entriesDeleted.
  ///
  /// In en, this message translates to:
  /// **'Deleted entries'**
  String get entriesDeleted;

  /// No description provided for @entriesFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed entries'**
  String get entriesFailed;

  /// No description provided for @entriesSkipped.
  ///
  /// In en, this message translates to:
  /// **'Skipped entries'**
  String get entriesSkipped;

  /// No description provided for @entriesTotal.
  ///
  /// In en, this message translates to:
  /// **'Total entries'**
  String get entriesTotal;

  /// No description provided for @entriesAdded.
  ///
  /// In en, this message translates to:
  /// **'Added entries'**
  String get entriesAdded;

  /// No description provided for @entriesExisting.
  ///
  /// In en, this message translates to:
  /// **'Existing entries'**
  String get entriesExisting;

  /// No description provided for @entriesSingle.
  ///
  /// In en, this message translates to:
  /// **'Single entry'**
  String get entriesSingle;

  /// No description provided for @entriesAuthorizedByMe.
  ///
  /// In en, this message translates to:
  /// **'All entries authorized by me'**
  String get entriesAuthorizedByMe;

  /// No description provided for @entriesNotFound.
  ///
  /// In en, this message translates to:
  /// **'Entries not found'**
  String get entriesNotFound;

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

  /// No description provided for @errorAlertIsClosed.
  ///
  /// In en, this message translates to:
  /// **'Alert is closed'**
  String get errorAlertIsClosed;

  /// No description provided for @errorAlertHasBeenExtended.
  ///
  /// In en, this message translates to:
  /// **'Alert has been extended'**
  String get errorAlertHasBeenExtended;

  /// No description provided for @errorAlertedUserNotReliable.
  ///
  /// In en, this message translates to:
  /// **'User is not reliable'**
  String get errorAlertedUserNotReliable;

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

  /// No description provided for @errorLocationAddressNotFound.
  ///
  /// In en, this message translates to:
  /// **'Address not found'**
  String get errorLocationAddressNotFound;

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
  /// **'Timeout error. Please retry'**
  String get errorLocationFetchTimeout;

  /// No description provided for @errorLocationNotAvailable.
  ///
  /// In en, this message translates to:
  /// **'Position not available'**
  String get errorLocationNotAvailable;

  /// No description provided for @errorLocationAccuracyIsLow.
  ///
  /// In en, this message translates to:
  /// **'The fetched position has a very low accuracy. Please retry'**
  String get errorLocationAccuracyIsLow;

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

  /// No description provided for @errorSessionNotValidOrExpired.
  ///
  /// In en, this message translates to:
  /// **'Session not valid or expired'**
  String get errorSessionNotValidOrExpired;

  /// No description provided for @errorUnknownState.
  ///
  /// In en, this message translates to:
  /// **'Unknown state'**
  String get errorUnknownState;

  /// No description provided for @errorUnableToOpenMap.
  ///
  /// In en, this message translates to:
  /// **'Unable to open map'**
  String get errorUnableToOpenMap;

  /// No description provided for @errorUserNotReliable.
  ///
  /// In en, this message translates to:
  /// **'User is not reliable'**
  String get errorUserNotReliable;

  /// No description provided for @errorUserBlocked.
  ///
  /// In en, this message translates to:
  /// **'Account blocked'**
  String get errorUserBlocked;

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

  /// No description provided for @gpsLocation.
  ///
  /// In en, this message translates to:
  /// **'GPS location'**
  String get gpsLocation;

  /// No description provided for @gpsLocationTest.
  ///
  /// In en, this message translates to:
  /// **'GPS location test'**
  String get gpsLocationTest;

  /// No description provided for @gpsPosition.
  ///
  /// In en, this message translates to:
  /// **'GPS position'**
  String get gpsPosition;

  /// No description provided for @gpsAccuracy.
  ///
  /// In en, this message translates to:
  /// **'Accuracy'**
  String get gpsAccuracy;

  /// No description provided for @gpsPositionAccuracy.
  ///
  /// In en, this message translates to:
  /// **'GPS position accuracy'**
  String get gpsPositionAccuracy;

  /// No description provided for @gpsPositionIsMoving.
  ///
  /// In en, this message translates to:
  /// **'Moving'**
  String get gpsPositionIsMoving;

  /// No description provided for @gpsPositionTest.
  ///
  /// In en, this message translates to:
  /// **'GPS position test'**
  String get gpsPositionTest;

  /// No description provided for @gpsLatitude.
  ///
  /// In en, this message translates to:
  /// **'Latitude'**
  String get gpsLatitude;

  /// No description provided for @gpsLongitude.
  ///
  /// In en, this message translates to:
  /// **'Longitude'**
  String get gpsLongitude;

  /// No description provided for @gpsLocationLog.
  ///
  /// In en, this message translates to:
  /// **'Background locations log'**
  String get gpsLocationLog;

  /// No description provided for @labelAllPm.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get labelAllPm;

  /// No description provided for @labelAllPf.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get labelAllPf;

  /// No description provided for @labelAllSm.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get labelAllSm;

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

  /// No description provided for @labelAreYouSure.
  ///
  /// In en, this message translates to:
  /// **'Are you sure?'**
  String get labelAreYouSure;

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

  /// No description provided for @labelEmailSingle.
  ///
  /// In en, this message translates to:
  /// **'Single email address'**
  String get labelEmailSingle;

  /// No description provided for @labelEmailsMany.
  ///
  /// In en, this message translates to:
  /// **'Many email addresses'**
  String get labelEmailsMany;

  /// No description provided for @labelEnterVerificationMailCode.
  ///
  /// In en, this message translates to:
  /// **'Enter the verification code just sent to you by email'**
  String get labelEnterVerificationMailCode;

  /// No description provided for @labelFileSelected.
  ///
  /// In en, this message translates to:
  /// **'File selected'**
  String get labelFileSelected;

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

  /// No description provided for @labelNote.
  ///
  /// In en, this message translates to:
  /// **'Note'**
  String get labelNote;

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

  /// No description provided for @labelPressButtonToObtainPosition.
  ///
  /// In en, this message translates to:
  /// **'Press button to obtain the position'**
  String get labelPressButtonToObtainPosition;

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

  /// No description provided for @labelShowAddress.
  ///
  /// In en, this message translates to:
  /// **'Show address'**
  String get labelShowAddress;

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

  /// No description provided for @labelSubmittingAlert.
  ///
  /// In en, this message translates to:
  /// **'Submitting alert'**
  String get labelSubmittingAlert;

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

  /// No description provided for @labelViewOnMap.
  ///
  /// In en, this message translates to:
  /// **'View on map'**
  String get labelViewOnMap;

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

  /// No description provided for @sectionAlertVote.
  ///
  /// In en, this message translates to:
  /// **'Vote'**
  String get sectionAlertVote;

  /// No description provided for @sectionAlertClosing.
  ///
  /// In en, this message translates to:
  /// **'Alert closing'**
  String get sectionAlertClosing;

  /// No description provided for @sectionPersonalInfo.
  ///
  /// In en, this message translates to:
  /// **'Personal Info'**
  String get sectionPersonalInfo;

  /// No description provided for @sectionRecentUserAlerts.
  ///
  /// In en, this message translates to:
  /// **'Recent user alerts'**
  String get sectionRecentUserAlerts;

  /// No description provided for @sectionTechnicalInfo.
  ///
  /// In en, this message translates to:
  /// **'Technical Info'**
  String get sectionTechnicalInfo;

  /// No description provided for @sectionUsers.
  ///
  /// In en, this message translates to:
  /// **'Users'**
  String get sectionUsers;

  /// No description provided for @sectionWhitelistAddSingleEntry.
  ///
  /// In en, this message translates to:
  /// **'Add single email address'**
  String get sectionWhitelistAddSingleEntry;

  /// No description provided for @sectionWhitelistAddManyEntries.
  ///
  /// In en, this message translates to:
  /// **'Add many email addresses'**
  String get sectionWhitelistAddManyEntries;

  /// No description provided for @sectionWhitelistAddInfoForAdmin.
  ///
  /// In en, this message translates to:
  /// **'For both entry modes, it\'s possible to select type and role'**
  String get sectionWhitelistAddInfoForAdmin;

  /// No description provided for @sectionWhitelistAddInfoForOfficer.
  ///
  /// In en, this message translates to:
  /// **'For both entry modes, it\'s possible to select the role'**
  String get sectionWhitelistAddInfoForOfficer;

  /// No description provided for @sectionLocationLog.
  ///
  /// In en, this message translates to:
  /// **'Background locations log'**
  String get sectionLocationLog;

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

  /// No description provided for @successAlertVoted.
  ///
  /// In en, this message translates to:
  /// **'Vote sent succesfully'**
  String get successAlertVoted;

  /// No description provided for @successAlertClosed.
  ///
  /// In en, this message translates to:
  /// **'Alert closed successfully'**
  String get successAlertClosed;

  /// No description provided for @successAlertExtended.
  ///
  /// In en, this message translates to:
  /// **'Alert extension request received. The alert is spreading'**
  String get successAlertExtended;

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

  /// No description provided for @userEmail.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get userEmail;

  /// No description provided for @userFirstname.
  ///
  /// In en, this message translates to:
  /// **'Firstname'**
  String get userFirstname;

  /// No description provided for @userSurname.
  ///
  /// In en, this message translates to:
  /// **'Surname'**
  String get userSurname;

  /// No description provided for @userAuthorizedBy.
  ///
  /// In en, this message translates to:
  /// **'Authorized by'**
  String get userAuthorizedBy;

  /// No description provided for @userAuthorizer.
  ///
  /// In en, this message translates to:
  /// **'Authorizer'**
  String get userAuthorizer;

  /// No description provided for @userActive.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get userActive;

  /// No description provided for @userReliability.
  ///
  /// In en, this message translates to:
  /// **'Reliability'**
  String get userReliability;

  /// No description provided for @userReliabilityScore.
  ///
  /// In en, this message translates to:
  /// **'Reliability score'**
  String get userReliabilityScore;

  /// No description provided for @userHeroScore.
  ///
  /// In en, this message translates to:
  /// **'Hero score'**
  String get userHeroScore;

  /// No description provided for @userType.
  ///
  /// In en, this message translates to:
  /// **'Type'**
  String get userType;

  /// No description provided for @userTypeChief.
  ///
  /// In en, this message translates to:
  /// **'Chief'**
  String get userTypeChief;

  /// No description provided for @userTypeOfficer.
  ///
  /// In en, this message translates to:
  /// **'Officer'**
  String get userTypeOfficer;

  /// No description provided for @userTypeAdmin.
  ///
  /// In en, this message translates to:
  /// **'Admin'**
  String get userTypeAdmin;

  /// No description provided for @userTypeBase.
  ///
  /// In en, this message translates to:
  /// **'Base'**
  String get userTypeBase;

  /// No description provided for @userRole.
  ///
  /// In en, this message translates to:
  /// **'Role'**
  String get userRole;

  /// No description provided for @userRoleFirefighter.
  ///
  /// In en, this message translates to:
  /// **'Firefighter'**
  String get userRoleFirefighter;

  /// No description provided for @userRoleWateroperator.
  ///
  /// In en, this message translates to:
  /// **'Wateroperator'**
  String get userRoleWateroperator;

  /// No description provided for @userRoleUsar.
  ///
  /// In en, this message translates to:
  /// **'Usar'**
  String get userRoleUsar;

  /// No description provided for @userRoleAlpinerescuer.
  ///
  /// In en, this message translates to:
  /// **'Alpinerescuer'**
  String get userRoleAlpinerescuer;

  /// No description provided for @userRoleMedic.
  ///
  /// In en, this message translates to:
  /// **'Medic'**
  String get userRoleMedic;

  /// No description provided for @userRoleMilitary.
  ///
  /// In en, this message translates to:
  /// **'Military'**
  String get userRoleMilitary;

  /// No description provided for @userRolePoliceman.
  ///
  /// In en, this message translates to:
  /// **'Policeman'**
  String get userRolePoliceman;

  /// No description provided for @userRoleVolunteer.
  ///
  /// In en, this message translates to:
  /// **'Volunteer'**
  String get userRoleVolunteer;

  /// No description provided for @userRoleCitizen.
  ///
  /// In en, this message translates to:
  /// **'Citizen'**
  String get userRoleCitizen;

  /// No description provided for @userStatus.
  ///
  /// In en, this message translates to:
  /// **'Status'**
  String get userStatus;

  /// No description provided for @userStatusOk.
  ///
  /// In en, this message translates to:
  /// **'Ok'**
  String get userStatusOk;

  /// No description provided for @userStatusUnreliable.
  ///
  /// In en, this message translates to:
  /// **'Unreliable'**
  String get userStatusUnreliable;

  /// No description provided for @userStatusBlocked.
  ///
  /// In en, this message translates to:
  /// **'Blocked'**
  String get userStatusBlocked;

  /// No description provided for @userLastRefreshAt.
  ///
  /// In en, this message translates to:
  /// **'Last refresh at'**
  String get userLastRefreshAt;

  /// No description provided for @userBirthdate.
  ///
  /// In en, this message translates to:
  /// **'Birthdate'**
  String get userBirthdate;

  /// No description provided for @userPhoneNumber.
  ///
  /// In en, this message translates to:
  /// **'Phone'**
  String get userPhoneNumber;

  /// No description provided for @userLanguage.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get userLanguage;

  /// No description provided for @userCompleteProfile.
  ///
  /// In en, this message translates to:
  /// **'Complete profile'**
  String get userCompleteProfile;

  /// No description provided for @whitelistEntryAuthorizedBy.
  ///
  /// In en, this message translates to:
  /// **'Authorized by'**
  String get whitelistEntryAuthorizedBy;

  /// No description provided for @whitelistEntryPendingType.
  ///
  /// In en, this message translates to:
  /// **'Pending type'**
  String get whitelistEntryPendingType;

  /// No description provided for @whitelistEntryPendingRole.
  ///
  /// In en, this message translates to:
  /// **'Pending role'**
  String get whitelistEntryPendingRole;

  /// No description provided for @whitelistEntryUserIsRegistered.
  ///
  /// In en, this message translates to:
  /// **'User is registered'**
  String get whitelistEntryUserIsRegistered;
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
