// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/services/shared.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/services/notification.dart';
import 'package:quidalert_flutter/services/background_location.dart';

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

  Future<void> startBackgroundLocationTracking(AuthClient ac) async {
    if (!ac.isLoggedIn()) {
      debugPrintC(
        "User is not logged in, skipping background location tracking.",
      );
    } else {
      try {
        await BackgroundLocationService.startTracking();
      } catch (e) {
        debugPrintC("Error initializing background location service: $e");
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    debugPrintC('Startup page building...');
    debugPrintC('Requesting SharedVars provider...');
    SharedVars shared = context.watch<SharedVars>();
    debugPrintC('Requesting AuthClient provider...');
    AuthClient authClient = context.watch<AuthClient>();
    bool termsAccepted = shared.termsAccepted;
    bool isLoggedIn = authClient.isLoggedIn();
    debugPrintC('Requesting NotificationProvider provider...');
    NotificationProvider notifProvider = context.watch<NotificationProvider>();
    notifProvider.setAuthClient(authClient);
    if ((!shared.initDone) ||
        (!authClient.initDone) ||
        (!notifProvider.initDone)) {
      debugPrintC("Providers not initialized yet...");
      return const Center(child: CircularProgressIndicator());
    } else {
      startBackgroundLocationTracking(authClient);
      debugPrintC("Adding post frame callback...");
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (notifProvider.initialMessage != null) {
          debugPrintC(
            "StartupPage: app opened from a notification, navigating to the correct route...",
          );
          notifProvider.handleNavigation(notifProvider.initialMessage!.data);
        } else if (termsAccepted == false) {
          Navigator.pushReplacementNamed(context, '/info');
        } else if (!isLoggedIn) {
          Navigator.pushReplacementNamed(context, '/login');
        } else {
          Navigator.pushReplacementNamed(context, '/home');
        }
      });
      debugPrintC("Returning empty scaffold...");
      return const SizedBox.shrink(); // empty page at start, for a little time interval
    }
  }
}
