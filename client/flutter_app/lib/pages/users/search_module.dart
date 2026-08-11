// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/models/general.dart';
import 'package:quidalert_flutter/utils/validators.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class UsersSearchModulePage extends StatelessWidget {
  const UsersSearchModulePage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuUsers, showBackButton: true),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: UsersSearchModuleBody()),
    );
  }
}

class UsersSearchModuleBody extends StatefulWidget {
  const UsersSearchModuleBody({super.key});

  @override
  State<UsersSearchModuleBody> createState() => _UsersSearchModuleBodyState();
}

class _UsersSearchModuleBodyState extends State<UsersSearchModuleBody> {
  final _formKey = GlobalKey<FormState>();
  final _scrollController = ScrollController();
  final _emailController = TextEditingController();
  final _firstnameController = TextEditingController();
  final _surnameController = TextEditingController();
  final _authorizerController = TextEditingController();
  UserStatus? selectedStatus;
  UserType? selectedType;
  UserRole? selectedRole;

  @override
  void dispose() {
    _firstnameController.dispose();
    _surnameController.dispose();
    _emailController.dispose();
    _authorizerController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final fname = _firstnameController.text.trim();
    final sname = _surnameController.text.trim();
    final email = _emailController.text.trim();
    final authorizer = _authorizerController.text.trim();
    Map<String, String?> fields = {};
    if (email.isNotEmpty) {
      fields["email"] = email;
    } else {
      fields["firstname"] = fname;
      fields["surname"] = sname;
      fields["authorizer"] = authorizer;
      fields["type"] = selectedType?.name;
      fields["role"] = selectedRole?.name;
      fields["status"] = selectedStatus?.name;
    }
    await _viewSearchResultsPage(fields);
  }

  Future<void> _viewSearchResultsPage(Map<String, String?> data) async {
    Navigator.pushNamed(
      context,
      '/accounts/users/search-results',
      arguments: data,
    );
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
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
              TextFormField(
                keyboardType: TextInputType.emailAddress,
                controller: _emailController,
                decoration: InputDecoration(labelText: "Email"),
                validator: (value) {
                  if ((value == null) || (value.isEmpty)) {
                    return null;
                  }
                  return validateEmail(context, value);
                },
              ),
              TextFormField(
                controller: _surnameController,
                decoration: InputDecoration(labelText: loc.userSurname),
                keyboardType: TextInputType.name,
                onChanged: (value) {
                  if (value.isEmpty) {
                    _firstnameController.clear();
                  }
                },
              ),
              TextFormField(
                controller: _firstnameController,
                decoration: InputDecoration(labelText: loc.userFirstname),
                keyboardType: TextInputType.name,
                onChanged: (value) {
                  if (_surnameController.text.isEmpty) {
                    _firstnameController.clear();
                  }
                },
              ),
              if (authClient.isAdmin())
                TextFormField(
                  keyboardType: TextInputType.emailAddress,
                  controller: _authorizerController,
                  decoration: InputDecoration(labelText: loc.userAuthorizedBy),
                  validator: (value) {
                    if ((value == null) || (value.isEmpty)) {
                      return null;
                    }
                    return validateEmail(context, value);
                  },
                ),
              const SizedBox(height: 20),
              if (authClient.isAdmin())
                DropdownButtonFormField<UserType>(
                  decoration: InputDecoration(
                    labelText: loc.userType,
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.category),
                  ),
                  initialValue: null,
                  items: UserType.values.map((UserType type) {
                    return DropdownMenuItem<UserType>(
                      value: type,
                      child: Text(
                        type.name[0].toUpperCase() + type.name.substring(1),
                      ),
                    );
                  }).toList(),
                  onChanged: (newValue) {
                    selectedType = newValue;
                  },
                ),
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
              ElevatedButton(
                onPressed: () => _submit(),
                child: Text(loc.buttonSearch),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () {
                  // clear all fields and reset dropdowns to initial state
                  setState(() {
                    _emailController.clear();
                    _firstnameController.clear();
                    _surnameController.clear();
                    _authorizerController.clear();
                    selectedType = null;
                    selectedRole = null;
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
