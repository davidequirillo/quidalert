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
    try {
      final response = await authClient.get('/user/profile', {
        'Content-Type': 'application/json',
      });
      if (response.statusCode == 200) {
        // Success
      } else if (response.statusCode == 401) {
        throw InvalidTokenException();
      } else {
        throw BadRequestException();
      }
      return json.decode(response.body);
    } on InvalidTokenException catch (_) {
      throw InvalidTokenException();
    } on ExpiredTokenException catch (_) {
      throw ExpiredTokenException();
    } catch (e) {
      rethrow;
    }
  }

  void goToLoginPage() {
    Navigator.of(context).pushReplacementNamed('/login');
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return FutureBuilder<Map<String, dynamic>>(
      future: fetchProfile(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return CircularProgressIndicator();
        }
        if (snapshot.hasError) {
          if ((snapshot.error.toString().startsWith("InvalidToken")) ||
              (snapshot.error.toString().startsWith("ExpiredToken"))) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              goToLoginPage();
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
          return Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _buildProfileCard(data),
              SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: _refreshProfile,
                icon: Icon(Icons.refresh),
                label: Text("Refresh"),
              ),
              SizedBox(height: 15),
              ElevatedButton.icon(
                onPressed: _refreshProfile,
                icon: Icon(Icons.add_alert),
                label: Text(loc.labelNewAlert),
              ),
              SizedBox(height: 15),
              ElevatedButton.icon(
                onPressed: _refreshProfile,
                icon: Icon(Icons.history),
                label: Text(loc.labelRecents),
              ),
            ],
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
        subtitle: Text(
          "${user['email']}\n ${loc.labelLastRefreshAt}: ${user['last_refresh_at']}",
        ),
        isThreeLine: true,
      ),
    );
  }
}
