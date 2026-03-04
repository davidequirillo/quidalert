// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:geocoding/geocoding.dart';

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

class LocationClient extends ChangeNotifier {
  Position? _currentPosition;
  String? _currentAddress;
  bool _isFetching = false;
  DateTime? _lastGeocodingTime;

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

  bool get isFetching => _isFetching;

  // Used for foreground location tracking (e.g., when user is filling an alert form)
  Future<void> fetchLocation({bool forceUpdate = false}) async {
    _isFetching = true;
    notifyListeners();
    int distanceFilterValue = forceUpdate ? 0 : LocationClient.distanceBoundary;
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        throw LocationClientServiceDisabledException();
      }
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          throw LocationClientPermissionDeniedException();
        }
      }
      if (permission == LocationPermission.deniedForever) {
        throw LocationClientPermissionsForeverException();
      }
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
      if (kDebugMode) {
        debugPrint(
          "Fetched position: ${returnedPosition.latitude}, ${returnedPosition.longitude}",
        );
      }
      // We optimize battery consumption
      // by not updating the relative address if the user
      // hasn't moved significantly or enough time hasn't passed since the last geocoding
      if (_currentPosition != null) {
        bool isTimePassed =
            (_lastGeocodingTime == null) ||
            (DateTime.now().difference(_lastGeocodingTime!).inSeconds >
                LocationClient.timeBoundary);
        if (kDebugMode) {
          debugPrint(
            "Time has passed? $isTimePassed (last geocoding: $_lastGeocodingTime)",
          );
        }
        double gap = Geolocator.distanceBetween(
          _currentPosition!.latitude,
          _currentPosition!.longitude,
          returnedPosition.latitude,
          returnedPosition.longitude,
        );
        if (kDebugMode) {
          debugPrint(
            "Distance from last position: $gap m (threshold: ${LocationClient.distanceBoundary} m)",
          );
        }
        if (((gap < LocationClient.distanceBoundary) || (!isTimePassed)) &&
            (!forceUpdate)) {
          if (kDebugMode) {
            debugPrint(
              "Minimum movement or time not passed: not updating address",
            );
          }
          _isFetching = false;
          notifyListeners();
          return;
        }
      }
      _currentPosition = returnedPosition;
      _lastGeocodingTime = DateTime.now();
      _currentAddress = await _translateToAddress(_currentPosition!);
      if (_currentAddress == null || _currentAddress!.isEmpty) {
        if (kDebugMode) {
          debugPrint("Address is <empty> for the current position");
        }
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
      Position? lastPos = await Geolocator.getLastKnownPosition();
      if (lastPos != null) {
        _currentPosition = lastPos;
        try {
          _currentAddress = await _translateToAddress(_currentPosition!);
        } catch (_) {
          _currentAddress = null;
        }
      } else {
        _currentPosition = null;
        _currentAddress = null;
      }
      throw LocationClientTimeoutException();
    } on NoResultFoundException catch (_) {
      if (kDebugMode) {
        debugPrint("No address found for the current position");
      }
      _currentAddress = null;
      throw LocationClientAddressNotFoundException();
    } catch (e) {
      if (kDebugMode) {
        debugPrint("Error fetching location: $e");
      }
      _currentPosition = null;
      _currentAddress = null;
      throw LocationClientFetchPositionException(e.toString());
    } finally {
      _isFetching = false;
      notifyListeners();
    }
  }

  Future<String?> _translateToAddress(Position pos) async {
    if (kDebugMode) {
      debugPrint(
        "Translating position to address: ${pos.latitude}, ${pos.longitude}",
      );
    }
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
      if (kDebugMode) {
        debugPrint("Unknown error translating position to address: $e");
      }
      return null;
    }
  }

  Future<void> openAppSettings() async {
    await Geolocator.openAppSettings();
  }
}
