// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
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
  bool positiveCloseUnblocked = false; // state for the checkbox
  bool negativeCloseUnblocked = false; // state for the checkbox
  bool neutralCloseUnblocked = false; // state for the checkbox
  bool punitiveCloseUnblocked = false; // state for the checkbox

  @override
  void dispose() {
    debugPrintC("Disposing AlertDetailsBody widget state");
    super.dispose();
  }

  Future<AlertWithInfo> _getAlertDetails(BuildContext context, int id) async {
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

  void _refreshPage() {
    final loc = AppLocalizations.of(context)!;
    final alertId = ModalRoute.of(context)!.settings.arguments as int;
    showLoadingDialog(context, loc.labelWaitPlease);
    Future.delayed(Duration(milliseconds: 4000), () {
      if (mounted) {
        debugPrintC(
          "Waited 4 seconds, now popping the loading dialog, and refreshing the page",
        );
        Navigator.pop(context);
        Navigator.pushReplacementNamed(
          context,
          '/alerts/view-alert-details',
          arguments: alertId,
        );
      }
    });
  }

  Future<void> _showAddress(BuildContext context, Alert alert) async {
    final loc = AppLocalizations.of(context)!;
    final String? address;
    if ((alert.address != null) && (alert.address!.isNotEmpty)) {
      debugPrintC("Using address coming from backend for alert ${alert.id}");
      address = alert.address;
    } else {
      final locationClient = context.read<LocationClient>();
      debugPrintC("Translating coordinates to address for alert ${alert.id}");
      address = await locationClient.translateToAddress(
        alert.latitude,
        alert.longitude,
      );
    }
    if (!context.mounted) return;
    showSimpleAlertDialog(
      context,
      loc.labelAddress,
      address ?? loc.errorLocationAddressNotFound,
    );
  }

  void _showSenderInfo(BuildContext context, User? sender) {
    final loc = AppLocalizations.of(context)!;
    if (sender == null) {
      return;
    }
    String senderDetailsStr = sender.email;
    senderDetailsStr += "\n${loc.userPhoneNumber}: ${sender.phone}";
    senderDetailsStr += "\n";
    if (sender.street.isNotEmpty) {
      senderDetailsStr += "\n${sender.street}";
    }
    if (sender.postalCode.isNotEmpty) {
      senderDetailsStr += "\n${sender.postalCode}, ";
    }
    if (sender.city.isNotEmpty) {
      senderDetailsStr += "${sender.city}, ";
    }
    if (sender.province.isNotEmpty) {
      senderDetailsStr += sender.province;
    }
    if (sender.country.isNotEmpty) {
      senderDetailsStr += "\n${sender.country}";
    }
    senderDetailsStr += "\n";
    senderDetailsStr +=
        "\n${loc.userType}: ${loc.getUserTypeString(sender.type).toLowerCase()}";
    senderDetailsStr +=
        "\n${loc.userStatus}: ${loc.getUserStatusString(sender.status).toLowerCase()}";
    senderDetailsStr += "\n${loc.userReliability}: ${sender.reliabilityScore}";
    senderDetailsStr += "\n";
    senderDetailsStr += "\n${loc.userBirthdate}: ${sender.birthDate}";
    senderDetailsStr +=
        "\n${loc.userRole}: ${loc.getUserRoleString(sender.role).toLowerCase()}";
    if (!context.mounted) return;
    showSimpleAlertDialog(
      context,
      "${sender.firstname} ${sender.surname}",
      senderDetailsStr,
    );
  }

  void _viewAlertedUsersPage(BuildContext context, int alertId) {
    Navigator.pushNamed(
      context,
      '/alerts/view-alerted-users',
      arguments: {"alert_id": alertId, "role": null},
    );
    return;
  }

  void _viewAlertRolesPage(BuildContext context, int alertId) {
    Navigator.pushNamed(
      context,
      '/alerts/view-alert-roles',
      arguments: alertId,
    );
    return;
  }

  void _viewMessagesPage(BuildContext context, int alertId) {
    Navigator.pushNamed(
      context,
      '/alerts/view-alert-messages',
      arguments: alertId,
    );
    return;
  }

  void _viewExpandAlertPage(BuildContext context, int alertId) {
    Navigator.pushNamed(context, '/alerts/expand', arguments: alertId);
    return;
  }

  Future<void> _voteAlert(int alertId, int vote) async {
    String retMessage = "";
    String retTitle = "";
    bool newLoginRequired = false;
    int respVote = 0;
    final authClient = context.read<AuthClient>();
    final loc = AppLocalizations.of(context)!;
    final dialogTitle = (vote > 0)
        ? loc.buttonVotePositive
        : (vote < 0)
        ? loc.buttonVoteNegative
        : loc.buttonVoteNeutral;
    final bool result =
        await showTwoWayAlertDialog(
          context,
          dialogTitle,
          loc.labelAreYouSure,
        ) ??
        false;
    if (result == false) {
      return;
    }
    try {
      final response = await authClient.doProtectedApiRequest(
        "post",
        '/alerts/$alertId/vote',
        body: {"vote": vote},
      );
      final Map<String, dynamic>? respObj = json.decode(response.body);
      if (respObj == null || respObj.isEmpty) {
        throw NotFoundException();
      }
      retTitle = loc.successGeneric;
      retMessage = loc.successAlertVoted;
      respVote = respObj["vote"];
    } catch (e) {
      final exceptionName = e.runtimeType.toString();
      if (exceptionName == "GenericNotAuthorizedException") {
        newLoginRequired = true;
      }
      retTitle = loc.errorError;
      retMessage = loc.getExceptionString(exceptionName) ?? loc.errorGeneric;
      if (e.toString().contains("Alert is closed")) {
        retMessage += ": ${loc.errorAlertIsClosed.toLowerCase()}";
      } else if (e.toString().contains("Alert has been expanded")) {
        retMessage += ": ${loc.errorAlertHasBeenExtended.toLowerCase()}";
      } else if (e.toString().contains("You are not a reliable user")) {
        retMessage += ": ${loc.errorAlertedUserNotReliable.toLowerCase()}";
      }
    } finally {
      if (mounted) {
        await showSimpleAlertDialog(context, retTitle, retMessage);
      }
      if (newLoginRequired) {
        if (mounted) {
          goToLoginPagePostFrameCallback(context);
        }
      }
    }
    if ((alertWithInfo != null) && (respVote != 0)) {
      setState(() {
        alertWithInfo!.positiveVotesNum += (respVote > 0) ? 1 : 0;
        alertWithInfo!.negativeVotesNum += (respVote < 0) ? 1 : 0;
        alertWithInfo!.userVote = respVote;
      });
    }
  }

  Future<void> _closeAlert(int alertId, String closingType) async {
    String retMessage = "";
    String retTitle = "";
    bool isError = false;
    bool newLoginRequired = false;
    final authClient = context.read<AuthClient>();
    final loc = AppLocalizations.of(context)!;
    final String dialogTitle = loc.getClosingTypeButtonString(closingType);
    final bool result =
        await showTwoWayAlertDialog(
          context,
          dialogTitle,
          loc.labelAreYouSure,
        ) ??
        false;
    if (result == false) {
      return;
    }
    try {
      final response = await authClient.doProtectedApiRequest(
        "post",
        '/alerts/$alertId/close',
        body: {"type": closingType},
      );
      final Map<String, dynamic>? respObj = json.decode(response.body);
      if (respObj == null || respObj.isEmpty) {
        throw NotFoundException();
      }
      retTitle = loc.successGeneric;
      retMessage = loc.successAlertClosed;
    } catch (e) {
      isError = true;
      final exceptionName = e.runtimeType.toString();
      if (exceptionName == "GenericNotAuthorizedException") {
        newLoginRequired = true;
      }
      retTitle = loc.errorError;
      retMessage = loc.getExceptionString(exceptionName) ?? loc.errorGeneric;
    } finally {
      if (mounted) {
        await showSimpleAlertDialog(context, retTitle, retMessage);
      }
      if (newLoginRequired) {
        if (mounted) {
          goToLoginPagePostFrameCallback(context);
        }
      }
    }
    if ((mounted) && (isError == false)) {
      Navigator.of(context).pushNamedAndRemoveUntil(
        '/alerts/view-alert-details',
        (route) => false,
        arguments: alertId,
      );
    }
    return;
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    final id = ModalRoute.of(context)!.settings.arguments as int;
    if (alertWithInfo != null) {
      debugPrintC("Using cached alert details for alert $id");
      return scrollableAlertDetails(context, alertWithInfo!);
    } else {
      debugPrintC("Fetching alert details for alert $id");
      return FutureBuilder<AlertWithInfo>(
        future: _getAlertDetails(context, id),
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
    final shortAlertId = convertToShortId(
      alertWithInfo.alert.id.toString(),
      lastCharsNum: 3,
    );
    final createdAt = datetimeAsStringWithoutMilliseconds(
      alertWithInfo.alert.createdAt,
    );
    final alertIsLocal = (alertWithInfo.alert.type == AlertType.local.name)
        ? true
        : false;
    final alertIsGeneral = (alertWithInfo.alert.type == AlertType.general.name)
        ? true
        : false;
    final alertIsClosed =
        (alertWithInfo.alert.status == AlertStatus.closed.name) ? true : false;
    final alertIsExpanded = alertWithInfo.alert.isExpanded;
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
      senderName += " (${loc.alertManager.toLowerCase()})";
    }
    if (alertWithInfo.userIsSender) {
      senderName += " (${loc.alertYou.toLowerCase()})";
    }
    String chiefName =
        "${alertWithInfo.chiefFirstname} ${alertWithInfo.chiefSurname}";
    if (alertWithInfo.userIsManager) {
      chiefName += " (${loc.alertYou.toLowerCase()})";
    }
    final String myVoteStr;
    if (alertWithInfo.userVote > 0) {
      myVoteStr =
          "+${alertWithInfo.userVote.abs()} (${loc.alertedUserVotePositive})";
    } else if (alertWithInfo.userVote < 0) {
      myVoteStr =
          "-${alertWithInfo.userVote.abs()} (${loc.alertedUserVoteNegative})";
    } else {
      myVoteStr =
          "0 (${loc.alertedUserVoteNeutral}, ${loc.alertedUserYouHaveNotVoted})";
    }
    final String chiefClosingVoteStr;
    if (alertWithInfo.chiefClosingVote > 0) {
      chiefClosingVoteStr =
          "+${alertWithInfo.chiefClosingVote.abs()} (${loc.alertedUserVotePositive})";
    } else if (alertWithInfo.chiefClosingVote < 0) {
      if (alertWithInfo.chiefClosingVote <= -100) {
        chiefClosingVoteStr =
            "-${alertWithInfo.chiefClosingVote.abs()} (${loc.alertedUserVotePunitive})";
      } else {
        chiefClosingVoteStr =
            "-${alertWithInfo.chiefClosingVote.abs()} (${loc.alertedUserVoteNegative})";
      }
    } else {
      chiefClosingVoteStr = "0 (${loc.alertedUserVoteNeutral})";
    }
    final String alertTypeStr = loc.getAlertTypeString(
      alertWithInfo.alert.type,
    );
    final String alertStatusStr = loc.getAlertStatusString(
      alertWithInfo.alert.status,
    );
    final int alertSpreadCount = alertWithInfo.alert.spreadCount;
    final int alertMaxSpreadCount = Alert.maxSpreadCount;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        buildSectionTitle(loc.sectionAlertInfo),
        Text('ID: ${alertWithInfo.alert.id}'),
        Text('${loc.labelShortID}: $shortAlertId'),
        Text('${loc.labelDatetime}: $createdAt'),
        Text('${loc.labelType}: ${alertTypeStr.toLowerCase()}'),
        Text('${loc.labelStatus}: ${alertStatusStr.toLowerCase()}'),
        if (alertWithInfo.alert.status == AlertStatus.pending.name)
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(height: 10),
              Text(
                loc.alertSpreadingInfo,
                style: TextStyle(fontStyle: FontStyle.italic),
              ),
              InkWell(
                onTap: () {
                  _refreshPage();
                },
                child: Text(
                  loc.labelReloadPage,
                  style: TextStyle(
                    decoration: TextDecoration.underline,
                    color: Colors.blue,
                  ),
                ),
              ),
            ],
          ),
        if (!alertIsGeneral)
          Text(loc.alertSpreadCountInfo(alertSpreadCount, alertMaxSpreadCount)),
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
        if (alertIsLocal)
          Text("${loc.gpsPositionAccuracy}: ${alertWithInfo.alert.accuracy} m"),
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
                  viewOnMap(
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
        // if the user is a chief or admin, show a link to view all sender details
        // (note: any chief or admin can view sender details, not only the chief manager of the alert)
        if (authClient.isChief() || authClient.isAdmin())
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
        if (alertIsLocal)
          Text(
            '${loc.userReliabilityScore}: ${alertWithInfo.senderReliabilityScore}',
          ),
        if (alertIsLocal)
          Text(
            chiefIsAlerted
                ? '${loc.alertChief} ${loc.alertManager.toLowerCase()}: $chiefName'
                : '${loc.alertChief} ${loc.alertManager.toLowerCase()}: N/A',
          ),
        SizedBox(height: 10),
        if (!alertIsGeneral)
          Text('${loc.alertAlertedUsers}: (${alertWithInfo.alertedUsersNum})'),
        // if the alert is not general, and there are alerted users,
        // and the user is a chief or admin, show a link to view all alerted users
        // (note: any chief or admin can view alerted users, not only the chief manager of the alert)
        if (!alertIsGeneral &&
            (alertWithInfo.alertedUsersNum > 0) &&
            (authClient.isChief() || authClient.isAdmin()))
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
        if (!alertIsGeneral &&
            (alertWithInfo.alertedUsersNum > 0) &&
            (authClient.isChief() || authClient.isAdmin()))
          Row(
            children: [
              Text('${loc.alertAlertedSpecialists}: '),
              InkWell(
                onTap: () {
                  _viewAlertRolesPage(context, alertWithInfo.alert.id);
                },
                child: Text(
                  loc.buttonView,
                  style: TextStyle(
                    decoration: TextDecoration.underline,
                    color: Colors.blue,
                  ),
                ),
              ),
            ],
          ),
        SizedBox(height: 10),
        if (alertIsLocal && alertWithInfo.alertedUsersNum > 0)
          Text(
            '${loc.alertPositiveVotesNum}: ${alertWithInfo.positiveVotesNum}',
          ),
        if (alertIsLocal && alertWithInfo.alertedUsersNum > 0)
          Text(
            '${loc.alertNegativeVotesNum}: ${alertWithInfo.negativeVotesNum}',
          ),
        SizedBox(height: 10),
        Text(loc.alertMessages),
        Row(
          children: [
            InkWell(
              onTap: () {
                _viewMessagesPage(context, alertWithInfo.alert.id);
              },
              child: Text(
                loc.buttonChat,
                style: TextStyle(
                  decoration: TextDecoration.underline,
                  color: Colors.blue,
                ),
              ),
            ),
          ],
        ),
        SizedBox(height: 10),
        // Only the chief alert manager can extend an alert
        if (alertWithInfo.userIsManager &&
            !alertIsGeneral &&
            !alertIsClosed &&
            (alertSpreadCount < alertMaxSpreadCount))
          InkWell(
            onTap: () {
              _viewExpandAlertPage(context, alertWithInfo.alert.id);
            },
            child: Text(
              loc.alertExtend,
              style: TextStyle(
                decoration: TextDecoration.underline,
                color: Colors.blue,
              ),
            ),
          ),
        // If the alert is closed, show the chief closing vote
        if (alertIsLocal && alertIsClosed)
          Text(
            '${loc.alertedUserClosingVote}: ${chiefClosingVoteStr.toLowerCase()}',
          ),
        // If the user is alerted, show their vote and buttons to vote
        if (alertWithInfo.userIsAlerted && alertIsLocal)
          Divider(height: 40, thickness: 1),
        if (alertWithInfo.userIsAlerted && alertIsLocal)
          buildSectionTitle(loc.sectionAlertVote),
        if ((alertWithInfo.userIsAlerted) && alertIsLocal)
          Text('${loc.alertedUserMyVote}: ${myVoteStr.toLowerCase()}'),
        if ((alertWithInfo.userIsAlerted) && alertIsLocal && alertIsExpanded)
          Text(
            loc.alertExtendedAndVoteTerminated,
            style: TextStyle(fontStyle: FontStyle.italic),
          ),
        if (alertWithInfo.userIsAlerted &&
            alertIsLocal &&
            !alertIsClosed &&
            !alertIsExpanded)
          SizedBox(height: 10),
        if (alertWithInfo.userIsAlerted &&
            alertIsLocal &&
            !alertIsClosed &&
            !alertIsExpanded &&
            (alertWithInfo.userVote == 0))
          Row(
            children: [
              ElevatedButton(
                onPressed: () {
                  _voteAlert(alertWithInfo.alert.id, 1);
                },
                child: Text(loc.buttonVotePositive),
              ),
              SizedBox(width: 10),
              ElevatedButton(
                onPressed: () {
                  _voteAlert(alertWithInfo.alert.id, -1);
                },
                child: Text(loc.buttonVoteNegative),
              ),
              SizedBox(width: 10),
              ElevatedButton(
                onPressed: () {
                  showSimpleAlertDialog(
                    context,
                    loc.labelOK,
                    loc.alertedUserVoteNeutralInfo,
                  );
                },
                child: Text(loc.buttonVoteNeutral),
              ),
            ],
          ),
        // If the user is a chief manager, show buttons to do a closing vote and close the alert
        if (alertWithInfo.userIsManager && !alertIsClosed)
          Divider(height: 40, thickness: 1),
        if (alertWithInfo.userIsManager && !alertIsClosed)
          buildSectionTitle(loc.sectionAlertClosing),
        if (alertWithInfo.userIsManager && !alertIsClosed && alertIsLocal)
          Row(
            children: [
              ElevatedButton(
                onPressed: positiveCloseUnblocked
                    ? () {
                        _closeAlert(alertWithInfo.alert.id, "positive");
                      }
                    : null,
                child: Text(loc.buttonClosingPositive),
              ),
              SizedBox(width: 2),
              Checkbox(
                value: positiveCloseUnblocked,
                onChanged: (value) {
                  setState(() {
                    positiveCloseUnblocked = value!;
                  });
                },
              ),
            ],
          ),
        if (alertWithInfo.userIsManager && !alertIsClosed) SizedBox(height: 10),
        if (alertWithInfo.userIsManager && !alertIsClosed && alertIsLocal)
          Row(
            children: [
              ElevatedButton(
                onPressed: negativeCloseUnblocked
                    ? () {
                        _closeAlert(alertWithInfo.alert.id, "negative");
                      }
                    : null,
                child: Text(loc.buttonClosingNegative),
              ),
              SizedBox(width: 2),
              Checkbox(
                value: negativeCloseUnblocked,
                onChanged: (value) {
                  setState(() {
                    negativeCloseUnblocked = value!;
                  });
                },
              ),
            ],
          ),
        if (alertWithInfo.userIsManager && !alertIsClosed) SizedBox(height: 10),
        if (alertWithInfo.userIsManager && !alertIsClosed)
          Row(
            children: [
              ElevatedButton(
                onPressed: neutralCloseUnblocked
                    ? () {
                        _closeAlert(alertWithInfo.alert.id, "neutral");
                      }
                    : null,
                child: Text(loc.buttonClosingNeutral),
              ),
              SizedBox(width: 2),
              Checkbox(
                value: neutralCloseUnblocked,
                onChanged: (value) {
                  setState(() {
                    neutralCloseUnblocked = value!;
                  });
                },
              ),
            ],
          ),
        if (alertWithInfo.userIsManager && !alertIsClosed) SizedBox(height: 10),
        if (alertWithInfo.userIsManager && !alertIsClosed && alertIsLocal)
          Row(
            children: [
              ElevatedButton(
                onPressed: punitiveCloseUnblocked
                    ? () {
                        _closeAlert(alertWithInfo.alert.id, "punitive");
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
