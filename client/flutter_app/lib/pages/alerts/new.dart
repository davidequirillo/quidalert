// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/services/location.dart';
import 'package:quidalert_flutter/models/general.dart';
import 'package:quidalert_flutter/utils/validators.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class NewAlertPage extends StatelessWidget {
  const NewAlertPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.labelNewAlert, showBackButton: true),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: NewAlertBody()),
    );
  }
}

class NewAlertBody extends StatefulWidget {
  const NewAlertBody({super.key});

  @override
  State<NewAlertBody> createState() => _NewAlertBodyState();
}

class _NewAlertBodyState extends State<NewAlertBody> {
  final _formKey = GlobalKey<FormState>();
  final _description = TextEditingController();
  final _customCoordinates = TextEditingController();
  String _selectedType = AlertType.local.name;
  bool alertRequestInProgress = false;
  bool fetchLocationError = false;

  @override
  void dispose() {
    debugPrintC("Disposing NewAlert widget state");
    _description.dispose();
    _customCoordinates.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    if (!_formKey.currentState!.validate()) return;
    fetchLocationError = false;
    final loc = AppLocalizations.of(context)!;
    final locationClient = context.read<LocationClient>();
    final description = _description.text.trim();
    final customCoords = _customCoordinates.text.trim();
    final bool result =
        await showTwoWayAlertDialog(
          context,
          loc.labelSubmittingAlert,
          loc.labelAreYouSure,
        ) ??
        false;
    if (result == false) {
      return;
    }
    Map<String, dynamic> fields = {
      "type": _selectedType,
      "description": description,
    };
    // Chiefs can create general alerts (without location)
    // or managed/empty alerts with custom coordinates.
    // Local alerts will use the device location as usual.
    if (_selectedType == AlertType.general.name) {
      // no operation needed
    } else if (_selectedType == AlertType.managed.name ||
        _selectedType == AlertType.empty.name) {
      if (customCoords.isNotEmpty) {
        final coordsArray = customCoords.split(",");
        if (coordsArray.length == 2) {
          final latitude = double.tryParse(coordsArray[0].trim());
          final longitude = double.tryParse(coordsArray[1].trim());
          if (latitude != null && longitude != null) {
            fields["latitude"] = latitude;
            fields["longitude"] = longitude;
          } else {
            return;
          }
        } else {
          return;
        }
      } else {
        return;
      }
    } else {
      await _fetchLocation();
      if (fetchLocationError == true) {
        return;
      }
      final Map<String, double>? pos = locationClient.currentPosition;
      if (pos == null) {
        if (mounted) {
          await showSimpleAlertDialog(
            context,
            loc.errorError,
            loc.errorPositionNotAvailable,
          );
        }
        return;
      }
      final double lat = pos['lat']!;
      final double long = pos['long']!;
      fields.addAll({
        "latitude": lat,
        "longitude": long,
        "address": locationClient.currentAddress ?? "",
      });
    }
    debugPrintC("Submitting alert with fields: $fields");
    _sendAlert(fields).whenComplete(() {
      debugPrintC("Alert submission completed");
    });
  }

  Future<void> _fetchLocation() async {
    String retMessage = "";
    String retTitle = "";
    final loc = AppLocalizations.of(context)!;
    final locationClient = context.read<LocationClient>();
    try {
      await locationClient.fetchLocation();
    } on LocationClientPermissionDeniedException {
      retMessage = loc.errorLocationPermissionDenied;
      retTitle = loc.errorError;
    } on LocationClientTimeoutException {
      retMessage = loc.errorLocationFetchTimeout;
      retTitle = loc.errorError;
    } on LocationClientAddressNotFoundException {
      // This error is not critical, we can proceed with alert creation without address
      retMessage = "";
      retTitle = "";
    } on LocationClientFetchPositionException {
      retMessage = loc.errorPositionNotAvailable;
      retTitle = loc.errorError;
    } catch (e) {
      retMessage = loc.errorError;
      retTitle = loc.errorError;
    } finally {
      if ((retMessage.isNotEmpty) && (mounted)) {
        fetchLocationError = true;
        await showSimpleAlertDialog(context, retTitle, retMessage);
      }
    }
  }

  Future<void> _sendAlert(Map<String, dynamic> data) async {
    AuthClient authClient = context.read<AuthClient>();
    final loc = AppLocalizations.of(context)!;
    String retTitle = "";
    String retMessage = "";
    bool error = false;
    bool newLoginRequired = false;
    try {
      final response = await authClient.doProtectedApiRequest(
        'POST',
        '/alert',
        body: data,
      );
      final respObj = json.decode(response.body);
      retTitle = loc.successGeneric;
      retMessage = respObj['message'] ?? "Alert created successfully";
      if (retMessage.contains("Local alert created")) {
        retMessage = loc.successAlertCreatedLocal;
      } else if (retMessage.contains("Managed alert created")) {
        retMessage = loc.successAlertCreatedManaged;
      } else if (retMessage.contains("Empty alert created")) {
        retMessage = loc.successAlertCreatedEmpty;
      } else if (retMessage.contains("General alert created")) {
        retMessage = loc.successAlertCreatedGeneral;
      } else if (retMessage.contains("Similar general alert already exists")) {
        retMessage = loc.errorAlertSimilarInGeneral;
      } else if (retMessage.contains("Similar alert already exists")) {
        retMessage = loc.errorAlertSimilarInZone;
      } else {
        retMessage = loc.successAlertCreated;
      }
    } on ForbiddenRequestException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorOpDeniedYouAreNotReliable;
      error = true;
    } on BadRequestException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorBadRequest;
      error = true;
    } on GenericNotAuthorizedException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorNotAuthorizedDoLogin;
      error = true;
      newLoginRequired = true;
    } on ServerException catch (_) {
      retTitle = loc.errorError;
      retMessage = loc.errorServer;
      error = true;
    } catch (e) {
      debugPrint('Error: cannot receive or read response');
      retTitle = loc.errorError;
      retMessage = e.toString();
      error = true;
    } finally {
      if (mounted) {
        debugPrintC(
          "Alert creation result: error=$error, newLoginRequired=$newLoginRequired",
        );
        await showSimpleAlertDialog(context, retTitle, retMessage);
      }
      if (error == false) {
        if (mounted) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            debugPrintC("Alert created successfully, pop 'New Alert' page");
            Navigator.pop(context);
          });
        }
      } else if (newLoginRequired == true) {
        if (mounted) {
          goToLoginPagePostFrameCallback(context);
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Form(
        key: _formKey,
        autovalidateMode: AutovalidateMode.disabled,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              if (authClient.isChief())
                SegmentedButton<String>(
                  segments: [
                    ButtonSegment(
                      value: AlertType.local.name,
                      label: Text(loc.labelLocal),
                      icon: Icon(Icons.place),
                    ),
                    ButtonSegment(
                      value: AlertType.managed.name,
                      label: Text(loc.labelManagedF),
                      icon: Icon(Icons.manage_accounts),
                    ),
                    ButtonSegment(
                      value: AlertType.general.name,
                      label: Text(loc.labelGeneral),
                      icon: Icon(Icons.public),
                    ),
                    ButtonSegment(
                      value: AlertType.empty.name,
                      label: Text(loc.labelEmptyF),
                      icon: Icon(Icons.block),
                    ),
                  ],
                  selected: {_selectedType},
                  onSelectionChanged: (Set<String> newSelection) {
                    setState(() {
                      _selectedType = newSelection.first;
                    });
                  },
                ),
              if (authClient.isChief() &&
                  (_selectedType == AlertType.managed.name ||
                      _selectedType == AlertType.empty.name))
                TextFormField(
                  controller: _customCoordinates,
                  decoration: InputDecoration(
                    labelText: loc.labelGpsPosition,
                    hintText: "lat, long",
                    border: const OutlineInputBorder(),
                  ),
                  validator: (value) {
                    if (_selectedType == AlertType.general.name ||
                        _selectedType == AlertType.local.name) {
                      return null; // Manual coordinates are only required for "custom" or "empty" alerts
                    }
                    return validateGpsCoordinates(context, value);
                  },
                ),
              TextFormField(
                controller: _description,
                decoration: InputDecoration(
                  labelText: loc.labelDescription,
                  border: const OutlineInputBorder(),
                ),
                maxLength: 256,
                minLines: 4,
                maxLines: 4,
                validator: (value) {
                  return validateDescription(context, value);
                },
              ),
              const SizedBox(height: 5),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ElevatedButton(
                    onPressed: () async {
                      if (alertRequestInProgress) {
                        return; // Prevent multiple submissions
                      }
                      setState(() => alertRequestInProgress = true);
                      await submit();
                      setState(() => alertRequestInProgress = false);
                    },
                    child: Text("OK"),
                  ),
                  const SizedBox(width: 10),
                  ElevatedButton(
                    onPressed: () => Navigator.pop(context),
                    child: Text(loc.buttonBack),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              if (alertRequestInProgress) ...[
                Text(loc.labelWaitPlease),
                const SizedBox(height: 5),
                const CircularProgressIndicator(),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
