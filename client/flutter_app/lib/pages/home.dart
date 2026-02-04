// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/widgets/common.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'dart:convert';
import 'package:quidalert_flutter/services/auth.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CAppBar(title: "Home"),
      drawer: const CAppDrawer(),
      body: HomeBody(),
    );
  }
}

class HomeBody extends StatefulWidget {
  const HomeBody({super.key});

  @override
  State<HomeBody> createState() => _HomeBodyState();
}

class _HomeBodyState extends State<HomeBody> {
  Future<void> _refreshProfile() async {
    final authClient = context.read<AuthClient>();
    try {
      await authClient.refreshTokens();
    } catch (e) {
      // Ignore errors here, they will be handled in fetchProfile
    }
    setState(() {
      // it triggers rebuild to fetch profile again});
    });
  }

  Future<Map<String, dynamic>> fetchProfile() async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/user/profile',
    );
    return json.decode(response.body);
  }

  Future<void> _testGpsPosition() async {
    final loc = AppLocalizations.of(context)!;
    await showDialog(
      context: context,
      builder: (context) => SimpleAlertDialog(
        title: loc.labelGpsPositionTest,
        content: "GPS test is not implemented yet.",
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authClient = context.read<AuthClient>();
    final loc = AppLocalizations.of(context)!;
    return FutureBuilder<Map<String, dynamic>>(
      future: fetchProfile(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return CircularProgressIndicator();
        }
        if (snapshot.hasError) {
          if (snapshot.error.toString().startsWith("GenericNotAuthorized")) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              goToLoginPage(context);
            });
            return Text(loc.errorSessionNotValidOrExpired);
          }
          if (snapshot.error.toString().startsWith("BadRequest")) {
            return Text(loc.errorBadRequest);
          }
          return Text(loc.errorNetwork);
        }
        if (snapshot.hasData) {
          final data = snapshot.data!;
          authClient.setUserInfo(data);
          return Scrollbar(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ElevatedButton.icon(
                    onPressed: () {
                      Navigator.of(context).pushNamed('/alerts/new');
                    },
                    icon: Icon(Icons.add_alert),
                    label: Text(loc.labelNewAlert),
                  ),
                  SizedBox(height: 15),
                  ElevatedButton.icon(
                    onPressed: () {
                      Navigator.of(context).pushNamed('/alerts/recents');
                    },
                    icon: Icon(Icons.history),
                    label: Text(loc.labelRecents),
                  ),
                  SizedBox(height: 15),
                  ElevatedButton.icon(
                    onPressed: () {
                      Navigator.of(context).pushNamed('/advice');
                    },
                    icon: Icon(Icons.help),
                    label: Text(loc.labelAdvice),
                  ),
                  SizedBox(height: 15),
                  ElevatedButton.icon(
                    onPressed: _testGpsPosition,
                    icon: Icon(Icons.gps_fixed),
                    label: Text(loc.labelGpsPositionTest),
                  ),
                  SizedBox(height: 15),
                  ElevatedButton.icon(
                    onPressed: _refreshProfile,
                    icon: Icon(Icons.refresh),
                    label: Text("Refresh"),
                  ),
                  SizedBox(height: 35),
                  _buildProfileCard(data),
                ],
              ),
            ),
          );
        }
        return Text(loc.errorGeneric);
      },
    );
  }

  Widget _buildProfileCard(Map<String, dynamic> user) {
    final loc = AppLocalizations.of(context)!;
    return Card(
      elevation: 4,
      margin: EdgeInsets.symmetric(horizontal: 20),
      child: ListTile(
        title: Text(
          "${user['firstname']} ${user['surname']}",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: ListBody(
          children: [
            Text(
              "${user['email']}\n${loc.labelLastRefreshAt}: ${user['last_refresh_at']}",
            ),
            Text("Superuser: ${user['is_superuser'] ? 'yes' : 'no'}"),
            Text("Admin: ${user['is_admin'] ? 'yes' : 'no'}"),
            Text("Officer: ${user['is_officer'] ? 'yes' : 'no'}"),
            Text("Chief: ${user['is_chief'] ? 'yes' : 'no'}"),
            Text("Status: ${user['status']}"),
            Text("Type: ${user['type']}"),
          ],
        ),
        isThreeLine: true,
      ),
    );
  }
}
