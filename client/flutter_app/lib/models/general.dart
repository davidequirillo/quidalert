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
  final String id;
  final String email;
  final String firstname;
  final String surname;
  final String? authorizedBy;
  final DateTime? authorizedAt;
  final String type;
  final String role;
  final String status;

  UserSmall({
    required this.id,
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
    final id = json['id'] ?? '';
    final email = json['email'] ?? '';
    final fname = json['firstname'] ?? '';
    final sname = json['surname'] ?? '';
    final authBy = json['authorized_by'];
    final authAt = json['authorized_at'] != null
        ? DateTime.parse(json['authorized_at'])
        : null;
    final isAdmin = json['is_admin'] ?? false;
    final isOfficer = json['is_officer'] ?? false;
    final isChief = json['is_chief'] ?? false;
    final role = json['role'] ?? '';
    final status = json['status'] ?? '';
    if (isAdmin == true) {
      t = "admin";
    } else if (isOfficer == true) {
      t = "officer";
    } else if (isChief == true) {
      t = "chief";
    } else {
      t = "base";
    }
    return UserSmall(
      id: id,
      email: email,
      firstname: fname,
      surname: sname,
      authorizedBy: authBy,
      authorizedAt: authAt,
      type: t,
      role: role,
      status: status,
    );
  }
}

class User {
  final String id;
  final String email;
  final String firstname;
  final String surname;
  final String language;
  final String type;
  final String role;
  final String status;
  final int reliabilityScore;
  final bool isActive;
  final DateTime? resetLockedUntil;
  final DateTime? lastResetDoneAt;
  final DateTime? loginLockedUntil;
  final DateTime? lastLoginDoneAt;
  final DateTime? lastRefreshAt;
  final DateTime? createdAt;
  final String? updatedBy;
  final DateTime? updatedAt;
  final String? authorizedBy;
  final DateTime? authorizedAt;
  final String street;
  final String postalCode;
  final String city;
  final String province;
  final String country;
  final String birthDate;
  final String phone;

  User({
    required this.id,
    required this.email,
    required this.firstname,
    required this.surname,
    required this.language,
    required this.type,
    required this.role,
    required this.status,
    required this.reliabilityScore,
    required this.isActive,
    required this.resetLockedUntil,
    required this.lastResetDoneAt,
    required this.loginLockedUntil,
    required this.lastLoginDoneAt,
    required this.lastRefreshAt,
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
    required this.birthDate,
    required this.phone,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    String t;
    final id = json['id'] ?? '';
    final email = json['email'] ?? '';
    final fname = json['firstname'] ?? '';
    final sname = json['surname'] ?? '';
    final lang = json['language'] ?? '';
    final isAdmin = json['is_admin'] ?? false;
    final isOfficer = json['is_officer'] ?? false;
    final isChief = json['is_chief'] ?? false;
    if (isAdmin == true) {
      t = "admin";
    } else if (isOfficer == true) {
      t = "officer";
    } else if (isChief == true) {
      t = "chief";
    } else {
      t = "base";
    }
    final role = json['role'] ?? '';
    final status = json['status'] ?? '';
    final reliabilityScore = json['reliability_score'] ?? 0;
    final isActive = json['is_active'] ?? false;
    final resetLockedUntil = json['reset_locked_until'] != null
        ? DateTime.parse(json['reset_locked_until'])
        : null;
    final lastResetDoneAt = json['last_reset_done_at'] != null
        ? DateTime.parse(json['last_reset_done_at'])
        : null;
    final loginLockedUntil = json['login_locked_until'] != null
        ? DateTime.parse(json['login_locked_until'])
        : null;
    final lastLoginDoneAt = json['last_login_done_at'] != null
        ? DateTime.parse(json['last_login_done_at'])
        : null;
    final lastRefreshAt = json['last_refresh_at'] != null
        ? DateTime.parse(json['last_refresh_at'])
        : null;
    final creatAt = json['created_at'] != null
        ? DateTime.parse(json['created_at'])
        : null;
    final authBy = json['authorized_by'];
    final authAt = json['authorized_at'] != null
        ? DateTime.parse(json['authorized_at'])
        : null;
    final updAt = json['updated_at'] != null
        ? DateTime.parse(json['updated_at'])
        : null;
    final updBy = json['updated_by'];
    final street = json['street'] ?? '';
    final postalCode = json['postal_code'] ?? '';
    final city = json['city'] ?? '';
    final province = json['province'] ?? '';
    final country = json['country'] ?? '';
    final birthDate = json['birthdate'] ?? '';
    final phone = json['phone'] ?? '';
    return User(
      id: id,
      email: email,
      firstname: fname,
      surname: sname,
      language: lang,
      type: t,
      role: role,
      status: status,
      reliabilityScore: reliabilityScore,
      isActive: isActive,
      resetLockedUntil: resetLockedUntil,
      lastResetDoneAt: lastResetDoneAt,
      loginLockedUntil: loginLockedUntil,
      lastLoginDoneAt: lastLoginDoneAt,
      lastRefreshAt: lastRefreshAt,
      createdAt: creatAt,
      updatedBy: updBy,
      updatedAt: updAt,
      authorizedBy: authBy,
      authorizedAt: authAt,
      street: street,
      postalCode: postalCode,
      city: city,
      province: province,
      country: country,
      birthDate: birthDate,
      phone: phone,
    );
  }
}

class Alert {
  final String id;
  final String userId;
  final String description;
  final int severity;
  final String status;
  final DateTime? createdAt;

  Alert({
    required this.id,
    required this.userId,
    required this.description,
    required this.severity,
    required this.status,
    required this.createdAt,
  });

  factory Alert.fromJson(Map<String, dynamic> json) {
    final id = json['id'] ?? '';
    final userId = json['user_id'] ?? '';
    final isClosed = json['is_closed'] ?? false;
    String status;
    if (isClosed) {
      status = "closed";
    } else {
      status = "open";
    }
    final createdAt = json['created_at'] != null
        ? DateTime.parse(json['created_at'])
        : null;
    final severity = json['severity'] ?? 0;
    final description = json['description'] ?? '';
    return Alert(
      id: id,
      userId: userId,
      description: description,
      severity: severity,
      status: status,
      createdAt: createdAt,
    );
  }
}
