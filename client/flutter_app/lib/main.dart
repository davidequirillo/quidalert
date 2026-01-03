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
import 'pages/terms.dart';
import 'pages/register.dart';
import 'pages/reset.dart';
import 'pages/login.dart';
import 'pages/request.dart';
import 'pages/recents.dart';
import 'pages/settings.dart';

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
        '/request': (_) => const RequestPage(),
        '/recents': (_) => const RecentsPage(),
        '/settings': (_) => const SettingsPage(),
      },
    );
  }
}
