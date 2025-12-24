// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'pages/terms.dart';

void main() {
  debugPrint('Hello from main()'); // a debug log
  runApp(const QuidalertWidget());
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
      debugShowCheckedModeBanner: false,
      localizationsDelegates: [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: [Locale('en'), Locale('it')],
      localeResolutionCallback: _resolveLocale,
      home: HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool termsAccepted = false;
  bool isLoggedIn = false;

  void onLoginSuccess() {
    setState(() {
      isLoggedIn = true;
    });
  }

  void onTermsAccepted() {
    setState(() {
      termsAccepted = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    final locale = Localizations.localeOf(context);
    final languageCode = locale.languageCode;

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,
        title: const Text('Quidalert'),
      ),
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: BoxDecoration(color: Colors.blue),
              child: Text(
                'Menu',
                style: TextStyle(color: Colors.white, fontSize: 24),
              ),
            ),
            if (termsAccepted && (!isLoggedIn))
              ListTile(leading: Icon(Icons.login), title: Text('Login')),
            if (termsAccepted && isLoggedIn)
              ListTile(leading: Icon(Icons.logout), title: Text('Logout')),

            const Divider(),

            if (termsAccepted && isLoggedIn)
              ListTile(leading: Icon(Icons.home), title: Text(loc.menuRequest)),
            if (termsAccepted && isLoggedIn)
              ListTile(leading: Icon(Icons.home), title: Text(loc.menuRecents)),
            if (termsAccepted && isLoggedIn)
              ListTile(
                leading: Icon(Icons.settings),
                title: Text(loc.menuSettings),
              ),
            ListTile(
              leading: Icon(Icons.description),
              title: Text(loc.menuTerms),
            ),
          ],
        ),
      ),
      body: TermsPage(), // Body shows only TermsPage at the moment
      bottomNavigationBar: termsAccepted && isLoggedIn
          ? BottomNavigationBar(
              items: [
                BottomNavigationBarItem(
                  icon: Icon(Icons.plus_one),
                  label: loc.menuRequest,
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.history),
                  label: loc.menuRecents,
                ),
              ],
              onTap: (index) {
                debugPrint('Pressed footer: Section ${index + 1}');
              }, // onTap
            )
          : null, // bottomNavigationBar or null
    ); // Scaffold
  } // build method
} // _MainAppState class
