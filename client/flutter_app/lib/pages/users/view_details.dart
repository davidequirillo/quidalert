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
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class UserDetailsPage extends StatelessWidget {
  const UserDetailsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.labelDetails, showBackButton: true),
      drawer: const CAppDrawer(),
      body: UserDetailsBody(),
    );
  }
}

class UserDetailsBody extends StatelessWidget {
  const UserDetailsBody({super.key});

  Future<List<dynamic>> getUserDetails(BuildContext context, String id) async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest("get", '/user/$id');
    final Map<String, dynamic> respobj = json.decode(response.body);
    if (respobj["user"] == null || respobj["user"].isEmpty) {
      throw NotFoundException();
    }
    final user = User.fromJson(respobj['user']);
    List<dynamic> alertsObj = respobj['alerts'];
    debugPrint(response.body);
    final alerts = alertsObj.map((item) => Alert.fromJson(item)).toList();
    return [user, alerts];
  }

  @override
  Widget build(BuildContext context) {
    final primaryController = PrimaryScrollController.of(context);
    final loc = AppLocalizations.of(context)!;
    final id = ModalRoute.of(context)!.settings.arguments as String;
    return FutureBuilder<List<dynamic>>(
      future: getUserDetails(context, id),
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
          if (snapshot.error.toString().startsWith("NotFound")) {
            return Center(child: Text(loc.errorNoEntryFound));
          }
          if (snapshot.error.toString().startsWith("Server")) {
            return Center(child: Text(loc.errorServer));
          }
          return Text(loc.errorGeneric);
        }
        if (snapshot.hasData) {
          final user = snapshot.data![0] as User;
          final alerts = snapshot.data![1] as List<Alert>;
          return Scrollbar(
            thumbVisibility: true,
            controller: primaryController,
            child: SingleChildScrollView(
              controller: primaryController,
              padding: const EdgeInsets.all(16),
              child: SafeArea(
                top: false,
                child: userColumn(context, user, alerts),
              ),
            ),
          );
        }
        return Text(loc.errorGeneric);
      },
    );
  }

  Widget userColumn(BuildContext context, User user, List<Alert> alerts) {
    final loc = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        buildSectionTitle(loc.labelPersonalInfo),
        Text('Email: ${user.email}'),
        Text('${loc.labelFirstname}: ${user.firstname}'),
        Text('${loc.labelSurname}: ${user.surname}'),
        Text('${loc.labelStreetAndNumber}: ${user.street}'),
        Text('${loc.labelPostalCode}: ${user.postalCode}'),
        Text('${loc.labelCity}: ${user.city}'),
        Text('${loc.labelProvince}: ${user.province}'),
        Text('${loc.labelCountry}: ${user.country}'),
        Text('${loc.labelBirthdate}: ${user.birthDate}'),
        Text('${loc.labelPhoneNumber}: ${user.phone}'),
        const Divider(height: 40, thickness: 2),
        buildSectionTitle(loc.labelTechnicalInfo),
        Text('${loc.labelLanguage}: ${user.language}'),
        Text('${loc.labelType}: ${user.type}'),
        Text('${loc.labelRole}: ${user.role}'),
        Text('Status: ${user.status}'),
        Text('${loc.labelReliability}: ${user.reliabilityScore}'),
        Text(
          '${loc.labelActive}: ${user.isActive ? loc.labelYes.toLowerCase() : loc.labelNo.toLowerCase()}',
        ),
        Text(
          'Reset locked until : ${user.resetLockedUntil != null ? datetimeAsStringWithoutMicroseconds(user.resetLockedUntil!) : "N/A"}',
        ),
        Text(
          'Last reset done at : ${user.lastResetDoneAt != null ? datetimeAsStringWithoutMicroseconds(user.lastResetDoneAt!) : "N/A"}',
        ),
        Text(
          'Login locked until : ${user.loginLockedUntil != null ? datetimeAsStringWithoutMicroseconds(user.loginLockedUntil!) : "N/A"}',
        ),
        Text(
          'Last login done at : ${user.lastLoginDoneAt != null ? datetimeAsStringWithoutMicroseconds(user.lastLoginDoneAt!) : "N/A"}',
        ),
        Text(
          'Last refresh at : ${user.lastRefreshAt != null ? datetimeAsStringWithoutMicroseconds(user.lastRefreshAt!) : "N/A"}',
        ),
        Text(
          'Created at : ${user.createdAt != null ? datetimeAsStringWithoutMicroseconds(user.createdAt!) : "N/A"}',
        ),
        Text('Updated by : ${user.updatedBy ?? "N/A"}'),
        Text(
          'Updated at : ${user.updatedAt != null ? datetimeAsStringWithoutMicroseconds(user.updatedAt!) : "N/A"}',
        ),
        Text('Authorized by : ${user.authorizedBy ?? "N/A"}'),
        Text(
          'Authorized at : ${user.authorizedAt != null ? datetimeAsStringWithoutMicroseconds(user.authorizedAt!) : "N/A"}',
        ),
        Text('${loc.labelNotes}: ${user.notes}'),
        SizedBox(height: 20),
        const Divider(height: 40, thickness: 2),
        buildSectionTitle(loc.labelRecents),
        if (alerts.isEmpty)
          Text(loc.errorNoEntryFound)
        else
          ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: alerts.length,
            itemBuilder: (context, index) {
              final createdAt = alerts[index].createdAt != null
                  ? datetimeAsStringWithoutMicroseconds(
                      alerts[index].createdAt!,
                    )
                  : "N/A";
              final description =
                  '${alerts[index].description.substring(0, alerts[index].description.length > 50 ? 50 : alerts[index].description.length)}...';
              return ListTile(
                title: Text('$createdAt - ${alerts[index].status}'),
                subtitle: Text('${alerts[index].id} - $description'),
              );
            },
          ),
      ],
    );
  }
}
