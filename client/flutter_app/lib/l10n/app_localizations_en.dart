// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get addressStreet => 'Street';

  @override
  String get addressStreetAndNumber => 'Street and civic number';

  @override
  String get addressCity => 'City';

  @override
  String get addressPostalCode => 'CAP/ZIP';

  @override
  String get addressProvince => 'Province';

  @override
  String get addressCountry => 'Country';

  @override
  String get alertSender => 'Sender';

  @override
  String get alertChief => 'Chief';

  @override
  String get alertManager => 'Manager';

  @override
  String get alertDescription => 'Description';

  @override
  String get alertInvolvedUsers => 'Alerted users';

  @override
  String get alertAlertedUsers => 'Alerted users';

  @override
  String get alertAlertedSpecialists => 'Alerted specialists';

  @override
  String get alertPositiveVotesNum => 'n. confirmation votes';

  @override
  String get alertNegativeVotesNum => 'n. denial votes';

  @override
  String get alertMessages => 'Messages';

  @override
  String get alertMessagesWriteNew => 'Write a new message...';

  @override
  String get alertMessagesEmpty => 'There are no messages at the moment';

  @override
  String get alertRadius => 'Radius';

  @override
  String get alertRadiusKm => 'Radius (km)';

  @override
  String get alertStatusOpen => 'Open';

  @override
  String get alertStatusClosed => 'Closed';

  @override
  String get alertStatusPending => 'Pending';

  @override
  String get alertTypeGeneral => 'General';

  @override
  String get alertTypeLocal => 'Local';

  @override
  String get alertTypeEmpty => 'Empty';

  @override
  String get alertTypeManaged => 'Managed';

  @override
  String get alertExtend => 'Extend alert';

  @override
  String get alertExtendedAndVoteTerminated => 'The alert has been extended by the chief manager, so vote is terminated';

  @override
  String get alertSpreadingInfo => 'The alert is spreading, wait please...';

  @override
  String alertSpreadCountInfo(Object count, Object max) {
    return 'Spread count: $count of $max';
  }

  @override
  String get alertNew => 'New alert';

  @override
  String get alertRecents => 'Recent alerts';

  @override
  String get alertYou => 'You';

  @override
  String get alertedUserVote => 'Vote';

  @override
  String get alertedUserMyVote => 'My vote';

  @override
  String get alertedUserClosingVote => 'Closing vote';

  @override
  String get alertedUserManager => 'Chief';

  @override
  String get alertedUserDistance => 'Distance';

  @override
  String get alertedUserVotePositive => 'Positive';

  @override
  String get alertedUserVoteNegative => 'Negative';

  @override
  String get alertedUserVoteNeutral => 'Neutral';

  @override
  String get alertedUserVotePunitive => 'Punitive';

  @override
  String get alertedUserVoteNeutralInfo => 'If you want you can still vote to confirm or deny the alert';

  @override
  String get alertedUserYouHaveNotVoted => 'You have not voted';

  @override
  String get booleanTrue => 'Yes';

  @override
  String get booleanFalse => 'No';

  @override
  String get buttonAccept => 'Accept';

  @override
  String get buttonAdd => 'Add';

  @override
  String get buttonBack => 'Back';

  @override
  String get buttonCancel => 'Cancel';

  @override
  String get buttonChat => 'Chat';

  @override
  String get buttonClear => 'Clear';

  @override
  String get buttonCopy => 'Copy';

  @override
  String get buttonDelete => 'Delete';

  @override
  String get buttonExtend => 'Extend';

  @override
  String get buttonModify => 'Modify';

  @override
  String get buttonObtain => 'Obtain';

  @override
  String get buttonPromote => 'Promote';

  @override
  String get buttonReject => 'Reject';

  @override
  String get buttonSearch => 'Search';

  @override
  String get buttonWrite => 'Write';

  @override
  String get buttonView => 'View';

  @override
  String get buttonTest => 'Test';

  @override
  String get buttonVotePositive => 'Confirm';

  @override
  String get buttonVoteNegative => 'Deny';

  @override
  String get buttonVoteNeutral => 'I don\'t know';

  @override
  String get buttonClosingPositive => 'Confirm and close';

  @override
  String get buttonClosingNegative => 'Deny and close';

  @override
  String get buttonClosingNeutral => 'Normal close';

  @override
  String get buttonClosingPunitive => 'Punitive close';

  @override
  String get buttonGoToAppSettings => 'Go to app settings';

  @override
  String get entriesAll => 'All entries';

  @override
  String get entriesDeleted => 'Deleted entries';

  @override
  String get entriesFailed => 'Failed entries';

  @override
  String get entriesSkipped => 'Skipped entries';

  @override
  String get entriesTotal => 'Total entries';

  @override
  String get entriesAdded => 'Added entries';

  @override
  String get entriesExisting => 'Existing entries';

  @override
  String get entriesSingle => 'Single entry';

  @override
  String get entriesAuthorizedByMe => 'All entries authorized by me';

  @override
  String get entriesNotFound => 'Entries not found';

  @override
  String get errorAlertSimilarInZone => 'A similar alert already exists in this zone';

  @override
  String get errorAlertSimilarInGeneral => 'A similar general alert already exists';

  @override
  String get errorAlertIsClosed => 'Alert is closed';

  @override
  String get errorAlertHasBeenExtended => 'Alert has been extended';

  @override
  String get errorAlertedUserNotReliable => 'User is not reliable';

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
  String get errorEmailNotValid => 'Email not valid';

  @override
  String get errorEmailAlreadyExist => 'Email already exists';

  @override
  String get errorEmailAlreadyRegistered => 'Email already registered';

  @override
  String get errorError => 'Error';

  @override
  String get errorGeneric => 'Generic error';

  @override
  String get errorInvalidCredentials => 'Email or password not valid';

  @override
  String get errorLoading => 'Loading error';

  @override
  String get errorLocationAddressNotFound => 'Address not found';

  @override
  String get errorLocationServicesDisabled => 'Location services are disabled, go to settings and enable gps and location services';

  @override
  String get errorLocationPermissionDenied => 'Location permissions are denied, go to settings to enable them';

  @override
  String get errorLocationPermissionDeniedForever => 'You have permanently denied location permissions, go to settings and enable them';

  @override
  String get errorLocationFetchTimeout => 'Timeout error. Please retry';

  @override
  String get errorLocationNotAvailable => 'Position not available';

  @override
  String get errorLocationAccuracyIsLow => 'The fetched position has a very low accuracy. Please retry';

  @override
  String get errorLoginLocked => 'Too many attempts, login is locked for 24 hours';

  @override
  String get errorNoEntryToAdd => 'No entry to add';

  @override
  String get errorNoEntryFound => 'No entry found';

  @override
  String get errorNoFileSelected => 'No file selected';

  @override
  String get errorNotAuthorized => 'Not authorized';

  @override
  String get errorNotAuthorizedDoLogin => 'Not authorized, retry login';

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
  String get errorRegisteringDeviceForPushNotifications => 'Failed to register device for push notification';

  @override
  String get errorSearchParamsNotSufficientToProceed => 'Query parameters not sufficient to proceed';

  @override
  String get errorServer => 'Server error';

  @override
  String get errorConnectionFailed => 'Connection failed';

  @override
  String get errorSomeEntriesNotAdded => 'Some entries have not been added';

  @override
  String get errorStringNotValid => 'String not valid';

  @override
  String get errorStringTooLong => 'String too long';

  @override
  String get errorStringTooShort => 'String too short';

  @override
  String get errorSessionNotValidOrExpired => 'Session not valid or expired';

  @override
  String get errorUserNotReliable => 'User is not reliable';

  @override
  String get errorUserBlocked => 'Account blocked';

  @override
  String get errorUserNotFound => 'User not found';

  @override
  String get errorUnknownState => 'Unknown state';

  @override
  String get errorUnableToOpenMap => 'Unable to open map';

  @override
  String get errorWhitelistCannotDelForRegUsers => 'Cannot delete entries for already registered users';

  @override
  String get exceptionBadRequest => 'Bad request';

  @override
  String get exceptionForbiddenRequest => 'Permissions not valid';

  @override
  String get exceptionGenericNotAuthorized => 'Not authorized, retry login';

  @override
  String get exceptionNetwork => 'Network error';

  @override
  String get exceptionServer => 'Server error';

  @override
  String get exceptionConnectionFailed => 'Connection failed';

  @override
  String get exceptionNotFound => 'Resource not found';

  @override
  String get exceptionFromJsonObj => 'Json object reading error';

  @override
  String get exceptionUnknown => 'Unknown error';

  @override
  String get gpsLocation => 'GPS location';

  @override
  String get gpsLocationTest => 'GPS location test';

  @override
  String get gpsPosition => 'GPS position';

  @override
  String get gpsPositionForegroundInfo => 'Detecting your position… Wait on this screen… Indoors, the waiting time can be up to 60 seconds…';

  @override
  String get gpsAccuracy => 'Accuracy';

  @override
  String get gpsPositionAccuracy => 'GPS position accuracy';

  @override
  String get gpsPositionIsMoving => 'Moving';

  @override
  String get gpsPositionTest => 'GPS position test';

  @override
  String get gpsLatitude => 'Latitude';

  @override
  String get gpsLongitude => 'Longitude';

  @override
  String get gpsLocationLog => 'Background locations log';

  @override
  String get gpsPermissionsRequiredTitle => 'Required permissions';

  @override
  String get gpsPermissionsRequiredMessage => 'These permissions will be required: precise GPS position, \'allow all the time\', allow motion tracking, battery \'without restrictions\'';

  @override
  String get gpsBatteryWithoutRestrictionsTitle => 'Disable battery limits';

  @override
  String get gpsBatteryWithoutRestrictionsMessage => 'To prevent the background GPS position tracking from sleeping, you need to go to the \'battery\' section of this app settings, and select \'without restrictions\'. Press \'ok\' to open the app settings panel... You will find \'battery\' section (in some device it\'s on the right), then select \'without restrictions\'...';

  @override
  String get labelAllPm => 'All';

  @override
  String get labelAllPf => 'All';

  @override
  String get labelAllSm => 'All';

  @override
  String get labelAddNotes => 'Add notes';

  @override
  String get labelAddress => 'Address';

  @override
  String get labelAddEmailsToWhitelist => 'Add email addressed to white list';

  @override
  String get labelAdvice => 'Advice';

  @override
  String get labelAreYouSure => 'Are you sure?';

  @override
  String get labelClickToSelectFile => 'Click to select file';

  @override
  String get labelClickSearchToLoadEntries => 'Click a search button to get entries';

  @override
  String get labelCompetenceTerritory => 'Competence territory';

  @override
  String get labelCompileToChangeAuthorizer => 'Compile only if you need to change the authorizer';

  @override
  String get labelConfirmPassword => 'Confirm password';

  @override
  String get labelConfirmNewPassword => 'Confirm new password';

  @override
  String get labelCurrentWhitelistEntries => 'Current white list entries';

  @override
  String get labelDatetime => 'Datetime';

  @override
  String get labelDatetimesAreInUTC => 'Datetimes are in UTC format';

  @override
  String get labelDetails => 'Details';

  @override
  String get labelDismissAccountConfirmation => 'Note: only in case you want to delete your account, type DELETE here and press ok';

  @override
  String get labelDoNotHaveAccount => 'Don\'t have an account? Sign Up';

  @override
  String get labelEmailSingle => 'Single email address';

  @override
  String get labelEmailsMany => 'Many email addresses';

  @override
  String get labelEnterVerificationMailCode => 'Enter the verification code just sent to you by email';

  @override
  String get labelFileSelected => 'File selected';

  @override
  String get labelNewPassword => 'New password';

  @override
  String get labelNo => 'No';

  @override
  String get labelNotes => 'Notes';

  @override
  String get labelNote => 'Note';

  @override
  String get labelOK => 'OK';

  @override
  String get labelPasswordForgotten => 'Forgot password?';

  @override
  String get labelPressButtonToObtainPosition => 'Press button to obtain the position';

  @override
  String get labelQueryUsers => 'Query users';

  @override
  String get labelRecents => 'Recents';

  @override
  String get labelRegistration => 'Registration';

  @override
  String get labelReloadPage => 'Reload page';

  @override
  String get labelRowsTotal => 'Total rows';

  @override
  String get labelSearchByCSV => 'Search by CSV';

  @override
  String get labelSelect => 'Select';

  @override
  String get labelShowAddress => 'Show address';

  @override
  String get labelShowPassword => 'Show password';

  @override
  String get labelStatus => 'Status';

  @override
  String get labelSubmittingAlert => 'Submitting alert';

  @override
  String get labelType => 'Type';

  @override
  String get labelTypeDeleteToConfirm => 'Type DELETE to confirm';

  @override
  String get labelVerificationCode => 'Verification code';

  @override
  String get labelViewOnMap => 'View on map';

  @override
  String get labelWaitPlease => 'Please, wait';

  @override
  String get labelWarning => 'Warning';

  @override
  String get labelYes => 'Yes';

  @override
  String get labelShortID => 'Short ID';

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
  String get menuWhitelist => 'Registration white list';

  @override
  String get notificationSwipeDownToHide => '⬇ to hide';

  @override
  String get sectionAlertInfo => 'Alert Info';

  @override
  String get sectionAlertVote => 'Vote';

  @override
  String get sectionAlertClosing => 'Alert closing';

  @override
  String get sectionPersonalInfo => 'Personal Info';

  @override
  String get sectionRecentUserAlerts => 'Recent user alerts';

  @override
  String get sectionTechnicalInfo => 'Technical Info';

  @override
  String get sectionUsers => 'Users';

  @override
  String get sectionWhitelistAddSingleEntry => 'Add single email address';

  @override
  String get sectionWhitelistAddManyEntries => 'Add many email addresses';

  @override
  String get sectionWhitelistAddInfoForAdmin => 'For both entry modes, it\'s possible to select type and role';

  @override
  String get sectionWhitelistAddInfoForOfficer => 'For both entry modes, it\'s possible to select the role';

  @override
  String get sectionWhitelistDeleteSingleEntry => 'Delete single entry';

  @override
  String get sectionWhitelistDeleteAllOwnedEntry => 'Delete all entries owned by you';

  @override
  String get sectionWhitelistDeleteInfo => 'Only email addresses not associated with already registered users will be deleted.';

  @override
  String get sectionLocationLog => 'Background locations log';

  @override
  String get successAccountDismissed => 'Account dismissed successfully. If you change your mind and log in again within 30 days, your account will not be dismissed, and it will remain active';

  @override
  String get successAlertCreated => 'Alert created successfully';

  @override
  String get successAlertCreatedLocal => 'Alert created successfully. Searching for nearby users and the chief';

  @override
  String get successAlertCreatedManaged => 'Managed alert created. Searching for users near the target zone';

  @override
  String get successAlertCreatedEmpty => 'Empty alert created. No need to search for any users to alert at the moment';

  @override
  String get successAlertCreatedGeneral => 'General alert created. It\'s visible to all';

  @override
  String get successAlertVoted => 'Vote sent succesfully';

  @override
  String get successAlertClosed => 'Alert closed successfully';

  @override
  String get successAlertExtended => 'Alert extension request received. The alert is spreading';

  @override
  String get successDeviceRegisteredForPushNotifications => 'Device registered for push notification';

  @override
  String get successEntryAdded => 'Entry added';

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
  String get successUsersModified => '<count> users modified';

  @override
  String get successGeneric => 'Operation done';

  @override
  String get userEmail => 'Email';

  @override
  String get userFirstname => 'Firstname';

  @override
  String get userSurname => 'Surname';

  @override
  String get userAuthorizedBy => 'Authorized by';

  @override
  String get userAuthorizer => 'Authorizer';

  @override
  String get userActive => 'Active';

  @override
  String get userReliability => 'Reliability';

  @override
  String get userReliabilityScore => 'Reliability score';

  @override
  String get userHeroScore => 'Hero score';

  @override
  String get userType => 'Type';

  @override
  String get userTypeChief => 'Chief';

  @override
  String get userTypeOfficer => 'Officer';

  @override
  String get userTypeAdmin => 'Admin';

  @override
  String get userTypeBase => 'Base';

  @override
  String get userRole => 'Role';

  @override
  String get userRoleFirefighter => 'Firefighter';

  @override
  String get userRoleWateroperator => 'Wateroperator';

  @override
  String get userRoleUsar => 'Usar';

  @override
  String get userRoleAlpinerescuer => 'Alpinerescuer';

  @override
  String get userRoleMedic => 'Medic';

  @override
  String get userRoleMilitary => 'Military';

  @override
  String get userRolePoliceman => 'Policeman';

  @override
  String get userRoleVolunteer => 'Volunteer';

  @override
  String get userRoleCitizen => 'Citizen';

  @override
  String get userStatus => 'Status';

  @override
  String get userStatusOk => 'Ok';

  @override
  String get userStatusUnreliable => 'Unreliable';

  @override
  String get userStatusBlocked => 'Blocked';

  @override
  String get userLastRefreshAt => 'Last refresh at';

  @override
  String get userBirthdate => 'Birthdate';

  @override
  String get userPhoneNumber => 'Phone';

  @override
  String get userLanguage => 'Language';

  @override
  String get userCompleteProfile => 'Complete profile';

  @override
  String get whitelistEntryAuthorizedBy => 'Authorized by';

  @override
  String get whitelistEntryPendingType => 'Pending type';

  @override
  String get whitelistEntryPendingRole => 'Pending role';

  @override
  String get whitelistEntryUserIsRegistered => 'User is registered';
}
