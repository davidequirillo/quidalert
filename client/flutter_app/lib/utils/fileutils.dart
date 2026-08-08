// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:io';

final regex = RegExp(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}');

List<String> readEmailsFromFile(String filePath) {
  List<String> emails = List<String>.empty(growable: true);
  final List<String> lines = File(filePath).readAsLinesSync();
  for (var line in lines) {
    final email = line.trim().contains(regex)
        ? regex.firstMatch(line)!.group(0)!
        : '';
    if (email.isNotEmpty) {
      emails.add(email.toLowerCase());
    }
  }
  return emails;
}
