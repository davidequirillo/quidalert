// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'dart:io';
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationProvider extends ChangeNotifier {
  FirebaseMessaging? _messaging = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();
  StreamSubscription<String>? _tokenStream;
  StreamSubscription<RemoteMessage>? _messageStream;
  String? fcmToken;
  bool initDone = false;

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
    super.dispose();
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
      await _initLocalNotifications();
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
        _setupFirebaseTokenListener(); // Listen for token refresh events
        _setupFirebaseMessageListener(); // Listen for incoming messages while the app is in the foreground
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

  Future<void> _initLocalNotifications() async {
    const AndroidInitializationSettings initializationSettingsAndroid =
        AndroidInitializationSettings(
          '@mipmap/ic_launcher',
        ); // Use the app icon as the notification icon
    const InitializationSettings initializationSettings =
        InitializationSettings(
          android: initializationSettingsAndroid,
          iOS: DarwinInitializationSettings(),
        );
    await _localNotifications.initialize(settings: initializationSettings);
  }

  void _showLocalNotification(RemoteMessage message) {
    RemoteNotification? notification = message.notification;
    if (notification != null) {
      _localNotifications
          .show(
            id: notification.hashCode, // Unique ID for the notification
            title: notification.title,
            body: notification.body,
            notificationDetails: NotificationDetails(
              android: AndroidNotificationDetails(
                'alert_notifications_channel',
                'Alert Notifications',
                channelDescription:
                    'This channel is used for alert notifications.',
                importance: Importance.high,
                priority: Priority.high,
                icon: '@mipmap/ic_launcher',
              ),
              iOS: DarwinNotificationDetails(
                presentAlert: true,
                presentBadge: true,
                presentSound: true,
              ),
            ),
          )
          .catchError(
            (e) => debugPrint('Error showing local notification: $e'),
          );
    }
  }

  void _setupFirebaseTokenListener() {
    _tokenStream = _messaging!.onTokenRefresh.listen((newToken) async {
      if (kDebugMode) {
        debugPrint('FCM token refreshed: $newToken');
      }
      fcmToken = newToken;
    });
  }

  void _setupFirebaseMessageListener() {
    _messageStream = FirebaseMessaging.onMessage.listen((
      RemoteMessage message,
    ) {
      if (kDebugMode) {
        debugPrint(
          'Notification: received a message while in the foreground: ${message.messageId}',
        );
      }
      _showLocalNotification(message);
    });
  }
}
