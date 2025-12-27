// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/config.dart' as config;
import 'package:http/http.dart' as http;
import 'dart:convert';

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
    final uri = Uri.parse('${config.apiBaseUrl}/terms');
    final http.Response response;
    try {
      response = await http.get(
        uri,
        headers: {"Accept": "application/json", "Accept-Language": "$lang"},
      );
    } catch (e) {
      debugPrint('Request error: cannot receive or read response');
      return 'Network error';
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      debugPrint('HTTP ${response.statusCode}: ${response.body}');
      return 'Network error';
    } else {
      final decoded = jsonDecode(response.body);
      final message = (decoded as Map<String, dynamic>)['message'];
      if (message is! String) {
        throw Exception(
          'JSON not valid: message not present or is not a string',
        );
      }
      return message;
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
          return Center(child: Text(loc.textLoadingErr));
        }
        return Padding(
          padding: EdgeInsets.all(16.0),
          child: Column(
            children: [
              Expanded(
                child: Scrollbar(
                  thumbVisibility: true,
                  child: SingleChildScrollView(
                    child: Text(snapshot.data!, style: TextStyle(fontSize: 18)),
                  ),
                ),
              ),
              const SizedBox(height: 10),
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
  final VoidCallback cbRetryTerms; // retry terms callback
  final VoidCallback cbRetryLogin; // retry login callback

  const InfoPage({
    super.key,
    required this.isAccepted,
    required this.cbRetryTerms,
    required this.cbRetryLogin,
  });

  @override
  Widget build(BuildContext context) {
    return Text("Hello World!");
  }
}
