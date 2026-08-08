// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SharedVars extends ChangeNotifier {
  bool termsAccepted = false;
  bool initDone = false;

  SharedVars() : super() {
    debugPrint("Inside SharedVars constructor");
    _init();
  }

  Future<void> _init() async {
    if (kDebugMode) {
      debugPrint('SharedVars initialization started');
    }
    await loadPrefs();
    initDone = true;
    if (kDebugMode) {
      debugPrint('SharedVars initialization completed');
    }
    notifyListeners();
  }

  Future<void> loadPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    termsAccepted = prefs.getBool('termsAccepted') ?? false;
  }

  Future<void> setTermsAcceptedAndSave() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('termsAccepted', true);
    termsAccepted = true;
    notifyListeners();
  }
}
