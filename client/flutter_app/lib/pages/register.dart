// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
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
import 'package:quidalert_flutter/utils/validators.dart';
import 'package:quidalert_flutter/config.dart' as config;

class RegisterPage extends StatelessWidget {
  const RegisterPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.labelRegistration),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: RegisterBody()),
    );
  }
}

class RegisterBody extends StatefulWidget {
  const RegisterBody({super.key});

  @override
  State<RegisterBody> createState() => _RegisterBodyState();
}

class _RegisterBodyState extends State<RegisterBody> {
  final _formKey = GlobalKey<FormState>();
  final ScrollController _scrollController = ScrollController();
  final _firstnameController = TextEditingController();
  final _surnameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _rePasswordController = TextEditingController();
  bool showPasswordFlag = false;

  @override
  void dispose() {
    _firstnameController.dispose();
    _surnameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _rePasswordController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    final locale = Localizations.localeOf(context);
    final languageCode = locale.languageCode.toLowerCase();
    if (!_formKey.currentState!.validate()) return;
    final fname = _firstnameController.text.trim();
    final sname = _surnameController.text.trim();
    final email = _emailController.text.trim().toLowerCase();
    final password = _passwordController.text;
    final fields = {
      "firstname": fname,
      "surname": sname,
      "email": email,
      "password": password,
      "language": languageCode,
    };
    await _doRegistration(fields);
  }

  Future<void> _doRegistration(Map<String, String> data) async {
    final loc = AppLocalizations.of(context)!;
    final jsonBody = jsonEncode(data);
    final isLoggedIn = context.read<AuthClient>().isLoggedIn();
    bool isSuccess = false;
    String endMessage;
    String endTitle;
    final http.Response response;
    try {
      final url = Uri.parse('${config.apiBaseUrl}/register');
      response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: jsonBody,
      );
      if (response.statusCode < 200) {
        endTitle = loc.errorError;
        endMessage = loc.errorBadRequest;
      } else if (response.statusCode >= 500) {
        endTitle = loc.errorError;
        endMessage = loc.errorServer;
      } else if (response.statusCode >= 300) {
        endTitle = loc.errorError;
        endMessage = loc.errorBadRequest;
      } else {
        isSuccess = true;
        endTitle = loc.successGeneric;
        endMessage = loc.successRegistration;
      }
    } catch (e) {
      debugPrint('Error: cannot receive or read response: ${e.toString()}');
      endTitle = loc.errorError;
      endMessage = loc.errorGeneric;
    }
    if (!mounted) return;
    await showGotoIfAlertDialog(
      context,
      endTitle,
      endMessage,
      isSuccess,
      (isLoggedIn) ? "/home" : "/login",
    );
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scrollbar(
      controller: _scrollController,
      thumbVisibility: true,
      child: SingleChildScrollView(
        controller: _scrollController,
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
                TextFormField(
                  controller: _firstnameController,
                  decoration: InputDecoration(
                    labelText: loc.userFirstname,
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 64,
                  validator: (value) {
                    return validateName(context, value);
                  },
                ),
                SizedBox(height: 5),
                TextFormField(
                  controller: _surnameController,
                  decoration: InputDecoration(
                    labelText: loc.userSurname,
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 64,
                  validator: (value) {
                    return validateName(context, value);
                  },
                ),
                SizedBox(height: 5),
                TextFormField(
                  keyboardType: TextInputType.emailAddress,
                  controller: _emailController,
                  decoration: InputDecoration(
                    labelText: 'Email',
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 128,
                  validator: (value) {
                    return validateEmail(context, value);
                  },
                ),
                SizedBox(height: 5),
                TextFormField(
                  keyboardType: TextInputType.visiblePassword,
                  controller: _passwordController,
                  decoration: InputDecoration(
                    labelText: 'Password',
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 256,
                  validator: (value) {
                    return validatePassword(context, value);
                  },
                  obscureText: !showPasswordFlag,
                ),
                SizedBox(height: 5),
                TextFormField(
                  keyboardType: TextInputType.visiblePassword,
                  controller: _rePasswordController,
                  decoration: InputDecoration(
                    labelText: loc.labelConfirmPassword,
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) {
                    if (value != _passwordController.text) {
                      return loc.errorPasswordsDoNotMatch;
                    }
                    return validatePassword(context, value);
                  },
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
                SizedBox(height: 5),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton(
                      onPressed: () {
                        submit();
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
    );
  }
}
