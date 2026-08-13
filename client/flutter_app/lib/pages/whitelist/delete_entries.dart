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
import 'package:quidalert_flutter/utils/validators.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';

class WhiteListDeletePage extends StatelessWidget {
  const WhiteListDeletePage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuWhiteList, showBackButton: true),
      body: SafeArea(top: false, child: WhiteListDeleteBody()),
    );
  }
}

class WhiteListDeleteBody extends StatefulWidget {
  const WhiteListDeleteBody({super.key});

  @override
  State<WhiteListDeleteBody> createState() => _WhiteListDeleteBodyState();
}

class _WhiteListDeleteBodyState extends State<WhiteListDeleteBody> {
  final _formDelByEmailKey = GlobalKey<FormState>();
  final _formDelMyEntriesKey = GlobalKey<FormState>();
  final _formDelAllEntriesKey = GlobalKey<FormState>();
  final ScrollController _scrollController = ScrollController();
  final _emailController = TextEditingController();
  final _confirmation1Controller = TextEditingController();
  final _confirmation2Controller = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _confirmation1Controller.dispose();
    _confirmation2Controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void submitDeleteSingleEntry() {
    if (!_formDelByEmailKey.currentState!.validate()) {
      return;
    }
    deleteSingleEntry();
  }

  void submitDeleteMyEntries() {
    if (!_formDelMyEntriesKey.currentState!.validate()) {
      return;
    }
    final loc = AppLocalizations.of(context)!;
    showLoadingDialog(context, loc.labelWaitPlease);
    deleteMyEntries().whenComplete(() {
      if (mounted) {
        Navigator.pop(context);
      }
    });
  }

  void submitDeleteAllEntries() {
    if (!_formDelAllEntriesKey.currentState!.validate()) {
      return;
    }
    final loc = AppLocalizations.of(context)!;
    showLoadingDialog(context, loc.labelWaitPlease);
    deleteAllEntries().whenComplete(() {
      if (mounted) {
        Navigator.pop(context);
      }
    });
  }

  Future<void> deleteSingleEntry() async {
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    String retMessage = loc.successGeneric;
    String retTitle = loc.successGeneric;
    bool newLoginRequired = false;
    if (!_formDelByEmailKey.currentState!.validate()) {
      return;
    }
    String email = _emailController.text.trim().toLowerCase();
    try {
      final response = await authClient.doProtectedApiRequest(
        "delete",
        '/whitelist-entries/single?email=${Uri.encodeComponent(email)}',
      );
      final Map<String, dynamic> respObj = json.decode(response.body);
      final int deletedCount = respObj['deleted_count'];
      final int totalCount = respObj['total_count'];
      if (totalCount > deletedCount) {
        retTitle = loc.errorError;
        retMessage = loc.errorError;
      } else if (deletedCount == 0) {
        retTitle = loc.errorError;
        retMessage = loc.errorEmailNotFound;
      } else {
        retTitle = loc.successGeneric;
        retMessage = '${loc.entriesDeleted}: $deletedCount';
      }
    } on GenericNotAuthorizedException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorNotAuthorizedDoLogin;
      newLoginRequired = true;
    } on ForbiddenRequestException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorPermissionsNotValid;
    } on BadRequestException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorBadRequest;
    } on ServerException catch (_) {
      retTitle = loc.errorError;
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
          goToLoginPage(context);
        }
      }
    }
    return;
  }

  Future<void> deleteMyEntries() async {
    await deleteEntries('/whitelist-entries/mine');
  }

  Future<void> deleteAllEntries() async {
    await deleteEntries('/whitelist-entries/all');
  }

  Future<void> deleteEntries(String relativeUrl) async {
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    String retMessage = loc.successGeneric;
    String retTitle = loc.successGeneric;
    bool newLoginRequired = false;
    try {
      final response = await authClient.doProtectedApiRequest(
        "delete",
        relativeUrl,
      );
      final Map<String, dynamic> respObj = json.decode(response.body);
      retMessage =
          '${loc.entriesDeleted}: ${respObj['deleted_count']}\n${loc.entriesTotal}: ${respObj['total_count']}';
      retTitle = loc.successGeneric;
    } on GenericNotAuthorizedException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorNotAuthorizedDoLogin;
      newLoginRequired = true;
    } on ForbiddenRequestException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorPermissionsNotValid;
    } on BadRequestException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorBadRequest;
    } on ServerException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorServer;
    } catch (e) {
      retTitle = loc.errorError;
      retMessage = e.toString();
    } finally {
      if (mounted) {
        setState(() {
          if (relativeUrl.contains('/mine')) {
            _confirmation1Controller.text = "";
          } else if (relativeUrl.contains('/all')) {
            _confirmation2Controller.text = "";
          }
        });
        await showSimpleAlertDialog(context, retTitle, retMessage);
      }
      if (newLoginRequired) {
        if (mounted) {
          goToLoginPage(context);
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authClient = context.read<AuthClient>();
    final loc = AppLocalizations.of(context)!;
    return Scrollbar(
      thumbVisibility: true,
      controller: _scrollController,
      child: SingleChildScrollView(
        controller: _scrollController,
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            buildSectionTitle(
              '${loc.buttonDelete} ${loc.entriesSingle.toLowerCase()} (by email)',
            ),
            Form(
              key: _formDelByEmailKey,
              child: Column(
                children: [
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
                          submitDeleteSingleEntry();
                        },
                        child: Text(loc.buttonDelete),
                      ),
                      const SizedBox(width: 25),
                      ElevatedButton(
                        onPressed: () => Navigator.pop(context),
                        child: Text(loc.buttonBack),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            SizedBox(height: 15),
            Divider(thickness: 0.25),
            SizedBox(height: 15),
            Form(
              key: _formDelMyEntriesKey,
              child: Column(
                children: [
                  buildSectionTitle(
                    '${loc.buttonDelete} ${loc.entriesAuthorizedByMe.toLowerCase()}',
                  ),
                  const SizedBox(height: 10),
                  TextFormField(
                    controller: _confirmation1Controller,
                    decoration: InputDecoration(
                      labelText: loc.labelTypeDeleteToConfirm,
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) {
                      return validateDeleteConfirmation(context, value);
                    },
                  ),
                  const SizedBox(height: 35),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      ElevatedButton(
                        onPressed: () {
                          submitDeleteMyEntries();
                        },
                        child: Text(loc.buttonDelete),
                      ),
                      const SizedBox(width: 25),
                      ElevatedButton(
                        onPressed: () => Navigator.pop(context),
                        child: Text(loc.buttonBack),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            SizedBox(height: 15),
            Divider(thickness: 0.25),
            SizedBox(height: 15),
            if (authClient.isAdmin()) ...[
              Form(
                key: _formDelAllEntriesKey,
                child: Column(
                  children: [
                    buildSectionTitle(
                      '${loc.buttonDelete} ${loc.entriesAll.toLowerCase()}',
                    ),
                    TextFormField(
                      controller: _confirmation2Controller,
                      decoration: InputDecoration(
                        labelText: loc.labelTypeDeleteToConfirm,
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) {
                        return validateDeleteConfirmation(context, value);
                      },
                    ),
                    const SizedBox(height: 35),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        ElevatedButton(
                          onPressed: () {
                            submitDeleteAllEntries();
                          },
                          child: Text(loc.buttonDelete),
                        ),
                        const SizedBox(width: 25),
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
          ],
        ),
      ),
    );
  }
}
