// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/services/shared.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/services/notification.dart';
import 'package:quidalert_flutter/services/background_location.dart';

class CAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;

  const CAppBar({super.key, required this.title, this.showBackButton = false});

  final bool showBackButton;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    if (showBackButton) {
      return AppBar(
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,
        title: Text(title),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            Navigator.of(context).pop();
          },
        ),
      );
    } else {
      return AppBar(
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,
        title: Text(title),
      );
    }
  }
}

class CAppDrawer extends StatelessWidget {
  const CAppDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final shared = context.read<SharedVars>();
    final authClient = context.read<AuthClient>();
    final notifProvider = context.read<NotificationProvider>();
    final loc = AppLocalizations.of(context)!;
    bool termsAccepted = shared.termsAccepted;
    bool isLoggedIn = authClient.isLoggedIn();
    if (!isLoggedIn) {
      notifProvider.setAuthClient(null);
    }
    bool isAdmin = authClient.isAdmin();
    bool isOfficer = authClient.isOfficer();
    bool isChief = authClient.isChief();
    debugPrint(
      'Building CAppDrawer: isLoggedIn: $isLoggedIn, termsAccepted: $termsAccepted, isAdmin: $isAdmin, isOfficer: $isOfficer, isChief: $isChief',
    );
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
                Navigator.of(context).pop();
                Navigator.pushReplacementNamed(context, '/login');
              },
            ),
          if (isLoggedIn)
            ListTile(
              leading: Icon(Icons.logout),
              title: Text('Logout'),
              onTap: () async {
                await BackgroundLocationService.stopTracking();
                // we don't register anymore to the backend for notifications
                notifProvider.setAuthClient(null);
                try {
                  await authClient.logout();
                  debugPrint("Logout successful");
                } catch (e) {
                  debugPrint("Error during logout: $e");
                }
                if (!context.mounted) return;
                Navigator.of(context).pop();
                Navigator.pushReplacementNamed(context, '/login');
              },
            ),

          const Divider(),

          if (true)
            ListTile(
              leading: Icon(Icons.info),
              title: Text("Info"),
              onTap: () {
                Navigator.of(context).pop();
                Navigator.pushReplacementNamed(context, '/info');
              },
            ),
          if (isLoggedIn)
            ListTile(
              leading: Icon(Icons.home),
              title: Text("Home"),
              onTap: () {
                Navigator.of(context).pop();
                Navigator.pushReplacementNamed(context, '/home');
              },
            ),
          if (isLoggedIn && (isAdmin || isOfficer))
            ListTile(
              leading: Icon(Icons.home),
              title: Text("Accounts"),
              onTap: () {
                Navigator.of(context).pop();
                Navigator.pushReplacementNamed(context, '/accounts');
              },
            ),
          if (isLoggedIn)
            ListTile(
              leading: Icon(Icons.settings),
              title: Text(loc.menuSettings),
              onTap: () {
                Navigator.of(context).pop();
                Navigator.pushReplacementNamed(context, '/settings');
              },
            ),
          if (true)
            ListTile(
              leading: Icon(Icons.description),
              title: Text(loc.menuTerms),
              onTap: () {
                Navigator.of(context).pop();
                Navigator.pushReplacementNamed(context, '/terms');
              },
            ),
        ],
      ),
    );
  }
}
