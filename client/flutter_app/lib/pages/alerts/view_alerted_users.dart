// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/l10n/app_localizations_extension.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/models/general.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';

class AlertedUsersPage extends StatelessWidget {
  const AlertedUsersPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.alertAlertedUsers, showBackButton: true),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: AlertedUsersBody()),
    );
  }
}

class AlertedUsersBody extends StatefulWidget {
  const AlertedUsersBody({super.key});

  @override
  State<AlertedUsersBody> createState() => _AlertedUsersBodyState();
}

class _AlertedUsersBodyState extends State<AlertedUsersBody> {
  List<AlertedUser> _alertedUsers = [];
  int _alertedUsersCount = 0;
  int? _currentCursor;
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
      _alertedUsers = [];
      _alertedUsersCount = 0;
      _currentCursor = null;
      _hasMore = true;
      _hasSearched = true;
    });
    _loadPage();
  }

  Future<void> _showUserDetails(AlertedUser alertedUser) async {
    final loc = AppLocalizations.of(context)!;
    String userDetailsStr =
        "${alertedUser.user.firstname} ${alertedUser.user.surname}\n${alertedUser.user.email}";
    userDetailsStr += "\n";
    userDetailsStr += "\n${loc.userBirthdate}: ${alertedUser.user.birthDate}";
    userDetailsStr += "\n${loc.userPhoneNumber}: ${alertedUser.user.phone}";
    userDetailsStr += "\n";
    userDetailsStr += "\n${alertedUser.user.street}";
    userDetailsStr +=
        "\n${alertedUser.user.postalCode}, ${alertedUser.user.city}";
    userDetailsStr += "\n${alertedUser.user.province}";
    userDetailsStr += "\n${alertedUser.user.country}";
    userDetailsStr += "\n";
    userDetailsStr += "\n${loc.userStatus}: ${alertedUser.user.status}";
    userDetailsStr +=
        "\n${loc.userReliabilityScore}: ${alertedUser.user.reliabilityScore}";
    userDetailsStr += "\n";
    userDetailsStr += "\n${loc.userRole}: ${alertedUser.user.role}";
    if (!context.mounted) return;
    showSimpleAlertDialog(context, loc.labelDetails, userDetailsStr);
  }

  Future<List<AlertedUser>> _getAlertedUsers() async {
    final authClient = context.read<AuthClient>();
    final id = ModalRoute.of(context)!.settings.arguments as String;
    final String offsetStr = (_currentCursor != null)
        ? "offset=$_currentCursor&limit=$_limit"
        : "offset=0&limit=$_limit";
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/alerts/$id/alerted-users?$offsetStr',
    );
    final Map<String, dynamic>? respObj = json.decode(response.body);
    if (respObj == null || respObj.isEmpty) {
      throw NotFoundException();
    }
    final alertedUsers = (respObj['alerted_users'] as List)
        .map((userJson) => AlertedUser.fromJson(userJson))
        .toList();
    return alertedUsers;
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
      List<AlertedUser> pageAlertedUsers = await _getAlertedUsers();
      setState(() {
        _alertedUsers.addAll(pageAlertedUsers);
        if ((pageAlertedUsers.length < _limit) || (_currentCursor == null)) {
          _hasMore = false;
        }
        _alertedUsersCount = _alertedUsersCount + pageAlertedUsers.length;
      });
    } catch (e) {
      final exceptionName = e.runtimeType.toString();
      if (exceptionName == "GenericNotAuthorizedException") {
        newLoginRequired = true;
      }
      final locAttribute = "exception$exceptionName".replaceAll(
        "Exception",
        "",
      );
      retMessage = loc.getString(locAttribute) ?? loc.errorGeneric;
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
    if (mounted && !_hasSearched) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _startNewSearch();
      });
    }
    final loc = AppLocalizations.of(context)!;
    return Column(
      children: [
        Expanded(
          child: !_hasSearched
              ? Center(child: Text(loc.labelWaitPlease))
              : _alertedUsers.isEmpty && _isLoadingPage
              ? Center(child: CircularProgressIndicator())
              : _alertedUsers.isEmpty
              ? Center(child: Text(loc.errorNoEntryFound))
              : ListView.separated(
                  controller: _scrollController,
                  itemCount: _alertedUsersCount + (_hasMore ? 1 : 0),
                  separatorBuilder: (_, _) => const Divider(),
                  itemBuilder: (context, index) {
                    if (index < _alertedUsersCount) {
                      final alertedUser = _alertedUsers[index];
                      return buildAlertedUserTile(alertedUser);
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

  Widget buildAlertedUserTile(AlertedUser alertedUser) {
    final loc = AppLocalizations.of(context)!;
    String name = "${alertedUser.user.firstname} ${alertedUser.user.surname}";
    if (alertedUser.isManager) {
      name = "$name (${loc.alertChief})";
    }
    String voteStr = "";
    voteStr = "${loc.alertedUserVote}: ${alertedUser.vote}";
    if (alertedUser.isManager) {
      voteStr += ", ${loc.alertedUserClosingVote}: ${alertedUser.closingVote}";
    }
    return ListTile(
      title: Text(name),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('${alertedUser.user.email}, ${alertedUser.user.phone}'),
          Text(voteStr),
        ],
      ),
      leading: Icon(Icons.person),
      trailing: Text("${alertedUser.distance.toStringAsFixed(3)} km"),
      onTap: () => {_showUserDetails(alertedUser)},
    );
  }
}
