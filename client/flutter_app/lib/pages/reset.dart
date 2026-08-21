// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/utils/validators.dart';
import 'package:quidalert_flutter/config.dart';

class ResetPage extends StatelessWidget {
  const ResetPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CAppBar(title: "Password reset"),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: ResetBody()),
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
  final ScrollController _scrollController = ScrollController();
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
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    if (!_formKey.currentState!.validate()) return;
    final email = _emailController.text.trim();
    String code = "";
    String newPassword = "";
    if (!resetRequestIsSent) {
      final fields = {"email": email};
      await _doPasswordResetRequest(fields);
    } else {
      code = _codeController.text.trim();
      newPassword = _passwordController.text;
      final fields = {
        "email": email,
        "code": code,
        "new_password": newPassword,
      };
      await _doPasswordResetConfirmation(fields);
    }
  }

  Future<void> _doPasswordResetRequest(Map<String, String> data) async {
    final loc = AppLocalizations.of(context)!;
    final jsonBody = jsonEncode(data);
    bool isSuccess = false;
    String endMessage;
    String endTitle;
    final http.Response response;
    try {
      final url = Uri.parse('${AppConfig.apiUrl}/password-reset/request');
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
        endTitle = loc.successGeneric;
        endMessage = loc.successResetRequest;
        isSuccess = true;
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
      (!isSuccess),
      "/login",
    );
    setState(() {
      resetRequestIsSent = true;
    });
  }

  Future<void> _doPasswordResetConfirmation(Map<String, String> data) async {
    final loc = AppLocalizations.of(context)!;
    final jsonBody = jsonEncode(data);
    bool isSuccess = false;
    String endMessage;
    String endTitle;
    final http.Response response;
    try {
      final url = Uri.parse('${AppConfig.apiUrl}/password-reset/confirm');
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
        if ((response.statusCode == 400) &&
            (response.body.contains('Code or email not valid'))) {
          endTitle = loc.errorError;
          endMessage = loc.errorCodeOrEmailNotValid;
        } else {
          endTitle = loc.errorError;
          endMessage = loc.errorBadRequest;
        }
      } else {
        endTitle = loc.successGeneric;
        endMessage = loc.successPasswordChanged;
        isSuccess = true;
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
      (isSuccess),
      "/login",
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
                if (resetRequestIsSent)
                  TextFormField(
                    keyboardType: TextInputType.number,
                    controller: _codeController,
                    decoration: InputDecoration(
                      labelText: loc.labelVerificationCode,
                      border: OutlineInputBorder(),
                    ),
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                    maxLength: 10,
                    validator: (value) {
                      return validateDigitCode(context, value, min: 10);
                    },
                  ),
                SizedBox(height: 5),
                if (resetRequestIsSent)
                  TextFormField(
                    keyboardType: TextInputType.visiblePassword,
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
                    keyboardType: TextInputType.visiblePassword,
                    controller: _rePasswordController,
                    decoration: InputDecoration(
                      labelText: loc.labelConfirmNewPassword,
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
    );
  }
}
