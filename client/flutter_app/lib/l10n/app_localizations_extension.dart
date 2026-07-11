// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:quidalert_flutter/l10n/app_localizations.dart';

extension AppLocalizationsExtension on AppLocalizations {
  String? getString(String key) {
    switch (key) {
      case 'exceptionBadRequest':
        return exceptionBadRequest;
      case 'exceptionForbiddenRequest':
        return exceptionForbiddenRequest;
      case 'exceptionGenericNotAuthorized':
        return exceptionGenericNotAuthorized;
      case 'exceptionNetwork':
        return exceptionNetwork;
      case 'exceptionServer':
        return exceptionServer;
      case 'exceptionNotFound':
        return exceptionNotFound;
      case 'exceptionFromJsonObj':
        return exceptionFromJsonObj;
      case 'exceptionUnknown':
        return exceptionUnknown;
      case 'alertTypeGeneral':
        return alertTypeGeneral;
      case 'alertTypeLocal':
        return alertTypeLocal;
      case 'alertTypeManaged':
        return alertTypeManaged;
      case 'alertTypeEmpty':
        return alertTypeEmpty;
      case 'alertStatusOpen':
        return alertStatusOpen;
      case 'alertStatusClosed':
        return alertStatusClosed;
      case 'alertStatusPending':
        return alertStatusPending;
      default:
        return null;
    }
  }

  String? operator [](String key) => getString(key);
}
