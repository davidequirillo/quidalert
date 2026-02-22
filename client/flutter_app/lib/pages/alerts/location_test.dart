// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/services/location.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';

class LocationTestPage extends StatelessWidget {
  const LocationTestPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.labelGpsLocationTest, showBackButton: true),
      drawer: const CAppDrawer(),
      body: const LocationTestBody(),
    );
  }
}

class LocationTestBody extends StatefulWidget {
  const LocationTestBody({super.key});

  @override
  State<LocationTestBody> createState() => _LocationTestBodyState();
}

class _LocationTestBodyState extends State<LocationTestBody> {
  @override
  void dispose() {
    super.dispose();
  }

  Future<void> _fetchCurrentLocation() async {
    String retMessage = "";
    String retTitle = "";
    bool gotoSettings = false;
    final loc = AppLocalizations.of(context)!;
    final locationClient = context.read<LocationClient>();
    try {
      await locationClient.fetchLocation();
      return;
    } on LocationClientServiceDisabledException {
      retMessage = loc.errorLocationServicesDisabled;
      retTitle = loc.errorError;
      gotoSettings = true;
    } on LocationClientPermissionDeniedException {
      retMessage = loc.errorLocationPermissionDenied;
      retTitle = loc.errorError;
      gotoSettings = true;
    } on LocationClientPermissionsForeverException {
      retMessage = loc.errorLocationPermissionDeniedForever;
      retTitle = loc.errorError;
      gotoSettings = true;
    } on LocationClientTimeoutException {
      retMessage = loc.errorLocationFetchTimeout;
      retTitle = loc.errorError;
    } on LocationClientAddressNotFoundException {
      retMessage = loc.errorAddressNotFound;
      retTitle = loc.errorError;
    } on LocationClientFetchPositionException {
      retMessage = loc.errorPositionNotAvailable;
      retTitle = loc.errorError;
    } catch (e) {
      retMessage = loc.errorError;
      retTitle = loc.errorError;
    } finally {
      if ((retMessage.isNotEmpty) && (mounted)) {
        await showDialog(
          context: context,
          builder: (context) =>
              SimpleAlertDialog(title: retTitle, content: retMessage),
        );
        if (gotoSettings) {
          await locationClient.openAppSettings();
        }
      }
    }
  }

  String getCoords(Map<String, double>? positionMap) {
    if (positionMap != null) {
      final String lat = positionMap['lat']!.toStringAsFixed(6);
      final String long = positionMap['long']!.toStringAsFixed(6);
      return "$lat, $long";
    } else {
      final loc = AppLocalizations.of(context)!;
      return loc.errorPositionNotAvailable;
    }
  }

  Future<void> copyCoordsToClipboard() async {
    final locationClient = context.read<LocationClient>();
    Map<String, double>? position = locationClient.currentPosition;
    if (position != null) {
      final String s = getCoords(position);
      await Clipboard.setData(ClipboardData(text: s));
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    final locationClient = context.watch<LocationClient>();
    final String coords = getCoords(locationClient.currentPosition);
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const Icon(Icons.location_on, size: 50, color: Colors.blue),
              const SizedBox(height: 15),
              const SizedBox(height: 15),
              SelectableText(
                '(${loc.labelLatitude}, ${loc.labelLongitude}): $coords',
                style: const TextStyle(fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 10),
              locationClient.isFetching
                  ? const CircularProgressIndicator()
                  : ElevatedButton(
                      onPressed: copyCoordsToClipboard,
                      child: Text(loc.buttonCopy),
                    ),
              const SizedBox(height: 20),
              SelectableText(
                locationClient.currentAddress ?? loc.errorAddressNotFound,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),
              locationClient.isFetching
                  ? const CircularProgressIndicator()
                  : ElevatedButton(
                      onPressed: _fetchCurrentLocation,
                      child: Text(loc.buttonObtain),
                    ),
            ],
          ),
        ),
      ),
    );
  }
}
