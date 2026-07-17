// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/widgets.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';

typedef StringValidator = String? Function(String? value);

String? validateName(BuildContext context, String? value) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.trim().isEmpty) {
    return l10n.errorStringNotValid;
  }
  if (value.trim().length < 2) {
    return l10n.errorStringTooShort;
  }
  if (value.trim().length > 64) {
    return l10n.errorStringTooLong;
  }
  return null;
}

String? validateDescription(
  BuildContext context,
  String? value, {
  int min = 1,
  int max = 512,
}) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.trim().isEmpty) {
    return l10n.errorStringNotValid;
  }
  final text = value.trim();
  if (text.length < min) {
    return l10n.errorStringTooShort;
  }
  if (text.length > max) {
    return l10n.errorStringTooLong;
  }
  return null;
}

String? validatePassword(
  BuildContext context,
  String? value, {
  int minLength = 10,
  bool requireUppercase = true,
  bool requireLowercase = true,
  bool requireDigit = true,
  bool requireSpecialChar = true,
}) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.isEmpty) {
    return l10n.errorStringNotValid;
  }
  if (value.length < minLength) {
    return l10n.errorStringTooShort;
  }
  if (requireUppercase && !value.contains(RegExp(r'[A-Z]'))) {
    return l10n.errorPasswordMissingUppercase;
  }
  if (requireLowercase && !value.contains(RegExp(r'[a-z]'))) {
    return l10n.errorPasswordMissingLowercase;
  }
  if (requireDigit && !value.contains(RegExp(r'[0-9]'))) {
    return l10n.errorPasswordMissingDigit;
  }
  if (requireSpecialChar &&
      !value.contains(RegExp(r'[!@#\$%\^&*()\[\],;+=.?":{}|<>_\-]'))) {
    return l10n.errorPasswordMissingSpecial;
  }
  return null;
}

String? validateEmail(BuildContext context, String? value) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.trim().isEmpty) {
    return l10n.errorStringNotValid;
  }
  final email = value.trim();
  final emailRegex = RegExp(r'^[^@]+@[^@]+\.[^@]+$');
  if (!emailRegex.hasMatch(email)) {
    return l10n.errorStringNotValid;
  }
  return null;
}

String? validateDeleteConfirmation(BuildContext context, String? value) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.trim() != "DELETE") {
    return l10n.errorStringNotValid;
  }
  return null;
}

String? validateDigitCode(
  BuildContext context,
  String? value, {
  int min = 10,
  int max = 32,
}) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.trim().isEmpty) {
    return l10n.errorStringNotValid;
  }
  final text = value.trim();
  if (!RegExp(r'^\d+$').hasMatch(text)) {
    return l10n.errorDigitOnly;
  }
  if (text.length < min) {
    return l10n.errorStringTooShort;
  }
  if (text.length > max) {
    return l10n.errorStringTooLong;
  }
  return null;
}

String? validateAddress(BuildContext context, String? value) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.trim().isEmpty) {
    return l10n.errorStringNotValid;
  }
  if (value.trim().length < 5) {
    return l10n.errorStringTooShort;
  }
  if (value.trim().length > 256) {
    return l10n.errorStringTooLong;
  }
  return null;
}

String? validateStreetAndNumber(BuildContext context, String? value) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.trim().isEmpty) {
    return l10n.errorStringNotValid;
  }
  if (value.trim().length < 5) {
    return l10n.errorStringTooShort;
  }
  if (value.trim().length > 256) {
    return l10n.errorStringTooLong;
  }
  return null;
}

String? validateCity(BuildContext context, String? value) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.trim().isEmpty) {
    return l10n.errorStringNotValid;
  }
  if (value.trim().length < 2) {
    return l10n.errorStringTooShort;
  }
  if (value.trim().length > 128) {
    return l10n.errorStringTooLong;
  }
  return null;
}

String? validatePostalCode(BuildContext context, String? value) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.trim().isEmpty) {
    return l10n.errorStringNotValid;
  }
  if (value.trim().length < 2) {
    return l10n.errorStringTooShort;
  }
  if (value.trim().length > 16) {
    return l10n.errorStringTooLong;
  }
  return null;
}

String? validateProvince(BuildContext context, String? value) {
  return validateCity(context, value);
}

String? validateCountry(BuildContext context, String? value) {
  return validateCity(context, value);
}

String? validateBirthdate(BuildContext context, String? value) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.trim().isEmpty) {
    return l10n.errorStringNotValid;
  }
  try {
    DateTime.parse(value.trim());
  } catch (e) {
    return l10n.errorStringNotValid;
  }
  return null;
}

String? validatePhoneNumber(BuildContext context, String? value) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.trim().isEmpty) {
    return l10n.errorStringNotValid;
  }
  final phone = value.trim();
  final phoneRegex = RegExp(r'^\+?[0-9\s\-]+$');
  if (!phoneRegex.hasMatch(phone)) {
    return l10n.errorStringNotValid;
  }
  if (phone.length < 5) {
    return l10n.errorStringTooShort;
  }
  if (phone.length > 32) {
    return l10n.errorStringTooLong;
  }
  return null;
}

String? validateGpsCoordinates(BuildContext context, String? value) {
  final l10n = AppLocalizations.of(context)!;
  if (value == null || value.trim().isEmpty) {
    return l10n.errorStringNotValid;
  }
  final coords = value.trim().split(",");
  if (coords.length != 2) {
    return l10n.errorStringNotValid;
  }
  final lat = double.tryParse(coords[0].trim());
  final lon = double.tryParse(coords[1].trim());
  if (lat == null || lon == null) {
    return l10n.errorStringNotValid;
  }
  if (lat < -90 || lat > 90) {
    return l10n.errorStringNotValid;
  }
  if (lon < -180 || lon > 180) {
    return l10n.errorStringNotValid;
  }
  return null;
}
