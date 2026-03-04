// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/firebase_options.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/config.dart' as config;
import 'package:quidalert_flutter/services/shared.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/services/location.dart';
import 'package:quidalert_flutter/services/notification.dart';
import 'package:quidalert_flutter/pages/startup.dart';
import 'package:quidalert_flutter/pages/terms/terms_info.dart';
import 'package:quidalert_flutter/pages/register.dart';
import 'package:quidalert_flutter/pages/reset.dart';
import 'package:quidalert_flutter/pages/login.dart';
import 'package:quidalert_flutter/pages/two_fa.dart';
import 'package:quidalert_flutter/pages/home.dart';
import 'package:quidalert_flutter/pages/alerts/location_test.dart';
import 'package:quidalert_flutter/pages/alerts/new.dart';
import 'package:quidalert_flutter/pages/alerts/recents.dart';
import 'package:quidalert_flutter/pages/settings.dart';
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
    if (lang == 'it') {
      return const Locale('it');
    }
    return const Locale('en');
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
              return MaterialPageRoute(builder: (_) => const StartupPage());
            case '/info':
              return MaterialPageRoute(builder: (_) => const InfoPage());
            case '/login':
              return MaterialPageRoute(builder: (_) => const LoginPage());
            case '/home':
              return MaterialPageRoute(builder: (_) => const HomePage());
            case '/terms':
              return MaterialPageRoute(builder: (_) => const TermsPage());
            case '/register':
              return MaterialPageRoute(builder: (_) => const RegisterPage());
            case '/reset':
              return MaterialPageRoute(builder: (_) => const ResetPage());
            case '/2fa':
              return MaterialPageRoute(builder: (_) => const TwoFAPage());
            case '/alerts/new':
              return MaterialPageRoute(builder: (_) => const NewAlertPage());
            case '/alerts/recents':
              return MaterialPageRoute(
                builder: (_) => const RecentAlertsPage(),
              );
            case '/alerts/location-test':
              return MaterialPageRoute(
                builder: (_) => const LocationTestPage(),
              );
            case '/advice':
              return MaterialPageRoute(builder: (_) => const AdvicePage());
            case '/profile/complete':
              return MaterialPageRoute(
                builder: (_) => const CompleteProfilePage(),
              );
            case '/accounts':
              return MaterialPageRoute(builder: (_) => const AccountsPage());
            case '/accounts/whitelist/add-entries':
              return MaterialPageRoute(
                builder: (_) => const WhiteListAddPage(),
              );
            case '/accounts/whitelist/search-entries':
              return MaterialPageRoute(
                builder: (_) => const WhiteListSearchPage(),
              );
            case '/accounts/whitelist/delete-entries':
              return MaterialPageRoute(
                builder: (_) => const WhiteListDeletePage(),
              );
            case '/accounts/upload-terms':
              return MaterialPageRoute(builder: (_) => const UploadTermsPage());
            case '/accounts/users/search-module':
              return MaterialPageRoute(
                builder: (_) => const UsersSearchModulePage(),
              );
            case '/accounts/users/search-by-csv':
              return MaterialPageRoute(
                builder: (_) => const UsersSearchByCSVPage(),
              );
            case '/accounts/users/search-results':
              return MaterialPageRoute(
                builder: (_) => const UsersSearchResultsPage(),
              );
            case '/accounts/users/view-user-details':
              return MaterialPageRoute(builder: (_) => const UserDetailsPage());
            case '/accounts/users/promote-results':
              return MaterialPageRoute(
                builder: (_) => const UsersPromoteResultsPage(),
              );
            case '/settings':
              return MaterialPageRoute(builder: (_) => const SettingsPage());
            default:
              debugPrint(
                "Unknown route: ${settings.name}, redirecting to startup page",
              );
              return MaterialPageRoute(builder: (_) => const StartupPage());
          }
        },
      ),
    );
  }
}
