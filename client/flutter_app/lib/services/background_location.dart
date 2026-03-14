// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/foundation.dart';
import 'dart:math';
import 'package:flutter_background_geolocation/flutter_background_geolocation.dart'
    as bg;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:jose/jose.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:quidalert_flutter/config.dart' as config;

class BackgroundLocationService {
  static bg.Location? _lastSentLocation;
  static DateTime? _lastSentTime;
  static double distanceFilterInMeters = 500; // 500 meters
  static int timeFilterInSeconds = 1800; // 30 minutes
  static int dailyLimitInSeconds = 86400; // 24 hours
  static final FlutterSecureStorage _storage = FlutterSecureStorage();

  static Future<void> init() async {
    bg.BackgroundGeolocation.onLocation((bg.Location location) {
      debugPrint(
        "Background location received: ${location.coords.latitude}, ${location.coords.longitude}",
      );
      _handleLocation(location);
    });

    await bg.BackgroundGeolocation.ready(
      bg.Config(
        desiredAccuracy: bg.Config.DESIRED_ACCURACY_HIGH,
        distanceFilter:
            distanceFilterInMeters, // get location if there is a significant movement
        stopOnTerminate: false,
        startOnBoot: true,
        foregroundService: true,
        heartbeatInterval: timeFilterInSeconds, // get location every 30 minutes
      ),
    );
  }

  static Future<void> startTracking() async {
    debugPrint("Starting background location tracking...");
    final state = await bg.BackgroundGeolocation.state;
    if (!state.enabled) {
      await bg.BackgroundGeolocation.start();
    }
  }

  static Future<void> stopTracking() async {
    await bg.BackgroundGeolocation.stop();
    debugPrint("Background location tracking stopped.");
  }

  static void _handleLocation(bg.Location location) {
    final now = DateTime.now();

    if (_lastSentLocation != null && _lastSentTime != null) {
      final distance = _calculateDistance(
        _lastSentLocation!.coords.latitude,
        _lastSentLocation!.coords.longitude,
        location.coords.latitude,
        location.coords.longitude,
      );
      final secondsSinceLast = now.difference(_lastSentTime!).inSeconds;
      // don't send the update to the backend if not enough time is passed
      // or there hasn't been a significant movement, but force the update after a daily limit
      if ((distance < distanceFilterInMeters ||
              secondsSinceLast < timeFilterInSeconds) &&
          secondsSinceLast < dailyLimitInSeconds) {
        return;
      }
    }
    sendToBackend(location.coords.latitude, location.coords.longitude);
    debugPrint(
      "Location sent to backend: Lat=${location.coords.latitude}, Lng=${location.coords.longitude}",
    );
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
    debugPrint("Sending to backend: Lat=$lat, Lng=$lng");
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
        debugPrint('Gps location update successful');
      } else {
        if (kDebugMode) {
          debugPrint('Server error: ${response.statusCode} - ${response.body}');
        }
      }
    } catch (e) {
      if (kDebugMode) {
        debugPrint("Error sending location to backend: $e");
      }
    }
  }

  static Future<String?> getGpsToken() async {
    final gpsToken = await _storage.read(key: "gpsToken");
    if (gpsToken != null) {
      debugPrint("GPS token loaded from storage");
      if (_isTokenExpired(gpsToken)) {
        debugPrint("GPS token is expired, returning null");
        return null;
      }
    } else {
      debugPrint("No GPS token found in storage");
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
