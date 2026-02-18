// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/models/general.dart';

class ChangeStatusPage extends StatelessWidget {
  const ChangeStatusPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuUsers, showBackButton: true),
      drawer: const CAppDrawer(),
      body: ChangeStatusBody(),
    );
  }
}

class ChangeStatusBody extends StatefulWidget {
  const ChangeStatusBody({super.key});

  @override
  State<ChangeStatusBody> createState() => _ChangeStatusBodyState();
}

class _ChangeStatusBodyState extends State<ChangeStatusBody> {
  final _formKey = GlobalKey<FormState>();
  UserStatus? selectedStatus;

  @override
  void dispose() {
    super.dispose();
  }

  Future<void> submit() async {
    final args =
        ModalRoute.of(context)!.settings.arguments as Map<String, String?>;
    String? id = args['id'];
    if (id != null) {
      await changeStatusById(id);
    }
  }

  Future<void> changeStatusById(String id) async {
    final requestStr = '/change-status-by-id?id=$id';
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "post",
      requestStr,
      body: {"status": selectedStatus!.name},
    );
    final respObj = json.decode(response.body);
    return;
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return SafeArea(
      top: false,
      child: Form(
        key: _formKey,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              DropdownButtonFormField<UserStatus>(
                decoration: InputDecoration(
                  labelText: "Status",
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.category),
                ),
                initialValue: null,
                items: UserStatus.values.map((UserStatus status) {
                  return DropdownMenuItem<UserStatus>(
                    value: status,
                    child: Text(
                      status.name[0].toUpperCase() + status.name.substring(1),
                    ),
                  );
                }).toList(),
                onChanged: (newValue) {
                  selectedStatus = newValue;
                },
              ),
              const SizedBox(height: 20),
              ElevatedButton(onPressed: () => submit(), child: Text("OK")),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () {
                  setState(() {
                    selectedStatus = null;
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
