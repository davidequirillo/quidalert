// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/services/notification.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/services/background_location.dart';

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
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _syncFcmToken();
      _startBackgroundLocationTracking();
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _refreshProfile() async {
    final authClient = context.read<AuthClient>();
    try {
      await authClient.refreshTokens();
    } catch (e) {
      // Ignore errors here, they will be handled in fetchProfile
    }
    setState(() {
      // it triggers rebuild to fetch profile again
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

  Future<void> _syncFcmToken() async {
    final notifProvider = context.read<NotificationProvider>();
    final authClient = context.read<AuthClient>();
    notifProvider.setAuthClient(authClient);
    if (notifProvider.fcmToken == null || notifProvider.fcmToken!.isEmpty) {
      debugPrint(
        "FCM token is null or empty, skipping registration for push notifications.",
      );
      return;
    }
    await authClient.registerFcmTokenForPushNotifications(
      notifProvider.fcmToken,
      context: context,
      localizations: AppLocalizations.of(context)!,
    );
  }

  Future<void> _startBackgroundLocationTracking() async {
    try {
      await BackgroundLocationService.startTracking();
    } catch (e) {
      debugPrint("Error initializing background location tracking: $e");
    }
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
            controller: _scrollController,
            thumbVisibility: true,
            child: SingleChildScrollView(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              child: SafeArea(
                top: false,
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
                      onPressed: () {
                        Navigator.of(
                          context,
                        ).pushNamed('/alerts/location-test');
                      },
                      icon: Icon(Icons.gps_fixed),
                      label: Text(loc.labelGpsLocationTest),
                    ),
                    SizedBox(height: 15),
                    ElevatedButton.icon(
                      onPressed: () {
                        Navigator.of(context).pushNamed('/profile/complete');
                      },
                      icon: Icon(Icons.person),
                      label: Text(loc.labelCompleteProfile),
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
            ),
          );
        }
        return Text(loc.errorGeneric);
      },
    );
  }

  Widget _buildProfileCard(Map<String, dynamic> user) {
    String type;
    String status;
    final lastRefreshAtStr = user['last_refresh_at'] != null
        ? datetimeAsStringWithoutMicroseconds(
            DateTime.parse(user['last_refresh_at']),
          )
        : "N/A";
    if (user['is_superuser'] == true) {
      type = "superuser";
    } else if (user['is_admin'] == true) {
      type = "admin";
    } else if (user['is_officer'] == true) {
      type = "officer";
    } else if (user['is_chief'] == true) {
      type = "chief";
    } else {
      type = "base";
    }
    if (user['is_reliable'] == false) {
      status = "unreliable";
    } else if (user['is_blocked'] == true) {
      status = "blocked";
    } else {
      status = "ok";
    }
    final loc = AppLocalizations.of(context)!;
    return Column(
      mainAxisAlignment: MainAxisAlignment.start,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        buildSectionTitle(loc.labelTechnicalInfo),
        ListTile(
          title: Text(
            "${user['firstname']} ${user['surname']}",
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          subtitle: ListBody(
            children: [
              Text(
                "${user['email']}\n${loc.labelLastRefreshAt}: $lastRefreshAtStr",
              ),
              Text(
                "${loc.labelAuthorizedBy}: ${user['authorized_by'] ?? "N/A"}",
              ),
              Text("${loc.labelType}: $type"),
              Text("${loc.labelRole}: ${user['role']}"),
              Text("Status: $status"),
              Text(
                "${loc.labelReliabilityScore}: ${user['reliability_score']}",
              ),
            ],
          ),
          isThreeLine: false,
        ),
        SizedBox(height: 20),
        buildSectionTitle(loc.labelPersonalInfo),
        ListTile(
          title: Text("${user['firstname']} ${user['surname']}"),
          subtitle: ListBody(
            children: [
              Text("${loc.labelStreet}: ${user['street'] ?? "N/A"}"),
              Text("${loc.labelPostalCode}: ${user['postal_code'] ?? "N/A"}"),
              Text("${loc.labelCity}: ${user['city'] ?? "N/A"}"),
              Text("${loc.labelProvince}: ${user['province'] ?? "N/A"}"),
              Text(
                "${loc.labelCountry}: ${user['country'] ?? "N/A"}",
              ), // example: "Italy", "United States", "Germany"
              Text("${loc.labelBirthdate}: ${user['birthdate'] ?? "N/A"}"),
              Text("${loc.labelPhoneNumber}: ${user['phone'] ?? "N/A"}"),
            ],
          ),
          isThreeLine: false,
        ),
      ],
    );
  }
}
