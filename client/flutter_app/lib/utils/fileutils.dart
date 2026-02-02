// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

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
