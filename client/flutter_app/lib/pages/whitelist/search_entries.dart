// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
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
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/models/general.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';

class WhiteListSearchPage extends StatelessWidget {
  const WhiteListSearchPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuWhiteList, showBackButton: true),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: WhiteListSearchBody()),
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
  final ScrollController _scrollController = ScrollController();
  List<WhiteListEntry> _entries = [];
  String searchCriteria = "";
  int _currentCursor = 0;
  int _entriesCount = 0;
  bool _isLoadingPage = false;
  bool _hasMore = true;
  final int _limit = 100;
  bool _hasSearched = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(() {
      if (_scrollController.position.pixels >=
          _scrollController.position.maxScrollExtent - 200) {
        _loadPage();
      }
    });
  }

  @override
  void dispose() {
    _emailController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _startNewSearch() {
    setState(() {
      _entries = [];
      _entriesCount = 0;
      _currentCursor = 0;
      _hasMore = true;
      _hasSearched = true;
    });
    _loadPage();
  }

  Future<List<WhiteListEntry>> getEntries() async {
    if (searchCriteria == "email" || searchCriteria == "authorizer") {
      if (validateEmail(context, _emailController.text) != null) {
        return [];
      }
    }
    String requestStr;
    if (searchCriteria == "email") {
      final email = Uri.encodeComponent(_emailController.text.trim());
      requestStr = '/whitelist-entries?email=$email';
    } else if (searchCriteria == "authorizer") {
      final auth = Uri.encodeComponent(_emailController.text.trim());
      requestStr =
          '/whitelist-entries?authorizer=$auth&last_seen_id=$_currentCursor&limit=$_limit';
    } else {
      requestStr =
          '/whitelist-entries?last_seen_id=$_currentCursor&limit=$_limit';
    }
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest("get", requestStr);
    final respObj = json.decode(response.body);
    List<dynamic> data = respObj['entries'];
    _currentCursor = respObj['next_cursor'];
    return data.map((item) => WhiteListEntry.fromJson(item)).toList();
  }

  Future<void> _loadPage() async {
    String? retMessage;
    bool newLoginRequired = false;
    final loc = AppLocalizations.of(context)!;
    if (_isLoadingPage || !_hasMore) return;
    setState(() {
      _isLoadingPage = true;
    });
    try {
      List<WhiteListEntry> pageEntries = await getEntries();
      setState(() {
        _entries.addAll(pageEntries);
        if ((pageEntries.length < _limit) || (_currentCursor == 0)) {
          _hasMore = false;
        }
        _entriesCount = _entriesCount + pageEntries.length;
      });
    } on GenericNotAuthorizedException catch (_) {
      retMessage = loc.errorNotAuthorizedDoLogin;
      newLoginRequired = true;
    } on ForbiddenRequestException catch (_) {
      retMessage = loc.errorPermissionsNotValid;
    } on BadRequestException catch (_) {
      retMessage = loc.errorBadRequest;
    } on ServerException catch (_) {
      retMessage = loc.errorServer;
    } catch (e) {
      retMessage = e.toString();
    } finally {
      if (mounted) {
        setState(() {
          _isLoadingPage = false;
        });
      }
      if (retMessage != null && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(retMessage),
            duration: const Duration(seconds: 4),
          ),
        );
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
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Form(
                key: _formKey,
                child: Column(
                  children: [
                    TextFormField(
                      keyboardType: TextInputType.emailAddress,
                      controller: _emailController,
                      decoration: InputDecoration(labelText: "Email"),
                      validator: (value) => validateEmail(context, value),
                    ),
                  ],
                ),
              ),
              buildSectionTitle(loc.buttonSearch),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ElevatedButton.icon(
                    onPressed: _isLoadingPage
                        ? null
                        : () {
                            searchCriteria = "email";
                            _startNewSearch();
                          },
                    label: Text("by Email"),
                  ),
                  const SizedBox(width: 25),
                  ElevatedButton.icon(
                    onPressed: _isLoadingPage
                        ? null
                        : () {
                            searchCriteria = "";
                            _startNewSearch();
                          },
                    label: Text(loc.labelAllSm),
                  ),
                ],
              ),
              SizedBox(height: 10),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (authClient.isAdmin())
                    ElevatedButton.icon(
                      onPressed: _isLoadingPage
                          ? null
                          : () {
                              searchCriteria = "authorizer";
                              _startNewSearch();
                            },
                      label: Text("by Authorizer"),
                    ),
                ],
              ),
            ],
          ),
        ),
        // Results area
        Expanded(
          child: !_hasSearched
              ? Center(child: Text(loc.labelClickSearchToLoadEntries))
              : _entries.isEmpty && _isLoadingPage
              ? Center(child: CircularProgressIndicator())
              : _entries.isEmpty
              ? Center(child: Text(loc.errorNoEntryFound))
              : ListView.separated(
                  controller: _scrollController,
                  itemCount: _entriesCount + (_hasMore ? 1 : 0),
                  separatorBuilder: (_, _) => const Divider(),
                  itemBuilder: (context, index) {
                    if (index < _entriesCount) {
                      final userIsReg = _entries[index].userIsRegistered;
                      return ListTile(
                        title: Text(_entries[index].email),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              "${loc.whiteListEntryAuthorizedBy}: ${_entries[index].createdBy}",
                            ),
                            if (!userIsReg)
                              Text(
                                "${loc.whiteListEntryPendingType}: ${_entries[index].registrationType}",
                              ),
                            if (!userIsReg)
                              Text(
                                "${loc.whiteListEntryPendingRole}: ${_entries[index].registrationRole}",
                              ),
                            Text(
                              "${loc.whiteListEntryUserIsRegistered}: ${_entries[index].userIsRegistered ? 'yes' : 'no'}",
                            ),
                          ],
                        ),
                        trailing: Text(
                          datetimeAsStringWithoutMicroseconds(
                            _entries[index].createdAt,
                            includeTimezone: false,
                          ),
                        ),
                      );
                    } else {
                      // Loading spinner at the bottom of the list
                      return const Padding(
                        padding: EdgeInsets.symmetric(vertical: 32.0),
                        child: Center(child: CircularProgressIndicator()),
                      );
                    }
                  },
                ),
        ),
      ],
    );
  }
}
