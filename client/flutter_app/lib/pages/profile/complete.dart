// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/utils/validator.dart';
import 'package:quidalert_flutter/config.dart' as config;

class CompleteProfilePage extends StatelessWidget {
  const CompleteProfilePage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.labelCompleteProfile, showBackButton: true),
      drawer: const CAppDrawer(),
      body: CompleteProfileBody(),
    );
  }
}

class CompleteProfileBody extends StatefulWidget {
  const CompleteProfileBody({super.key});

  @override
  State<CompleteProfileBody> createState() => _CompleteProfileBodyState();
}

class _CompleteProfileBodyState extends State<CompleteProfileBody> {
  final _formKey = GlobalKey<FormState>();
  final _firstnameController = TextEditingController();
  final _surnameController = TextEditingController();
  final _addressController = TextEditingController();
  final _birthdateController = TextEditingController();
  final _phoneController = TextEditingController();
  bool showPasswordFlag = false;

  @override
  void dispose() {
    _firstnameController.dispose();
    _surnameController.dispose();
    _addressController.dispose();
    _birthdateController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    if (!_formKey.currentState!.validate()) return;
    final fname = _firstnameController.text.trim();
    final sname = _surnameController.text.trim();
    final address = _addressController.text.trim();
    final birthdate = _birthdateController.text.trim();
    final phone = _phoneController.text.trim();
    final fields = {
      "firstname": fname,
      "surname": sname,
      "address": address,
      "birthdate": birthdate,
      "phone": phone,
    };
    await _completeProfile(fields);
  }

  Future<void> _completeProfile(Map<String, dynamic> data) async {
    try {
      // Here you would send the data to the server to complete the profile
    } catch (e) {
      debugPrint('Error: cannot receive or read response');
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return SafeArea(
      child: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.start,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Form(
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
                          onPressed: () => Navigator.pop(context),
                          child: Text(loc.buttonCancel),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            SizedBox(height: 20),
            Padding(
              padding: const EdgeInsets.symmetric(
                vertical: 25.0,
                horizontal: 25.0,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  buildSectionTitle("Extra info"),
                  Text("View profile extra information here"),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
