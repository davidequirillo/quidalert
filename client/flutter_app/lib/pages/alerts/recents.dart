// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
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
import 'package:quidalert_flutter/models/general.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';

class RecentAlertsPage extends StatelessWidget {
  const RecentAlertsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.alertRecents, showBackButton: true),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: RecentAlertsBody()),
    );
  }
}

class RecentAlertsBody extends StatelessWidget {
  const RecentAlertsBody({super.key});

  Future<List<Alert>> _getRecentAlerts(BuildContext context) async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/alerts/recent',
    );
    final List<dynamic>? respObj = json.decode(response.body);
    if (respObj == null) {
      throw NotFoundException();
    }
    final alerts = respObj.map((e) => Alert.fromJson(e)).toList();
    return alerts;
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return FutureBuilder<List<Alert>>(
      future: _getRecentAlerts(context),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          debugPrint("Error fetching recent alerts: ${snapshot.error}");
          final exceptionName = snapshot.error.runtimeType.toString();
          final errorMessage =
              loc.getExceptionString(exceptionName) ?? loc.errorGeneric;
          if (snapshot.error.toString().startsWith("GenericNotAuthorized")) {
            goToLoginPagePostFrameCallback(context);
          }
          return Center(child: Text(errorMessage));
        }
        if (snapshot.hasData) {
          final alerts = snapshot.data!;
          return alertList(context, alerts);
        }
        return Center(child: Text(loc.errorGeneric));
      },
    );
  }

  Widget alertList(BuildContext context, List<Alert> alerts) {
    final primaryScrollController = PrimaryScrollController.of(context);
    final loc = AppLocalizations.of(context)!;
    if (alerts.isEmpty) {
      return Center(child: Text(loc.entriesNotFound));
    }
    return Column(
      children: [
        Expanded(
          child: ListView.separated(
            controller: primaryScrollController,
            itemCount: alerts.length,
            separatorBuilder: (context, index) => Divider(),
            itemBuilder: (context, index) {
              final alert = alerts[index];
              final alertTypeKey = alert.type;
              final alertStatusKey = alert.status;
              final description =
                  alert.description.substring(
                    0,
                    alert.description.length > 50
                        ? 50
                        : alert.description.length,
                  ) +
                  (alert.description.length > 50 ? "..." : "");
              final alertCreatedAt = alert.createdAt;
              final alertDateTimeStr = datetimeAsStringWithoutMilliseconds(
                alertCreatedAt,
                includeTimezone: false,
              );
              return ListTile(
                title: Text(description),
                subtitle: Text(
                  "${loc.labelType}: ${loc.getAlertTypeString(alertTypeKey)}, ${loc.labelStatus}: ${loc.getAlertStatusString(alertStatusKey)}",
                ),
                trailing: Text(alertDateTimeStr),
                onTap: () {
                  Navigator.pushNamed(
                    context,
                    '/alerts/view-alert-details',
                    arguments: alert.id,
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
