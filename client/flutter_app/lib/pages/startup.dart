// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/services/shared.dart';
import 'package:quidalert_flutter/services/auth.dart';

class StartupPage extends StatelessWidget {
  const StartupPage({super.key});

  @override
  Widget build(BuildContext context) {
    final shared = context.watch<SharedVars>();
    final authClient = context.watch<AuthClient>();
    bool termsAccepted = shared.termsAccepted;
    bool isLoggedIn = authClient.isLoggedIn();

    if ((!shared.initDone) || (!authClient.initDone)) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (termsAccepted == false) {
        Navigator.pushReplacementNamed(context, '/info');
      } else if (!isLoggedIn) {
        Navigator.pushReplacementNamed(context, '/login');
      } else {
        Navigator.pushReplacementNamed(context, '/home');
      }
    });

    return const Scaffold(
      body:
          SizedBox.shrink(), // empty page at start, for a little time interval
    );
  }
}
