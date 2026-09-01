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
      appBar: CAppBar(title: loc.menuWhitelist, showBackButton: true),
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
  final ScrollController _scrollController = ScrollController();
  final _emailController = TextEditingController();
  final _confirmationController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _confirmationController.dispose();
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
    deleteEntries().whenComplete(() {
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
    String email = _emailController.text.trim().toLowerCase();
    try {
      final response = await authClient.doProtectedApiRequest(
        "delete",
        '/whitelist-entries/single?email=${Uri.encodeComponent(email)}',
      );
      final Map<String, dynamic> respObj = json.decode(response.body);
      final int deletedCount = respObj['deleted_count'];
      retTitle = loc.successGeneric;
      retMessage = '${loc.entriesDeleted}: $deletedCount';
    } on GenericNotAuthorizedException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorNotAuthorizedDoLogin;
      newLoginRequired = true;
    } on ForbiddenRequestException catch (e) {
      retTitle = loc.errorError;
      if (e.toString().contains("registered user")) {
        retMessage = loc.errorWhitelistCannotDelForRegUsers;
      } else {
        retMessage = loc.errorPermissionsNotValid;
      }
    } on NotFoundException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorEmailNotFound;
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
          goToLoginPagePostFrameCallback(context);
        }
      }
    }
    return;
  }

  Future<void> deleteEntries() async {
    // Note: This function deletes "all" whitelist entries
    // owned by the current user (not "all" in absolute terms).
    final relativeUrl = '/whitelist-entries/all';
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
          _confirmationController.text = "";
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
    return Scrollbar(
      thumbVisibility: true,
      controller: _scrollController,
      child: SingleChildScrollView(
        controller: _scrollController,
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Text(loc.sectionWhitelistDeleteInfo),
            SizedBox(height: 20),
            buildSectionTitle(loc.sectionWhitelistDeleteSingleEntry),
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
                  buildSectionTitle(loc.sectionWhitelistDeleteAllOwnedEntry),
                  const SizedBox(height: 10),
                  TextFormField(
                    controller: _confirmationController,
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
          ],
        ),
      ),
    );
  }
}
