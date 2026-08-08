// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
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
      if (location.isMoving) {
        debugPrintC("The device is moving, skipping update");
        return;
      }
      await BackgroundLocationService.handleLocation(location);
    } else if (event.name == bg.Event.HEARTBEAT) {
      bg.HeartbeatEvent heartbeatEvent = event.event as bg.HeartbeatEvent;
      bg.Location? location = heartbeatEvent.location;
      debugPrintC("Headless heartbeat received (${event.name})");
      if (location != null) {
        debugPrintC(
          "Heartbeat event contains a location: ${location.coords.latitude}, ${location.coords.longitude} location_id: ${location.uuid}",
        );
        if (location.isMoving) {
          debugPrintC("The device is moving, skipping update");
          return;
        }
        await BackgroundLocationService.handleHeartbeatLocation(location);
      } else {
        debugPrintC("No location data in heartbeat event, skipping update");
      }
    } else if (event.name == bg.Event.MOTIONCHANGE) {
      bg.Location location = event.event as bg.Location;
      debugPrintC(
        "Headless motion change received (${event.name}): ${location.coords.latitude}, ${location.coords.longitude}, location_id: ${location.uuid}",
      );
      if (location.isMoving) {
        debugPrintC("The device is moving, skipping update");
        return;
      }
      await BackgroundLocationService.handleLocation(location);
    }
  } catch (e) {
    debugPrintC('[HeadlessTask] Unknown error: $e');
  }
}
