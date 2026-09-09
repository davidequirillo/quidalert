// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:math';
import 'package:flutter_background_geolocation/flutter_background_geolocation.dart'
    as bg;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:jose/jose.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:quidalert_flutter/config.dart';
import 'package:quidalert_flutter/utils/strings.dart';

// The following class is used for background location tracking.
// It's a wrapper around the flutter_background_geolocation plugin,
// which starts in the main.dart file and runs in the background even when the app is closed.
class BackgroundLocationService {
  static double distanceLimitInMeters = 350; // 350 meters
  static int dailyLimitInSeconds = 3600 * 24; // 24 hours
  static double accuracyLimitInMeters = 150; // 150 meters
  static final FlutterSecureStorage _storage = FlutterSecureStorage();
  static SharedPreferences? _prefs;

  static Future<void> init() async {
    await ensurePrefsLoaded();
    debugPrintC(
      "Cleaning pre-existing background location listeners and locations...",
    );
    await bg.BackgroundGeolocation.removeListeners();
    debugPrintC("Initializing background location service...");
    bg.BackgroundGeolocation.onLocation((bg.Location location) async {
      debugPrintC(
        "Background location received: ${location.coords.latitude}, ${location.coords.longitude}, location_id: ${location.uuid}",
      );
      try {
        await handleLocation(location, withActivityCheck: true);
      } catch (e) {
        debugPrintC(
          '[BackgroundLocationService, onLocation] Unknown error handling location: $e',
        );
      }
    });
    bg.BackgroundGeolocation.onHeartbeat((bg.HeartbeatEvent event) async {
      debugPrintC(
        "Background heartbeat received, checking if the last cached location must be sent to the backend...",
      );
      bg.Location? location = event.location;
      if (location != null) {
        debugPrintC(
          "Heartbeat event contains a location: ${location.coords.latitude}, ${location.coords.longitude} location_id: ${location.uuid}",
        );
        try {
          await handleLocation(location);
        } catch (e) {
          debugPrintC(
            '[BackgroundLocationService, heartbeat] Unknown error handling location: $e',
          );
        }
      } else {
        debugPrintC("No location data in heartbeat event, skipping update");
      }
    });
    bg.BackgroundGeolocation.onMotionChange((bg.Location location) async {
      debugPrintC(
        "Background motion change received: ${location.coords.latitude}, ${location.coords.longitude}, location_id: ${location.uuid}",
      );
      try {
        await handleLocation(location);
      } catch (e) {
        debugPrintC(
          '[BackgroundLocationService, onMotionChange] Unknown error handling motion change location: $e',
        );
      }
    });
    await bg.BackgroundGeolocation.ready(
      bg.Config(
        reset: true,
        debug: false,
        allowIdenticalLocations: false,
        enableHeadless: true,
        persistence: bg.PersistenceConfig(
          persistMode: bg.PersistMode.all,
          maxRecordsToPersist: 50,
          maxDaysToPersist: 30,
        ),
        autoSync: false,
        desiredAccuracy: bg
            .Config
            .DESIRED_ACCURACY_MEDIUM, // balance between accuracy and battery
        distanceFilter:
            distanceLimitInMeters, // in meters (movement threshold for update location events)
        heartbeatInterval: 7200, // heartbeat event every 2 hours
        stopTimeout:
            1, // the device is considered stationary after 1 minute of "no movement" (see stationaryRadius)
        stationaryRadius:
            50, // 50 meters radius to consider the device not in movement
        stopOnStationary:
            false, // we don't stop completely the background service when stationary
        speedJumpFilter: 40,
        stopOnTerminate: false,
        startOnBoot: true,
        disableMotionActivityUpdates: false,
        // Android specific settings: ensures the notification is shown while the service is running
        foregroundService: true,
        notification: bg.Notification(
          title: "Background Location Service",
          text: "Tracking your location in the background.",
          priority: bg.NotificationPriority.high,
          sticky: true,
        ),
        // iOS specific settings
        pausesLocationUpdatesAutomatically: false,
        showsBackgroundLocationIndicator: true,
      ),
    );
    debugPrintC("Background location service initialized.");
  }

  // Ensures that the shared preferences instance is loaded.
  // If the shared preferences instance is not null, it won't be reloaded.
  static Future<void> ensurePrefsLoaded() async {
    _prefs ??= await SharedPreferences.getInstance();
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
    await _prefs?.remove('lastSentLocationLat');
    await _prefs?.remove('lastSentLocationLng');
    await _prefs?.remove('lastSentAt');
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

  static Future<void> handleLocation(
    bg.Location location, {
    bool withActivityCheck = false,
  }) async {
    final now = DateTime.now();
    final locationAccuracy = location.coords.accuracy;
    debugPrintC(
      "Handling location: ${location.coords.latitude}, ${location.coords.longitude}, accuracy=${locationAccuracy.toStringAsFixed(2)} meters",
    );
    // Skip handling the location if it is a sample location.
    if (location.sample == true) {
      debugPrintC("Location is a sample, skipping update");
      return;
    }
    // Skip handling the location if its accuracy is worse than the configured limit.
    if (locationAccuracy > accuracyLimitInMeters) {
      debugPrintC(
        "Location accuracy is worse than the limit (${accuracyLimitInMeters.toStringAsFixed(2)} meters), skipping update",
      );
      return;
    }
    // We retrieve the last sent location and timestamp from shared preferences
    // to determine if we should send the new location to the backend (server).
    // Note: we cannot use static variables to store and retrieve them, because the two BackgroundLocationService classes
    // (one running in the background as headless task, and one in the foreground at app level) run in separate isolates and do not share static variables,
    // so we use shared preferences to persist the last sent location and related timestamp.
    final lastSentLocationLat = _prefs?.getDouble('lastSentLocationLat');
    final lastSentLocationLng = _prefs?.getDouble('lastSentLocationLng');
    final lastSentAt = _prefs?.getInt('lastSentAt');
    final lastSentAtDatetime = lastSentAt != null
        ? DateTime.fromMillisecondsSinceEpoch(lastSentAt)
        : null;
    if (lastSentLocationLat != null &&
        lastSentLocationLng != null &&
        lastSentAtDatetime != null) {
      final distance = calculateDistance(
        lastSentLocationLat,
        lastSentLocationLng,
        location.coords.latitude,
        location.coords.longitude,
      );
      // We skip sending the location to the backend if the distance is less than 350 meters,
      // but if 24 hours have passed, we send it anyway, even if the distance is less than 350 meters,
      // to ensure that the backend has a recent location for the user.
      final secondsSinceLast = now.difference(lastSentAtDatetime).inSeconds;
      debugPrintC(
        "Difference between last sent location and current location: ${distance.toStringAsFixed(2)} meters, $secondsSinceLast seconds",
      );
      if ((distance < distanceLimitInMeters) &&
          (secondsSinceLast < dailyLimitInSeconds)) {
        debugPrintC("Location update skipped");
        return;
      }
      // Activity-based location update check:
      // "still", "walking", "on_foot", "running", "on_bicycle", "in_vehicle", "unknown"
      // We perform an additional check based on a user's current activity type.
      // If the activity check is enabled, we will skip location updates based on the user's current activity and the time since the last update.
      // The time required between location updates varies depending on the activity type (more speed-intensive activities require longer intervals).
      if (withActivityCheck) {
        switch (location.activity.type) {
          case "still":
            if (secondsSinceLast < 60) {
              debugPrintC(
                "Location update skipped (not enough time since last 'still' activity)",
              );
              return;
            }
            break;
          case "walking":
          case "on_foot":
            if (secondsSinceLast < 300) {
              debugPrintC(
                "Location update skipped (not enough time since last 'walking'/'on_foot' activity)",
              );
              return;
            }
            break;
          case "running":
            if (secondsSinceLast < 600) {
              debugPrintC(
                "Location update skipped (not enough time since last 'running' activity)",
              );
              return;
            }
            break;
          case "on_bicycle":
            if (secondsSinceLast < 900) {
              debugPrintC(
                "Location update skipped (not enough time since last 'on_bicycle' activity)",
              );
              return;
            }
            break;
          case "in_vehicle":
            if (secondsSinceLast < 1800) {
              debugPrintC(
                "Location update skipped (not enough time since last 'in_vehicle' activity)",
              );
              return;
            }
            break;
          case "unknown":
            if (secondsSinceLast < 3600) {
              debugPrintC(
                "Location update skipped (not enough time since last 'unknown' activity)",
              );
              return;
            }
            break;
          default:
            break;
        }
      }
    }
    final currLocationLat = location.coords.latitude;
    final currLocationLng = location.coords.longitude;
    final currLocationAt = now.millisecondsSinceEpoch;
    // Optimistically update the last sent location in SharedPreferences before sending to the backend
    // so the app has the latest location stored quickly (locally).
    // If another similar location is fetched shortly after the current one, it will have the correct latest location to compare against.
    await Future.wait([
      _prefs?.setDouble('lastSentLocationLat', currLocationLat) ??
          Future.value(false),
      _prefs?.setDouble('lastSentLocationLng', currLocationLng) ??
          Future.value(false),
      _prefs?.setInt('lastSentAt', currLocationAt) ?? Future.value(false),
    ]);
    final isSuccess = await sendToBackend(
      currLocationLat,
      currLocationLng,
      location.uuid,
      location.coords.accuracy,
      location.isMoving,
      location.coords.speed,
      location.activity.type,
    );
    if (!isSuccess) {
      // If sending to the backend fails, rollback the last sent location in SharedPreferences
      await Future.wait([
        lastSentLocationLat != null
            ? (_prefs?.setDouble('lastSentLocationLat', lastSentLocationLat) ??
                  Future.value(false))
            : (_prefs?.remove('lastSentLocationLat') ?? Future.value(false)),
        lastSentLocationLng != null
            ? (_prefs?.setDouble('lastSentLocationLng', lastSentLocationLng) ??
                  Future.value(false))
            : (_prefs?.remove('lastSentLocationLng') ?? Future.value(false)),
        lastSentAt != null
            ? (_prefs?.setInt('lastSentAt', lastSentAt) ?? Future.value(false))
            : (_prefs?.remove('lastSentAt') ?? Future.value(false)),
      ]);
    }
  }

  static double calculateDistance(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    const R = 6371000; // Earth radius in meters
    final dLat = _degreesToRadians(lat2 - lat1);
    final dLon = _degreesToRadians(lon2 - lon1);
    final a =
        sin(dLat / 2) * sin(dLat / 2) +
        cos(_degreesToRadians(lat1)) *
            cos(_degreesToRadians(lat2)) *
            sin(dLon / 2) *
            sin(dLon / 2);
    final c = 2 * atan2(sqrt(a), sqrt(1 - a));
    return R * c;
  }

  static double _degreesToRadians(double degrees) => degrees * pi / 180;

  static Future<bool> sendToBackend(
    double lat,
    double lng,
    String locationId,
    double accuracy,
    bool isMoving,
    double speed,
    String activity,
  ) async {
    String? token;
    try {
      token = await getGpsToken();
    } catch (e) {
      debugPrintC("Error retrieving GPS token: $e");
      return false;
    }
    if (token == null) return false;
    debugPrintC("Sending to backend: Lat=$lat, Lng=$lng");
    final String url = "${AppConfig.apiUrl}/update-gps-position";
    try {
      final uri = Uri.parse(url);
      final response = await http.post(
        uri,
        headers: {
          "Authorization": "Bearer $token",
          "Content-Type": "application/json",
        },
        body: jsonEncode({
          "latitude": lat,
          "longitude": lng,
          "location_id": locationId,
          "accuracy": accuracy,
          "is_moving": isMoving,
          "speed": speed,
          "activity": activity,
        }),
      );
      if (response.statusCode == 200) {
        debugPrintC('Gps location update successful');
        return true;
      } else {
        debugPrintC('Server error: ${response.statusCode} - ${response.body}');
        return false;
      }
    } catch (e) {
      debugPrintC("Error sending location to backend: $e");
      return false;
    }
  }

  static Future<String?> getGpsToken() async {
    final gpsToken = await _storage.read(key: "gpsToken");
    if (gpsToken != null) {
      debugPrintC("GPS token loaded from storage");
      if (_isTokenExpired(gpsToken)) {
        debugPrintC("GPS token is expired, returning null");
        return null;
      }
    } else {
      debugPrintC("No GPS token found in storage");
      return null;
    }
    return gpsToken;
  }

  static bool _isTokenExpired(String token) {
    final jwt = JsonWebToken.unverified(token);
    final exp = jwt.claims.getTyped('exp');
    if (exp == null) return true;
    final expiry = DateTime.fromMillisecondsSinceEpoch(exp * 1000, isUtc: true);
    return DateTime.now().toUtc().isAfter(expiry);
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
    List<dynamic> storedLocations = await bg.BackgroundGeolocation.locations;
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
        "uuid": location["uuid"]?.toString() ?? "n/a",
        "latitude": location["coords"]?["latitude"]?.toString() ?? "n/a",
        "longitude": location["coords"]?["longitude"]?.toString() ?? "n/a",
        "accuracy": location["coords"]?["accuracy"]?.toString() ?? "n/a",
        "is_moving": location["is_moving"]?.toString() ?? "n/a",
        "activity": location["activity"]["type"]?.toString() ?? "n/a",
        "timestamp": locationDatetimeStr,
      });
    }
    return locations;
  }
}
