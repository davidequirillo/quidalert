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

class WhiteListSearchPage extends StatelessWidget {
  const WhiteListSearchPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuWhiteList, showBackButton: true),
      drawer: const CAppDrawer(),
      body: WhiteListSearchBody(),
    );
  }
}

class WhiteListSearchBody extends StatefulWidget {
  const WhiteListSearchBody({super.key});

  @override
  State<WhiteListSearchBody> createState() => _WhiteListSearchBodyState();
}

class _WhiteListSearchBodyState extends State<WhiteListSearchBody> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  Future<List<WhiteListEntry>>? _entriesFuture;

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  void searchBy(String mode) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );
    Function func;
    switch (mode) {
      case "email":
        func = getByEmail;
        break;
      case "all":
        func = getAll;
        break;
      case "creator":
        func = getByCreator;
        break;
      default:
        func = getAll;
    }
    setState(() {
      _entriesFuture = func().whenComplete(() {
        if (mounted) {
          Navigator.pop(context);
        }
      });
    });
  }

  Future<List<WhiteListEntry>> getByEmail() async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/whitelist-entries?email=${Uri.encodeComponent(_emailController.text)}',
    );
    final respObj = json.decode(response.body);
    List<dynamic> data = respObj['entries'];
    // int offset = respObj['offset'];
    // int size = respObj['size'];
    return data.map((item) => WhiteListEntry.fromJson(item)).toList();
  }

  Future<List<WhiteListEntry>> getByCreator() async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/whitelist-entries?authorized-by=${Uri.encodeComponent(_emailController.text)}',
    );
    final respObj = json.decode(response.body);
    List<dynamic> data = respObj['entries'];
    // int offset = respObj['offset'];
    // int size = respObj['size'];
    return data.map((item) => WhiteListEntry.fromJson(item)).toList();
  }

  Future<List<WhiteListEntry>> getAll() async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/whitelist-entries',
    );
    final respObj = json.decode(response.body);
    List<dynamic> data = respObj['entries'];
    // int offset = respObj['offset'];
    // int size = respObj['size'];
    return data.map((item) => WhiteListEntry.fromJson(item)).toList();
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          Form(
            key: _formKey,
            child: Column(
              children: [
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
                buildSectionTitle(loc.buttonSearch),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton(
                      onPressed: () {
                        searchBy("email");
                      },
                      child: Text("by Email"),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton(
                      onPressed: () {
                        searchBy("all");
                      },
                      child: Text(loc.labelAllMasculinePlural),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton(
                      onPressed: () {
                        searchBy("creator");
                      },
                      child: Text("by Me"),
                    ),
                  ],
                ),
                const SizedBox(height: 25),
                ElevatedButton(
                  onPressed: () => Navigator.pop(context),
                  child: Text(loc.buttonBack),
                ),
              ],
            ),
          ),
          const SizedBox(height: 30),
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
