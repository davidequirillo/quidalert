import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:dynalert_flutter/l10n/app_localizations.dart';

void main() {
  print('Hello from main()'); // a debug log
  runApp(const MainApp());
}

class MainApp extends StatefulWidget {
  const MainApp({super.key});

  @override
  State<MainApp> createState() => _MainAppState();
}

class _MainAppState extends State<MainApp> {
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
    return MaterialApp(
      // Scaffold Widget
      debugShowCheckedModeBanner: false,
      // Localizations
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [Locale('en'), Locale('it')],

      // ✅ fallback (custom, optional): if it doesn't IT or EN, then default: en
      localeResolutionCallback: (locale, supportedLocales) {
        final lang = locale?.languageCode.toLowerCase();
        if (lang == 'it') return const Locale('it');
        return const Locale('en'); // default
      },

      home: Scaffold(
        appBar: AppBar(
          backgroundColor: Colors.blue,
          foregroundColor: Colors.white,
          title: const Text('Dynalert'),
        ),
        drawer: Builder(
          builder: (context) {
            final t = AppLocalizations.of(context)!;
            return Drawer(
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
                    ListTile(leading: Icon(Icons.home), title: Text('Home')),
                  if (termsAccepted && isLoggedIn)
                    ListTile(
                      leading: Icon(Icons.settings),
                      title: Text(t.menuSettings),
                    ),
                  if (termsAccepted && isLoggedIn)
                    ListTile(
                      leading: Icon(Icons.logout),
                      title: Text('Logout'),
                    ),
                  ListTile(
                    leading: Icon(Icons.description),
                    title: Text(t.menuTerms),
                  ),
                ],
              ),
            );
          },
        ),
        body: Builder(
          builder: (context) {
            final t = AppLocalizations.of(context)!;
            return const Center(child: Text('Hello World'));
          },
        ),
      ),
    );
  } // build method
} // _MainAppState class
