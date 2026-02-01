// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

class WhiteListEntry {
  final String email;
  final String createdBy;
  final DateTime createdAt;

  WhiteListEntry({
    required this.email,
    required this.createdBy,
    required this.createdAt,
  });

  factory WhiteListEntry.fromJson(Map<String, dynamic> json) {
    return WhiteListEntry(
      email: json['email'],
      createdBy: json['created_by'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
