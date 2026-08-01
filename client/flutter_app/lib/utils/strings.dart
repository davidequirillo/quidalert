// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/foundation.dart';

String timezoneOffsetAsString(DateTime datetime) {
  final offset = datetime.timeZoneOffset;
  final hours = offset.inHours.abs().toString().padLeft(2, '0');
  final minutes = (offset.inMinutes.abs() % 60).toString().padLeft(2, '0');
  final sign = offset.isNegative ? '-' : '+';
  return "$sign$hours:$minutes";
}

String datetimeAsStringWithoutMilliseconds(
  DateTime datetime, {
  bool includeTimezone = true,
}) {
  return "${datetime.toIso8601String().replaceFirst('T', ' ').split('.').first}${includeTimezone ? timezoneOffsetAsString(datetime) : ''}";
}

String gpsCoordinatesAsString(double latitude, double longitude) {
  return "${latitude.toStringAsFixed(6)}, ${longitude.toStringAsFixed(6)}";
}

void debugPrintC(String message) {
  if (kDebugMode) {
    print(message);
  }
}
