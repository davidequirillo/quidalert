// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025-2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/l10n/app_localizations_extension.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';

class ViewAlertRolesPage extends StatelessWidget {
  const ViewAlertRolesPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.alertAlertedSpecialists, showBackButton: true),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: ViewAlertRolesBody()),
    );
  }
}

class ViewAlertRolesBody extends StatelessWidget {
  const ViewAlertRolesBody({super.key});

  Future<List<Map<String, String>>> _getAlertRoles(
    BuildContext context,
    int alertId,
  ) async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/alerts/$alertId/roles',
    );
    final Map<String, dynamic>? respObj = json.decode(response.body);
    if (respObj == null || !respObj.containsKey("alert_roles")) {
      throw NotFoundException();
    }
    if (respObj["alert_roles"] == null) {
      throw NotFoundException();
    }
    if (respObj["alert_roles"] is! List) {
      throw FormatException(
        "Invalid response format: 'alert_roles' is not a list",
      );
    }
    final alertRoles = (respObj["alert_roles"]! as List)
        .map(
          (e) => {
            "role": e["role"] as String,
            "specialists_count": (e["specialists_count"] ?? 0).toString(),
          },
        )
        .toList();
    return alertRoles;
  }

  @override
  Widget build(BuildContext context) {
    final alertId = ModalRoute.of(context)!.settings.arguments as int;
    final loc = AppLocalizations.of(context)!;
    return FutureBuilder<List<Map<String, String>>>(
      future: _getAlertRoles(context, alertId),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          debugPrint("Error fetching alert roles: ${snapshot.error}");
          final exceptionName = snapshot.error.runtimeType.toString();
          final errorMessage =
              loc.getExceptionString(exceptionName) ?? loc.errorGeneric;
          if (snapshot.error.toString().startsWith("GenericNotAuthorized")) {
            goToLoginPagePostFrameCallback(context);
          }
          return Center(child: Text(errorMessage));
        }
        if (snapshot.hasData) {
          final alertRoles = snapshot.data!;
          return alertList(context, alertRoles);
        }
        return Center(child: Text(loc.errorGeneric));
      },
    );
  }

  Widget alertList(BuildContext context, List<Map<String, String>> alertRoles) {
    final primaryScrollController = PrimaryScrollController.of(context);
    final alertId = ModalRoute.of(context)!.settings.arguments as int;
    final loc = AppLocalizations.of(context)!;
    if (alertRoles.isEmpty) {
      return Center(child: Text(loc.entriesNotFound));
    }
    return Column(
      children: [
        Expanded(
          child: ListView.separated(
            controller: primaryScrollController,
            itemCount: alertRoles.length,
            separatorBuilder: (context, index) => Divider(),
            itemBuilder: (context, index) {
              final alertRole = alertRoles[index];
              final String role = alertRole["role"] ?? "";
              final specialistsCount = alertRole["specialists_count"] ?? "0";
              return ListTile(
                title: Text(role),
                subtitle: Text(
                  "${loc.alertAlertedSpecialists}: $specialistsCount",
                ),
                onTap: () {
                  final specialistsCountAsInt =
                      int.tryParse(specialistsCount) ?? 0;
                  if (specialistsCountAsInt == 0) {
                    return;
                  }
                  Navigator.pushNamed(
                    context,
                    '/alerts/view-alerted-users',
                    arguments: {"alert_id": alertId, "role": role},
                  );
                },
              );
            },
          ),
        ),
      ],
    );
  }
}
