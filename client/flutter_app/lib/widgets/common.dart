// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/services/shared.dart';
import 'package:quidalert_flutter/services/auth.dart';

class CAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;

  const CAppBar({super.key, required this.title});

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      backgroundColor: Colors.blue,
      foregroundColor: Colors.white,
      title: Text(title),
    );
  }
}

class CAppDrawer extends StatelessWidget {
  const CAppDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final authClient = context.read<AuthClient>();
    final shared = context.read<SharedVars>();
    final loc = AppLocalizations.of(context)!;
    bool termsAccepted = shared.termsAccepted;
    bool isLoggedIn = authClient.isLoggedIn();
    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          DrawerHeader(
            decoration: BoxDecoration(color: Colors.blue),
            child: Text(
              'Menu',
              style: TextStyle(color: Colors.white, fontSize: 24),
            ),
          ),
          if (termsAccepted && (!isLoggedIn))
            ListTile(
              leading: Icon(Icons.login),
              title: Text('Login'),
              onTap: () {
                Navigator.pushReplacementNamed(context, '/login');
              },
            ),
          if (termsAccepted && isLoggedIn)
            ListTile(
              leading: Icon(Icons.logout),
              title: Text('Logout'),
              onTap: () {
                // authClient.logout()
                Navigator.of(context).pop();
              },
            ),

          const Divider(),

          if (true)
            ListTile(
              leading: Icon(Icons.home),
              title: Text("Info"),
              onTap: () {
                Navigator.pushReplacementNamed(context, '/info');
              },
            ),
          if (termsAccepted && isLoggedIn)
            ListTile(
              leading: Icon(Icons.request_page),
              title: Text(loc.menuRequest),
              onTap: () {
                Navigator.pushReplacementNamed(context, '/request');
              },
            ),
          if (termsAccepted && isLoggedIn)
            ListTile(
              leading: Icon(Icons.history),
              title: Text(loc.menuRecents),
              onTap: () {
                Navigator.pushReplacementNamed(context, '/recents');
              },
            ),
          if (termsAccepted && isLoggedIn)
            ListTile(
              leading: Icon(Icons.settings),
              title: Text(loc.menuSettings),
              onTap: () {
                Navigator.pushReplacementNamed(context, '/settings');
              },
            ),
          if (true)
            ListTile(
              leading: Icon(Icons.description),
              title: Text(loc.menuTerms),
              onTap: () {
                Navigator.pushReplacementNamed(context, '/terms');
              },
            ),
        ],
      ),
    );
  }
}

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
      content: Text(content),
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
