// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';
import 'package:flutter_background_geolocation/flutter_background_geolocation.dart'
    as bg;
import 'package:quidalert_flutter/services/background_location.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/services/headless_task.dart';
import 'package:quidalert_flutter/firebase_options.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/config.dart' as config;
import 'package:quidalert_flutter/services/shared.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/services/location.dart';
import 'package:quidalert_flutter/services/notification.dart';
import 'package:quidalert_flutter/widgets/app_keys.dart';
import 'package:quidalert_flutter/pages/startup.dart';
import 'package:quidalert_flutter/pages/terms/terms_and_info.dart';
import 'package:quidalert_flutter/pages/register.dart';
import 'package:quidalert_flutter/pages/reset.dart';
import 'package:quidalert_flutter/pages/login.dart';
import 'package:quidalert_flutter/pages/two_fa.dart';
import 'package:quidalert_flutter/pages/home.dart';
import 'package:quidalert_flutter/pages/alerts/location_test.dart';
import 'package:quidalert_flutter/pages/alerts/new.dart';
import 'package:quidalert_flutter/pages/alerts/extend.dart';
import 'package:quidalert_flutter/pages/alerts/recents.dart';
import 'package:quidalert_flutter/pages/alerts/view_alert_details.dart';
import 'package:quidalert_flutter/pages/alerts/view_alert_users.dart';
import 'package:quidalert_flutter/pages/alerts/view_alert_messages.dart';
import 'package:quidalert_flutter/pages/accounts.dart';
import 'package:quidalert_flutter/pages/whitelist/add_entries.dart';
import 'package:quidalert_flutter/pages/whitelist/search_entries.dart';
import 'package:quidalert_flutter/pages/whitelist/delete_entries.dart';
import 'package:quidalert_flutter/pages/terms/upload_terms.dart';
import 'package:quidalert_flutter/pages/users/search_module.dart';
import 'package:quidalert_flutter/pages/users/search_by_csv.dart';
import 'package:quidalert_flutter/pages/users/search_results.dart';
import 'package:quidalert_flutter/pages/users/promote_results.dart';
import 'package:quidalert_flutter/pages/users/view_details.dart';
import 'package:quidalert_flutter/pages/advice.dart';
import 'package:quidalert_flutter/pages/profile/complete.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  debugPrintC("Registering headless task for background location...");
  await bg.BackgroundGeolocation.registerHeadlessTask(
    backgroundLocationHeadlessTask,
  );
  await BackgroundLocationService.init();
  try {
    if (Firebase.apps.isEmpty) {
      await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform,
      );
    }
  } catch (e) {
    debugPrint("Firebase not configured. Push notifications disabled.");
  }
  debugPrint('Hello from main()');
  runApp(const QuidalertWidget());
  return;
}

class QuidalertWidget extends StatelessWidget {
  const QuidalertWidget({super.key});

  Locale? _resolveLocale(Locale? locale, Iterable<Locale> supportedLocales) {
    final String? lang = locale?.languageCode.toLowerCase();
    debugPrintC("System language is: $lang");
    if (lang == 'it') {
      return const Locale('it');
    }
    return const Locale('it');
  }

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<SharedVars>(create: (context) => SharedVars()),
        ChangeNotifierProvider<AuthClient>(create: (context) => AuthClient()),
        ChangeNotifierProvider<LocationClient>(
          create: (context) => LocationClient(),
        ),
        ChangeNotifierProvider<NotificationProvider>(
          create: (context) => NotificationProvider(),
        ),
      ],
      child: MaterialApp(
        navigatorKey: AppKeys.navigatorKey,
        scaffoldMessengerKey: AppKeys.snackbarKey,
        title: config.appName,
        debugShowCheckedModeBanner: false,
        localizationsDelegates: [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: [Locale('en'), Locale('it')],
        localeResolutionCallback: _resolveLocale,
        initialRoute: '/',
        onGenerateRoute: (settings) {
          debugPrint("Navigating to: ${settings.name}");
          switch (settings.name) {
            case '/':
              return MaterialPageRoute(
                builder: (_) => const StartupPage(),
                settings: settings,
              );
            case '/info':
              return MaterialPageRoute(
                builder: (_) => const InfoPage(),
                settings: settings,
              );
            case '/login':
              return MaterialPageRoute(
                builder: (_) => const LoginPage(),
                settings: settings,
              );
            case '/home':
              return MaterialPageRoute(
                builder: (_) => const HomePage(),
                settings: settings,
              );
            case '/terms':
              return MaterialPageRoute(
                builder: (_) => const TermsPage(),
                settings: settings,
              );
            case '/register':
              return MaterialPageRoute(
                builder: (_) => const RegisterPage(),
                settings: settings,
              );
            case '/reset':
              return MaterialPageRoute(
                builder: (_) => const ResetPage(),
                settings: settings,
              );
            case '/2fa':
              return MaterialPageRoute(
                builder: (_) => const TwoFAPage(),
                settings: settings,
              );
            case '/alerts/new':
              return MaterialPageRoute(
                builder: (_) => const NewAlertPage(),
                settings: settings,
              );
            case '/alerts/extend':
              return MaterialPageRoute(
                builder: (_) => const ExtendAlertPage(),
                settings: settings,
              );
            case '/alerts/recents':
              return MaterialPageRoute(
                builder: (_) => const RecentAlertsPage(),
                settings: settings,
              );
            case '/alerts/view-alert-details':
              return MaterialPageRoute(
                builder: (_) => const AlertDetailsPage(),
                settings: settings,
              );
            case '/alerts/view-alert-users':
              return MaterialPageRoute(
                builder: (_) => const AlertUsersPage(),
                settings: settings,
              );
            case '/alerts/view-alert-messages':
              return MaterialPageRoute(
                builder: (_) => const AlertMessagesPage(),
                settings: settings,
              );
            case '/alerts/location-test':
              return MaterialPageRoute(
                builder: (_) => const LocationTestPage(),
                settings: settings,
              );
            case '/advice':
              return MaterialPageRoute(
                builder: (_) => const AdvicePage(),
                settings: settings,
              );
            case '/profile/complete':
              return MaterialPageRoute(
                builder: (_) => const CompleteProfilePage(),
                settings: settings,
              );
            case '/accounts':
              return MaterialPageRoute(
                builder: (_) => const AccountsPage(),
                settings: settings,
              );
            case '/accounts/whitelist/add-entries':
              return MaterialPageRoute(
                builder: (_) => const WhiteListAddPage(),
                settings: settings,
              );
            case '/accounts/whitelist/search-entries':
              return MaterialPageRoute(
                builder: (_) => const WhiteListSearchPage(),
                settings: settings,
              );
            case '/accounts/whitelist/delete-entries':
              return MaterialPageRoute(
                builder: (_) => const WhiteListDeletePage(),
                settings: settings,
              );
            case '/accounts/upload-terms':
              return MaterialPageRoute(
                builder: (_) => const UploadTermsPage(),
                settings: settings,
              );
            case '/accounts/users/search-module':
              return MaterialPageRoute(
                builder: (_) => const UsersSearchModulePage(),
                settings: settings,
              );
            case '/accounts/users/search-by-csv':
              return MaterialPageRoute(
                builder: (_) => const UsersSearchByCSVPage(),
                settings: settings,
              );
            case '/accounts/users/search-results':
              return MaterialPageRoute(
                builder: (_) => const UsersSearchResultsPage(),
                settings: settings,
              );
            case '/accounts/users/view-user-details':
              return MaterialPageRoute(
                builder: (_) => const UserDetailsPage(),
                settings: settings,
              );
            case '/accounts/users/promote-results':
              return MaterialPageRoute(
                builder: (_) => const UsersPromoteResultsPage(),
                settings: settings,
              );
            default:
              debugPrint(
                "Unknown route: ${settings.name}, redirecting to startup page",
              );
              return MaterialPageRoute(
                builder: (_) => const StartupPage(),
                settings: settings,
              );
          }
        },
      ),
    );
  }
}
