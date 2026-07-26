// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/utils/validators.dart';
import 'package:quidalert_flutter/utils/strings.dart';

class TwoFAPage extends StatelessWidget {
  const TwoFAPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CAppBar(title: "2FA"),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: TwoFABody()),
    );
  }
}

class TwoFABody extends StatefulWidget {
  const TwoFABody({super.key});

  @override
  State<TwoFABody> createState() => _TwoFABodyState();
}

class _TwoFABodyState extends State<TwoFABody> {
  final _formKey = GlobalKey<FormState>();
  final _codeController = TextEditingController();

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> submit(String email, String password) async {
    if (!_formKey.currentState!.validate()) return;
    final code = _codeController.text.trim();
    await _complete2FA(email, password, code);
  }

  Future<void> _complete2FA(String email, String password, String code) async {
    final loc = AppLocalizations.of(context)!;
    final locale = Localizations.localeOf(context);
    final languageCode = locale.languageCode.toLowerCase();
    final authClient = context.read<AuthClient>();
    String? error;
    String endMessage;
    String endTitle;
    final http.Response response;
    try {
      debugPrintC(
        "Submitting 2FA code... (email: $email, password: ${'*' * password.length}, login_code: $code, language: $languageCode)",
      );
      response = await authClient.login(
        email,
        password,
        loginCode: code,
        language: languageCode,
      );
      if (response.statusCode < 200 || response.statusCode >= 300) {
        debugPrintC(
          '2FA failed, response status: ${response.statusCode}, response body: ${response.body}',
        );
        if (response.statusCode == 401) {
          final jsonResp = jsonDecode(response.body);
          error = jsonResp['detail'] ?? 'Not authorized';
        } else if (response.statusCode == 403) {
          error = 'Forbidden request';
        } else if (response.statusCode >= 500) {
          error = 'Server error';
        } else if (response.statusCode >= 300) {
          error = 'Bad request';
        } else {
          error = 'Unknown error';
        }
      } else {
        error = null;
      }
    } catch (e) {
      debugPrintC(
        '2FA error: cannot receive or read response: ${e.toString()}',
      );
      error = "Unknown error";
    }
    if (error != null) {
      switch (error) {
        case 'Unknown error':
          endMessage = loc.errorGeneric;
          break;
        case 'Bad request':
          endMessage = loc.errorBadRequest;
          break;
        case 'Server error':
          endMessage = loc.errorServer;
          break;
        case '2FA code not valid':
          endMessage = loc.errorCodeNotValid;
          break;
        case '2FA locked':
          endMessage = loc.errorLoginLocked;
          break;
        case 'Forbidden request':
          endMessage = loc.errorUserBlocked;
          break;
        default:
          endMessage = loc.errorBadRequest;
      }
      endTitle = loc.errorError;
    } else {
      endTitle = loc.successLogin;
      endMessage = loc.successLogin;
    }
    if (!mounted) return;
    await showGotoIfAlertDialog(
      context,
      endTitle,
      endMessage,
      (error == null),
      "/home",
    );
  }

  @override
  Widget build(BuildContext context) {
    final args =
        ModalRoute.of(context)!.settings.arguments as Map<String, String>;
    final email = args['email']!;
    final password = args['password']!;
    final loc = AppLocalizations.of(context)!;
    return Form(
      key: _formKey,
      autovalidateMode: AutovalidateMode.onUserInteraction,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              loc.labelEnterVerificationMailCode,
              style: TextStyle(fontSize: 18),
            ),
            SizedBox(height: 15),
            TextFormField(
              keyboardType: TextInputType.number,
              controller: _codeController,
              decoration: InputDecoration(
                labelText: loc.labelVerificationCode,
                border: OutlineInputBorder(),
              ),
              maxLength: 6,
              validator: (value) {
                return validateDigitCode(context, value, min: 6);
              },
            ),
            SizedBox(height: 5),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                ElevatedButton(
                  onPressed: () {
                    submit(email, password);
                  },
                  child: Text("OK"),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: () =>
                      Navigator.pushReplacementNamed(context, '/login'),
                  child: Text(loc.buttonCancel),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
