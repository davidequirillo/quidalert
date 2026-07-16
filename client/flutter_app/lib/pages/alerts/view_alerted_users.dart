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

class AlertedUsersBody extends StatelessWidget {
  const AlertedUsersBody({super.key});

  Future<List<AlertedUserWithInfo>> _getAlertedUsers(
    BuildContext context,
    String id,
  ) async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/alerts/$id/alerted-users',
    );
    final Map<String, dynamic>? respObj = json.decode(response.body);
    if (respObj == null || respObj.isEmpty) {
      throw NotFoundException();
    }
    final alertedUsers = (respObj as List)
        .map((userJson) => AlertedUserWithInfo.fromJson(userJson))
        .toList();
    return alertedUsers;
  }

  Future<void> _showUserDetails(
    BuildContext context,
    AlertedUserWithInfo alertedUser,
  ) async {
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
    if (!context.mounted) return;
    showSimpleAlertDialog(context, loc.labelDetails, userDetailsStr);
  }

  @override
  Widget build(BuildContext context) {
    final id = ModalRoute.of(context)!.settings.arguments as String;
    final loc = AppLocalizations.of(context)!;
    return FutureBuilder<List<AlertedUserWithInfo>>(
      future: _getAlertedUsers(context, id),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          debugPrint("Error fetching alerted users: ${snapshot.error}");
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
          final alertedUsers = snapshot.data!;
          return alertedUsersList(context, alertedUsers);
        }
        return Center(child: Text(loc.errorGeneric));
      },
    );
  }

  Widget alertedUsersList(
    BuildContext context,
    List<AlertedUserWithInfo> alertedUsers,
  ) {
    final loc = AppLocalizations.of(context)!;
    return ListView.builder(
      itemCount: alertedUsers.length,
      itemBuilder: (context, index) {
        final alertedUser = alertedUsers[index];
        String name =
            "${alertedUser.user.firstname} ${alertedUser.user.surname}";
        if (alertedUser.isManager) {
          name = "$name (${loc.alertChief})";
        }
        String voteStr = "";
        voteStr = "${loc.alertedUserVote}: ${alertedUser.vote}";
        if (alertedUser.isManager) {
          voteStr +=
              " (${loc.alertedUserClosingVote}) ${alertedUser.closingVote}";
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
          onTap: () => {_showUserDetails(context, alertedUser)},
        );
      },
    );
  }
}
