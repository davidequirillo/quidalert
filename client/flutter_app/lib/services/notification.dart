// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:io';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/widgets/app_keys.dart';

class NotificationProvider extends ChangeNotifier {
  FirebaseMessaging? _messaging;
  StreamSubscription<String>? _tokenStream;
  StreamSubscription<RemoteMessage>? _onMessageStream;
  StreamSubscription<RemoteMessage>? _onMessageOpenedAppStream;
  RemoteMessage? _initialMessage;
  String? fcmToken;
  bool initDone = false;
  AuthClient? _authClient;
  String currentNotificationOrigin = '';
  int currentNotificationOriginCounter = 0;

  NotificationProvider() : super() {
    fcmToken = null;
    if (!kIsWeb && !Platform.isWindows) {
      debugPrintC(
        'Push notifications are supported on this platform. Initializing...',
      );
      _init();
    } else {
      debugPrintC(
        'Push notifications are not supported on this platform. Skipping initialization... Done',
      );
      initDone = true;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _tokenStream?.cancel();
    _onMessageStream?.cancel();
    _onMessageOpenedAppStream?.cancel();
    _tokenStream = null;
    _onMessageStream = null;
    _onMessageOpenedAppStream = null;
    _authClient = null;
    super.dispose();
  }

  void setAuthClient(AuthClient? client) {
    _authClient = client;
  }

  Future<void> _init() async {
    _messaging = FirebaseMessaging.instance;
    debugPrintC('NotificationProvider initialization started');
    NotificationSettings settings = await _messaging!.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      debugPrintC('Push notification permission granted');
    } else if (settings.authorizationStatus ==
        AuthorizationStatus.provisional) {
      debugPrintC('Push notification permission granted provisionally');
    } else {
      debugPrintC('Push notification permission denied');
    }
    final bool isAllowed =
        settings.authorizationStatus == AuthorizationStatus.authorized ||
        settings.authorizationStatus == AuthorizationStatus.provisional;
    if (isAllowed) {
      debugPrintC('Push notifications are allowed. Getting FCM token...');
      await getFcmToken();
      try {
        debugPrintC('Setting up Firebase listeners for push notifications...');
        _setupFirebaseTokenListener(); // Listen for fcm token refresh events
        _setupFirebaseMessageForegroundListener(); // Listend for messages when the app is in foreground
        _setupFirebaseMessageBackgroundListener(); // Listend for essages when the app is in background, but not closed
        await _setupFirebaseMessageTerminatedListener(); // Listen for messages when the app is terminated
        debugPrintC(
          'Firebase listeners for push notifications set up successfully',
        );
        debugPrintC('FCM token at startup: $fcmToken');
        if (fcmToken != null && fcmToken!.isNotEmpty) {
          debugPrintC('Syncing FCM token with backend...');
          if ((_authClient != null) && _authClient!.isLoggedIn()) {
            await _authClient!.syncFcmTokenWithBackendinBackground(fcmToken!);
          } else {
            debugPrintC(
              'AuthClient is null or user is not logged in. Skipping FCM token sync with backend.',
            );
          }
        }
      } catch (e) {
        debugPrintC('Error setting up Firebase listeners: $e');
        _tokenStream?.cancel();
        _onMessageStream?.cancel();
        _onMessageOpenedAppStream?.cancel();
        _tokenStream = null;
        _onMessageStream = null;
        _onMessageOpenedAppStream = null;
      }
    }
    initDone = true;
    debugPrintC('NotificationProvider initialization completed');
    notifyListeners();
  }

  Future<void> getFcmToken() async {
    if (_messaging == null) {
      fcmToken = null;
      debugPrintC('FirebaseMessaging instance is null, cannot get FCM token');
      return;
    }
    try {
      String? newToken = await _messaging!.getToken();
      if (newToken != null) {
        fcmToken = newToken;
        debugPrintC('FCM token obtained : $newToken');
      } else {
        debugPrintC('Failed to get FCM token');
      }
    } catch (e) {
      debugPrintC('Error getting FCM token: $e');
      fcmToken = null;
    }
  }

  void _setupFirebaseTokenListener() {
    _tokenStream?.cancel();
    _tokenStream = _messaging!.onTokenRefresh.listen(
      (newToken) async {
        debugPrintC('FCM token refreshed locally: $newToken');
        debugPrintC('Syncing refreshed FCM token with backend...');
        fcmToken = newToken;
        if ((_authClient != null) && _authClient!.isLoggedIn()) {
          await _authClient!.syncFcmTokenWithBackendinBackground(newToken);
        } else {
          debugPrintC(
            'AuthClient is null or user is not logged in. Skipping FCM token sync with backend.',
          );
        }
      },
      onError: (error) {
        debugPrintC('Error in onTokenRefresh stream: $error');
        // We could use FirebaseCrashlytics to report this error
      },
    );
  }

  void _setupFirebaseMessageForegroundListener() {
    _onMessageStream?.cancel();
    _onMessageStream = FirebaseMessaging.onMessage.listen(
      (RemoteMessage message) {
        debugPrintC(
          'Notification: received a message while in the foreground: ${message.messageId}',
        );
        final actionLabel = message.data['action_label'] ?? "Ok";
        final messageTitle = message.notification?.title ?? 'Notification';
        final origin = message.data['origin'] ?? 'unknown';
        final alertId = message.data['alert_id'] ?? 'unknown';
        final currentRouteName = AppKeys.currentRouteName ?? '';
        if (currentRouteName.isNotEmpty) {
          debugPrintC('Notification: current route: $currentRouteName');
          if (origin == 'new_message' &&
              currentRouteName == '/alerts/view-alert-messages') {
            final currentAlertId = AppKeys.currentRouteArguments as int? ?? -1;
            if (currentAlertId != -1 && currentAlertId.toString() == alertId) {
              debugPrintC(
                'Notification: received a new_message for alert_id $alertId while already on the alert messages page. Not showing snackbar.',
              );
              _refreshMessagesPage(currentAlertId);
              return;
            }
          }
        }
        String notificationCounterStr = '';
        if (origin == currentNotificationOrigin) {
          if ((origin == 'new_message') || (origin == 'expand_alert')) {
            AppKeys.snackbarKey.currentState?.removeCurrentSnackBar();
            currentNotificationOriginCounter++;
            notificationCounterStr = ' ($currentNotificationOriginCounter)';
            debugPrintC(
              'Notification: received a message with the same origin "$origin" as the previous one. Incrementing counter to $currentNotificationOriginCounter.',
            );
          }
        } else {
          currentNotificationOriginCounter = 1;
          notificationCounterStr = '';
        }
        currentNotificationOrigin = origin;
        if (currentRouteName == '/alerts/view-alert-messages') {
          _showMaterialBanner(
            '$messageTitle$notificationCounterStr',
            actionLabel,
            () {
              currentNotificationOriginCounter = 0;
              handleNavigation(message.data);
            },
          );
        } else {
          _showSnackBar(
            '$messageTitle$notificationCounterStr',
            actionLabel,
            () {
              currentNotificationOriginCounter = 0;
              handleNavigation(message.data);
            },
          );
        }
      },
      onError: (error, stackTrace) {
        debugPrintC('Error in onMessage stream: $error');
        // We could use FirebaseCrashlytics to report this error
      },
    );
  }

  void _showSnackBar(
    String message,
    String actionLabel,
    VoidCallback onAction,
  ) {
    AppKeys.snackbarKey.currentState?.showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(
          hours: 24,
        ), // Keep the snackbar visible until the user interacts with it
        dismissDirection: DismissDirection.down,
        action: SnackBarAction(label: actionLabel, onPressed: onAction),
      ),
    );
  }

  void _showMaterialBanner(
    String message,
    String actionLabel,
    VoidCallback onAction,
  ) {
    AppKeys.snackbarKey.currentState?.showMaterialBanner(
      MaterialBanner(
        content: Text(message),
        leading: const Icon(Icons.notifications_active),
        actions: [
          TextButton(
            onPressed: () {
              AppKeys.snackbarKey.currentState?.hideCurrentMaterialBanner();
              onAction();
            },
            child: Text(actionLabel),
          ),
          IconButton(
            icon: const Icon(Icons.close),
            onPressed: () {
              AppKeys.snackbarKey.currentState?.hideCurrentMaterialBanner();
            },
          ),
        ],
      ),
    );
  }

  void _setupFirebaseMessageBackgroundListener() {
    _onMessageOpenedAppStream?.cancel();
    // It will trigger if the app is in background, but not terminated
    _onMessageOpenedAppStream = FirebaseMessaging.onMessageOpenedApp.listen(
      (RemoteMessage message) {
        debugPrintC(
          'Notification: app opened from background by tapping on a notification: ${message.messageId}',
        );
        WidgetsBinding.instance.addPostFrameCallback((_) {
          handleNavigation(message.data);
        });
      },
      onError: (error, stackTrace) {
        debugPrintC('Error in onMessageOpenedApp stream: $error');
        // We could use FirebaseCrashlytics to report this error
      },
    );
  }

  RemoteMessage? get initialMessage => _initialMessage;

  Future<void> _setupFirebaseMessageTerminatedListener() async {
    // It will only trigger if the app is completely terminated and opened by tapping on a notification
    if (_messaging == null) {
      debugPrintC(
        'FirebaseMessaging instance is null, cannot check for initial message.',
      );
      return;
    }
    try {
      debugPrintC(
        'Checking for initial message (app opened from terminated state)...',
      );
      _initialMessage = await _messaging!.getInitialMessage();
    } catch (e) {
      debugPrintC('Error checking for initial message: $e');
      _initialMessage = null;
      // We could use FirebaseCrashlytics to report this error
    }
    if (_initialMessage != null) {
      debugPrintC(
        'Notification: app opened from terminated state by tapping on a notification: ${_initialMessage!.messageId}',
      );
    } else {
      debugPrintC(
        'Notification: no initial message found when checking for app launch from terminated state.',
      );
    }
  }

  void handleNavigation(Map<String, dynamic> messageData) {
    if (!messageData.containsKey('origin') || messageData['origin'] == null) {
      debugPrintC(
        'Notification: message data does not contain an "origin" field. Ignoring.',
      );
      return;
    }
    switch (messageData['origin']) {
      case 'new_alert':
        _navigateToAlertDetails(messageData);
        break;
      case 'expand_alert':
        _navigateToAlertDetails(messageData);
        break;
      case 'close_alert':
        _navigateToAlertDetails(messageData);
        break;
      case 'new_message':
        _navigateToMessagesPage(messageData);
        break;
      default:
        debugPrintC(
          'Notification: unrecognized message origin "${messageData['origin']}". Ignoring.',
        );
    }
  }

  void _navigateToAlertDetails(Map<String, dynamic> messageData) {
    if (!messageData.containsKey('alert_id') ||
        messageData['alert_id'] == null) {
      debugPrintC(
        'Notification: ${messageData["origin"]} message does not contain an "alert_id" field.',
      );
      return;
    }
    debugPrintC(
      'Notification: navigating to alert details for alert_id: ${messageData["alert_id"]}',
    );
    String alertIdStr = messageData['alert_id'];
    AppKeys.navigatorKey.currentState?.pushNamedAndRemoveUntil(
      '/alerts/view-alert-details',
      (route) => false,
      arguments: int.tryParse(alertIdStr) ?? -1,
    );
  }

  void _navigateToMessagesPage(Map<String, dynamic> messageData) {
    if (!messageData.containsKey('alert_id') ||
        messageData['alert_id'] == null) {
      debugPrintC(
        'Notification: new_message message does not contain an "alert_id" field.',
      );
      return;
    }
    debugPrintC(
      'Notification: navigating to alert messages for alert_id: ${messageData["alert_id"]}',
    );
    String alertIdStr = messageData['alert_id'];
    AppKeys.navigatorKey.currentState?.pushNamedAndRemoveUntil(
      '/alerts/view-alert-messages',
      (route) => false,
      arguments: int.tryParse(alertIdStr) ?? -1,
    );
  }

  void _refreshMessagesPage(int alertId) {
    debugPrintC(
      'Notification: refreshing alert messages page for alert_id: $alertId',
    );
    AppKeys.navigatorKey.currentState?.pushReplacementNamed(
      '/alerts/view-alert-messages',
      arguments: alertId,
    );
  }
}
