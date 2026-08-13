// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class AlertMessagesPage extends StatelessWidget {
  const AlertMessagesPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.alertMessages, showBackButton: true),
      body: SafeArea(top: false, child: AlertMessagesBody()),
    );
  }
}

class AlertMessagesBody extends StatelessWidget {
  const AlertMessagesBody({super.key});

  @override
  Widget build(BuildContext context) {
    final id = ModalRoute.of(context)!.settings.arguments as int;
    final loc = AppLocalizations.of(context)!;
    return Center(child: Text(loc.alertMessages));
  }
}
