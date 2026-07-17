// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2026  Davide Quirillo
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
import 'package:quidalert_flutter/l10n/app_localizations_extension.dart';
import 'package:quidalert_flutter/services/location.dart';
import 'package:quidalert_flutter/models/general.dart';
import 'package:quidalert_flutter/utils/validators.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class ExtendAlertPage extends StatelessWidget {
  const ExtendAlertPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.alertExtend, showBackButton: true),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: ExtendAlertBody()),
    );
  }
}

class ExtendAlertBody extends StatefulWidget {
  const ExtendAlertBody({super.key});

  @override
  State<ExtendAlertBody> createState() => _ExtendAlertBodyState();
}

class _ExtendAlertBodyState extends State<ExtendAlertBody> {
  // state attributes

  @override
  void dispose() {
    debugPrintC("Disposing ExtendAlert widget state");
    super.dispose();
  }

  Future<void> submit() async {
    // Validate form
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Center(child: Text(loc.alertExtend));
  }
}
