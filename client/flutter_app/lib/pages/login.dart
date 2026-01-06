// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
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
  String? loginError;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _doLogin() async {
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    debugPrint(loc.menuProfile);
    debugPrint(authClient.isLoggedIn().toString());
    // we will set loginError string, based on api error code
    // (using if or switch statements)
    if (loginError != null) {
      if (!mounted) return;
      // change state with setState
      //
    } else {
      Navigator.pushReplacementNamed(context, '/request');
    }
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
                    _doLogin();
                  },
                  child: Text('Login', style: TextStyle(fontSize: 16)),
                ),
              ),
              if (loginError != null)
                Text(loginError!, style: const TextStyle(color: Colors.red)),
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
