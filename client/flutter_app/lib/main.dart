// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'config.dart' as config;
import 'services/shared.dart';
import 'services/auth.dart';
import 'pages/startup.dart';
import 'pages/terms/terms_info.dart';
import 'pages/register.dart';
import 'pages/reset.dart';
import 'pages/login.dart';
import 'pages/two_fa.dart';
import 'pages/home.dart';
import 'pages/new_alert.dart';
import 'pages/recents.dart';
import 'pages/settings.dart';
import 'pages/accounts.dart';
import 'pages/whitelist/add_entries.dart';
import 'pages/whitelist/search_entries.dart';
import 'pages/whitelist/delete_entries.dart';
import 'pages/terms/upload_terms.dart';
import 'pages/users/search_module.dart';
import 'pages/users/search_by_csv.dart';
import 'pages/users/search_results.dart';
import 'pages/users/promote_results.dart';
import 'pages/users/view.dart';
import 'pages/advice.dart';
import 'pages/profile/complete.dart';

void main() {
  debugPrint('Hello from main()');
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<SharedVars>(create: (_) => SharedVars()),
        ChangeNotifierProvider<AuthClient>(create: (_) => AuthClient()),
      ],
      child: const QuidalertWidget(),
    ),
  );
}

class QuidalertWidget extends StatelessWidget {
  const QuidalertWidget({super.key});

  Locale? _resolveLocale(Locale? locale, Iterable<Locale> supportedLocales) {
    final lang = locale?.languageCode.toLowerCase();
    if (lang == 'it') {
      return const Locale('it');
    }
    return const Locale('en');
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
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
      initialRoute: "/",
      routes: {
        '/': (_) => const StartupPage(),
        '/terms': (_) => const TermsPage(),
        '/info': (_) => const InfoPage(),
        '/register': (_) => const RegisterPage(),
        '/reset': (_) => const ResetPage(),
        '/login': (_) => const LoginPage(),
        '/2fa': (_) => const TwoFAPage(),
        '/home': (_) => const HomePage(),
        '/alerts/new': (_) => const NewAlertPage(),
        '/alerts/recents': (_) => const RecentsPage(),
        '/advice': (_) => const AdvicePage(),
        '/profile/complete': (_) => const CompleteProfilePage(),
        '/accounts': (_) => const AccountsPage(),
        '/accounts/whitelist/add-entries': (_) => const WhiteListAddPage(),
        '/accounts/whitelist/search-entries': (_) =>
            const WhiteListSearchPage(),
        '/accounts/whitelist/delete-entries': (_) =>
            const WhiteListDeletePage(),
        '/accounts/upload-terms': (_) => const UploadTermsPage(),
        '/accounts/users/search-module': (_) => const UsersSearchModulePage(),
        '/accounts/users/search-by-csv': (_) => const UsersSearchByCSVPage(),
        '/accounts/users/search-results': (_) => const UsersSearchResultsPage(),
        '/accounts/users/view-user': (_) => const UserPage(),
        '/accounts/users/promote-results': (_) =>
            const UsersPromoteResultsPage(),
        '/settings': (_) => const SettingsPage(),
      },
    );
  }
}
