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
import 'package:quidalert_flutter/models/general.dart';
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
      body: AlertDetailsBody(),
    );
  }
}

class AlertDetailsBody extends StatelessWidget {
  const AlertDetailsBody({super.key});

  Future<Alert> _getAlertDetails(BuildContext context, String id) async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/alert/$id',
    );
    final Map<String, dynamic>? respObj = json.decode(response.body);
    if (respObj == null || respObj.isEmpty) {
      throw NotFoundException();
    }
    final alert = Alert.fromJson(respObj);
    return alert;
  }

  @override
  Widget build(BuildContext context) {
    final primaryController = PrimaryScrollController.of(context);
    final loc = AppLocalizations.of(context)!;
    final id = ModalRoute.of(context)!.settings.arguments as String;
    return FutureBuilder<Alert>(
      future: _getAlertDetails(context, id),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return CircularProgressIndicator();
        }
        if (snapshot.hasError) {
          if (snapshot.error.toString().startsWith("GenericNotAuthorized")) {
            goToLoginPagePostFrameCallback(context);
            return Text(loc.errorSessionNotValidOrExpired);
          }
          if (snapshot.error.toString().startsWith("Forbidden")) {
            return Text(loc.errorPermissionsNotValid);
          }
          if (snapshot.error.toString().startsWith("BadRequest")) {
            return Text(loc.errorBadRequest);
          }
          if (snapshot.error.toString().startsWith("Server")) {
            return Text(loc.errorServer);
          }
          if (snapshot.error.toString().startsWith("NotFound")) {
            return Center(child: Text(loc.errorNoEntryFound));
          }
          return Text(loc.errorGeneric);
        }
        if (snapshot.hasData) {
          final alert = snapshot.data!;
          return Scrollbar(
            thumbVisibility: true,
            controller: primaryController,
            child: SingleChildScrollView(
              controller: primaryController,
              padding: const EdgeInsets.all(16),
              child: SafeArea(top: false, child: alertColumn(context, alert)),
            ),
          );
        }
        return Text(loc.errorGeneric);
      },
    );
  }

  Widget alertColumn(BuildContext context, Alert alert) {
    final loc = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [buildSectionTitle("Alert Info")],
    );
  }
}
