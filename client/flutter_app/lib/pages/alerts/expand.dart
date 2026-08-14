// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/l10n/app_localizations_extension.dart';
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
  final _radiusController = TextEditingController();
  UserRole? selectedRole;

  @override
  void dispose() {
    debugPrintC("Disposing ExpandAlert widget state");
    _scrollController.dispose();
    _radiusController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    await _extendAlert();
  }

  Future<void> _extendAlert() async {
    String retTitle = "";
    String retMessage = "";
    bool newLoginRequired = false;
    bool isError = true;
    final alertId = ModalRoute.of(context)!.settings.arguments as int;
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    final radius = double.tryParse(_radiusController.text.trim());
    if (radius == null) {
      return;
    }
    Map<String, dynamic> fields = {};
    if ((selectedRole != null) && selectedRole!.name.isNotEmpty) {
      fields["role"] = selectedRole!.name;
    }
    fields["radius"] = radius;
    try {
      await authClient.doProtectedApiRequest(
        'POST',
        '/alerts/$alertId/expand',
        body: fields,
      );
      retTitle = loc.successGeneric;
      retMessage = loc.successAlertExtended;
      isError = false;
    } catch (e) {
      final exceptionName = e.runtimeType.toString();
      if (exceptionName == "GenericNotAuthorizedException") {
        newLoginRequired = true;
      }
      retTitle = loc.errorError;
      retMessage = loc.getExceptionString(exceptionName) ?? loc.errorGeneric;
    } finally {
      if (mounted) {
        await showSimpleAlertDialog(context, retTitle, retMessage);
      }
      if (isError == false) {
        if (mounted) {
          Navigator.of(context).pushNamedAndRemoveUntil(
            '/alerts/view-alert-details',
            (route) => false,
            arguments: alertId,
          );
        }
      } else if (newLoginRequired == true) {
        if (mounted) {
          goToLoginPage(context);
        }
      }
    }
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
              TextFormField(
                controller: _radiusController,
                decoration: InputDecoration(
                  labelText: loc.alertRadiusKm,
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.map),
                ),
                keyboardType: TextInputType.number,
                maxLength: 3,
                validator: (value) {
                  return validateRadius(context, value);
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
