// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
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
  DateTime? _lastFetchingTime;

  static const double accuracy =
      10; // meters, high accuracy, used for fetching location with the "getCurrentPosition" method
  static const int distanceBoundary = 30; // meters
  static const int timeBoundary = 60; // seconds
  // distanceBoundary and timeBoundary, used to optimize battery
  // consumption by not updating address if user hasn't moved significantly
  // or if enough time hasn't passed

  static const int maxTimeout = 15; // seconds

  String? get currentAddress => _currentAddress;

  Map<String, double>? get currentPosition {
    if (_currentPosition != null) {
      final Map<String, double> gpsMap = {
        "lat": _currentPosition!.coords.latitude,
        "long": _currentPosition!.coords.longitude,
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
  Future<void> fetchLocation({bool forceUpdate = false}) async {
    _isFetching = true;
    notifyListeners();
    double accuracy = LocationClient.accuracy;
    int distanceBoundary = LocationClient.distanceBoundary;
    debugPrintC(
      "Fetching foreground location with accuracy: $accuracy m, distance boundary: $distanceBoundary m, force update: $forceUpdate",
    );
    try {
      bg.Location returnedPosition;
      try {
        returnedPosition =
            await BackgroundLocationService.getForegroundCurrentPosition();
      } catch (errorCode) {
        // it can throw an error code (int) if the position cannot be fetched, for example:
        // 0: Location unknown, 1: Location permission denied, 2: Network error, 4: Location timeout
        debugPrintC("Error during foreground location fetch: $errorCode");
        if (errorCode == 0) {
          throw LocationClientFetchPositionException("Location unknown");
        } else if (errorCode == 1) {
          throw LocationClientPermissionDeniedException();
        } else if (errorCode == 2) {
          throw LocationClientFetchPositionException("Network error");
        } else if (errorCode == 4) {
          throw LocationClientTimeoutException();
        } else {
          throw LocationClientFetchPositionException("Error code: $errorCode");
        }
      }
      debugPrintC(
        "Fetched position: ${returnedPosition.coords.latitude}, ${returnedPosition.coords.longitude}",
      );
      // We optimize battery consumption
      // by not updating the relative address if the user
      // hasn't moved significantly or enough time hasn't passed since the last fetching
      if (_currentPosition != null) {
        bool isTimePassed =
            (_lastFetchingTime == null) ||
            (DateTime.now().difference(_lastFetchingTime!).inSeconds >
                LocationClient.timeBoundary);
        debugPrintC(
          "Time has passed? $isTimePassed (last fetching: $_lastFetchingTime)",
        );
        double gap = BackgroundLocationService.calculateDistance(
          _currentPosition!.coords.latitude,
          _currentPosition!.coords.longitude,
          returnedPosition.coords.latitude,
          returnedPosition.coords.longitude,
        );
        debugPrintC(
          "Distance from last position: $gap m (threshold: ${LocationClient.distanceBoundary} m)",
        );
        if (((gap < LocationClient.distanceBoundary) || (!isTimePassed)) &&
            (!forceUpdate)) {
          debugPrintC(
            "Minimum movement or time not passed: not updating position and address",
          );
          return;
        }
      }
      _currentPosition = returnedPosition;
      _lastFetchingTime = DateTime.now();
      _currentAddress = await _translateToAddress(_currentPosition!);
      if (_currentAddress == null || _currentAddress!.isEmpty) {
        debugPrintC("Address is <empty> for the current position");
        throw LocationClientAddressNotFoundException();
      }
      return;
    } on LocationClientPermissionDeniedException catch (_) {
      _currentPosition = null;
      _currentAddress = null;
      rethrow;
    } on LocationClientFetchPositionException catch (_) {
      _currentPosition = null;
      _currentAddress = null;
      rethrow;
    } on LocationClientAddressNotFoundException catch (_) {
      _currentAddress = null;
      rethrow;
    } on LocationClientTimeoutException catch (_) {
      debugPrintC("Location fetch timed out");
      _currentPosition = null;
      _currentAddress = null;
      rethrow;
    } on NoResultFoundException catch (_) {
      debugPrintC("No address found for the current position");
      _currentAddress = null;
      throw LocationClientAddressNotFoundException();
    } catch (e) {
      debugPrintC("Error fetching foreground location: $e");
      _currentPosition = null;
      _currentAddress = null;
      throw LocationClientFetchPositionException(e.toString());
    } finally {
      debugPrintC("Finished fetching foreground location");
      _isFetching = false;
      notifyListeners();
      debugPrintC("Notified listeners about fetching state change");
    }
  }

  Future<String?> _translateToAddress(bg.Location pos) async {
    debugPrintC(
      "Translating position to address: ${pos.coords.latitude}, ${pos.coords.longitude}",
    );
    try {
      List<Placemark> p = await placemarkFromCoordinates(
        pos.coords.latitude,
        pos.coords.longitude,
      );
      if (p.isNotEmpty) {
        final addr = p.first;
        return "${addr.street}, ${addr.locality}, ${addr.administrativeArea}, ${addr.country}";
      } else {
        return null;
      }
    } on NoResultFoundException catch (_) {
      rethrow;
    } catch (e) {
      debugPrintC("Unknown error translating position to address: $e");
      return null;
    }
  }
}
