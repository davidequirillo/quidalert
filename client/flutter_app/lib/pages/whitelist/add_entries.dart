// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import 'package:quidalert_flutter/utils/validators.dart';
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
      drawer: const CAppDrawer(),
      body: const WhiteListAddBody(),
    );
  }
}

class WhiteListAddBody extends StatefulWidget {
  const WhiteListAddBody({super.key});

  @override
  State<WhiteListAddBody> createState() => _WhiteListAddBodyState();
}

class _WhiteListAddBodyState extends State<WhiteListAddBody> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  PlatformFile? _pickedFile;

  @override
  void dispose() {
    _emailController.dispose();
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
    showLoadingDialog(context, loc.labelWaitPlease);
    addEntries().whenComplete(() {
      if (mounted) {
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
    List<String> emailsToAdd = [];
    if (!_formKey.currentState!.validate()) {
      return;
    }
    String email = _emailController.text.trim().toLowerCase();
    emailsToAdd.add(email);
    try {
      final response = await authClient.doProtectedApiRequest(
        "post",
        '/whitelist-entries',
        body: {"emails": emailsToAdd},
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
        retMessage = loc.successGeneric;
      }
    } on GenericNotAuthorizedException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorNotAuthorizedDoLogin;
      if (mounted) {
        goToLoginPagePostFrameCallback(context);
      }
    } on ForbiddenRequestException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorPermissionsNotValid;
    } on BadRequestException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorBadRequest;
    } on NetworkException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorNetwork;
    } catch (e) {
      retTitle = loc.errorError;
      retMessage = e.toString();
    } finally {
      if (mounted) {
        setState(() {
          _emailController.text = ''; // reset email input
        });
        await showDialog(
          context: context,
          builder: (BuildContext context) {
            return SimpleAlertDialog(title: retTitle, content: retMessage);
          },
        );
      }
    }
    return;
  }

  Future<void> addEntries() async {
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    String retMessage = loc.successGeneric;
    String retTitle = loc.successGeneric;
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
        final response = await authClient.doProtectedApiRequest(
          "post",
          '/whitelist-entries',
          body: {"emails": emailsToAdd},
        );
        final Map<String, dynamic> respObj = json.decode(response.body);
        final List<String> emailsNotAdded = List<String>.from(
          respObj['failed_emails'],
        );
        final int totalCount = respObj['total_count'];
        final int addedCount = respObj['added_count'];
        final int failedCount = respObj['failed_count'];
        final int existingCount = respObj['existing_count'];
        retTitle = loc.successGeneric;
        retMessage =
            '${loc.labelRowsTotal}: $totalCount\n${loc.labelEntriesAdded}: $addedCount\n${loc.labelEntriesFailed}: $failedCount\n${loc.labelEntriesExisting}: $existingCount';
        if (emailsNotAdded.isNotEmpty) {
          retMessage += '\n\n${loc.labelEntriesFailed}:\n';
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
      if (mounted) {
        goToLoginPagePostFrameCallback(context);
      }
    } on ForbiddenRequestException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorPermissionsNotValid;
    } on BadRequestException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorBadRequest;
    } on NetworkException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorNetwork;
    } catch (e) {
      retTitle = loc.errorError;
      retMessage = e.toString();
    } finally {
      if (mounted) {
        setState(() {
          _pickedFile = null; // reset picked file
        });
        await showDialog(
          context: context,
          builder: (BuildContext context) {
            return SimpleAlertDialog(title: retTitle, content: retMessage);
          },
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            buildSectionTitle(
              '${loc.buttonAdd} ${loc.labelEmailSingle.toLowerCase()}',
            ),
            Form(
              key: _formKey,
              child: Column(
                children: [
                  const SizedBox(height: 5),
                  TextFormField(
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
                    ],
                  ),
                  const SizedBox(height: 15),
                  Divider(),
                  const SizedBox(height: 15),
                  buildSectionTitle(
                    '${loc.buttonAdd} ${loc.labelEmailMany.toLowerCase()}',
                  ),
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
          ],
        ),
      ),
    );
  }
}
