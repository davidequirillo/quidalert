// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/services/shared.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/services/notification.dart';

class StartupPage extends StatelessWidget {
  const StartupPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CAppBar(title: "Starting up..."),
      drawer: null,
      body: const StartupPageBody(),
    );
  }
}

class StartupPageBody extends StatefulWidget {
  const StartupPageBody({super.key});

  @override
  StartupPageBodyState createState() => StartupPageBodyState();
}

class StartupPageBodyState extends State<StartupPageBody> {
  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    debugPrint('Startup page building...');
    debugPrint('Requesting SharedVars provider...');
    SharedVars shared = context.watch<SharedVars>();
    debugPrint('Requesting AuthClient provider...');
    AuthClient authClient = context.watch<AuthClient>();
    debugPrint('Requesting NotificationProvider provider...');
    NotificationProvider notifProvider = context.watch<NotificationProvider>();
    bool termsAccepted = shared.termsAccepted;
    bool isLoggedIn = authClient.isLoggedIn();
    if ((!shared.initDone) ||
        (!authClient.initDone) ||
        (!notifProvider.initDone)) {
      debugPrint("Returning loading circular progress indicator...");
      return const Center(child: CircularProgressIndicator());
    } else {
      debugPrint("Adding post frame callback...");
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (termsAccepted == false) {
          Navigator.pushReplacementNamed(context, '/info');
        } else if (!isLoggedIn) {
          Navigator.pushReplacementNamed(context, '/login');
        } else {
          Navigator.pushReplacementNamed(context, '/home');
        }
      });
      debugPrint("Returning empty scaffold...");
      return const SizedBox.shrink(); // empty page at start, for a little time interval
    }
  }
}
