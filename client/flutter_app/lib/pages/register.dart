// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/common.dart';
import 'package:quidalert_flutter/utils/validator.dart';
import 'package:quidalert_flutter/config.dart' as config;

class RegisterPage extends StatelessWidget {
  const RegisterPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.labelRegistration),
      drawer: const CAppDrawer(),
      body: RegisterBody(),
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
    super.dispose();
  }

  void submit() {
    final locale = Localizations.localeOf(context);
    final languageCode = locale.languageCode;
    if (!_formKey.currentState!.validate()) return;
    final fname = _firstnameController.text.trim();
    final sname = _surnameController.text.trim();
    final email = _emailController.text.trim();
    final password = _passwordController.text;
    final fields = {
      "firstname": fname,
      "surname": sname,
      "email": email,
      "password": password,
      "language": languageCode,
    };
    _doRegistration(fields);
  }

  void _doRegistration(Map<String, dynamic> data) async {
    final loc = AppLocalizations.of(context)!;
    final jsonBody = jsonEncode(data);
    String? registerError;
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
      if (response.statusCode < 200 || response.statusCode >= 300) {
        debugPrint("HTTP ${response.statusCode}: ${response.body}");
        registerError = jsonDecode(response.body)['detail'];
      } else {
        registerError = null;
      }
    } catch (e) {
      debugPrint('Error: cannot receive or read response');
      registerError = "Network error";
    }
    if (registerError != null) {
      switch (registerError) {
        case 'Email already registered':
          endMessage = loc.errorEmailAlreadyRegistered;
        case 'Network error':
          endMessage = loc.errorNetwork;
        default:
          endMessage = loc.errorBadRequest;
      }
      endTitle = loc.errorGeneric;
      endMessage = registerError;
    } else {
      endTitle = loc.successGeneric;
      endMessage = loc.successRegistration;
    }
    if (!mounted) return;
    await showDialog(
      context: context,
      builder: (_) => GotoIfAlertDialog(
        title: endTitle,
        content: endMessage,
        condition: (registerError == null),
        route: "/login",
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
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
                  TextFormField(
                    controller: _firstnameController,
                    decoration: InputDecoration(
                      labelText: loc.labelFirstname,
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
                      labelText: loc.labelSurname,
                      border: OutlineInputBorder(),
                    ),
                    maxLength: 64,
                    validator: (value) {
                      return validateName(context, value);
                    },
                  ),
                  SizedBox(height: 5),
                  TextFormField(
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
                    controller: _rePasswordController,
                    decoration: InputDecoration(
                      labelText: 'Confirm password',
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) {
                      if (value != _passwordController.text) {
                        return loc.errorPasswordsDoNotMatch;
                      }
                      return validateName(context, value);
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
      ),
    );
  }
}
