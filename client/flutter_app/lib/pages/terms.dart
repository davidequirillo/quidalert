// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/config.dart' as config;
import 'package:http/http.dart' as http;
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';

class TermsPage extends StatelessWidget {
  final bool isAccepted;
  final VoidCallback cbAccept; // Accept Callback
  final VoidCallback cbReject; // Reject Callback

  const TermsPage({
    super.key,
    required this.isAccepted,
    required this.cbAccept,
    required this.cbReject,
  });

  Future<String> _loadFromServer({String? lang}) async {
    final url = Uri.parse('${config.apiBaseUrl}/terms');
    final http.Response response;
    try {
      response = await http.get(url, headers: {"Accept-Language": "$lang"});
    } catch (e) {
      debugPrint('Error: cannot receive or read response');
      return 'Network error';
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      debugPrint("HTTP ${response.statusCode}: ${response.body}");
      return 'Network error';
    } else {
      return response.body;
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    final locale = Localizations.localeOf(context);
    final languageCode = locale.languageCode;
    return FutureBuilder<String>(
      future: _loadFromServer(lang: languageCode),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          debugPrint("Error: ${snapshot.error}");
          return Center(child: Text(loc.textLoadingError));
        }
        return Padding(
          padding: EdgeInsets.all(16.0),
          child: Column(
            children: [
              Expanded(child: Markdown(data: snapshot.data!)),
              const SizedBox(height: 10),
              if (!isAccepted)
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton(
                      onPressed: cbAccept,
                      child: Text(loc.buttonAccept),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton(
                      onPressed: cbReject,
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
  } // build
}

class InfoPage extends StatelessWidget {
  final bool isAccepted;
  final bool isLogged;
  final VoidCallback cbRetryTerms; // retry terms callback
  final VoidCallback cbRetryLogin; // retry login callback

  const InfoPage({
    super.key,
    required this.isAccepted,
    required this.isLogged,
    required this.cbRetryTerms,
    required this.cbRetryLogin,
  });

  Future<String> _fetchMarkdown({String? lang}) async {
    final String assetPath = 'info_$lang.md';
    final text = await rootBundle.loadString(assetPath);
    return text;
  }

  @override
  Widget build(BuildContext context) {
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
          return Center(child: Text(loc.textLoadingError));
        }
        return Padding(
          padding: EdgeInsets.all(16.0),
          child: Column(
            children: [
              Expanded(
                child: Markdown(
                  data: snapshot.data!,
                  onTapLink: (text, href, title) {
                    switch (href) {
                      case '/terms':
                        cbRetryTerms();
                        break;
                      case '/login':
                        cbRetryLogin();
                        break;
                    }
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
