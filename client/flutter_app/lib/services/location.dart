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
  static const int distanceBoundary = 30;
  // distanceBoundary in meters, used to optimize battery
  // consumption by not updating address if user hasn't moved significantly

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
          timeLimit: const Duration(seconds: 15), // timeout after 15 seconds
        ),
      );
      // We optimize battery consumption
      // by not updating the relative address if the user
      // hasn't moved significantly
      if (_currentPosition != null) {
        double gap = Geolocator.distanceBetween(
          _currentPosition!.latitude,
          _currentPosition!.longitude,
          returnedPosition.latitude,
          returnedPosition.longitude,
        );
        if (gap < LocationClient.distanceBoundary && !forceUpdate) {
          if (kDebugMode) {
            debugPrint("Minimum movement ($gap m): not updating address");
          }
          _isFetching = false;
          notifyListeners();
          return;
        }
      }
      _currentPosition = returnedPosition;
      _currentAddress = await _translateToAddress(_currentPosition!);
      if (_currentAddress == null || _currentAddress!.isEmpty) {
        throw LocationClientAddressNotFoundException();
      }
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
      throw LocationClientAddressNotFoundException();
    } catch (e) {
      throw LocationClientFetchPositionException(e.toString());
    } finally {
      _isFetching = false;
      notifyListeners();
    }
  }

  Future<String?> _translateToAddress(Position pos) async {
    List<Placemark> p = await placemarkFromCoordinates(
      pos.latitude,
      pos.longitude,
    );
    if (p.isNotEmpty) {
      return "${p[0].street}, ${p[0].locality}, ${p[0].administrativeArea}, ${p[0].country}";
    } else {
      return null;
    }
  }

  Future<void> openAppSettings() async {
    await Geolocator.openAppSettings();
  }
}
