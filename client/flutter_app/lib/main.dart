// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter/foundation.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:jose/jose.dart';
import 'pages/terms.dart';
import 'pages/login.dart';
import 'pages/request.dart';
import 'pages/recents.dart';
import 'pages/settings.dart';

void main() {
  debugPrint('Hello from main()');
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
  bool isLoadingPrefs = true;
  String? refreshToken;
  String? accessToken;
  final _secureStorage = FlutterSecureStorage();

  @override
  void initState() {
    super.initState();
    refreshToken = null;
    accessToken = null;
    _init();
  }

  Future<void> _init() async {
    await loadPrefs();
    await loadRefreshToken();
    await getAccessToken();
  }

  Future<void> loadPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    termsAccepted = prefs.getBool('termsAccepted') ?? false;
    setState(() {
      isLoadingPrefs = false;
    });
  }

  Future<void> saveRefreshToken(String? token) async {
    if (refreshToken != null) {
      await _secureStorage.write(key: 'refreshToken', value: token);
      if (kDebugMode) {
        debugPrint('RefreshToken saved');
      }
    }
  }

  Future<void> loadRefreshToken() async {
    final token = await _secureStorage.read(key: 'refreshToken');
    if (kDebugMode) {
      debugPrint('RefreshToken: $refreshToken');
    }
    setState(() => refreshToken = token);
  }

  Future<void> deleteRefreshToken() async {
    await _secureStorage.delete(key: 'refreshToken');
    if (kDebugMode) {
      debugPrint('RefreshToken deleted');
    }
  }

  bool _isTokenExpired(String token) {
    final jwt = JsonWebToken.unverified(token);
    final exp = jwt.claims.getTyped('exp');
    if (exp == null) return true;
    final expiry = DateTime.fromMillisecondsSinceEpoch(exp * 1000, isUtc: true);
    return DateTime.now().toUtc().isAfter(expiry);
  }

  bool isLoggedIn() {
    if (refreshToken == null) {
      return false;
    } else if (_isTokenExpired(refreshToken!)) {
      return false;
    } else {
      return true;
    }
  }

  Future<void> getAccessToken() async {
    // Call an API to the server, using refresh token as input
    // Note: it gets a new refresh token too
    final aToken = null; // from api result
    final rToken = null; // from api result
    await saveRefreshToken(rToken);
    setState(() {
      accessToken = aToken;
      refreshToken = rToken;
    });
    if (kDebugMode) {
      debugPrint('Access token refreshed');
    }
  }

  Future<void> saveTermsAccepted() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('termsAccepted', true);
    setState(() {
      termsAccepted = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    final loggedIn = isLoggedIn();
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
            if (termsAccepted && (!loggedIn))
              ListTile(
                leading: Icon(Icons.login),
                title: Text('Login'),
                onTap: () {
                  Navigator.of(context).pop();
                  setState(() => currentPage = SubPage.login);
                },
              ),
            if (termsAccepted && loggedIn)
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
            if (termsAccepted && loggedIn)
              ListTile(
                leading: Icon(Icons.request_page),
                title: Text(loc.menuRequest),
                onTap: () {
                  Navigator.of(context).pop();
                  setState(() => currentPage = SubPage.request);
                },
              ),
            if (termsAccepted && loggedIn)
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
      body: isLoadingPrefs
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : _buildCurrentPage(), // current page is based on the widget state
      bottomNavigationBar: termsAccepted && loggedIn
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
    final loggedIn = isLoggedIn();
    // 1) At app boot: current page is "terms"
    if (currentPage == SubPage.terms) {
      return TermsPage(
        isAccepted: termsAccepted,
        cbAccept: () => saveTermsAccepted(),
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
        isLogged: loggedIn,
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
    if ((currentPage == SubPage.login) && termsAccepted && !loggedIn) {
      return LoginPage(
        cbLoginSuccess: () {
          currentPage = SubPage.request;
        },
      );
    }
    // 4) Legal terms accepted and logged in
    if ((currentPage == SubPage.request) && termsAccepted && loggedIn) {
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
