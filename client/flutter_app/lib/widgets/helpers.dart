// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';

// USEFUL WIDGETS

class GotoIfAlertDialog extends StatelessWidget {
  final String title;
  final String content;
  final bool condition;
  final String route;

  const GotoIfAlertDialog({
    super.key,
    required this.title,
    required this.content,
    required this.condition,
    required this.route,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(child: Text(content)),
      actions: [
        TextButton(
          onPressed: () {
            if (condition) {
              Navigator.pushReplacementNamed(context, route);
            } else {
              Navigator.of(context).pop();
            }
          },
          child: const Text("OK"),
        ),
      ],
    );
  }
}

class SimpleAlertDialog extends StatelessWidget {
  final String title;
  final String content;

  const SimpleAlertDialog({
    super.key,
    required this.title,
    required this.content,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(child: Text(content)),
      actions: [
        TextButton(
          onPressed: () {
            Navigator.of(context).pop();
          },
          child: const Text("OK"),
        ),
      ],
    );
  }
}

class TwoWayAlertDialog extends StatelessWidget {
  final String title;
  final String content;

  const TwoWayAlertDialog({
    super.key,
    required this.title,
    required this.content,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(child: Text(content)),
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
    );
  }
}

// USEFUL FUNCTIONS

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

void showLoadingDialog(BuildContext context, String message) {
  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (context) => AlertDialog(
      content: Row(
        children: [
          const CircularProgressIndicator(),
          const SizedBox(width: 20),
          Expanded(child: Text(message)),
        ],
      ),
    ),
  );
}

void debugPrintAncestors(BuildContext context) {
  context.visitAncestorElements((element) {
    debugPrint(element.widget.runtimeType.toString());
    return true;
  });
}
