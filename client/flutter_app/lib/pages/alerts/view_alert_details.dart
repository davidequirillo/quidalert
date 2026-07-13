// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import 'package:url_launcher/url_launcher.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/services/location.dart';
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

class AlertDetailsBody extends StatefulWidget {
  const AlertDetailsBody({super.key});

  @override
  State<AlertDetailsBody> createState() => _AlertDetailsBodyState();
}

class _AlertDetailsBodyState extends State<AlertDetailsBody> {
  AlertWithInfo? alertWithInfo;
  bool punitiveCloseUnblocked = false; // state for the checkbox

  @override
  void dispose() {
    debugPrintC("Disposing AlertDetailsBody widget state");
    super.dispose();
  }

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

  Future<void> _showAddress(
    BuildContext context,
    double latitude,
    double longitude,
  ) async {
    final loc = AppLocalizations.of(context)!;
    final locationClient = context.read<LocationClient>();
    final address = await locationClient.translateToAddress(
      latitude,
      longitude,
    );
    if (!context.mounted) return;
    showSimpleAlertDialog(
      context,
      loc.labelAddress,
      address ?? loc.errorAddressNotFound,
    );
  }

  Future<void> _viewOnMap(
    BuildContext context,
    double latitude,
    double longitude,
  ) async {
    final loc = AppLocalizations.of(context)!;
    Uri url;
    if (Platform.isAndroid) {
      url = Uri.parse("geo:$latitude,$longitude?q=$latitude,$longitude");
    } else if (Platform.isIOS) {
      url = Uri.parse("maps://?ll=$latitude,$longitude&q=$latitude,$longitude");
    } else {
      url = Uri.parse(
        "https://www.google.com/maps/search/?api=1&query=$latitude,$longitude",
      );
    }
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    } else {
      if (!context.mounted) return;
      showSimpleAlertDialog(context, loc.errorError, loc.errorUnableToOpenMap);
    }
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

  void _viewExtendAlertPage(BuildContext context, int alertId) {
    Navigator.pushNamed(
      context,
      '/alerts/extend',
      arguments: alertId.toString(),
    );
    return;
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    final id = ModalRoute.of(context)!.settings.arguments as String;
    if (alertWithInfo != null) {
      debugPrintC("Using cached alert details for id: $id");
      return scrollableAlertDetails(context, alertWithInfo!);
    } else {
      debugPrintC("Fetching alert details for id: $id");
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
            final errorMessage =
                loc.getString(locAttribute) ?? loc.errorGeneric;
            if (snapshot.error.toString().startsWith("GenericNotAuthorized")) {
              goToLoginPagePostFrameCallback(context);
            }
            return Center(child: Text(errorMessage));
          }
          if (snapshot.hasData) {
            alertWithInfo = snapshot.data!;
            return scrollableAlertDetails(context, alertWithInfo!);
          }
          return Center(child: Text(loc.errorGeneric));
        },
      );
    }
  }

  Widget scrollableAlertDetails(
    BuildContext context,
    AlertWithInfo alertWithInfo,
  ) {
    final primaryController = PrimaryScrollController.of(context);
    return Scrollbar(
      controller: primaryController,
      child: SingleChildScrollView(
        controller: primaryController,
        padding: const EdgeInsets.all(16.0),
        child: alertColumn(context, alertWithInfo),
      ),
    );
  }

  Widget alertColumn(BuildContext context, AlertWithInfo alertWithInfo) {
    final authClient = context.read<AuthClient>();
    final loc = AppLocalizations.of(context)!;
    final createdAt = datetimeAsStringWithoutMicroseconds(
      alertWithInfo.alert.createdAt,
      includeTimezone: false,
    );
    final alertIsNotLocal = (alertWithInfo.alert.type != AlertType.local.name)
        ? true
        : false;
    final chiefIsAlerted =
        (alertWithInfo.chiefFirstname != null &&
            alertWithInfo.chiefFirstname!.isNotEmpty &&
            alertWithInfo.chiefSurname != null &&
            alertWithInfo.chiefSurname!.isNotEmpty)
        ? true
        : false;
    String senderName =
        "${alertWithInfo.senderFirstname} ${alertWithInfo.senderSurname}";
    if (alertIsNotLocal) {
      senderName += " (${loc.alertChief})";
    }
    if (alertWithInfo.userIsSender) {
      senderName += " (${loc.alertYou})";
    }
    String chiefName =
        "${alertWithInfo.chiefFirstname} ${alertWithInfo.chiefSurname}";
    if (alertWithInfo.userIsManager) {
      chiefName += " (${loc.alertYou})";
    }
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
          Row(
            children: [
              InkWell(
                onTap: () {
                  _showAddress(
                    context,
                    alertWithInfo.alert.latitude,
                    alertWithInfo.alert.longitude,
                  );
                },
                child: Text(
                  loc.labelShowAddress,
                  style: TextStyle(
                    decoration: TextDecoration.underline,
                    color: Colors.blue,
                  ),
                ),
              ),
              SizedBox(width: 20),
              // we add an icon to viewonmap link
              InkWell(
                onTap: () {
                  _viewOnMap(
                    context,
                    alertWithInfo.alert.latitude,
                    alertWithInfo.alert.longitude,
                  );
                },
                child: Text(
                  loc.labelViewOnMap,
                  style: TextStyle(
                    decoration: TextDecoration.underline,
                    color: Colors.blue,
                  ),
                ),
              ),
              Icon(Icons.map, size: 20, color: Colors.blue),
            ],
          ),
        if (alertWithInfo.alert.type != AlertType.general.name)
          Text('${loc.alertRadius}: ${alertWithInfo.alert.radius} km'),
        SizedBox(height: 20),
        Text('${loc.alertDescription}: ${alertWithInfo.alert.description}'),
        Divider(height: 40, thickness: 1),
        buildSectionTitle(loc.sectionUsers),
        Text('${loc.alertSender}: $senderName'),
        Text(
          chiefIsAlerted
              ? '${loc.alertChief}: $chiefName'
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
        Row(
          children: [
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
            if (alertWithInfo.messagesNum > 0 && alertWithInfo.userIsSender)
              SizedBox(width: 20),
            if (alertWithInfo.userIsSender)
              InkWell(
                onTap: () {
                  _viewMessagesPage(context, alertWithInfo.alert.id);
                },
                child: Text(
                  loc.buttonWrite,
                  style: TextStyle(
                    decoration: TextDecoration.underline,
                    color: Colors.blue,
                  ),
                ),
              ),
          ],
        ),
        SizedBox(height: 20),
        if (authClient.isChief())
          InkWell(
            onTap: () {
              _viewExtendAlertPage(context, alertWithInfo.alert.id);
            },
            child: Text(
              loc.alertExtend,
              style: TextStyle(
                decoration: TextDecoration.underline,
                color: Colors.blue,
              ),
            ),
          ),
        Divider(height: 40, thickness: 1),
        buildSectionTitle(loc.sectionAlertVote),
        // buttons for voting
        Row(
          children: [
            ElevatedButton(
              onPressed: () {
                // Handle positive vote
              },
              child: Text(loc.buttonVotePositive),
            ),
            SizedBox(width: 10),
            ElevatedButton(
              onPressed: () {
                // Handle negative vote
              },
              child: Text(loc.buttonVoteNegative),
            ),
            SizedBox(width: 10),
            ElevatedButton(
              onPressed: () {
                // Handle neutral vote
              },
              child: Text(loc.buttonVoteNeutral),
            ),
          ],
        ),
        Divider(height: 40, thickness: 1),
        if (authClient.isChief()) buildSectionTitle(loc.sectionAlertClosing),
        if (authClient.isChief())
          Row(
            children: [
              ElevatedButton(
                onPressed: () {
                  // Handle chief closing vote
                },
                child: Text(loc.buttonClosingPositive),
              ),
              SizedBox(width: 10),
              ElevatedButton(
                onPressed: () {
                  // Handle chief closing vote
                },
                child: Text(loc.buttonClosingNegative),
              ),
            ],
          ),
        SizedBox(height: 20),
        Row(
          children: [
            ElevatedButton(
              onPressed: () {
                // Handle close alert
              },
              child: Text(loc.buttonClosingNeutral),
            ),
            SizedBox(width: 10),
            ElevatedButton(
              onPressed: punitiveCloseUnblocked
                  ? () {
                      // Handle reopen alert
                    }
                  : null,
              child: Text(loc.buttonClosingPunitive),
            ),
            SizedBox(width: 5),
            Checkbox(
              value: punitiveCloseUnblocked,
              onChanged: (value) {
                setState(() {
                  punitiveCloseUnblocked = value!;
                });
              },
            ),
          ],
        ),
      ],
    );
  }
}
