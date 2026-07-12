// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/l10n/app_localizations_extension.dart';
import 'package:quidalert_flutter/models/general.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class AlertDetailsPage extends StatelessWidget {
  const AlertDetailsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.labelDetails, showBackButton: true),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: AlertDetailsBody()),
    );
  }
}

class AlertDetailsBody extends StatelessWidget {
  const AlertDetailsBody({super.key});

  Future<AlertWithInfo> _getAlertDetails(
    BuildContext context,
    String id,
  ) async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/alert/$id',
    );
    final Map<String, dynamic>? respObj = json.decode(response.body);
    if (respObj == null || respObj.isEmpty) {
      throw NotFoundException();
    }
    if (!respObj.containsKey("alert") || respObj["alert"] == null) {
      throw NotFoundException();
    }
    final alertWithInfo = AlertWithInfo.fromJson(respObj);
    return alertWithInfo;
  }

  void _refreshPage(BuildContext context) {
    final id = ModalRoute.of(context)!.settings.arguments as String;
    Navigator.pushReplacementNamed(
      context,
      '/alerts/view-alert-details',
      arguments: id,
    );
  }

  void _viewInTheMap(BuildContext context, double latitude, double longitude) {
    // todo: open the map using the default external map application
    // or using the default browser with Google Maps
    final url =
        'https://www.google.com/maps/search/?api=1&query=$latitude,$longitude';
  }

  void _viewAlertedUsersPage(BuildContext context, int alertId) {
    Navigator.pushNamed(
      context,
      '/alerts/view-alert-users',
      arguments: alertId.toString(),
    );
    return;
  }

  void _viewMessagesPage(BuildContext context, int alertId) {
    Navigator.pushNamed(
      context,
      '/alerts/view-alert-messages',
      arguments: alertId.toString(),
    );
    return;
  }

  void _extendAlertPage(BuildContext context) {
    Navigator.pushNamed(context, '/alerts/extend-alert');
    return;
  }

  @override
  Widget build(BuildContext context) {
    final primaryController = PrimaryScrollController.of(context);
    final loc = AppLocalizations.of(context)!;
    final id = ModalRoute.of(context)!.settings.arguments as String;
    return FutureBuilder<AlertWithInfo>(
      future: _getAlertDetails(context, id),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          debugPrint("Error fetching recent alerts: ${snapshot.error}");
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
          final alert = snapshot.data!;
          return Scrollbar(
            thumbVisibility: true,
            controller: primaryController,
            child: SingleChildScrollView(
              controller: primaryController,
              padding: const EdgeInsets.all(16),
              child: alertColumn(context, alert),
            ),
          );
        }
        return Center(child: Text(loc.errorGeneric));
      },
    );
  }

  Widget alertColumn(BuildContext context, AlertWithInfo alertWithInfo) {
    final authClient = context.read<AuthClient>();
    final loc = AppLocalizations.of(context)!;
    final createdAt = datetimeAsStringWithoutMicroseconds(
      alertWithInfo.alert.createdAt,
      includeTimezone: false,
    );
    final senderIsChief = (alertWithInfo.alert.type != AlertType.local.name)
        ? true
        : false;
    final chiefIsAlerted =
        (alertWithInfo.chiefFirstname != null &&
            alertWithInfo.chiefFirstname!.isNotEmpty &&
            alertWithInfo.chiefSurname != null &&
            alertWithInfo.chiefSurname!.isNotEmpty)
        ? true
        : false;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        buildSectionTitle("Alert Info"),
        Text('${loc.labelDatetime}: $createdAt'),
        Text('${loc.labelType}: ${alertWithInfo.alert.type}'),
        Text('${loc.labelStatus}: ${alertWithInfo.alert.status}'),
        if (alertWithInfo.alert.status == AlertStatus.pending.name)
          InkWell(
            onTap: () {
              _refreshPage(context);
            },
            child: Text(
              loc.labelReloadPage,
              style: TextStyle(
                decoration: TextDecoration.underline,
                color: Colors.blue,
              ),
            ),
          ),
        if (alertWithInfo.alert.type != AlertType.general.name)
          Text(
            '${loc.gpsPosition}: ${gpsCoordinatesAsString(alertWithInfo.alert.latitude, alertWithInfo.alert.longitude)}',
          ),
        if (alertWithInfo.alert.type != AlertType.general.name)
          InkWell(
            onTap: () {
              _viewInTheMap(
                context,
                alertWithInfo.alert.latitude,
                alertWithInfo.alert.longitude,
              );
            },
            child: Text(
              loc.labelViewInTheMap,
              style: TextStyle(
                decoration: TextDecoration.underline,
                color: Colors.blue,
              ),
            ),
          ),
        if (alertWithInfo.alert.type != AlertType.general.name)
          Text('${loc.alertRadius}: ${alertWithInfo.alert.radius} km'),
        SizedBox(height: 20),
        Text('${loc.alertDescription}: ${alertWithInfo.alert.description}'),
        Divider(height: 40, thickness: 1),
        buildSectionTitle(loc.sectionUsers),
        Text(
          senderIsChief
              ? '${loc.alertSender}: ${alertWithInfo.senderFirstname} ${alertWithInfo.senderSurname} (${loc.alertChief})'
              : '${loc.alertSender}: ${alertWithInfo.senderFirstname} ${alertWithInfo.senderSurname}',
        ),
        Text(
          chiefIsAlerted
              ? '${loc.alertChief}: ${alertWithInfo.chiefFirstname} ${alertWithInfo.chiefSurname}'
              : '${loc.alertChief}: N/A',
        ),
        SizedBox(height: 20),
        Text('${loc.alertAlertedUsers}: (${alertWithInfo.alertedUsersNum})'),
        if (alertWithInfo.alertedUsersNum > 0 && authClient.isChief())
          InkWell(
            onTap: () {
              _viewAlertedUsersPage(context, alertWithInfo.alert.id);
            },
            child: Text(
              loc.buttonView,
              style: TextStyle(
                decoration: TextDecoration.underline,
                color: Colors.blue,
              ),
            ),
          ),
        SizedBox(height: 20),
        Text('${loc.alertMessages}: (${alertWithInfo.messagesNum})'),
        if (alertWithInfo.messagesNum > 0)
          InkWell(
            onTap: () {
              _viewMessagesPage(context, alertWithInfo.alert.id);
            },
            child: Text(
              loc.buttonView,
              style: TextStyle(
                decoration: TextDecoration.underline,
                color: Colors.blue,
              ),
            ),
          ),
        SizedBox(height: 20),
        if (authClient.isChief())
          InkWell(
            onTap: () {
              _extendAlertPage(context);
            },
            child: Text(
              "Extend alert",
              style: TextStyle(
                decoration: TextDecoration.underline,
                color: Colors.blue,
              ),
            ),
          ),
        Divider(height: 40, thickness: 1),
      ],
    );
  }
}
