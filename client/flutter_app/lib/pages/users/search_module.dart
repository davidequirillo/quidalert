// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
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
      body: UsersSearchModuleBody(),
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
    await _prepareSearchFields(fields);
  }

  Future<void> _prepareSearchFields(Map<String, String?> data) async {
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
        child: SafeArea(
          top: false,
          child: Form(
            key: _formKey,
            child: Column(
              children: [
                TextFormField(
                  controller: _emailController,
                  decoration: InputDecoration(labelText: "Email"),
                  keyboardType: TextInputType.emailAddress,
                  validator: (value) {
                    if ((value == null) || (value.isEmpty)) {
                      return null;
                    }
                    return validateEmail(context, value);
                  },
                ),
                TextFormField(
                  controller: _firstnameController,
                  decoration: InputDecoration(labelText: loc.labelFirstname),
                  keyboardType: TextInputType.name,
                ),
                TextFormField(
                  controller: _surnameController,
                  decoration: InputDecoration(labelText: loc.labelSurname),
                  keyboardType: TextInputType.name,
                ),
                if (authClient.isAdmin())
                  TextFormField(
                    controller: _authorizerController,
                    decoration: InputDecoration(
                      labelText: loc.labelAuthorizedBy,
                    ),
                    keyboardType: TextInputType.emailAddress,
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
                      labelText: loc.labelType,
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
                    labelText: loc.labelRole,
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
      ),
    );
  }
}
