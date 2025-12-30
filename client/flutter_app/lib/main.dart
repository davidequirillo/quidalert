// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'pages/terms.dart';
import 'pages/login.dart';
import 'pages/request.dart';
import 'pages/recents.dart';
import 'pages/settings.dart';

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

enum SubPage { login, terms, info, request, recents, settings }

class _HomePageState extends State<HomePage> {
  SubPage currentPage = SubPage.terms;
  bool termsAccepted = false;
  bool isLoggedIn = false;

  void setLoginFlag() {
    setState(() {
      isLoggedIn = true;
    });
  }

  void setLogoutFlag() {
    setState(() {
      isLoggedIn = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;

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
              ListTile(
                leading: Icon(Icons.login),
                title: Text('Login'),
                onTap: () {
                  Navigator.of(context).pop();
                  setState(() => currentPage = SubPage.login);
                },
              ),
            if (termsAccepted && isLoggedIn)
              ListTile(
                leading: Icon(Icons.logout),
                title: Text('Logout'),
                onTap: () {
                  Navigator.of(context).pop();
                  setState(() => currentPage = SubPage.login);
                },
              ),

            const Divider(),

            if (true)
              ListTile(
                leading: Icon(Icons.home),
                title: Text("Info"),
                onTap: () {
                  Navigator.of(context).pop();
                  setState(() => currentPage = SubPage.info);
                },
              ),
            if (termsAccepted && isLoggedIn)
              ListTile(
                leading: Icon(Icons.request_page),
                title: Text(loc.menuRequest),
                onTap: () {
                  Navigator.of(context).pop();
                  setState(() => currentPage = SubPage.request);
                },
              ),
            if (termsAccepted && isLoggedIn)
              ListTile(
                leading: Icon(Icons.history),
                title: Text(loc.menuRecents),
                onTap: () {
                  Navigator.of(context).pop();
                  setState(() => currentPage = SubPage.recents);
                },
              ),
            if (termsAccepted)
              ListTile(
                leading: Icon(Icons.settings),
                title: Text(loc.menuSettings),
                onTap: () {
                  Navigator.of(context).pop();
                  setState(() => currentPage = SubPage.settings);
                },
              ),
            if (true)
              ListTile(
                leading: Icon(Icons.description),
                title: Text(loc.menuTerms),
                onTap: () {
                  Navigator.of(context).pop();
                  setState(() => currentPage = SubPage.terms);
                },
              ),
          ],
        ),
      ),
      body: _buildCurrentPage(), // current page is based on the widget state
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
                debugPrint('Pressed footer: section ${index + 1}');
                if (index == 0) {
                  setState(() => currentPage = SubPage.request);
                } else {
                  setState(() => currentPage = SubPage.recents);
                }
              }, // onTap
            )
          : null, // bottomNavigationBar or null
    ); // Scaffold
  } // build method

  Widget _buildCurrentPage() {
    // 1) At app boot: current page is "terms"
    if (currentPage == SubPage.terms) {
      return TermsPage(
        isAccepted: termsAccepted,
        cbAccept: () {
          setState(() {
            termsAccepted = true;
            currentPage = SubPage.login;
          });
        },
        cbReject: () {
          setState(() {
            currentPage = SubPage.info;
          });
        },
      );
    }
    // 2) Example case: when legal terms are rejected
    if (currentPage == SubPage.info) {
      return InfoPage(
        isAccepted: termsAccepted,
        isLogged: isLoggedIn,
        cbRetryTerms: () {
          setState(() {
            currentPage = SubPage.terms;
          });
        },
        cbRetryLogin: () {
          setState(() {
            if (termsAccepted) {
              currentPage = SubPage.login;
            } else {
              currentPage = SubPage.terms;
            }
          });
        },
      );
    }
    // 3) Legal terms accepted but not logged
    if ((currentPage == SubPage.login) && termsAccepted && !isLoggedIn) {
      return LoginPage(
        cbLoginSuccess: () {
          setState(() {
            isLoggedIn = true;
            currentPage = SubPage.request;
          });
        },
      );
    }
    // 4) Legal terms accepted and logged in
    if ((currentPage == SubPage.request) && termsAccepted && isLoggedIn) {
      return RequestPage();
    }
    // 5) Menu
    if (currentPage == SubPage.recents) {
      return RecentsPage();
    }
    if (currentPage == SubPage.settings) {
      return SettingsPage();
    }
    // else: security fallback
    return const Scaffold(body: Center(child: Text("Unknown state")));
  }
} // _MainAppState class
