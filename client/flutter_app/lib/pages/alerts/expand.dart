// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/l10n/app_localizations_extension.dart';
import 'package:quidalert_flutter/services/location.dart';
import 'package:quidalert_flutter/models/general.dart';
import 'package:quidalert_flutter/utils/validators.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class ExpandAlertPage extends StatelessWidget {
  const ExpandAlertPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.alertExtend, showBackButton: true),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: ExpandAlertBody()),
    );
  }
}

class ExpandAlertBody extends StatefulWidget {
  const ExpandAlertBody({super.key});

  @override
  State<ExpandAlertBody> createState() => _ExpandAlertBodyState();
}

class _ExpandAlertBodyState extends State<ExpandAlertBody> {
  final _formKey = GlobalKey<FormState>();
  final _scrollController = ScrollController();
  UserRole? selectedRole;

  @override
  void dispose() {
    debugPrintC("Disposing ExpandAlert widget state");
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scrollbar(
      thumbVisibility: true,
      controller: _scrollController,
      child: SingleChildScrollView(
        controller: _scrollController,
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            children: [
              const SizedBox(height: 20),
              DropdownButtonFormField<UserRole>(
                decoration: InputDecoration(
                  labelText: loc.userRole,
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.category),
                ),
                initialValue: null,
                items: UserRole.values.map((UserRole role) {
                  return DropdownMenuItem<UserRole>(
                    value: role,
                    child: Text(
                      role.name[0].toUpperCase() + role.name.substring(1),
                    ),
                  );
                }).toList(),
                onChanged: (newValue) {
                  selectedRole = newValue;
                },
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () => _submit(),
                child: Text(loc.buttonExtend),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () {
                  // clear all fields and reset dropdowns to initial state
                  setState(() {
                    selectedRole = null;
                    _formKey.currentState?.reset();
                  });
                },
                child: Text(loc.buttonClear),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
