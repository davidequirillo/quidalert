// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/widgets.dart';
import 'package:flutter_background_geolocation/flutter_background_geolocation.dart'
    as bg;
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/services/background_location.dart';

@pragma('vm:entry-point')
void backgroundLocationHeadlessTask(bg.HeadlessEvent event) async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    debugPrintC('[HeadlessTask] Triggered: ${event.name}');
    if (event.name == bg.Event.LOCATION) {
      bg.Location location = event.event as bg.Location;
      debugPrintC(
        "Headless location received (${event.name}): ${location.coords.latitude}, ${location.coords.longitude}, location_id: ${location.uuid}",
      );
      await BackgroundLocationService.handleLocation(location);
    } else if (event.name == bg.Event.HEARTBEAT) {
      debugPrintC(
        "Headless heartbeat received (${event.name}), fetching current location...",
      );
      await BackgroundLocationService.getBackgroundCurrentPosition();
      // Note: it triggers the "onLocation" event too
    }
  } catch (e) {
    debugPrintC('[HeadlessTask] Error: $e');
  }
}
