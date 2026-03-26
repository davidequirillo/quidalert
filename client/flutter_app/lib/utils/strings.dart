// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/foundation.dart';

String datetimeAsStringWithoutMicroseconds(
  DateTime datetime, {
  bool includeTimezone = true,
}) {
  return "${datetime.toIso8601String().replaceFirst('T', ' ').split('.').first}${includeTimezone ? ' UTC' : ''}";
}

void debugPrintC(String message) {
  if (kDebugMode) {
    print(message);
  }
}
