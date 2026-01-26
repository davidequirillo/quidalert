// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/common.dart';
import 'package:quidalert_flutter/utils/validator.dart';

class TwoFAPage extends StatelessWidget {
  const TwoFAPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CAppBar(title: "2FA"),
      drawer: const CAppDrawer(),
      body: TwoFABody(),
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
    final authClient = context.read<AuthClient>();
    String? error;
    String endMessage;
    String endTitle;
    final http.Response response;
    try {
      response = await authClient.login(email, password, code: code);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        error = jsonDecode(response.body)['detail'];
      } else {
        error = null;
      }
    } catch (e) {
      debugPrint('Error: cannot receive or read response');
      error = "Network error";
    }
    if (error != null) {
      switch (error) {
        case 'Network error':
          endMessage = loc.errorNetwork;
          break;
        case '2FA code not valid':
          endMessage = loc.errorCodeNotValid;
          break;
        case '2FA locked':
          endMessage = loc.errorLoginLocked;
          break;
        default:
          endMessage = loc.errorBadRequest;
      }
      endTitle = loc.errorGeneric;
    } else {
      endTitle = loc.successLogin;
      endMessage = '${loc.successLogin}. ${loc.successLoginAdvice}';
    }
    if (!mounted) return;
    await showDialog(
      context: context,
      builder: (_) => GotoIfAlertDialog(
        title: endTitle,
        content: endMessage,
        condition: (error == null),
        route: "/home",
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final args =
        ModalRoute.of(context)!.settings.arguments as Map<String, String>;
    final email = args['email']!;
    final password = args['password']!;
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.all(16),
          child: Form(
            key: _formKey,
            autovalidateMode: AutovalidateMode.onUserInteraction,
            child: Padding(
              padding: const EdgeInsets.all(5.0),
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
          ),
        ),
      ),
    );
  }
}
