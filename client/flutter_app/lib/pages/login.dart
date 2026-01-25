// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/widgets/common.dart';

class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CAppBar(title: 'Login'),
      drawer: const CAppDrawer(),
      body: LoginBody(),
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
    final code = null;
    await _doLogin(email, password, code: code);
  }

  Future<void> _doLogin(String email, String password, {String? code}) async {
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    String? loginError;
    String endMessage;
    String endTitle;
    final http.Response response;
    try {
      response = await authClient.login(email, password, code: code);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        if (response.statusCode == 422) {
          loginError = 'Invalid credentials';
        } else if ((response.statusCode == 401) &&
            (response.body.contains('2FA required'))) {
          loginError = '2FA required'; // Handled separately
        } else if (response.statusCode == 401) {
          loginError = 'Invalid credentials';
        } else {
          loginError = 'Unknown error';
        }
      } else {
        loginError = null;
      }
    } catch (e) {
      debugPrint('Error: cannot receive or read response');
      loginError = "Network error";
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
        case 'Invalid credentials':
          endMessage = loc.errorInvalidCredentials;
          break;
        case 'Network error':
          endMessage = loc.errorNetwork;
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
        condition: (loginError == null),
        route: "/home",
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              TextField(
                controller: _usernameController,
                decoration: InputDecoration(
                  labelText: 'Email',
                  border: OutlineInputBorder(),
                ),
              ),
              SizedBox(height: 20),
              TextField(
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
                height: 30,
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
        ),
      ),
    );
  }
}
