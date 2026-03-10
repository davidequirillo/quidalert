// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'dart:io';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/widgets/app_keys.dart';

class NotificationProvider extends ChangeNotifier {
  FirebaseMessaging? _messaging = FirebaseMessaging.instance;
  StreamSubscription<String>? _tokenStream;
  StreamSubscription<RemoteMessage>? _messageStream;
  String? fcmToken;
  bool initDone = false;
  AuthClient? _authClient;

  NotificationProvider() : super() {
    fcmToken = null;
    if (!kIsWeb && !Platform.isWindows) {
      debugPrint(
        'Push notifications are supported on this platform. Initializing...',
      );
      _init();
    } else {
      if (kDebugMode) {
        debugPrint(
          'Push notifications are not supported on this platform. Skipping initialization... Done',
        );
      }
      initDone = true;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _tokenStream?.cancel();
    _messageStream?.cancel();
    _tokenStream = null;
    _messageStream = null;
    _authClient = null;
    super.dispose();
  }

  void setAuthClient(AuthClient? client) {
    _authClient = client;
  }

  Future<void> _init() async {
    _messaging = FirebaseMessaging.instance;
    if (kDebugMode) {
      debugPrint('NotificationProvider initialization started');
    }
    NotificationSettings settings = await _messaging!.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      if (kDebugMode) {
        debugPrint('Push notification permission granted');
      }
    } else if (settings.authorizationStatus ==
        AuthorizationStatus.provisional) {
      if (kDebugMode) {
        debugPrint('Push notification permission granted provisionally');
      }
    } else {
      if (kDebugMode) {
        debugPrint('Push notification permission denied');
      }
    }
    final bool isAllowed =
        settings.authorizationStatus == AuthorizationStatus.authorized ||
        settings.authorizationStatus == AuthorizationStatus.provisional;
    if (isAllowed) {
      late final String? token;
      try {
        token = await _messaging!.getToken();
      } catch (e) {
        debugPrint('Error getting FCM token: $e');
        token = null;
      }
      if (token != null) {
        fcmToken = token;
        if (kDebugMode) {
          debugPrint('FCM token obtained: $fcmToken');
        }
      } else {
        if (kDebugMode) {
          debugPrint('Failed to get FCM token');
        }
      }
      try {
        _setupFirebaseTokenListener(); // Listen for fcm token refresh events
        _setupFirebaseMessageForegroundListener(); // Listend for messages when the app is in foreground
        await _setupFirebaseMessageBackgroundListener(); // Listend for essages when the app is in background, but not closed
        await _setupFirebaseMessageTerminatedListener(); // Listen for messages when the app is terminated
      } catch (e) {
        debugPrint('Error setting up Firebase listeners: $e');
        _tokenStream?.cancel();
        _messageStream?.cancel();
        _tokenStream = null;
        _messageStream = null;
      }
    }
    initDone = true;
    if (kDebugMode) {
      debugPrint('NotificationProvider initialization completed');
    }
    notifyListeners();
  }

  void _setupFirebaseTokenListener() {
    _tokenStream = _messaging!.onTokenRefresh.listen((newToken) async {
      if (kDebugMode) {
        debugPrint('FCM token refreshed locally: $newToken');
      }
      fcmToken = newToken;
      if (_authClient != null) {
        await _authClient!.syncFcmTokenWithBackend(newToken);
      }
    });
  }

  void _setupFirebaseMessageForegroundListener() {
    _messageStream = FirebaseMessaging.onMessage.listen((
      RemoteMessage message,
    ) {
      if (kDebugMode) {
        debugPrint(
          'Notification: received a message while in the foreground: ${message.messageId}',
        );
      }
      AppKeys.snackbarKey.currentState?.showSnackBar(
        SnackBar(
          content: Text(message.data['type']),
          action: SnackBarAction(
            label: "View",
            onPressed: () {
              _handleNavigation(message.data['route']);
            },
          ),
        ),
      );
    });
  }

  Future<void> _setupFirebaseMessageBackgroundListener() async {
    // It will trigger if the app is in background, but not terminated
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) async {
      await Future.delayed(Duration(milliseconds: 1000));
      if (kDebugMode) {
        debugPrint(
          'Notification: app opened from background by tapping on a notification: ${message.messageId}',
        );
      }
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _handleNavigation(message.data['route']);
      });
    });
  }

  Future<void> _setupFirebaseMessageTerminatedListener() async {
    // It will only trigger if the app is completely terminated and opened by tapping on a notification
    RemoteMessage? initialMessage = await FirebaseMessaging.instance
        .getInitialMessage();
    if (initialMessage != null) {
      await Future.delayed(Duration(milliseconds: 1000));
      if (kDebugMode) {
        debugPrint(
          'Notification: app opened from terminated state by tapping on a notification: ${initialMessage.messageId}',
        );
      }
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _handleNavigation(initialMessage.data['route']);
      });
    }
  }

  void _handleNavigation(String route) {
    AppKeys.navigatorKey.currentState?.pushNamedAndRemoveUntil(
      '/home',
      (route) => false,
    );
    AppKeys.navigatorKey.currentState?.pushNamed(route);
  }
}
