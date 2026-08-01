// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_background_geolocation/flutter_background_geolocation.dart'
    as bg;
import 'package:geocoding/geocoding.dart';
import 'package:quidalert_flutter/services/background_location.dart';
import 'package:quidalert_flutter/utils/strings.dart';

class LocationClientPermissionDeniedException implements Exception {
  final String message;
  LocationClientPermissionDeniedException([
    this.message = 'Location permissions are denied',
  ]);
  @override
  String toString() => 'LocationClientPermissionDeniedException: $message';
}

class LocationClientAddressNotFoundException implements Exception {
  final String message;
  LocationClientAddressNotFoundException([
    this.message = 'No address found for the given coordinates',
  ]);
  @override
  String toString() => 'LocationClientAddressNotFoundException: $message';
}

class LocationClientFetchPositionException implements Exception {
  final String message;
  LocationClientFetchPositionException([
    this.message = 'Error fetching position',
  ]);
  @override
  String toString() => 'LocationClientFetchPositionException: $message';
}

class LocationClientAccuracyLowException implements Exception {
  final String message;
  LocationClientAccuracyLowException([
    this.message = 'Location accuracy is low',
  ]);
  @override
  String toString() => 'LocationClientAccuracyLowException: $message';
}

class LocationClientTimeoutException implements Exception {
  final String message;
  LocationClientTimeoutException([this.message = 'Location fetch timed out']);
  @override
  String toString() => 'LocationClientTimeoutException: $message';
}

// Main class for fetching location and translating it to an address
// Used for foreground location tracking (e.g., when user is filling an alert form)
class LocationClient extends ChangeNotifier {
  bg.Location? _currentPosition;
  String? _currentAddress;
  bool _isFetching = false;
  double accuracyLimit = 50.0; // meters

  String? get currentAddress => _currentAddress;

  Map<String, double>? get currentPosition {
    if (_currentPosition != null) {
      final Map<String, double> gpsMap = {
        "latitude": _currentPosition!.coords.latitude,
        "longitude": _currentPosition!.coords.longitude,
        "accuracy": _currentPosition!.coords.accuracy,
      };
      return gpsMap;
    } else {
      return null;
    }
  }

  bool get isFetching {
    return _isFetching;
  }

  // Used for foreground location tracking (e.g., when user is filling an alert form)
  Future<Map<String, double>?> fetchLocation() async {
    _isFetching = true;
    notifyListeners();
    debugPrintC("Fetching foreground location...");
    try {
      try {
        _currentPosition =
            await BackgroundLocationService.getForegroundCurrentPosition();
      } on bg.LocationError catch (e) {
        final msg = e.message.toLowerCase();
        // it can throw an error code (int) if the position cannot be fetched, for example:
        // 1: Location unknown, 2: Location timeout, 3: Permission denied, 4: Network error, 408: Network timeout
        debugPrintC("Error fetching foreground location: ${e.code}");
        if (e.code == 1 || msg.contains("unknown")) {
          throw LocationClientFetchPositionException("Location unknown");
        } else if (e.code == 3 || msg.contains("permission")) {
          throw LocationClientPermissionDeniedException();
        } else if (e.code == 4 || msg.contains("network")) {
          throw LocationClientFetchPositionException("Network error");
        } else if ((e.code == 2) ||
            (e.code == 408) ||
            msg.contains("timeout")) {
          throw LocationClientTimeoutException();
        } else {
          throw LocationClientFetchPositionException("Error code: ${e.code}");
        }
      } catch (e) {
        debugPrintC("Unknown error during foreground location fetch: $e");
        throw LocationClientFetchPositionException(e.toString());
      }
      debugPrintC(
        "Fetched position: ${_currentPosition!.coords.latitude}, ${_currentPosition!.coords.longitude}, accuracy: ${_currentPosition!.coords.accuracy} meters",
      );
      if (_currentPosition!.coords.accuracy > accuracyLimit) {
        throw LocationClientAccuracyLowException(
          "${_currentPosition!.coords.accuracy} m",
        );
      }
      _currentAddress = await translateToAddress(
        _currentPosition!.coords.latitude,
        _currentPosition!.coords.longitude,
      );
      if (_currentAddress == null || _currentAddress!.isEmpty) {
        debugPrintC("Address is <empty> for the current position");
        throw LocationClientAddressNotFoundException();
      }
      return currentPosition;
    } on LocationClientPermissionDeniedException catch (e) {
      debugPrintC("Location permission denied: ${e.message}");
      _currentPosition = null;
      _currentAddress = null;
      rethrow;
    } on LocationClientFetchPositionException catch (e) {
      debugPrintC("Error fetching position: ${e.message}");
      _currentPosition = null;
      _currentAddress = null;
      rethrow;
    } on LocationClientAccuracyLowException catch (e) {
      debugPrintC("Location accuracy is low: ${e.message}");
      _currentPosition = null;
      _currentAddress = null;
      rethrow;
    } on LocationClientTimeoutException catch (_) {
      debugPrintC("Location fetch timeout");
      _currentPosition = null;
      _currentAddress = null;
      rethrow;
    } catch (e) {
      debugPrintC("Unknown error fetching foreground location: $e");
      _currentPosition = null;
      _currentAddress = null;
      rethrow;
    } finally {
      debugPrintC("Finished fetching foreground location");
      _isFetching = false;
      notifyListeners();
      debugPrintC("Notified listeners about fetching state change");
    }
  }

  Future<String?> translateToAddress(double latitude, double longitude) async {
    debugPrintC("Translating position to address: $latitude, $longitude");
    try {
      List<Placemark> p = await placemarkFromCoordinates(latitude, longitude);
      if (p.isNotEmpty) {
        debugPrintC("Address found");
        final addr = p.first;
        return "${addr.street}, ${addr.locality}, ${addr.administrativeArea}, ${addr.country}";
      } else {
        debugPrintC("No address found");
        return null;
      }
    } on NoResultFoundException catch (_) {
      debugPrintC("No address found for the given coordinates");
      return null;
    } catch (e) {
      debugPrintC("Unknown error translating position to address: $e");
      return null;
    }
  }
}
