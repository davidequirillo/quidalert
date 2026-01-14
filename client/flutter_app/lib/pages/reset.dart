// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/common.dart';
import 'package:quidalert_flutter/utils/validator.dart';
import 'package:quidalert_flutter/config.dart' as config;

class ResetPage extends StatelessWidget {
  const ResetPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CAppBar(title: "Password reset"),
      drawer: const CAppDrawer(),
      body: ResetBody(),
    );
  }
}

class ResetBody extends StatefulWidget {
  const ResetBody({super.key});

  @override
  State<ResetBody> createState() => _ResetBodyState();
}

class _ResetBodyState extends State<ResetBody> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _codeController = TextEditingController();
  final _passwordController = TextEditingController();
  final _rePasswordController = TextEditingController();
  bool showPasswordFlag = false;
  bool resetRequestIsSent = false;

  @override
  void dispose() {
    _emailController.dispose();
    _codeController.dispose();
    _passwordController.dispose();
    _rePasswordController.dispose();
    super.dispose();
  }

  void submit() {
    if (!_formKey.currentState!.validate()) return;
    final email = _emailController.text.trim();
    String code = "";
    String newPassword = "";
    if (!resetRequestIsSent) {
      final fields = {"email": email};
      _doPasswordResetRequest(fields);
    } else {
      code = _codeController.text.trim();
      newPassword = _passwordController.text;
      final fields = {
        "email": email,
        "code": code,
        "new_password": newPassword,
      };
      _doPasswordResetConfirmation(fields);
    }
  }

  void _doPasswordResetRequest(Map<String, dynamic> data) async {
    final loc = AppLocalizations.of(context)!;
    final jsonBody = jsonEncode(data);
    String? requestError;
    String endMessage;
    String endTitle;
    final http.Response response;
    try {
      final url = Uri.parse('${config.apiBaseUrl}/password-reset/request');
      response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: jsonBody,
      );
      if (response.statusCode < 200 || response.statusCode >= 300) {
        debugPrint("HTTP ${response.statusCode}: ${response.body}");
        requestError = jsonDecode(response.body)['detail'];
      } else {
        requestError = null;
      }
    } catch (e) {
      debugPrint('Error: cannot receive or read response');
      requestError = "Network error";
    }
    if (requestError != null) {
      switch (requestError) {
        case 'Network error':
          endMessage = loc.errorNetwork;
        default:
          endMessage = loc.errorBadRequest;
      }
      endTitle = loc.errorGeneric;
    } else {
      endTitle = loc.successGeneric;
      endMessage = loc.successResetRequest;
    }
    if (!mounted) return;
    await showDialog(
      context: context,
      builder: (_) => GotoIfAlertDialog(
        title: endTitle,
        content: endMessage,
        condition: (requestError != null),
        route: "/login",
      ),
    );
    setState(() {
      resetRequestIsSent = true;
    });
  }

  void _doPasswordResetConfirmation(Map<String, dynamic> data) async {
    final loc = AppLocalizations.of(context)!;
    final jsonBody = jsonEncode(data);
    String? resetError;
    String endMessage;
    String endTitle;
    final http.Response response;
    try {
      final url = Uri.parse('${config.apiBaseUrl}/password-reset/confirm');
      response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: jsonBody,
      );
      if (response.statusCode < 200 || response.statusCode >= 300) {
        debugPrint("HTTP ${response.statusCode}: ${response.body}");
        resetError = jsonDecode(response.body)['detail'];
      } else {
        resetError = null;
      }
    } catch (e) {
      debugPrint('Error: cannot receive or read response');
      resetError = "Network error";
    }
    if (resetError != null) {
      switch (resetError) {
        case 'Network error':
          endMessage = loc.errorNetwork;
        case 'Code or email not valid':
          endMessage = loc.errorCodeOrEmailNotValid;
        default:
          endMessage = loc.errorBadRequest;
      }
      endTitle = loc.errorGeneric;
    } else {
      endTitle = loc.successGeneric;
      endMessage = loc.successPasswordChanged;
    }
    if (!mounted) return;
    await showDialog(
      context: context,
      builder: (_) => GotoIfAlertDialog(
        title: endTitle,
        content: endMessage,
        condition: (resetError == null),
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
                  if (resetRequestIsSent)
                    TextFormField(
                      controller: _codeController,
                      decoration: InputDecoration(
                        labelText: loc.labelVerificationCode,
                        border: OutlineInputBorder(),
                      ),
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                      maxLength: 10,
                      validator: (value) {
                        return validateDigitCode(context, value);
                      },
                    ),
                  SizedBox(height: 5),
                  if (resetRequestIsSent)
                    TextFormField(
                      controller: _passwordController,
                      decoration: InputDecoration(
                        labelText: loc.labelNewPassword,
                        border: OutlineInputBorder(),
                      ),
                      maxLength: 256,
                      validator: (value) {
                        return validatePassword(context, value);
                      },
                      obscureText: !showPasswordFlag,
                    ),
                  SizedBox(height: 5),
                  if (resetRequestIsSent)
                    TextFormField(
                      controller: _rePasswordController,
                      decoration: InputDecoration(
                        labelText: loc.labelConfirmNewPassword,
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
                  if (resetRequestIsSent)
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
