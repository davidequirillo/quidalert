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
  static double SpeedLimitInKmH = 10; // 10 km/h
  static double distanceLimitInMeters = 250; // 250 meters
  static int timeIntervalInSeconds = 600; // 10 minutes
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
        await handleLocation(location, withTimeIntervalCheck: true);
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
            250, // in meters (movement threshold for update location events)
        heartbeatInterval: 1800, // heartbeat event every 30 minutes
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
    bool withTimeIntervalCheck = false,
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
    // Calculate the speed limit in meters per second based on the configured km/h limit.
    final speedLimit = BackgroundLocationService.SpeedLimitInKmH * 1000 / 3600;
    if (location.isMoving &&
        (location.coords.speed < 0 || location.coords.speed > speedLimit)) {
      debugPrintC(
        "The device is moving too fast or with an invalid speed, skipping update",
      );
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
      // We skip sending the location to the backend if the distance is less than 250 meters,
      // but if 24 hours have passed, we send it anyway, even if the distance is less than 250 meters,
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
      if (withTimeIntervalCheck) {
        if (secondsSinceLast < timeIntervalInSeconds) {
          debugPrintC(
            "Location update paused due to short interval since last update",
          );
          return;
        }
      }
    }
    final isSuccess = await sendToBackend(
      location.coords.latitude,
      location.coords.longitude,
    );
    if (isSuccess) {
      await _prefs?.setDouble('lastSentLocationLat', location.coords.latitude);
      await _prefs?.setDouble('lastSentLocationLng', location.coords.longitude);
      await _prefs?.setInt('lastSentAt', now.millisecondsSinceEpoch);
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

  static Future<bool> sendToBackend(double lat, double lng) async {
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
        body: jsonEncode({"latitude": lat, "longitude": lng}),
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
      final double? speed = location["coords"]?["speed"] as double?;
      final double? speedKmh = (speed != null) ? (speed * 3.6) : null;
      final String speedKmhStr = (speedKmh != null) && (speedKmh >= 0)
          ? speedKmh.toStringAsFixed(1) + " km/h"
          : "n/a";
      locations.add({
        "uuid": location["uuid"]?.toString() ?? "n/a",
        "latitude": location["coords"]?["latitude"]?.toString() ?? "n/a",
        "longitude": location["coords"]?["longitude"]?.toString() ?? "n/a",
        "accuracy": location["coords"]?["accuracy"]?.toString() ?? "n/a",
        "is_moving": location["is_moving"]?.toString() ?? "n/a",
        "speed": speedKmhStr,
        "timestamp": locationDatetimeStr,
      });
    }
    return locations;
  }
}
