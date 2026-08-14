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
import 'package:file_picker/file_picker.dart';
import 'package:quidalert_flutter/models/general.dart';
import 'package:quidalert_flutter/utils/validators.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/utils/fileutils.dart';

class WhiteListAddPage extends StatelessWidget {
  const WhiteListAddPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuWhiteList, showBackButton: true),
      body: SafeArea(top: false, child: WhiteListAddBody()),
    );
  }
}

class WhiteListAddBody extends StatefulWidget {
  const WhiteListAddBody({super.key});

  @override
  State<WhiteListAddBody> createState() => _WhiteListAddBodyState();
}

class _WhiteListAddBodyState extends State<WhiteListAddBody> {
  final _scrollController = ScrollController();
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  UserTypeExtended? selectedType;
  UserRoleExtended? selectedRole;
  PlatformFile? _pickedFile;

  @override
  void dispose() {
    _emailController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ["csv", "txt"],
    );
    if (result != null) {
      setState(() {
        _pickedFile = result.files.first;
      });
    }
  }

  void submitMany() {
    final loc = AppLocalizations.of(context)!;
    debugPrintC(
      "Showing waiting dialog and submitting entries from file: ${_pickedFile?.name}",
    );
    showLoadingDialog(context, loc.labelWaitPlease);
    addEntries().whenComplete(() {
      if (mounted) {
        debugPrintC("Entries addition process completed, pop 'loading dialog'");
        Navigator.pop(context);
      }
    });
  }

  void submitSingle() {
    addEntry();
  }

  Future<void> addEntry() async {
    // Implementation for adding a single entry goes here
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    String retMessage = loc.successGeneric;
    String retTitle = loc.successGeneric;
    bool newLoginRequired = false;
    List<String> emailsToAdd = [];
    if (!_formKey.currentState!.validate()) {
      return;
    }
    final String? registrationType = selectedType?.name;
    final String? registrationRole = selectedRole?.name;
    String email = _emailController.text.trim().toLowerCase();
    emailsToAdd.add(email);
    final Map<String, dynamic> fields = {"emails": emailsToAdd};
    if (registrationType != null &&
        registrationType != UserTypeExtended.base.name) {
      fields["type"] = registrationType;
    }
    if (registrationRole != null &&
        registrationRole != UserRoleExtended.citizen.name) {
      fields["role"] = registrationRole;
    }
    try {
      final response = await authClient.doProtectedApiRequest(
        "post",
        '/whitelist-entries',
        body: fields,
      );
      final Map<String, dynamic> respObj = json.decode(response.body);
      final List<String> emailsNotAdded = List<String>.from(
        respObj['failed_emails'],
      );
      final int existingCount = respObj['existing_count'];
      if (emailsNotAdded.contains(email)) {
        retTitle = loc.errorError;
        retMessage = loc.errorEmailNotValid;
      } else if (existingCount > 0) {
        retTitle = loc.errorError;
        retMessage = loc.errorEmailAlreadyExist;
      } else {
        retTitle = loc.successGeneric;
        retMessage = loc.successEntryAdded;
      }
    } on GenericNotAuthorizedException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorNotAuthorizedDoLogin;
      newLoginRequired = true;
    } on ForbiddenRequestException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorPermissionsNotValid;
    } on BadRequestException catch (e) {
      retTitle = loc.errorBadRequest;
      retMessage = e.toString();
    } on ServerException catch (_) {
      retTitle = loc.errorServer;
      retMessage = loc.errorServer;
    } catch (e) {
      retTitle = loc.errorError;
      retMessage = e.toString();
    } finally {
      if (mounted) {
        setState(() {
          _emailController.text = ''; // reset email input
        });
        await showSimpleAlertDialog(context, retTitle, retMessage);
      }
      if (newLoginRequired) {
        if (mounted) {
          goToLoginPagePostFrameCallback(context);
        }
      }
    }
    return;
  }

  Future<void> addEntries() async {
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    String retMessage = loc.successGeneric;
    String retTitle = loc.successGeneric;
    bool newLoginRequired = false;
    List<String> emailsToAdd = [];
    if (_pickedFile != null) {
      await Future.delayed(const Duration(seconds: 2));
      final filePath = _pickedFile!.path;
      if (filePath != null) {
        try {
          final List<String> emailsFromFile = readEmailsFromFile(filePath);
          emailsToAdd.addAll(emailsFromFile);
        } catch (e) {
          retTitle = loc.errorError;
          retMessage = loc.errorCannotReadFile;
        }
      }
    }
    try {
      if (emailsToAdd.isNotEmpty) {
        final String? registrationType = selectedType?.name;
        final String? registrationRole = selectedRole?.name;
        final Map<String, dynamic> fields = {"emails": emailsToAdd};
        if (registrationType != null &&
            registrationType != UserTypeExtended.base.name) {
          fields["type"] = registrationType;
        }
        if (registrationRole != null &&
            registrationRole != UserRoleExtended.citizen.name) {
          fields["role"] = registrationRole;
        }
        final response = await authClient.doProtectedApiRequest(
          "post",
          '/whitelist-entries',
          body: fields,
        );
        final Map<String, dynamic> respObj = json.decode(response.body);
        final List<String> emailsNotAdded = List<String>.from(
          respObj['failed_emails'],
        );
        final int totalCount = respObj['total_count'];
        final int addedCount = respObj['added_count'];
        final int skippedCount = respObj['skipped_count'];
        final int failedCount = respObj['failed_count'];
        final int existingCount = respObj['existing_count'];
        retTitle = loc.successGeneric;
        retMessage =
            '${loc.labelRowsTotal}: $totalCount\n${loc.entriesAdded}: $addedCount\n${loc.entriesSkipped}: $skippedCount\n${loc.entriesFailed}: $failedCount\n${loc.entriesExisting}: $existingCount';
        if (emailsNotAdded.isNotEmpty) {
          retMessage += '\n\n${loc.entriesFailed}:\n';
          for (var email in emailsNotAdded) {
            retMessage += ', $email\n';
          }
        }
      } else {
        if (retMessage != loc.errorCannotReadFile) {
          retMessage = loc.errorNoEntryToAdd;
        }
      }
    } on GenericNotAuthorizedException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorNotAuthorizedDoLogin;
      newLoginRequired = true;
    } on ForbiddenRequestException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorPermissionsNotValid;
    } on BadRequestException catch (e) {
      if (e.message.contains("Email list too long")) {
        retTitle = loc.errorBadRequest;
        retMessage = e.toString();
      } else {
        retTitle = loc.errorError;
        retMessage = loc.errorBadRequest;
      }
    } on ServerException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorServer;
    } catch (e) {
      retTitle = loc.errorError;
      retMessage = e.toString();
    } finally {
      if (mounted) {
        setState(() {
          _pickedFile = null; // reset picked file
        });
        await showSimpleAlertDialog(context, retTitle, retMessage);
      }
      if (newLoginRequired) {
        if (mounted) {
          goToLoginPagePostFrameCallback(context);
        }
      }
    }
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
              if (authClient.isAdmin())
                Text(
                  '${loc.labelNote}: ${loc.sectionWhitelistAddInfoForAdmin.toLowerCase()}',
                ),
              if (!authClient.isAdmin())
                Text(
                  '${loc.labelNote}: ${loc.sectionWhitelistAddInfoForOfficer.toLowerCase()}',
                ),
              const SizedBox(height: 10),
              if (authClient.isAdmin())
                DropdownButtonFormField<UserTypeExtended>(
                  decoration: InputDecoration(
                    labelText: loc.userType,
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.category),
                  ),
                  initialValue: null,
                  items: UserTypeExtended.values.map((UserTypeExtended type) {
                    return DropdownMenuItem<UserTypeExtended>(
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
              const SizedBox(height: 10),
              DropdownButtonFormField<UserRoleExtended>(
                decoration: InputDecoration(
                  labelText: loc.userRole,
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.category),
                ),
                initialValue: null,
                items: UserRoleExtended.values.map((UserRoleExtended role) {
                  return DropdownMenuItem<UserRoleExtended>(
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
              buildSectionTitle(loc.sectionWhitelistAddSingleEntry),
              const SizedBox(height: 5),
              TextFormField(
                keyboardType: TextInputType.emailAddress,
                controller: _emailController,
                decoration: InputDecoration(
                  labelText: "Email",
                  border: OutlineInputBorder(),
                ),
                maxLength: 128,
                validator: (value) {
                  return validateEmail(context, value);
                },
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ElevatedButton(
                    onPressed: () {
                      submitSingle();
                    },
                    child: Text(loc.buttonAdd),
                  ),
                  const SizedBox(width: 15),
                  ElevatedButton(
                    onPressed: () => Navigator.pop(context),
                    child: Text(loc.buttonBack),
                  ),
                  const SizedBox(width: 15),
                  ElevatedButton(
                    onPressed: () {
                      setState(() {
                        setState(() {
                          _emailController.clear();
                          selectedType = null;
                          selectedRole = null;
                          _formKey.currentState?.reset();
                        });
                      });
                    },
                    child: Text(loc.buttonClear),
                  ),
                ],
              ),
              const SizedBox(height: 15),
              Divider(),
              const SizedBox(height: 15),
              buildSectionTitle(loc.sectionWhitelistAddManyEntries),
              const SizedBox(height: 10),
              ElevatedButton(onPressed: _pickFile, child: Text("File CSV")),
              if (_pickedFile != null) ...[
                const SizedBox(height: 10),
                Text('${loc.labelFileSelected}: ${_pickedFile!.name}'),
              ],
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ElevatedButton(
                    onPressed: () {
                      submitMany();
                    },
                    child: Text(loc.buttonAdd),
                  ),
                  const SizedBox(width: 15),
                  ElevatedButton(
                    onPressed: () => Navigator.pop(context),
                    child: Text(loc.buttonBack),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
