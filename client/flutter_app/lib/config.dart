// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2025-2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

abstract class AppConfig {
  // The API URL is set via environment variable at build time.
  // If not set, it defaults to "defaultValue" for local development.
  static const String _rawApiUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://10.0.2.2:8000/api',
  );
  static const appName = 'Quidalert';
  // The competence territory, examples:
  // Italy, France, Germany, Spain, Britain, United States, Canada, etc.
  static const competenceTerritory = 'Italy';
  // The API URL, cleaned of any trailing slashes.
  static String get apiUrl {
    final cleanUrl = _rawApiUrl.trim();
    if (cleanUrl.endsWith('/')) {
      return cleanUrl.substring(0, cleanUrl.length - 1);
    }
    return cleanUrl;
  }
}
