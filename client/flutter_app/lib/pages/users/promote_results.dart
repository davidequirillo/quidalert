// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/utils/validators.dart';
import 'package:quidalert_flutter/models/general.dart';

class UsersPromoteResultsPage extends StatelessWidget {
  const UsersPromoteResultsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuUsers, showBackButton: true),
      drawer: const CAppDrawer(),
      body: UsersPromoteResultsBody(),
    );
  }
}

class UsersPromoteResultsBody extends StatefulWidget {
  const UsersPromoteResultsBody({super.key});

  @override
  State<UsersPromoteResultsBody> createState() =>
      _UsersPromoteResultsBodyState();
}

class _UsersPromoteResultsBodyState extends State<UsersPromoteResultsBody> {
  final _formKey = GlobalKey<FormState>();
  final _scrollController = ScrollController();
  final TextEditingController _authorizerController = TextEditingController();
  final TextEditingController _notesController = TextEditingController();
  UserType? selectedType;
  UserRole? selectedRole;
  UserStatus? selectedStatus;
  bool _activateNotes = false;

  @override
  void dispose() {
    _scrollController.dispose();
    _authorizerController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    bool error = false;
    String retMessage = "";
    String retTitle = "";
    final args = ModalRoute.of(context)!.settings.arguments;
    final loc = AppLocalizations.of(context)!;
    if (!_formKey.currentState!.validate()) {
      return;
    }
    try {
      Map<String, dynamic> respObj;
      if (args is List<String>) {
        respObj = await promoteUsersByEmails(args);
      } else if (args is Map<String, String?>) {
        respObj = await promoteUsersByFields(args);
      } else {
        throw Exception("Invalid arguments for search results page");
      }
      retTitle = loc.successGeneric;
      int promotedCount = respObj['updated_count'];
      retMessage = loc.successUsersModified.replaceAll(
        "<count>",
        promotedCount.toString(),
      );
      return;
    } on BadRequestException catch (_) {
      retTitle = loc.errorGeneric;
      retMessage = loc.errorBadRequest;
      error = true;
    } on ForbiddenRequestException catch (_) {
      retTitle = loc.errorPermissionsNotValid;
      retMessage = loc.errorPermissionsNotValid;
      error = true;
    } on GenericNotAuthorizedException catch (_) {
      retTitle = loc.errorGeneric;
      retMessage = loc.errorNotAuthorizedDoLogin;
      error = true;
      if (mounted) {
        goToLoginPagePostFrameCallback(context);
      }
    } on NetworkException catch (_) {
      retTitle = loc.errorGeneric;
      retMessage = loc.errorNetwork;
      error = true;
    } catch (e) {
      debugPrint('Error: cannot receive or read response');
      retTitle = loc.errorGeneric;
      retMessage = e.toString();
      error = true;
    } finally {
      if (mounted) {
        await showDialog(
          context: context,
          builder: (_) =>
              SimpleAlertDialog(title: retTitle, content: retMessage),
        );
        if (error == false) {
          if (mounted) {
            Navigator.pop(context);
            Navigator.pop(context);
            Navigator.pushNamed(
              context,
              "/accounts/users/search-results",
              arguments: args,
            );
          }
        }
      }
    }
  }

  Future<Map<String, dynamic>> promoteUsersByFields(
    Map<String, String?> args,
  ) async {
    String queryStr = args.entries
        .where((entry) => entry.value != null && entry.value!.isNotEmpty)
        .map((entry) => "${entry.key}=${Uri.encodeComponent(entry.value!)}")
        .join("&");
    final requestStr = '/users/promote?$queryStr';
    final authClient = context.read<AuthClient>();
    final updateFields = {
      if (selectedType != null) "type": selectedType!.name,
      if (selectedRole != null) "role": selectedRole!.name,
      if (selectedStatus != null) "status": selectedStatus!.name,
      if (_activateNotes) "notes": _notesController.text.trim(),
      if (_authorizerController.text.isNotEmpty)
        "authorizer": _authorizerController.text.trim(),
    };
    if (updateFields.isEmpty) {
      return {"message": "No fields to update", "updated_count": 0};
    }
    final response = await authClient.doProtectedApiRequest(
      "post",
      requestStr,
      body: updateFields,
    );
    final respObj = json.decode(response.body);
    return respObj;
  }

  Future<Map<String, dynamic>> promoteUsersByEmails(List<String> emails) async {
    final requestStr = '/users/promote-by-emails';
    final authClient = context.read<AuthClient>();
    final updateFields = {
      if (selectedType != null) "type": selectedType!.name,
      if (selectedRole != null) "role": selectedRole!.name,
      if (selectedStatus != null) "status": selectedStatus!.name,
      if (_activateNotes) "notes": _notesController.text.trim(),
      if (_authorizerController.text.isNotEmpty)
        "authorizer": _authorizerController.text.trim(),
    };
    if (updateFields.isEmpty) {
      return {"message": "No fields to update", "updated_count": 0};
    }
    final response = await authClient.doProtectedApiRequest(
      "post",
      requestStr,
      body: {"emails": emails, "update_fields": updateFields},
    );
    final respObj = json.decode(response.body);
    return respObj;
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    final args = ModalRoute.of(context)!.settings.arguments;
    String searchStr;
    if (args is List<String>) {
      searchStr = "${args.length} email addresses from CSV file";
    } else if (args is Map<String, String?>) {
      searchStr = args.entries
          .where((entry) => entry.value != null && entry.value!.isNotEmpty)
          .map((entry) => "${entry.key}: ${entry.value}")
          .join(", ");
      if (searchStr.isEmpty) {
        searchStr = loc.labelAllMasculinePlural;
      }
    } else {
      throw Exception("Invalid arguments for search results page");
    }
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
                Text(
                  "Query -> $searchStr",
                  style: Theme.of(context).textTheme.titleMedium,
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
                    labelText: loc.labelStatus,
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
                CheckboxListTile(
                  title: Text(loc.labelAddNotes),
                  value: _activateNotes,
                  onChanged: (bool? value) {
                    setState(() {
                      _activateNotes = value ?? false;
                    });
                  },
                ),
                if (_activateNotes) const SizedBox(height: 20),
                if (_activateNotes)
                  TextFormField(
                    controller: _notesController,
                    decoration: InputDecoration(
                      labelText: loc.labelNotes,
                      border: OutlineInputBorder(),
                    ),
                    maxLines: 3,
                    maxLength: 256,
                    validator: (value) {
                      if ((value == null) || (value.isEmpty)) {
                        return null;
                      }
                      return validateDescription(context, value);
                    },
                  ),
                const SizedBox(height: 50),
                Text(loc.labelCompileToChangeAuthorizer),
                TextFormField(
                  controller: _authorizerController,
                  decoration: InputDecoration(
                    labelText: loc.labelAuthorizedBy,
                    border: OutlineInputBorder(),
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
                ElevatedButton(
                  onPressed: () => submit(),
                  child: Text(loc.buttonModify),
                ),
                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: () {
                    // clear all fields and reset dropdowns to initial state
                    setState(() {
                      selectedType = null;
                      selectedRole = null;
                      selectedStatus = null;
                      _authorizerController.clear();
                      _notesController.clear();
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
