// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/components.dart';

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

  @override
  Widget build(BuildContext context) {
    final id = ModalRoute.of(context)!.settings.arguments as String;
    final loc = AppLocalizations.of(context)!;
    return Center(child: Text(loc.alertAlertedUsers));
  }
}
