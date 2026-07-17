// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';

// USEFUL DIALOGS

Future<void> showGotoIfAlertDialog(
  BuildContext context,
  String title,
  String content,
  bool condition,
  String route,
) async {
  return await showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Scrollbar(
        thumbVisibility: true,
        child: SingleChildScrollView(child: Text(content)),
      ),
      actions: [
        TextButton(
          onPressed: () {
            if (condition) {
              Navigator.of(context).pop();
              Navigator.pushReplacementNamed(context, route);
            } else {
              Navigator.of(context).pop();
            }
          },
          child: const Text("OK"),
        ),
      ],
    ),
  );
}

Future<void> showSimpleAlertDialog(
  BuildContext context,
  String title,
  String content,
) async {
  return await showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Scrollbar(
        thumbVisibility: true,
        child: SingleChildScrollView(child: Text(content)),
      ),
      actions: [
        TextButton(
          onPressed: () {
            Navigator.of(context).pop();
          },
          child: const Text("OK"),
        ),
      ],
    ),
  );
}

Future<bool?> showTwoWayAlertDialog(
  BuildContext context,
  String title,
  String content,
) async {
  return await showDialog<bool?>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Scrollbar(
        thumbVisibility: true,
        child: SingleChildScrollView(child: Text(content)),
      ),
      actions: [
        TextButton(
          onPressed: () {
            Navigator.of(context).pop(true);
          },
          child: const Text("OK"),
        ),
        TextButton(
          onPressed: () {
            Navigator.of(context).pop(false);
          },
          child: Text(AppLocalizations.of(context)!.buttonCancel),
        ),
      ],
    ),
  );
}

Future<void> showLoadingDialog(BuildContext context, String message) async {
  return await showDialog<void>(
    context: context,
    barrierDismissible: false,
    builder: (context) => PopScope(
      canPop: false,
      child: AlertDialog(
        content: Row(
          children: [
            const CircularProgressIndicator(),
            const SizedBox(width: 20),
            Expanded(child: Text(message)),
          ],
        ),
      ),
    ),
  );
}

// NAVIGATION HELPERS

void goToLoginPage(BuildContext context) {
  Navigator.pushNamedAndRemoveUntil(context, '/login', (route) => false);
}

void goToLoginPagePostFrameCallback(BuildContext context) {
  WidgetsBinding.instance.addPostFrameCallback((_) {
    Navigator.pushNamedAndRemoveUntil(context, '/login', (route) => false);
  });
}

void goToHomePage(BuildContext context) {
  Navigator.pushNamedAndRemoveUntil(context, '/home', (route) => false);
}

void goToHomePagePostFrameCallback(BuildContext context) {
  WidgetsBinding.instance.addPostFrameCallback((_) {
    Navigator.pushNamedAndRemoveUntil(context, '/home', (route) => false);
  });
}

// USEFUL WIDGETS

Widget buildSectionLink(BuildContext context, String text, String routeName) {
  return Card(
    child: ListTile(
      title: Text(
        text,
        style: const TextStyle(color: Colors.blue, fontWeight: FontWeight.bold),
      ),
      trailing: const Icon(Icons.arrow_forward, size: 16),
      onTap: () {
        Navigator.pushNamed(context, routeName);
      },
    ),
  );
}

Widget buildSectionTitle(String title) {
  return Padding(
    padding: const EdgeInsets.only(bottom: 12.0),
    child: Text(
      title,
      style: const TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.bold,
        color: Colors.blue,
      ),
    ),
  );
}

// DEBUGGING HELPERS

void debugPrintAncestors(BuildContext context) {
  context.visitAncestorElements((element) {
    debugPrint(element.widget.runtimeType.toString());
    return true;
  });
}
