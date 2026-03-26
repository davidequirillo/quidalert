// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:geocoding/geocoding.dart';
import 'package:quidalert_flutter/utils/strings.dart';

class LocationClientServiceDisabledException implements Exception {
  final String message;
  LocationClientServiceDisabledException([
    this.message = 'Location services are disabled',
  ]);
  @override
  String toString() => 'LocationClientServiceDisabledException: $message';
}

class LocationClientPermissionDeniedException implements Exception {
  final String message;
  LocationClientPermissionDeniedException([
    this.message = 'Location permissions are denied',
  ]);
  @override
  String toString() => 'LocationClientPermissionDeniedException: $message';
}

class LocationClientPermissionsForeverException implements Exception {
  final String message;
  LocationClientPermissionsForeverException([
    this.message = 'Location permissions are permanently denied',
  ]);
  @override
  String toString() => 'LocationClientPermissionsForeverException: $message';
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
  Position? _currentPosition;
  String? _currentAddress;
  bool _isFetching = false;
  DateTime? _lastFetchingTime;

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
        "lat": _currentPosition!.latitude,
        "long": _currentPosition!.longitude,
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
    int distanceFilterValue = forceUpdate ? 0 : LocationClient.distanceBoundary;
    debugPrintC(
      "Fetching location with distance filter: $distanceFilterValue m, force update: $forceUpdate",
    );
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        debugPrintC("Location services are disabled");
        throw LocationClientServiceDisabledException();
      }
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        debugPrintC("Location permissions are denied, requesting permissions");
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          debugPrintC("Location permissions are still denied after requesting");
          throw LocationClientPermissionDeniedException();
        }
      }
      if (permission == LocationPermission.deniedForever) {
        debugPrintC("Location permissions are permanently denied");
        throw LocationClientPermissionsForeverException();
      }
      debugPrintC("Location permissions granted, fetching position");
      Position returnedPosition = await Geolocator.getCurrentPosition(
        locationSettings: LocationSettings(
          accuracy: LocationAccuracy.high,
          distanceFilter:
              distanceFilterValue, // we update gps position only if moved significantly (to save battery)
          timeLimit: const Duration(
            seconds: LocationClient.maxTimeout,
          ), // timeout after x seconds
        ),
      );
      debugPrintC(
        "Fetched position: ${returnedPosition.latitude}, ${returnedPosition.longitude}",
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
        double gap = Geolocator.distanceBetween(
          _currentPosition!.latitude,
          _currentPosition!.longitude,
          returnedPosition.latitude,
          returnedPosition.longitude,
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
    } on LocationClientServiceDisabledException catch (_) {
      _currentPosition = null;
      _currentAddress = null;
      rethrow;
    } on LocationClientPermissionDeniedException catch (_) {
      _currentPosition = null;
      _currentAddress = null;
      rethrow;
    } on LocationClientPermissionsForeverException catch (_) {
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
    } on PermissionDeniedException catch (_) {
      _currentPosition = null;
      _currentAddress = null;
      throw LocationClientPermissionDeniedException();
    } on LocationServiceDisabledException catch (_) {
      _currentPosition = null;
      _currentAddress = null;
      throw LocationClientServiceDisabledException();
    } on TimeoutException catch (_) {
      // Geolocator throws a TimeoutException if the position cannot be fetched within the specified time limit
      debugPrintC(
        "Location fetch timed out, trying to get last known position",
      );
      Position? lastPos = await Geolocator.getLastKnownPosition();
      if (lastPos != null) {
        debugPrintC(
          "Last known position: ${lastPos.latitude}, ${lastPos.longitude}, using it as current position",
        );
        _currentPosition = lastPos;
        try {
          _currentAddress = await _translateToAddress(_currentPosition!);
        } catch (_) {
          _currentAddress = null;
        }
      } else {
        debugPrintC("No last known position available");
        _currentPosition = null;
        _currentAddress = null;
      }
      throw LocationClientTimeoutException();
    } on NoResultFoundException catch (_) {
      debugPrintC("No address found for the current position");
      _currentAddress = null;
      throw LocationClientAddressNotFoundException();
    } catch (e) {
      debugPrintC("Error fetching location: $e");
      _currentPosition = null;
      _currentAddress = null;
      throw LocationClientFetchPositionException(e.toString());
    } finally {
      debugPrintC("Finished fetching location");
      _isFetching = false;
      notifyListeners();
      debugPrintC("Notified listeners about fetching state change");
    }
  }

  Future<String?> _translateToAddress(Position pos) async {
    debugPrintC(
      "Translating position to address: ${pos.latitude}, ${pos.longitude}",
    );
    try {
      List<Placemark> p = await placemarkFromCoordinates(
        pos.latitude,
        pos.longitude,
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

  Future<void> openAppSettings() async {
    await Geolocator.openAppSettings();
  }
}
