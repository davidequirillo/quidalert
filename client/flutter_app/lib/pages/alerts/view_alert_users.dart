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

class AlertUsersPage extends StatelessWidget {
  const AlertUsersPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.alertAlertedUsers, showBackButton: true),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: AlertUsersBody()),
    );
  }
}

class AlertUsersBody extends StatelessWidget {
  const AlertUsersBody({super.key});

  Future<AlertWithUsers> _getAlertUsers(BuildContext context, String id) async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/alerts/$id/users',
    );
    final Map<String, dynamic>? respObj = json.decode(response.body);
    if (respObj == null || respObj.isEmpty) {
      throw NotFoundException();
    }
    final alertWithUsers = AlertWithUsers.fromJson(respObj);
    return alertWithUsers;
  }

  Future<void> _showUserDetails(
    BuildContext context,
    AlertWithUsers alertWithUsers,
    String userId,
  ) async {
    final loc = AppLocalizations.of(context)!;
    final User user = alertWithUsers.users.firstWhere(
      (u) => (u.id == userId),
      orElse: () => throw NotFoundException(),
    );
    String userDetailsStr = "${user.firstname} ${user.surname}\n${user.email}";
    userDetailsStr += "\n";
    userDetailsStr += "\n${loc.userBirthdate}: ${user.birthDate}";
    userDetailsStr += "\n${loc.userPhoneNumber}: ${user.phone}";
    userDetailsStr += "\n";
    userDetailsStr += "\n${user.street}";
    userDetailsStr += "\n${user.postalCode}, ${user.city}";
    userDetailsStr += "\n${user.province}";
    userDetailsStr += "\n${user.country}";

    if (!context.mounted) return;
    showSimpleAlertDialog(context, loc.labelDetails, userDetailsStr);
  }

  @override
  Widget build(BuildContext context) {
    final id = ModalRoute.of(context)!.settings.arguments as String;
    final loc = AppLocalizations.of(context)!;
    return FutureBuilder<AlertWithUsers>(
      future: _getAlertUsers(context, id),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          debugPrint("Error fetching alert users: ${snapshot.error}");
          final exceptionName = snapshot.error.runtimeType.toString();
          final locAttribute = "exception$exceptionName".replaceAll(
            "Exception",
            "",
          );
          final errorMessage = loc.getString(locAttribute) ?? loc.errorGeneric;
          if (snapshot.error.toString().startsWith("GenericNotAuthorized")) {
            goToLoginPagePostFrameCallback(context);
          }
          return Center(child: Text(errorMessage));
        }
        if (snapshot.hasData) {
          final alertWithUsers = snapshot.data!;
          return alertUsersList(context, alertWithUsers);
        }
        return Center(child: Text(loc.errorGeneric));
      },
    );
  }

  Widget alertUsersList(BuildContext context, AlertWithUsers alertWithUsers) {
    final loc = AppLocalizations.of(context)!;
    return ListView.builder(
      itemCount: alertWithUsers.users.length,
      itemBuilder: (context, index) {
        final user = alertWithUsers.users[index];
        final alertedUser = alertWithUsers.votesMap[user.id];
        final vote = alertedUser?.vote ?? 0;
        final isManager = alertedUser?.isManager ?? false;
        final isManagerText = isManager ? "(${loc.alertedUserManager})" : "";
        final closingVote = alertedUser?.closingVote ?? 0;
        final closingVoteText = closingVote > 0
            ? "${loc.alertedUserClosingVote}: $closingVote"
            : "";
        return ListTile(
          title: Text("${user.firstname} ${user.surname} $isManagerText"),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text("${user.email}, ${user.phone}"),
              Text(
                "${loc.alertedUserVote}: $vote${closingVoteText.isNotEmpty ? ', $closingVoteText' : ''}",
              ),
            ],
          ),
          leading: Icon(Icons.person_outline),
          onTap: () => {_showUserDetails(context, alertWithUsers, user.id)},
        );
      },
    );
  }
}
