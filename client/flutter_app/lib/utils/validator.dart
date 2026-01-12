// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

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
  int min = 0,
  int max = 256,
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

String? validateDigitCode(
  BuildContext context,
  String? value, {
  int min = 8,
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
