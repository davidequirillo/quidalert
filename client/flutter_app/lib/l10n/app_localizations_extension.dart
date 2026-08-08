// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:quidalert_flutter/l10n/app_localizations.dart';

extension AppLocalizationsExtension on AppLocalizations {
  String? getString(String key) {
    switch (key) {
      default:
        return null;
    }
  }

  String? getExceptionString(String key) {
    switch (key) {
      case 'BadRequestException':
        return exceptionBadRequest;
      case 'ForbiddenRequestException':
        return exceptionForbiddenRequest;
      case 'GenericNotAuthorizedException':
        return exceptionGenericNotAuthorized;
      case 'NetworkException':
        return exceptionNetwork;
      case 'ServerException':
        return exceptionServer;
      case 'NotFoundException':
        return exceptionNotFound;
      case 'FromJsonObjException':
        return exceptionFromJsonObj;
      case 'UnknownException':
        return exceptionUnknown;
      default:
        return null;
    }
  }

  String getBooleanString(String value) {
    switch (value) {
      case "true":
        return booleanTrue;
      case "false":
        return booleanFalse;
      default:
        return '';
    }
  }

  String getAlertTypeString(String key) {
    switch (key) {
      case 'general':
        return alertTypeGeneral;
      case 'local':
        return alertTypeLocal;
      case 'managed':
        return alertTypeManaged;
      case 'empty':
        return alertTypeEmpty;
      default:
        return '';
    }
  }

  String getAlertStatusString(String key) {
    switch (key) {
      case 'open':
        return alertStatusOpen;
      case 'closed':
        return alertStatusClosed;
      case 'pending':
        return alertStatusPending;
      default:
        return '';
    }
  }

  String getUserRoleString(String key) {
    switch (key) {
      case 'firefighter':
        return userRoleFirefighter;
      case 'wateroperator':
        return userRoleWateroperator;
      case 'usar':
        return userRoleUsar;
      case 'alpinerescuer':
        return userRoleAlpinerescuer;
      case 'medic':
        return userRoleMedic;
      case 'military':
        return userRoleMilitary;
      case 'policeman':
        return userRolePoliceman;
      case 'volunteer':
        return userRoleVolunteer;
      case 'citizen':
        return userRoleCitizen;
      default:
        return '';
    }
  }

  String getUserStatusString(String key) {
    switch (key) {
      case 'ok':
        return userStatusOk;
      case 'unreliable':
        return userStatusUnreliable;
      case 'blocked':
        return userStatusBlocked;
      default:
        return '';
    }
  }

  String getUserTypeString(String key) {
    switch (key) {
      case 'chief':
        return userTypeChief;
      case 'officer':
        return userTypeOfficer;
      case 'admin':
        return userTypeAdmin;
      case 'base':
        return userTypeBase;
      default:
        return '';
    }
  }

  String getClosingTypeButtonString(String key) {
    switch (key) {
      case 'positive':
        return buttonClosingPositive;
      case 'negative':
        return buttonClosingNegative;
      case 'neutral':
        return buttonClosingNeutral;
      case 'punitive':
        return buttonClosingPunitive;
      default:
        return '';
    }
  }

  String? operator [](String key) => getString(key);
}
