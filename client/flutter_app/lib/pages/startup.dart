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

  Future<void> startBackgroundLocationService() async {
    final authClient = context.read<AuthClient>();
    if (!authClient.isLoggedIn()) {
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

  Future<void> syncFcmTokenWithBackend() async {
    final authClient = context.read<AuthClient>();
    final notifClient = context.read<NotificationProvider>();
    notifClient.setAuthClient(authClient);
    if (notifClient.fcmToken != null && notifClient.fcmToken!.isNotEmpty) {
      debugPrintC('Syncing FCM token with backend...');
      if (authClient.isLoggedIn()) {
        await authClient.syncFcmTokenWithBackendinBackground(
          notifClient.fcmToken!,
        );
      } else {
        debugPrintC(
          'AuthClient is null or user is not logged in. Skipping FCM token sync with backend.',
        );
      }
    }
  }

  void goToNextPagePostFrameCallback() {
    final authClient = context.read<AuthClient>();
    final notifProvider = context.read<NotificationProvider>();
    final sharedProvider = context.read<SharedVars>();
    debugPrintC("Adding post frame callback...");
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (notifProvider.initialMessage != null) {
        debugPrintC(
          "StartupPage: app opened from a notification, navigating to the correct route...",
        );
        notifProvider.handleNavigation(notifProvider.initialMessage!.data);
      } else if (sharedProvider.termsAccepted == false) {
        Navigator.pushReplacementNamed(context, '/info');
      } else if (!authClient.isLoggedIn()) {
        Navigator.pushReplacementNamed(context, '/login');
      } else {
        Navigator.pushReplacementNamed(context, '/home');
      }
    });
  }

  Future<void> _doExtraInit() async {
    await syncFcmTokenWithBackend();
    await startBackgroundLocationService();
    goToNextPagePostFrameCallback();
    return;
  }

  @override
  Widget build(BuildContext context) {
    debugPrintC('Startup page building...');
    debugPrintC('Requesting SharedVars provider...');
    SharedVars shared = context.watch<SharedVars>();
    debugPrintC('Requesting AuthClient provider...');
    AuthClient authClient = context.watch<AuthClient>();
    debugPrintC('Requesting NotificationProvider provider...');
    NotificationProvider notifProvider = context.watch<NotificationProvider>();
    if ((!shared.initDone) ||
        (!authClient.initDone) ||
        (!notifProvider.initDone)) {
      debugPrintC("Providers not initialized yet...");
      return const Center(child: CircularProgressIndicator());
    } else {
      debugPrintC(
        "Calling _doExtraInit and returning future empty scaffold...",
      );
      return FutureBuilder(
        future: _doExtraInit(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.done) {
            debugPrintC("Extra initialization done, returning empty page...");
            return const SizedBox.shrink(); // empty page after init
          } else {
            debugPrintC(
              "Extra initialization in progress, showing loading indicator...",
            );
            return const Center(child: CircularProgressIndicator());
          }
        },
      );
    }
  }
}
