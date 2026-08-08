// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/l10n/app_localizations_extension.dart';
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
      body: SafeArea(top: false, child: HomeBody()),
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
  final TextEditingController _dismissInputFieldController =
      TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      debugPrintC(
        "HomeBody initState: syncing FCM token and starting background location tracking...",
      );
      await _syncFcmToken();
      await _startBackgroundLocationTracking();
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _dismissInputFieldController.dispose();
    super.dispose();
  }

  Future<void> _refreshProfile() async {
    try {
      // Calling authClient.refreshTokens function can be helpful for debugging,
      // but it's not strictly necessary, as the tokens are refreshed automatically
      // by the AuthClient when we do a protected API request (like fetchProfile) and the access token is expired.
      // await authClient.refreshTokens();
      debugPrintC("Home page: tokens refreshed successfully.");
    } catch (e) {
      debugPrintC("Home page: error refreshing tokens: $e");
    }
    setState(() {
      debugPrintC("Home page: refreshProfile called, triggering rebuild.");
      // it triggers rebuild to fetch profile again
    });
  }

  Future<Map<String, dynamic>> fetchProfile() async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest("get", '/profile');
    return json.decode(response.body);
  }

  Future<void> submitDismissAccountRequest() async {
    if (_dismissInputFieldController.text.trim().toLowerCase() != "delete") {
      return;
    }
    final authClient = context.read<AuthClient>();
    final loc = AppLocalizations.of(context)!;
    String retTitle = "";
    String retMessage = "";
    bool isError = true;
    try {
      await authClient.doProtectedApiRequest("post", '/dismiss-account');
      isError = false;
      retTitle = loc.successGeneric;
      retMessage = loc.successAccountDismissed;
    } catch (e) {
      debugPrintC("Error submitting dismiss account request: $e");
      final exceptionName = e.runtimeType.toString();
      final errorMessage =
          loc.getExceptionString(exceptionName) ?? loc.errorGeneric;
      retTitle = loc.errorGeneric;
      retMessage = errorMessage;
    } finally {
      if (mounted) {
        await showSimpleAlertDialog(context, retTitle, retMessage);
      }
      if (!isError) {
        if (mounted) {
          goToLoginPagePostFrameCallback(context);
        }
      } else {
        _dismissInputFieldController.clear();
      }
    }
  }

  Future<void> _syncFcmToken() async {
    final notifProvider = context.read<NotificationProvider>();
    final authClient = context.read<AuthClient>();
    notifProvider.setAuthClient(authClient);
    await notifProvider.getFcmToken();
    if (notifProvider.fcmToken == null || notifProvider.fcmToken!.isEmpty) {
      debugPrintC(
        "FCM token is null or empty, skipping registration for push notifications.",
      );
      return;
    }
    if (mounted) {
      await authClient.syncFcmTokenWithBackendinForeground(
        notifProvider.fcmToken!,
        context: context,
        localizations: AppLocalizations.of(context)!,
      );
    } else {
      await authClient.syncFcmTokenWithBackendinBackground(
        notifProvider.fcmToken!,
      );
    }
  }

  Future<void> _startBackgroundLocationTracking() async {
    try {
      await BackgroundLocationService.startTracking();
    } catch (e) {
      debugPrintC("Error initializing background location tracking: $e");
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
          return Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          debugPrintC("Home page: error fetching profile: ${snapshot.error}");
          if (snapshot.error.toString().startsWith("GenericNotAuthorized")) {
            goToLoginPagePostFrameCallback(context);
            return Center(child: Text(loc.errorSessionNotValidOrExpired));
          }
          if (snapshot.error.toString().startsWith("BadRequest")) {
            return Center(child: Text(loc.errorBadRequest));
          }
          if (snapshot.error.toString().startsWith("Server")) {
            return Center(child: Text(loc.errorServer));
          }
          return Center(child: Text(loc.errorGeneric));
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
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ElevatedButton.icon(
                    onPressed: () {
                      Navigator.of(context).pushNamed('/alerts/new');
                    },
                    icon: Icon(Icons.add_alert),
                    label: Text(loc.alertNew),
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
                      Navigator.of(context).pushNamed('/alerts/location-test');
                    },
                    icon: Icon(Icons.gps_fixed),
                    label: Text(loc.gpsLocationTest),
                  ),
                  SizedBox(height: 15),
                  ElevatedButton.icon(
                    onPressed: () {
                      Navigator.of(context).pushNamed('/profile/complete');
                    },
                    icon: Icon(Icons.person),
                    label: Text(loc.userCompleteProfile),
                  ),
                  SizedBox(height: 15),
                  ElevatedButton.icon(
                    onPressed: _refreshProfile,
                    icon: Icon(Icons.refresh),
                    label: Text("Refresh"),
                  ),
                  SizedBox(height: 35),
                  _buildProfileCard(data),
                  ListTile(
                    leading: Icon(Icons.delete_forever),
                    title: Text(loc.labelDismissAccountConfirmation),
                  ),
                  TextField(
                    keyboardType: TextInputType.emailAddress,
                    controller: _dismissInputFieldController,
                    decoration: InputDecoration(
                      labelText: loc.labelTypeDeleteToConfirm,
                      border: OutlineInputBorder(),
                    ),
                  ),
                  ElevatedButton.icon(
                    onPressed: () {
                      submitDismissAccountRequest();
                    },
                    label: Text(loc.labelOK),
                  ),
                ],
              ),
            ),
          );
        }
        return Center(child: Text(loc.errorGeneric));
      },
    );
  }

  Widget _buildProfileCard(Map<String, dynamic> user) {
    String type;
    String status;
    final lastRefreshAtStr = user['last_refresh_at'] != null
        ? datetimeAsStringWithoutMilliseconds(
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
        buildSectionTitle(loc.sectionTechnicalInfo),
        ListTile(
          title: Text(
            "${user['firstname']} ${user['surname']}",
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          subtitle: ListBody(
            children: [
              Text(
                "${user['email']}\n${loc.userLastRefreshAt}: $lastRefreshAtStr",
              ),
              Text(
                "${loc.userAuthorizedBy}: ${user['authorized_by'] ?? "N/A"}",
              ),
              Text("${loc.userType}: $type"),
              Text("${loc.userRole}: ${user['role']}"),
              Text("Status: $status"),
              Text("${loc.userReliabilityScore}: ${user['reliability_score']}"),
              Text("${loc.userHeroScore}: ${user['hero_score']}"),
            ],
          ),
          isThreeLine: false,
        ),
        SizedBox(height: 20),
        buildSectionTitle(loc.sectionPersonalInfo),
        ListTile(
          title: Text("${user['firstname']} ${user['surname']}"),
          subtitle: ListBody(
            children: [
              Text("${loc.addressStreet}: ${user['street'] ?? "N/A"}"),
              Text("${loc.addressPostalCode}: ${user['postal_code'] ?? "N/A"}"),
              Text("${loc.addressCity}: ${user['city'] ?? "N/A"}"),
              Text("${loc.addressProvince}: ${user['province'] ?? "N/A"}"),
              Text(
                "${loc.addressCountry}: ${user['country'] ?? "N/A"}",
              ), // example: "Italy", "United States", "Germany"
              Text("${loc.userBirthdate}: ${user['birthdate'] ?? "N/A"}"),
              Text("${loc.userPhoneNumber}: ${user['phone'] ?? "N/A"}"),
            ],
          ),
          isThreeLine: false,
        ),
      ],
    );
  }
}
