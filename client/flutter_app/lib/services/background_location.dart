// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:math';
import 'package:flutter_background_geolocation/flutter_background_geolocation.dart'
    as bg;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:jose/jose.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:quidalert_flutter/config.dart' as config;
import 'package:quidalert_flutter/utils/strings.dart';

class BackgroundLocationService {
  static bg.Location? _lastSentLocation;
  static DateTime? _lastSentTime;
  static double distanceLimitInMeters = 250; // 250 meters
  static int dailyLimitInSeconds = 86400; // 24 hours
  static double accuracyLimitInMeters = 150; // 150 meters
  static final FlutterSecureStorage _storage = FlutterSecureStorage();

  static Future<void> init() async {
    debugPrintC(
      "Cleaning pre-existing background location listeners and locations...",
    );
    //await bg.BackgroundGeolocation.removeListeners(); // not needed probably
    debugPrintC("Initializing background location service...");
    bg.BackgroundGeolocation.onLocation((bg.Location location) async {
      debugPrintC(
        "Background location received: ${location.coords.latitude}, ${location.coords.longitude}, location_id: ${location.uuid}",
      );
      if (location.isMoving) {
        debugPrintC("The device is moving, skipping update");
        return;
      }
      try {
        await handleLocation(location);
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
        if (location.isMoving) {
          debugPrintC("The device is moving, skipping update");
          return;
        }
        try {
          await handleHeartbeatLocation(location);
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
      if (location.isMoving) {
        debugPrintC("The device is moving, skipping update");
        return;
      }
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
        allowIdenticalLocations: false,
        maxRecordsToPersist: 50,
        autoSync: false,
        desiredAccuracy: bg
            .Config
            .DESIRED_ACCURACY_MEDIUM, // balance between accuracy and battery
        distanceFilter:
            250, // in meters (movement threshold for update location events)
        heartbeatInterval: 1800, // heartbeat event every 30 minutes
        stopTimeout:
            3, // the device is considered stationary after 3 minutes of "no movement" (see stationaryRadius)
        stationaryRadius:
            25, // 25 meters radius to consider the device not in movement
        stopOnStationary:
            false, // we don't stop completely the background service when stationary
        stopOnTerminate: false,
        startOnBoot: true,
        foregroundService:
            true, // keep the service running in the foreground to prevent it from being killed by the OS
        disableMotionActivityUpdates:
            true, // we don't need motion activity updates
        enableHeadless: true,
        debug: false,
      ),
    );
    debugPrintC("Background location service initialized.");
  }

  static Future<void> dispose() async {
    await bg.BackgroundGeolocation.stop();
    debugPrintC("Background location service disposed.");
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

  static Future<void> stopTracking() async {
    await bg.BackgroundGeolocation.stop();
    await bg.BackgroundGeolocation.destroyLocations();
    debugPrintC("Background location tracking stopped.");
    _lastSentLocation = null;
    _lastSentTime = null;
  }

  static Future<void> handleLocation(bg.Location location) async {
    final now = DateTime.now();
    final locationAccuracyInMeters = location.coords.accuracy;
    debugPrintC(
      "Handling location: ${location.coords.latitude}, ${location.coords.longitude}, accuracy=${locationAccuracyInMeters.toStringAsFixed(2)} meters",
    );
    if (locationAccuracyInMeters > accuracyLimitInMeters) {
      debugPrintC(
        "Location accuracy is worse than the limit (${accuracyLimitInMeters.toStringAsFixed(2)} meters), skipping update",
      );
      return;
    }
    if (_lastSentLocation != null && _lastSentTime != null) {
      final distance = calculateDistance(
        _lastSentLocation!.coords.latitude,
        _lastSentLocation!.coords.longitude,
        location.coords.latitude,
        location.coords.longitude,
      );
      // We skip sending the location to the backend if the distance is less than 250 meters,
      // but if 24 hours have passed, we send it anyway, even if the distance is less than 250 meters,
      // to ensure that the backend has a recent location for the user.
      final secondsSinceLast = now.difference(_lastSentTime!).inSeconds;
      debugPrintC(
        "Difference between last sent location and current location: ${distance.toStringAsFixed(2)} meters, $secondsSinceLast seconds",
      );
      if ((distance < distanceLimitInMeters) &&
          (secondsSinceLast < dailyLimitInSeconds)) {
        debugPrintC("Location update skipped");
        return;
      }
    }
    final success = await sendToBackend(
      location.coords.latitude,
      location.coords.longitude,
    );
    if (success) {
      _lastSentLocation = location;
      _lastSentTime = now;
    }
  }

  static Future<void> handleHeartbeatLocation(bg.Location location) async {
    final now = DateTime.now();
    bg.Location locationToSend;
    final locationAccuracyInMeters = location.coords.accuracy;
    debugPrintC(
      "Handling heartbeat location: ${location.coords.latitude}, ${location.coords.longitude}, accuracy=${locationAccuracyInMeters.toStringAsFixed(2)} meters",
    );
    if (locationAccuracyInMeters > accuracyLimitInMeters) {
      debugPrintC(
        "Location accuracy is worse than the limit (${accuracyLimitInMeters.toStringAsFixed(2)} meters), skipping update",
      );
      return;
    }
    if (_lastSentLocation != null && _lastSentTime != null) {
      final secondsSinceLast = now.difference(_lastSentTime!).inSeconds;
      debugPrintC(
        "Time between last sent location and current heartbeat location: $secondsSinceLast seconds",
      );
      if (secondsSinceLast < dailyLimitInSeconds) {
        debugPrintC("Heartbeat location will not be sent to the backend");
        return;
      } else {
        debugPrintC("Heartbeat location will be sent to the backend");
        locationToSend = location;
      }
    } else {
      debugPrintC(
        "No last sent location available, sending current heartbeat location to the backend",
      );
      locationToSend = location;
    }
    final success = await sendToBackend(
      locationToSend.coords.latitude,
      locationToSend.coords.longitude,
    );
    if (success) {
      _lastSentLocation = locationToSend;
      _lastSentTime = now;
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
    final token = await getGpsToken();
    if (token == null) return false;
    debugPrintC("Sending to backend: Lat=$lat, Lng=$lng");
    final String url = "${config.apiBaseUrl}/update-gps-position";
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
}
