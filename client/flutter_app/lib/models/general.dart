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

enum UserStatus { ok, unreliable, blocked }

enum UserType { admin, officer, chief }

enum UserRole {
  firefighter,
  wateroperator,
  usar,
  alpinrescuer,
  medic,
  military,
  policeman,
  volunteer,
  citizen,
}

class UserSmall {
  final String email;
  final String firstname;
  final String surname;
  final String? authorizedBy;
  final DateTime? authorizedAt;
  final String type;
  final String role;
  final String status;

  UserSmall({
    required this.email,
    required this.firstname,
    required this.surname,
    required this.authorizedBy,
    required this.authorizedAt,
    required this.type,
    required this.role,
    required this.status,
  });

  factory UserSmall.fromJson(Map<String, dynamic> json) {
    String t;
    if (json['is_admin'] == true) {
      t = "admin";
    } else if (json['is_officer'] == true) {
      t = "officer";
    } else if (json['is_chief'] == true) {
      t = "chief";
    } else {
      t = "base";
    }
    final authAt = json['authorized_at'] != null
        ? DateTime.parse(json['authorized_at'])
        : null;
    return UserSmall(
      email: json['email'],
      firstname: json['firstname'],
      surname: json['surname'],
      authorizedBy: json['authorized_by'],
      authorizedAt: authAt,
      type: t,
      role: json['role'],
      status: json['status'],
    );
  }
}

class User {
  final String email;
  final String firstname;
  final String surname;
  final String type;
  final String role;
  final String status;
  final DateTime? createdAt;
  final String? updatedBy;
  final DateTime? updatedAt;
  final String? authorizedBy;
  final DateTime? authorizedAt;
  final String? street;
  final String? postalCode;
  final String? city;
  final String? province;
  final String? country;
  final String? phone;

  User({
    required this.email,
    required this.firstname,
    required this.surname,
    required this.type,
    required this.role,
    required this.status,
    required this.createdAt,
    required this.updatedBy,
    required this.updatedAt,
    required this.authorizedBy,
    required this.authorizedAt,
    required this.street,
    required this.postalCode,
    required this.city,
    required this.province,
    required this.country,
    required this.phone,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    String t;
    if (json['is_admin'] == true) {
      t = "admin";
    } else if (json['is_officer'] == true) {
      t = "officer";
    } else if (json['is_chief'] == true) {
      t = "chief";
    } else {
      t = "base";
    }
    final authAt = json['authorized_at'] != null
        ? DateTime.parse(json['authorized_at'])
        : null;
    final creatAt = json['created_at'] != null
        ? DateTime.parse(json['created_at'])
        : null;
    final updAt = json['updated_at'] != null
        ? DateTime.parse(json['updated_at'])
        : null;
    return User(
      email: json['email'],
      firstname: json['firstname'],
      surname: json['surname'],
      type: t,
      role: json['role'],
      status: json['status'],
      createdAt: creatAt,
      updatedBy: json['updated_by'],
      updatedAt: updAt,
      authorizedBy: json['authorized_by'],
      authorizedAt: authAt,
      street: json['street'],
      postalCode: json['postal_code'],
      city: json['city'],
      province: json['province'],
      country: json['country'],
      phone: json['phone'],
    );
  }
}
