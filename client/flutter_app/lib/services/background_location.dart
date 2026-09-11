// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter_background_geolocation/flutter_background_geolocation.dart'
    as bg;
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/config.dart';
import 'package:quidalert_flutter/utils/strings.dart';

// The following class is used for background location tracking.
// It's a wrapper around the flutter_background_geolocation plugin,
// which starts in the main.dart file and runs in the background even when the app is closed.
class BackgroundLocationService {
  static AuthClient? authClient = null;
  static DateTime? httpConfigUpdatedAt = null;

  static void setAuthClient(AuthClient client) {
    authClient = client;
  }

  static Future<void> refreshGpsTokenInConfig() async {
    try {
      debugPrintC(
        "[BackgroundLocationService] Refreshing http configuration with new GPS token...",
      );
      if (authClient?.gpsToken == null) {
        debugPrintC(
          "[BackgroundLocationService] No GPS token available, skipping http configuration refresh.",
        );
        return;
      }
      debugPrintC(
        "[BackgroundLocationService] Current GPS token: ${authClient?.gpsToken ?? 'NO_GPS_TOKEN'}",
      );
      if (httpConfigUpdatedAt != null) {
        final timeElapsed = DateTime.now()
            .difference(httpConfigUpdatedAt!)
            .inSeconds;
        if (timeElapsed < 300) {
          debugPrintC(
            "[BackgroundLocationService] Http configuration was updated recently, skipping GPS token refresh.",
          );
          return;
        }
      }
      httpConfigUpdatedAt = DateTime.now();
      await bg.BackgroundGeolocation.setConfig(
        bg.Config(http: getHttpConfig()),
      );
      debugPrintC(
        '[BackgroundLocationService] Http configuration refreshed successfully with new GPS token!',
      );
    } catch (e) {
      debugPrintC(
        '[BackgroundLocationService] Error refreshing http configuration with new GPS token: $e',
      );
    }
  }

  static bg.HttpConfig getHttpConfig() {
    return bg.HttpConfig(
      url: "${AppConfig.apiUrl}/update-gps-position",
      method: "POST",
      autoSync: true,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': "Bearer ${authClient?.gpsToken ?? 'NO_GPS_TOKEN'}",
      },
      timeout: 45, // timeout for HTTP requests in seconds
    );
  }

  static Future<void> init() async {
    debugPrintC(
      "Cleaning pre-existing background location listeners and locations...",
    );
    await bg.BackgroundGeolocation.removeListeners();
    debugPrintC("Initializing background location service...");
    bg.BackgroundGeolocation.onHttp((bg.HttpEvent response) {
      if (!response.success) {
        if (response.status == 401) {
          debugPrintC('[onHttp] UNAUTHORIZED: ${response}');
          refreshGpsTokenInConfig();
        } else {
          debugPrintC('[onHttp] FAILURE: ${response}');
        }
      }
    });
    await bg.BackgroundGeolocation.ready(
      bg.Config(
        activity: bg.ActivityConfig(
          disableMotionActivityUpdates:
              false, // motion activity is required for detecting movement, so we don't disable it
          disableStopDetection:
              false, // "stop detection" feature is very useful so we don't disable it
          stopOnStationary:
              false, // we don't stop completely the background service when stationary
        ),
        app: bg.AppConfig(
          stopOnTerminate:
              false, // continue tracking even if the app is terminated
          startOnBoot:
              true, // start tracking automatically when the device boots
          enableHeadless:
              false, // we don't need it, because it is used only if we want to track events for custom headless tasks.
          heartbeatInterval:
              1800, // heartbeat event every 30 minutes, not used for now
          preventSuspend:
              false, // we don't prevent the suspension of the app by the system
        ),
        notification: bg.Notification(
          title: "Background Location Service",
          text: "Tracking your location in the background.",
          priority: bg.NotificationPriority.high,
          sticky: true,
        ),
        http:
            getHttpConfig(), // see getHttpConfig() method for HTTP configuration
        persistence: bg.PersistenceConfig(
          persistMode: bg.PersistMode.location,
          maxRecordsToPersist: 100,
          maxDaysToPersist: 30,
          // Template for location data to be persisted (it also defines the HTTP payload structure)
          locationTemplate: '''{
            "latitude": <%= latitude %>,
            "longitude": <%= longitude %>,
            "location_id": "<%= uuid %>",
            "accuracy": <%= accuracy %>,
            "is_moving": <%= is_moving %>,
            "speed": <%= speed %>,
            "activity": "<%= activity.type %>",
            "timestamp": "<%= timestamp %>"
          }''',
        ),
        geolocation: bg.GeoConfig(
          desiredAccuracy:
              bg.DesiredAccuracy.high, // use also GPS for high accuracy
          distanceFilter:
              250, // minimum distance in meters to trigger a location update
          stopTimeout:
              3, // the device is considered stationary after 3 minutes of "no movement" (see stationaryRadius)
          stationaryRadius:
              50, // 50 meters radius to consider the device not in movement
          locationAuthorizationRequest: "Always",
          disableElasticity:
              false, // We use elasticity to improve battery efficiency (if speed is high, location updates are delayed)
          elasticityMultiplier:
              10, // multiplier for elasticity effect (higher -> more delay in location updates). Default is 1.
          showsBackgroundLocationIndicator: true,
          allowIdenticalLocations: false,
        ),
        logger: bg.LoggerConfig(
          debug: false,
          logLevel: bg.LogLevel.info,
          logMaxDays: 3,
        ),
      ),
    );
    debugPrintC("Background location service initialized.");
  }

  static Future<void> startTracking() async {
    debugPrintC("Starting background location tracking...");
    final state = await bg.BackgroundGeolocation.state;
    if (!state.enabled) {
      await bg.BackgroundGeolocation.start();
      debugPrintC("Background location tracking started.");
    } else {
      debugPrintC("Background location tracking is already running.");
    }
  }

  static Future<bool> isTrackingEnabled() async {
    final state = await bg.BackgroundGeolocation.state;
    return state.enabled;
  }

  static Future<void> stopTracking() async {
    await bg.BackgroundGeolocation.stop();
    await bg.BackgroundGeolocation.destroyLocations();
    debugPrintC("Background location tracking stopped.");
  }

  static Future<bool> isBatteryOptimizationIgnored() async {
    try {
      final isIgnoring = await bg.DeviceSettings.isIgnoringBatteryOptimizations;
      if (isIgnoring) {
        debugPrintC("Battery optimization ignoring status: $isIgnoring");
        return true;
      }
    } catch (e) {
      debugPrintC("Error checking battery optimization status: $e");
    }
    return false;
  }

  // Not used at the moment, but kept for potential future use.
  static Future<void> showIgnoreBatteryOptimizationsWindow() async {
    try {
      await bg.DeviceSettings.showIgnoreBatteryOptimizations();
      debugPrintC("Requested to show ignore battery optimizations window.");
    } catch (e) {
      debugPrintC("Error showing ignore battery optimizations window: $e");
    }
  }

  static Future<bg.Location> getForegroundCurrentPosition() async {
    bg.Location location = await bg.BackgroundGeolocation.getCurrentPosition(
      persist: false,
      samples: 3,
      desiredAccuracy:
          10, // 10 meters accuracy for foreground location fetches, since it's used for user-initiated actions that require more precision
      maximumAge:
          15000, // (in milliseconds) if a cached location is available and is not older than 15 seconds, it will be returned
      timeout: 60, // Max time (in seconds) to wait for a location fix
      extras: {"reason": "foreground location"},
    );
    return location;
  }

  static Future<List<Map<String, String>>> getLocationLog() async {
    List<Map<String, String>> locations = [];
    List<dynamic> storedLocations = await bg.BackgroundGeolocation.getLocations(
      bg.LocationQuery(limit: 100, page: 0, order: bg.LocationQuery.ORDER_DESC),
    );
    debugPrintC(
      "Retrieved ${storedLocations.length} stored locations from the database",
    );
    for (var location in storedLocations) {
      // Convert the timestamp in ISO 8601 format
      // to a DateTime object (in local timezone)
      final String? locationTimestampStr = location["timestamp"];
      final DateTime? locationDatetime = locationTimestampStr != null
          ? DateTime.parse(locationTimestampStr).toLocal()
          : null;
      final String locationDatetimeStr = locationDatetime != null
          ? datetimeAsStringWithoutMilliseconds(locationDatetime)
          : "n/a";
      locations.add({
        "location_id": location["location_id"]?.toString() ?? "n/a",
        "latitude": location["latitude"]?.toString() ?? "n/a",
        "longitude": location["longitude"]?.toString() ?? "n/a",
        "accuracy": location["accuracy"]?.toString() ?? "n/a",
        "is_moving": location["is_moving"]?.toString() ?? "n/a",
        "activity": location["activity"]?.toString() ?? "n/a",
        "created_at": locationDatetimeStr,
      });
    }
    return locations;
  }
}
