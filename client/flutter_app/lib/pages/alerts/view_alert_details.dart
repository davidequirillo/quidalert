// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
      '/alerts/$id',
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

  Future<void> _showAddress(BuildContext context, Alert alert) async {
    final loc = AppLocalizations.of(context)!;
    final String? address;
    if ((alert.address != null) && (alert.address!.isNotEmpty)) {
      address = alert.address;
    } else {
      final locationClient = context.read<LocationClient>();
      address = await locationClient.translateToAddress(
        alert.latitude,
        alert.longitude,
      );
    }
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

  void _showSenderInfo(BuildContext context, User? sender) {
    final loc = AppLocalizations.of(context)!;
    if (sender == null) {
      return;
    }
    String senderDetailsStr =
        "${sender.firstname} ${sender.surname}\n${sender.email}";
    senderDetailsStr += "\n";
    senderDetailsStr += "\n${loc.userBirthdate}: ${sender.birthDate}";
    senderDetailsStr += "\n${loc.userPhoneNumber}: ${sender.phone}";
    senderDetailsStr += "\n";
    senderDetailsStr += "\n${sender.street}";
    senderDetailsStr += "\n${sender.postalCode}, ${sender.city}";
    senderDetailsStr += "\n${sender.province}";
    senderDetailsStr += "\n${sender.country}";
    if (!context.mounted) return;
    showSimpleAlertDialog(context, loc.labelDetails, senderDetailsStr);
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
      thumbVisibility: true,
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
    final alertIsLocal = (alertWithInfo.alert.type == AlertType.local.name)
        ? true
        : false;
    final alertIsGeneral = (alertWithInfo.alert.type == AlertType.general.name)
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
    if (!alertIsLocal) {
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
    final String? myVote;
    if (alertWithInfo.userVote > 0) {
      myVote = loc.alertedUserVotePositive;
    } else if (alertWithInfo.userVote < 0) {
      myVote = loc.alertedUserVoteNegative;
    } else {
      myVote = loc.alertedUserYouHaveNotVoted;
    }
    final String chiefClosingVote;
    if (alertWithInfo.chiefClosingVote > 0) {
      chiefClosingVote = loc.alertedUserVotePositive;
    } else if (alertWithInfo.chiefClosingVote < 0) {
      if (alertWithInfo.chiefClosingVote <= -100) {
        chiefClosingVote = loc.alertedUserVotePunitive;
      } else {
        chiefClosingVote = loc.alertedUserVoteNegative;
      }
    } else {
      chiefClosingVote = loc.alertedUserVoteNeutral;
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
        if (!alertIsGeneral)
          Row(
            children: [
              Text(
                '${loc.gpsPosition}: ${gpsCoordinatesAsString(alertWithInfo.alert.latitude, alertWithInfo.alert.longitude)}',
              ),
              SizedBox(width: 10),
              InkWell(
                onTap: () {
                  final gpsCoordsStr = gpsCoordinatesAsString(
                    alertWithInfo.alert.latitude,
                    alertWithInfo.alert.longitude,
                  );
                  Clipboard.setData(ClipboardData(text: gpsCoordsStr));
                },
                child: Text(
                  loc.buttonCopy,
                  style: TextStyle(
                    decoration: TextDecoration.underline,
                    color: Colors.blue,
                  ),
                ),
              ),
            ],
          ),
        if (!alertIsGeneral)
          Row(
            children: [
              InkWell(
                onTap: () {
                  _showAddress(context, alertWithInfo.alert);
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
        if (!alertIsGeneral)
          Text('${loc.alertRadius}: ${alertWithInfo.alert.radius} km'),
        SizedBox(height: 20),
        Text(
          '${loc.alertDescription}: ${alertWithInfo.alert.description}',
          style: TextStyle(fontSize: 18, fontStyle: FontStyle.italic),
        ),
        Divider(height: 40, thickness: 1),
        buildSectionTitle(loc.sectionUsers),
        Text('${loc.alertSender}: $senderName'),
        if (authClient.isChief())
          InkWell(
            onTap: () {
              _showSenderInfo(context, alertWithInfo.sender);
            },
            child: Text(
              loc.buttonView,
              style: TextStyle(
                decoration: TextDecoration.underline,
                color: Colors.blue,
              ),
            ),
          ),
        Text(
          chiefIsAlerted
              ? '${loc.alertChief}: $chiefName'
              : '${loc.alertChief}: N/A',
        ),
        SizedBox(height: 20),
        if (!alertIsGeneral)
          Text('${loc.alertAlertedUsers}: (${alertWithInfo.alertedUsersNum})'),
        if (!alertIsGeneral &&
            (alertWithInfo.alertedUsersNum > 0) &&
            authClient.isChief())
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
            if ((alertWithInfo.messagesNum > 0) &&
                ((alertWithInfo.userIsSender) || (alertWithInfo.userIsManager)))
              SizedBox(width: 20),
            if ((alertWithInfo.userIsSender) || (alertWithInfo.userIsManager))
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
        if (alertWithInfo.userIsManager)
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
        if (alertWithInfo.userIsAlerted) Divider(height: 40, thickness: 1),
        if (alertWithInfo.userIsAlerted)
          buildSectionTitle(loc.sectionAlertVote),
        // buttons for voting
        if (alertWithInfo.userIsAlerted)
          Text('${loc.alertedUserMyVote}: $myVote'),
        if (alertWithInfo.userIsAlerted)
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
        if (alertWithInfo.userIsManager) Divider(height: 40, thickness: 1),
        if (alertWithInfo.userIsManager)
          buildSectionTitle(loc.sectionAlertClosing),
        if (alertWithInfo.userIsManager &&
            (alertWithInfo.alert.status == AlertStatus.closed.name))
          Text('${loc.alertedUserClosingVote}: $chiefClosingVote'),
        if (alertWithInfo.userIsManager)
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
        if (alertWithInfo.userIsManager) SizedBox(height: 20),
        if (alertWithInfo.userIsManager)
          ElevatedButton(
            onPressed: () {
              // Handle close alert
            },
            child: Text(loc.buttonClosingNeutral),
          ),
        SizedBox(height: 20),
        if (alertWithInfo.userIsManager)
          Row(
            children: [
              ElevatedButton(
                onPressed: punitiveCloseUnblocked
                    ? () {
                        // Handle reopen alert
                      }
                    : null,
                child: Text(loc.buttonClosingPunitive),
              ),
              SizedBox(width: 2),
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
