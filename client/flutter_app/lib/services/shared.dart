// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SharedVars extends ChangeNotifier {
  bool termsAccepted = false;
  bool initDone = false;

  SharedVars() : super() {
    _init();
  }

  Future<void> _init() async {
    await loadPrefs();
    initDone = true;
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
