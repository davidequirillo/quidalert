// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';

class AppKeys {
  // Global keys for navigation and snackbar management
  static final GlobalKey<NavigatorState> navigatorKey =
      GlobalKey<NavigatorState>();
  static final GlobalKey<ScaffoldMessengerState> snackbarKey =
      GlobalKey<ScaffoldMessengerState>();
  // Keeps track of the current route name to allow navigation from anywhere in the app
  static String? currentRouteName;
  // Keeps track of the current route arguments to allow navigation from anywhere in the app
  static Object? currentRouteArguments;
}

class AppRouteObserver extends NavigatorObserver {
  void _updateContext(Route<dynamic>? route) {
    if (route is PageRoute) {
      AppKeys.currentRouteName = route.settings.name;
      AppKeys.currentRouteArguments = route.settings.arguments;
    }
  }

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    _updateContext(route);
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    _updateContext(previousRoute);
  }

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) {
    _updateContext(newRoute);
  }
}
