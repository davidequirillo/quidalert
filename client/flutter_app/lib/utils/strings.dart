// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/foundation.dart';

void debugPrintC(String message) {
  if (kDebugMode) {
    print(message);
  }
}

String timezoneOffsetAsString(DateTime datetime) {
  final offset = datetime.timeZoneOffset;
  final hours = offset.inHours.abs().toString().padLeft(2, '0');
  final minutes = (offset.inMinutes.abs() % 60).toString().padLeft(2, '0');
  final sign = offset.isNegative ? '-' : '+';
  return "$sign$hours:$minutes";
}

String datetimeAsStringWithoutMilliseconds(
  DateTime datetime, {
  bool includeTimezone = false,
}) {
  return "${datetime.toIso8601String().replaceFirst('T', ' ').split('.').first}${includeTimezone ? timezoneOffsetAsString(datetime) : ''}";
}

String gpsCoordinatesAsString(double latitude, double longitude) {
  return "${latitude.toStringAsFixed(6)}, ${longitude.toStringAsFixed(6)}";
}

String convertToShortId(String s, {int lastCharsNum = 3, String prefix = '*'}) {
  // We took the last [lastCharsNum] characters of the string
  if (lastCharsNum <= 0) {
    return '';
  }
  if (s.length > lastCharsNum) {
    s = s.substring(s.length - lastCharsNum);
  }
  return '$prefix$s';
}
