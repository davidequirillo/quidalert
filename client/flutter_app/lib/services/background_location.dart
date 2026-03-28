// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
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
  static double distanceFilterInMeters = 250; // 250 meters
  static int timeFilterInSeconds = 300; // 30 minutes
  static int dailyLimitInSeconds = 86400; // 24 hours
  static double distanceLimitInMeters = 15000; // 15 km
  static double accuracyLimitInMeters = 500; // 500 meters
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
      await handleLocation(location);
    });
    bg.BackgroundGeolocation.onHeartbeat((bg.HeartbeatEvent event) async {
      debugPrintC(
        "Background heartbeat received, fetching current location...",
      );
      await bg.BackgroundGeolocation.getCurrentPosition();
      // Note: it triggers the "onLocation" event too
    });
    await bg.BackgroundGeolocation.ready(
      bg.Config(
        allowIdenticalLocations: false,
        desiredAccuracy: bg
            .Config
            .DESIRED_ACCURACY_MEDIUM, // balance between accuracy and battery
        distanceFilter: distanceFilterInMeters,
        heartbeatInterval: timeFilterInSeconds, // get location every 30 minutes
        stopOnStationary: false, // we don't stop completely when stationary
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
    if (_lastSentLocation != null && _lastSentTime != null) {
      final distance = _calculateDistance(
        _lastSentLocation!.coords.latitude,
        _lastSentLocation!.coords.longitude,
        location.coords.latitude,
        location.coords.longitude,
      );
      double accuracyMeters = location.coords.accuracy;
      debugPrintC(
        "Location accuracy=${accuracyMeters.toStringAsFixed(2)} meters",
      );
      if (accuracyMeters > accuracyLimitInMeters &&
          (distance > accuracyLimitInMeters)) {
        debugPrintC("Location accuracy is bad, skipping update");
        return;
      }
      final secondsSinceLast = now.difference(_lastSentTime!).inSeconds;
      // don't send the update to the backend if not enough time is passed
      // or there hasn't been a significant movement,
      // but force the update after a daily limit or if the user moved very far away
      debugPrintC(
        "Difference between last sent location and current location: ${distance.toStringAsFixed(2)} meters, $secondsSinceLast seconds",
      );
      if ((distance < distanceFilterInMeters ||
              secondsSinceLast < timeFilterInSeconds) &&
          (distance < distanceLimitInMeters) &&
          (secondsSinceLast < dailyLimitInSeconds)) {
        debugPrintC("Location update skipped");
        return;
      }
    }
    await sendToBackend(location.coords.latitude, location.coords.longitude);
    _lastSentLocation = location;
    _lastSentTime = now;
  }

  static double _calculateDistance(
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

  static Future<void> sendToBackend(double lat, double lng) async {
    final token = await getGpsToken();
    if (token == null) return;
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
      } else {
        debugPrintC('Server error: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      debugPrintC("Error sending location to backend: $e");
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
}
