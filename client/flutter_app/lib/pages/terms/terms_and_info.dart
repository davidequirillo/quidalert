// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/services/shared.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/config.dart' as config;

class TermsPage extends StatelessWidget {
  const TermsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuTerms),
      drawer: const CAppDrawer(),
      body: TermsBody(),
    ); // build
  }
}

class TermsBody extends StatelessWidget {
  const TermsBody({super.key});

  Future<String> _loadFromServer(BuildContext context, {String? lang}) async {
    final loc = AppLocalizations.of(context)!;
    final url = Uri.parse('${config.apiBaseUrl}/terms');
    final http.Response response;
    try {
      response = await http.get(url, headers: {"Accept-Language": "$lang"});
    } catch (e) {
      debugPrint(
        'Error: cannot receive or read response from server, ${e.toString()}',
      );
      return loc.errorGeneric;
    }
    if (response.statusCode < 200) {
      debugPrint("HTTP ${response.statusCode}: ${response.body}");
      return loc.errorBadRequest;
    }
    if (response.statusCode >= 500) {
      debugPrint("HTTP ${response.statusCode}: ${response.body}");
      return loc.errorServer;
    }
    if (response.statusCode >= 300) {
      debugPrint("HTTP ${response.statusCode}: ${response.body}");
      return loc.errorBadRequest;
    } else {
      return response.body;
    }
  }

  @override
  Widget build(BuildContext context) {
    final shared = context.read<SharedVars>();
    bool termsAccepted = shared.termsAccepted;
    final loc = AppLocalizations.of(context)!;
    final locale = Localizations.localeOf(context);
    final languageCode = locale.languageCode;
    return FutureBuilder<String>(
      future: _loadFromServer(context, lang: languageCode),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          debugPrint("${snapshot.error}");
          return Center(child: Text(loc.errorLoading));
        }
        return Padding(
          padding: EdgeInsets.all(16.0),
          child: Column(
            children: [
              Expanded(child: Markdown(data: snapshot.data!, onTapLink: null)),
              const SizedBox(height: 10),
              if (!termsAccepted)
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton(
                      onPressed: () {
                        shared.setTermsAcceptedAndSave();
                        if (context.mounted) {
                          Navigator.pushReplacementNamed(context, '/login');
                        }
                      },
                      child: Text(loc.buttonAccept),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton(
                      onPressed: () =>
                          Navigator.pushReplacementNamed(context, '/info'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red,
                        foregroundColor: Colors.white,
                      ),
                      child: Text(loc.buttonReject),
                    ),
                  ],
                ),
            ],
          ),
        );
      },
    );
  }
}

class InfoPage extends StatelessWidget {
  const InfoPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CAppBar(title: 'Info'),
      drawer: const CAppDrawer(),
      body: InfoBody(),
    ); // build
  }
}

class InfoBody extends StatelessWidget {
  const InfoBody({super.key});

  Future<String> _fetchMarkdown({String? lang}) async {
    final String assetPath = 'assets/info_$lang.md';
    final text = await rootBundle.loadString(assetPath);
    return text;
  }

  @override
  Widget build(BuildContext context) {
    final shared = context.read<SharedVars>();
    final authClient = context.read<AuthClient>();
    bool termsAccepted = shared.termsAccepted;
    final loc = AppLocalizations.of(context)!;
    final locale = Localizations.localeOf(context);
    final languageCode = locale.languageCode;
    return FutureBuilder<String>(
      future: _fetchMarkdown(lang: languageCode),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          debugPrint("Error: ${snapshot.error}");
          return Center(child: Text(loc.errorLoading));
        }
        return SafeArea(
          top: false,
          child: Padding(
            padding: EdgeInsets.all(16.0),
            child: Column(
              children: [
                Text(
                  '${loc.labelCompetenceTerritory}: ${config.competenceTerritory}',
                ),
                Expanded(
                  child: Markdown(
                    data: snapshot.data!,
                    onTapLink: (text, href, title) {
                      switch (href) {
                        case '/terms':
                          Navigator.pushReplacementNamed(context, '/terms');
                          break;
                        case '/register':
                          if (termsAccepted && !authClient.isLoggedIn()) {
                            Navigator.pushReplacementNamed(
                              context,
                              '/register',
                            );
                          } else if (authClient.isLoggedIn() &&
                              !authClient.isAdmin()) {
                            Navigator.pushReplacementNamed(context, '/home');
                          } else if (authClient.isLoggedIn() &&
                              authClient.isAdmin()) {
                            Navigator.pushReplacementNamed(
                              context,
                              '/register',
                            );
                          } else {
                            Navigator.pushReplacementNamed(context, '/terms');
                          }
                          break;
                        case '/login':
                          if (termsAccepted && !authClient.isLoggedIn()) {
                            Navigator.pushReplacementNamed(context, '/login');
                          } else if (authClient.isLoggedIn()) {
                            Navigator.pushReplacementNamed(context, '/home');
                          } else {
                            Navigator.pushReplacementNamed(context, '/terms');
                          }
                          break;
                        default:
                          debugPrint('Unknown link: $href');
                      }
                    },
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
