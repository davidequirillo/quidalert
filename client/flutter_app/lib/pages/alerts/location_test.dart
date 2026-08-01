// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/l10n/app_localizations_extension.dart';
import 'package:quidalert_flutter/services/location.dart';
import 'package:quidalert_flutter/services/background_location.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';

class LocationTestPage extends StatelessWidget {
  const LocationTestPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.gpsLocationTest, showBackButton: true),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: LocationTestBody()),
    );
  }
}

class LocationTestBody extends StatefulWidget {
  const LocationTestBody({super.key});

  @override
  State<LocationTestBody> createState() => _LocationTestBodyState();
}

class _LocationTestBodyState extends State<LocationTestBody> {
  String coords = "";
  String accuracy = "";
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _fetchCurrentLocation() async {
    String retMessage = "";
    String retTitle = "";
    final loc = AppLocalizations.of(context)!;
    final locationClient = context.read<LocationClient>();
    try {
      await locationClient.fetchLocation();
      setState(() {
        coords = getCoords(locationClient.currentPosition);
        accuracy = getAccuracy(locationClient.currentPosition);
      });
    } on LocationClientPermissionDeniedException {
      retMessage = loc.errorLocationPermissionDenied;
      retTitle = loc.errorError;
    } on LocationClientTimeoutException {
      retMessage = loc.errorLocationFetchTimeout;
      retTitle = loc.errorError;
    } on LocationClientAddressNotFoundException {
      retMessage = loc.errorLocationAddressNotFound;
      retTitle = loc.errorError;
    } on LocationClientFetchPositionException {
      retMessage = loc.errorLocationNotAvailable;
      retTitle = loc.errorError;
    } on LocationClientAccuracyLowException catch (e) {
      retMessage = loc.errorLocationAccuracyIsLow;
      retMessage += "(${e.message})";
      retTitle = loc.errorError;
    } catch (e) {
      retMessage = loc.errorError;
      retTitle = loc.errorError;
    } finally {
      if ((retMessage.isNotEmpty) && (mounted)) {
        await showSimpleAlertDialog(context, retTitle, retMessage);
      }
    }
  }

  String getCoords(Map<String, double>? positionMap) {
    if (positionMap != null) {
      final coordStr = gpsCoordinatesAsString(
        positionMap['latitude']!,
        positionMap['longitude']!,
      );
      return coordStr;
    } else {
      final loc = AppLocalizations.of(context)!;
      return loc.errorLocationNotAvailable;
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

  String getAccuracy(Map<String, double>? positionMap) {
    if (positionMap != null) {
      return "${positionMap['accuracy']!} m";
    } else {
      final loc = AppLocalizations.of(context)!;
      return loc.errorLocationNotAvailable;
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    final locationClient = context.watch<LocationClient>();
    return SingleChildScrollView(
      controller: _scrollController,
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
              '(${loc.gpsLatitude}, ${loc.gpsLongitude}): $coords',
              style: const TextStyle(fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 10),
            Text(
              "${loc.gpsPositionAccuracy}: $accuracy",
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
              locationClient.currentAddress ?? loc.errorLocationAddressNotFound,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            locationClient.isFetching
                ? const CircularProgressIndicator()
                : ElevatedButton(
                    onPressed: _fetchCurrentLocation,
                    child: Text(loc.buttonObtain),
                  ),
            Divider(height: 30, thickness: 1),
            buildSectionTitle(loc.sectionLocationLog),
            buildLocationLogListView(),
          ],
        ),
      ),
    );
  }

  Widget buildLocationLogListView() {
    final loc = AppLocalizations.of(context)!;
    return FutureBuilder<List<dynamic>>(
      future: BackgroundLocationService.getLocationLog(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const CircularProgressIndicator();
        } else if (snapshot.hasError) {
          return Text('${loc.errorError}: ${snapshot.error}');
        } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
          return Text(loc.entriesNotFound);
        } else {
          final locations = snapshot.data!;
          return ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: locations.length,
            itemBuilder: (context, index) {
              final location = locations[index] as Map<String, String>;
              final coords =
                  "${location["latitude"]}, ${location["longitude"]}";
              final String accuracy = "${location["accuracy"]} m";
              final String isMovingStr = loc.getBooleanString(
                location["is_moving"]!,
              );
              final String timestamp = location["timestamp"]!;
              final String uuidPart = location["uuid"]!.length > 8
                  ? location["uuid"]!.substring(0, 8)
                  : location["uuid"]!;
              String subtitleText = "${loc.gpsPositionAccuracy}: $accuracy\n";
              subtitleText +=
                  "${loc.gpsPositionIsMoving}: ${isMovingStr.toLowerCase()}\n";
              subtitleText += "ID: $uuidPart";
              return ListTile(
                title: Text(coords),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(subtitleText),
                    InkWell(
                      onTap: () {
                        final double? lat = double.tryParse(
                          location["latitude"]!,
                        );
                        final double? long = double.tryParse(
                          location["longitude"]!,
                        );
                        if ((lat != null) && (long != null)) {
                          viewOnMap(context, lat, long);
                        }
                      },
                      child: Text(
                        loc.labelViewOnMap,
                        style: TextStyle(
                          decoration: TextDecoration.underline,
                          color: Colors.blue,
                        ),
                      ),
                    ),
                  ],
                ),
                trailing: Text(timestamp, style: const TextStyle(fontSize: 12)),
              );
            },
          );
        }
      },
    );
  }
}
