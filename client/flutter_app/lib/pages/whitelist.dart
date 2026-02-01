// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import 'package:quidalert_flutter/utils/validator.dart';
import 'package:quidalert_flutter/widgets/common.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/models/general.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/utils/fileutils.dart';

class WhiteListPage extends StatelessWidget {
  const WhiteListPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuWhiteList, showBackButton: true),
      drawer: const CAppDrawer(),
      body: WhiteListBody(),
    );
  }
}

class WhiteListBody extends StatefulWidget {
  const WhiteListBody({super.key});

  @override
  State<WhiteListBody> createState() => _WhiteListBodyState();
}

class _WhiteListBodyState extends State<WhiteListBody> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  PlatformFile? _pickedFile;

  Future<List<WhiteListEntry>>? _entriesFuture;

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles();

    if (result != null) {
      setState(() {
        _pickedFile = result.files.first;
      });
    }
  }

  Future<List<WhiteListEntry>> fetchEntries() async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/whitelist-entries',
    );
    List<dynamic> data = json.decode(response.body);
    return data.map((item) => WhiteListEntry.fromJson(item)).toList();
  }

  Future<void> submitSearch() async {
    setState(() {
      _entriesFuture = fetchEntries();
    });
  }

  Future<void> submitAdd() async {
    await addEntries();
  }

  Future<void> addEntries() async {
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    String retMessage = loc.successGeneric;
    String retTitle = loc.successGeneric;
    List<String> emailsToAdd = [];
    if (_emailController.text.trim().isNotEmpty) {
      emailsToAdd.add(_emailController.text.trim().toLowerCase());
      if (_pickedFile == null) {
        if (!_formKey.currentState!.validate()) {
          return; // invalid single email, stop here
        }
      }
    }
    if (_pickedFile != null) {
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
            '${loc.labelEntriesTotal}: $totalCount\n${loc.labelEntriesAdded}: $addedCount\n${loc.labelEntriesFailed}: $failedCount\n${loc.labelEntriesExisting}: $existingCount';
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
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          buildSectionTitle('Add/Search ${loc.labelEmailSingle}'),
          Form(
            key: _formKey,
            child: Column(
              children: [
                Text('Add/Search ${loc.labelEmailSingle.toLowerCase()}'),
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
                const SizedBox(height: 15),
                Text(
                  'Add/Search ${loc.labelEmailMany.toLowerCase()} from CSV file',
                ),
                ElevatedButton(onPressed: _pickFile, child: Text("File CSV")),
                if (_pickedFile != null) ...[
                  const SizedBox(height: 10),
                  Text('Selected file: ${_pickedFile!.name}'),
                ],
                const SizedBox(height: 30),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton(
                      onPressed: () {
                        submitAdd();
                      },
                      child: Text(loc.buttonAdd),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton(
                      onPressed: () {
                        submitSearch();
                      },
                      child: Text(loc.buttonSearch),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton(
                      onPressed: () => Navigator.pop(context),
                      child: Text(loc.buttonBack),
                    ),
                  ],
                ),
                const SizedBox(height: 15),
              ],
            ),
          ),
          const SizedBox(height: 30),
          buildSectionTitle(loc.labelCurrentWhiteListEntries),
          Expanded(
            child: _entriesFuture == null
                ? Center(child: Text(loc.labelClickSearchToLoadEntries))
                : FutureBuilder<List<WhiteListEntry>>(
                    future: _entriesFuture,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState == ConnectionState.waiting) {
                        return const Center(child: CircularProgressIndicator());
                      } else if (snapshot.hasError) {
                        if (snapshot.error.toString().startsWith(
                          "GenericNotAuthorized",
                        )) {
                          WidgetsBinding.instance.addPostFrameCallback((_) {
                            goToLoginPage(context);
                          });
                          return Text(loc.errorSessionNotValidOrExpired);
                        }
                        if (snapshot.error.toString().startsWith(
                          "BadRequest",
                        )) {
                          return Text(loc.errorBadRequest);
                        }
                        return Text(loc.errorNetwork);
                      } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                        return Center(child: Text(loc.labelNoEntryFound));
                      }
                      final entries = snapshot.data!;
                      return ListView.separated(
                        itemCount: entries.length,
                        separatorBuilder: (context, index) => const Divider(),
                        itemBuilder: (context, index) {
                          final entry = entries[index];
                          // Semi tabular layout for each entry
                          return ListTile(
                            leading: const CircleAvatar(
                              child: Icon(Icons.person),
                            ),
                            title: Text(
                              entry.email,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            subtitle: Text(
                              '${loc.labelAuthorizedBy.toLowerCase()}: ${entry.createdBy}',
                            ),
                            trailing: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 4,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.blue.shade50,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Text(
                                datetimeAsStringWithoutMicroseconds(
                                  entry.createdAt,
                                ),
                                style: const TextStyle(color: Colors.blue),
                              ),
                            ),
                          );
                        },
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
