// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2025-2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/utils/strings.dart';

class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CAppBar(title: 'Login'),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: LoginBody()),
    );
  }
}

class LoginBody extends StatefulWidget {
  const LoginBody({super.key});

  @override
  State<LoginBody> createState() => _LoginBodyState();
}

class _LoginBodyState extends State<LoginBody> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool showPasswordFlag = false;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    final email = _usernameController.text.trim();
    final password = _passwordController.text;
    await _doLogin(email, password, code: null);
  }

  Future<void> _doLogin(String email, String password, {String? code}) async {
    final loc = AppLocalizations.of(context)!;
    final locale = Localizations.localeOf(context);
    final languageCode = locale.languageCode.toLowerCase();
    final authClient = context.read<AuthClient>();
    String? loginError;
    String endMessage;
    String endTitle;
    final http.Response response;
    try {
      debugPrintC("Attempting login for $email");
      response = await authClient.login(
        email,
        password,
        loginCode: code,
        language: languageCode,
      );
      debugPrintC("Login response: ${response.statusCode} ${response.body}");
      if (response.statusCode < 200 || response.statusCode >= 300) {
        if (response.statusCode == 422) {
          loginError = 'Invalid credentials';
        } else if (response.statusCode == 401) {
          final jsonResp = jsonDecode(response.body);
          loginError = jsonResp['detail'] ?? 'Not authorized';
        } else if (response.statusCode >= 500) {
          loginError = 'Server error';
        } else if (response.statusCode >= 300) {
          loginError = 'Bad request';
        } else {
          loginError = 'Unknown error';
        }
      } else {
        loginError = null;
      }
    } on http.ClientException catch (_) {
      debugPrintC('HTTP Client Exception occurred during login');
      loginError = "Connection failed";
    } catch (e) {
      debugPrintC('Error: cannot receive or read response: ${e.toString()}');
      loginError = "Unknown error";
    }
    if (loginError != null) {
      switch (loginError) {
        case '2FA required':
          endMessage = "2FA is required";
          if (!mounted) return;
          await Navigator.pushReplacementNamed(
            context,
            '/2fa',
            arguments: {'email': email, 'password': password},
          );
          return;
        case '2FA locked':
          endMessage = loc.errorLoginLocked;
          break;
        case 'Invalid credentials':
          endMessage = loc.errorInvalidCredentials;
          break;
        case 'Server error':
          endMessage = loc.errorServer;
          break;
        case 'Bad request':
          endMessage = loc.errorBadRequest;
          break;
        case 'Connection failed':
          endMessage = loc.errorConnectionFailed;
          break;
        case 'Unknown error':
          endMessage = loc.errorGeneric;
          break;
        default:
          endMessage = loc.errorGeneric;
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
      (loginError == null),
      "/home",
    );
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          TextField(
            keyboardType: TextInputType.emailAddress,
            controller: _usernameController,
            decoration: InputDecoration(
              labelText: 'Email',
              border: OutlineInputBorder(),
            ),
          ),
          SizedBox(height: 20),
          TextField(
            keyboardType: TextInputType.visiblePassword,
            controller: _passwordController,
            decoration: InputDecoration(
              labelText: 'Password',
              border: OutlineInputBorder(),
            ),
            obscureText: !showPasswordFlag,
          ),
          SizedBox(height: 5),
          Row(
            children: [
              Checkbox(
                tristate: false,
                value: showPasswordFlag,
                onChanged: (value) {
                  setState(() {
                    showPasswordFlag = value!;
                  });
                },
              ),
              Text(loc.labelShowPassword),
            ],
          ),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton(
              onPressed: () {
                submit();
              },
              child: Text('Login', style: TextStyle(fontSize: 16)),
            ),
          ),
          SizedBox(height: 20),
          InkWell(
            onTap: () {
              Navigator.pushReplacementNamed(context, '/reset');
            },
            child: Text(
              loc.labelPasswordForgotten,
              style: TextStyle(
                decoration: TextDecoration.underline,
                color: Colors.blue,
              ),
            ),
          ),
          SizedBox(height: 5),
          InkWell(
            onTap: () {
              Navigator.pushReplacementNamed(context, '/register');
            },
            child: Text(
              loc.labelDoNotHaveAccount,
              style: TextStyle(
                decoration: TextDecoration.underline,
                color: Colors.blue,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
