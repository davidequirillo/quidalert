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
import 'package:quidalert_flutter/models/general.dart';
import 'package:quidalert_flutter/utils/strings.dart';

class UsersSearchResultsPage extends StatelessWidget {
  const UsersSearchResultsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuUsers, showBackButton: true),
      drawer: const CAppDrawer(),
      body: UsersSearchResultsBody(),
    );
  }
}

class UsersSearchResultsBody extends StatefulWidget {
  const UsersSearchResultsBody({super.key});

  @override
  State<UsersSearchResultsBody> createState() => _UsersSearchResultsBodyState();
}

class _UsersSearchResultsBodyState extends State<UsersSearchResultsBody> {
  List<UserSmall> _users = [];
  int _usersCount = 0;
  String? _currentCursor;
  bool _isLoadingPage = false;
  bool _hasMore = true;
  final int _limit = 100;
  bool _hasSearched = false;
  final ScrollController _scrollController = ScrollController();

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
    _scrollController.dispose();
    super.dispose();
  }

  void _startNewSearch() {
    setState(() {
      _users = [];
      _usersCount = 0;
      _currentCursor = null;
      _hasMore = true;
      _hasSearched = true;
    });
    _loadPage();
  }

  Future<List<UserSmall>> getUsers() async {
    final args = ModalRoute.of(context)!.settings.arguments;
    if (args is List<String>) {
      return await getUsersByEmails(args);
    } else if (args is Map<String, String?>) {
      return await getUsersByFields(args);
    } else {
      throw Exception("Invalid arguments for search results page");
    }
  }

  Future<List<UserSmall>> getUsersByFields(Map<String, String?> args) async {
    String queryStr = args.entries
        .where((entry) => entry.value != null && entry.value!.isNotEmpty)
        .map((entry) => "${entry.key}=${Uri.encodeComponent(entry.value!)}")
        .join("&");
    final String currCurs = (_currentCursor != null) ? _currentCursor! : '';
    final String offsetStr = 'last_seen_id=$currCurs&limit=$_limit';
    if (queryStr.isEmpty) {
      queryStr = offsetStr;
    } else {
      queryStr = '$queryStr&$offsetStr';
    }
    final requestStr = '/users?$queryStr';
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest("get", requestStr);
    final respObj = json.decode(response.body);
    List<dynamic> data = respObj['users'];
    _currentCursor = respObj['next_cursor'];
    return data.map((item) => UserSmall.fromJson(item)).toList();
  }

  Future<List<UserSmall>> getUsersByEmails(List<String> emails) async {
    final String currCurs = (_currentCursor != null) ? _currentCursor! : '';
    final String offsetStr = 'last_seen_id=$currCurs&limit=$_limit';
    final requestStr = '/users/get-by-emails?$offsetStr';
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "post",
      requestStr,
      body: {"emails": emails},
    );
    final respObj = json.decode(response.body);
    List<dynamic> data = respObj['users'];
    _currentCursor = respObj['next_cursor'];
    return data.map((item) => UserSmall.fromJson(item)).toList();
  }

  Future<void> _loadPage() async {
    String? retMessage;
    final loc = AppLocalizations.of(context)!;
    if (_isLoadingPage || !_hasMore) return;
    setState(() {
      _isLoadingPage = true;
    });
    try {
      List<UserSmall> pageUsers = await getUsers();
      setState(() {
        _users.addAll(pageUsers);
        if ((pageUsers.length < _limit) || (_currentCursor == null)) {
          _hasMore = false;
        }
        _usersCount = _usersCount + pageUsers.length;
      });
    } on GenericNotAuthorizedException catch (_) {
      retMessage = loc.errorNotAuthorizedDoLogin;
      if (mounted) {
        goToLoginPagePostFrameCallback(context);
      }
    } on ForbiddenRequestException catch (_) {
      retMessage = loc.errorPermissionsNotValid;
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
    if (mounted && !_hasSearched) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _startNewSearch();
      });
    }
    final loc = AppLocalizations.of(context)!;
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
    return SafeArea(
      top: false,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.start,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "Query -> $searchStr",
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                SizedBox(height: 10),
                ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pushNamed(
                      context,
                      '/accounts/users/promote-results',
                      arguments: args,
                    );
                  },
                  icon: Icon(Icons.edit),
                  label: Text(
                    '${loc.buttonPromote}/${loc.buttonModify.toLowerCase()} ${loc.labelQueryUsers.toLowerCase()}',
                  ),
                ),
              ],
            ),
          ),
          Divider(),
          // Query results area
          Expanded(
            child: !_hasSearched
                ? Center(child: Text(loc.labelWaitPlease))
                : _users.isEmpty && _isLoadingPage
                ? Center(child: CircularProgressIndicator())
                : _users.isEmpty
                ? Center(child: Text(loc.errorNoEntryFound))
                : ListView.separated(
                    controller: _scrollController,
                    itemCount: _usersCount + (_hasMore ? 1 : 0),
                    separatorBuilder: (_, _) => const Divider(),
                    itemBuilder: (context, index) {
                      if (index < _usersCount) {
                        String fname = _users[index].firstname;
                        String sname = _users[index].surname;
                        String subtitle =
                            '${loc.labelAuthorizedBy}: ${_users[index].authorizedBy ?? "N/A"}';
                        subtitle +=
                            '\n${_users[index].type},'
                            ' ${_users[index].role},'
                            ' ${_users[index].status}';
                        return ListTile(
                          title: Text('${_users[index].email} ($fname $sname)'),
                          subtitle: Text(subtitle),
                          trailing: Text(
                            (_users[index].authorizedAt != null)
                                ? datetimeAsStringWithoutMicroseconds(
                                    _users[index].authorizedAt!,
                                  )
                                : "N/A",
                          ),
                          onTap: () => {
                            Navigator.pushNamed(
                              context,
                              '/accounts/users/view-user-details',
                              arguments: _users[index].id,
                            ),
                          },
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
      ),
    );
  }
}
