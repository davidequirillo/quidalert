// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/utils/validator.dart';
import 'package:quidalert_flutter/widgets/common.dart';
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
  final ScrollController _scrollController = ScrollController();
  List<WhiteListEntry> _entries = [];
  String searchCriteria = "";
  int _entriesCount = 0;
  int _currentPage = 0;
  bool _isLoadingPage = false;
  bool _hasMore = true;
  final int _limit = 10;
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

  void _startNewSearch() {
    setState(() {
      _entries = [];
      _entriesCount = 0;
      _currentPage = 0;
      _hasMore = true;
      _hasSearched = true;
    });
    _loadPage();
  }

  @override
  void dispose() {
    _emailController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<List<WhiteListEntry>> getEntries() async {
    if (searchCriteria == "email" || searchCriteria == "authorizer") {
      if (!_formKey.currentState!.validate()) {
        return [];
      }
    }
    String requestStr;
    if (searchCriteria == "email") {
      final email = Uri.encodeComponent(_emailController.text.trim());
      requestStr =
          '/whitelist-entries?email=$email&offset=${_currentPage * _limit}&limit=$_limit';
    } else if (searchCriteria == "authorizer") {
      final auth = Uri.encodeComponent(_emailController.text.trim());
      requestStr =
          '/whitelist-entries?authorizer=$auth&offset=${_currentPage * _limit}&limit=$_limit';
    } else if (searchCriteria == "me") {
      final auth = Uri.encodeComponent(
        context.read<AuthClient>().userInfo['email'],
      );
      requestStr =
          '/whitelist-entries?authorizer=$auth&offset=${_currentPage * _limit}&limit=$_limit';
    } else {
      requestStr =
          '/whitelist-entries?offset=${_currentPage * _limit}&limit=$_limit';
    }
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest("get", requestStr);
    final respObj = json.decode(response.body);
    List<dynamic> data = respObj['entries'];
    return data.map((item) => WhiteListEntry.fromJson(item)).toList();
  }

  Future<void> _loadPage() async {
    String? retMessage;
    final loc = AppLocalizations.of(context)!;
    if (_isLoadingPage || !_hasMore) return;
    setState(() {
      _isLoadingPage = true;
    });
    try {
      List<WhiteListEntry> pageEntries = await getEntries();
      setState(() {
        _entries.addAll(pageEntries);
        _currentPage++;
        if (pageEntries.length < _limit) {
          _hasMore = false;
        }
        _entriesCount = _entriesCount + pageEntries.length;
      });
    } on GenericNotAuthorizedException catch (_) {
      retMessage = loc.errorNotAuthorizedDoLogin;
    } on BadRequestException catch (_) {
      retMessage = loc.errorBadRequest;
    } on NetworkException catch (_) {
      retMessage = loc.errorNetwork;
    } catch (e) {
      retMessage = e.toString();
    } finally {
      if (retMessage != null && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(retMessage),
            duration: const Duration(seconds: 4),
          ),
        );
      }
      setState(() {
        _isLoadingPage = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    return Column(
      children: [
        // Search area
        Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              Form(
                key: _formKey,
                child: Column(
                  children: [
                    TextFormField(
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
                    icon: const Icon(Icons.search),
                    label: Text("by Email"),
                  ),
                  const SizedBox(width: 25),
                  ElevatedButton.icon(
                    onPressed: _isLoadingPage
                        ? null
                        : () {
                            searchCriteria = "me";
                            _startNewSearch();
                          },
                    icon: const Icon(Icons.search),
                    label: Text("by Me"),
                  ),
                  if (authClient.isAdmin()) const SizedBox(width: 25),
                  if (authClient.isAdmin())
                    ElevatedButton(
                      onPressed: _isLoadingPage
                          ? null
                          : () {
                              searchCriteria = "authorizer";
                              _startNewSearch();
                            },
                      child: Text("by Authorizer"),
                    ),
                  if (authClient.isAdmin()) const SizedBox(width: 25),
                  if (authClient.isAdmin())
                    ElevatedButton.icon(
                      onPressed: _isLoadingPage
                          ? null
                          : () {
                              searchCriteria = "";
                              _startNewSearch();
                            },
                      icon: const Icon(Icons.search),
                      label: Text(loc.labelAllMasculinePlural),
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
              : ListView.separated(
                  controller: _scrollController,
                  itemCount: _entriesCount + (_hasMore ? 1 : 0),
                  separatorBuilder: (_, _) => const Divider(),
                  itemBuilder: (context, index) {
                    if (index < _entriesCount) {
                      return ListTile(
                        title: Text(_entries[index].email),
                        subtitle: Text(
                          "Authorized by: ${_entries[index].createdBy}",
                        ),
                        trailing: Text(
                          datetimeAsStringWithoutMicroseconds(
                            _entries[index].createdAt,
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
