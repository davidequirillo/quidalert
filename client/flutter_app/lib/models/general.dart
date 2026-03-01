// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

class WhiteListEntry {
  final int id;
  final String email;
  final String createdBy;
  final DateTime createdAt;

  WhiteListEntry({
    required this.id,
    required this.email,
    required this.createdBy,
    required this.createdAt,
  });

  factory WhiteListEntry.fromJson(Map<String, dynamic> json) {
    return WhiteListEntry(
      id: json['id'],
      email: json['email'],
      createdBy: json['created_by'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

enum UserStatus { ok, unreliable, blocked }

enum UserType { admin, officer, chief, base }

enum UserRole {
  firefighter,
  wateroperator,
  usar,
  alpinerescuer,
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
    String st;
    final String id = json['id'] ?? '';
    final String email = json['email'] ?? '';
    final String fname = json['firstname'] ?? '';
    final String sname = json['surname'] ?? '';
    final String? authBy = json['authorized_by'];
    final DateTime? authAt = json['authorized_at'] != null
        ? DateTime.parse(json['authorized_at'])
        : null;
    final bool isAdmin = json['is_admin'] ?? false;
    final bool isOfficer = json['is_officer'] ?? false;
    final bool isChief = json['is_chief'] ?? false;
    final String role = json['role'] ?? '';
    final bool isReliable = json['is_reliable'] ?? true;
    final bool isBlocked = json['is_blocked'] ?? false;
    if (isAdmin == true) {
      t = "admin";
    } else if (isOfficer == true) {
      t = "officer";
    } else if (isChief == true) {
      t = "chief";
    } else {
      t = "base";
    }
    if (isReliable == false) {
      st = "unreliable";
    } else if (isBlocked == true) {
      st = "blocked";
    } else {
      st = "ok";
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
      status: st,
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
  final String notes;

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
    required this.notes,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    String t;
    String st;
    final String id = json['id'] ?? '';
    final String email = json['email'] ?? '';
    final String fname = json['firstname'] ?? '';
    final String sname = json['surname'] ?? '';
    final String lang = json['language'] ?? '';
    final bool isAdmin = json['is_admin'] ?? false;
    final bool isOfficer = json['is_officer'] ?? false;
    final bool isChief = json['is_chief'] ?? false;
    if (isAdmin == true) {
      t = "admin";
    } else if (isOfficer == true) {
      t = "officer";
    } else if (isChief == true) {
      t = "chief";
    } else {
      t = "base";
    }
    final String role = json['role'] ?? '';
    final bool isReliable = json['is_reliable'] ?? true;
    final bool isBlocked = json['is_blocked'] ?? false;
    if (isReliable == false) {
      st = "unreliable";
    } else if (isBlocked == true) {
      st = "blocked";
    } else {
      st = "ok";
    }
    final int reliabilityScore = json['reliability_score'] ?? 0;
    final bool isActive = json['is_active'] ?? false;
    final DateTime? resetLockedUntil = json['reset_locked_until'] != null
        ? DateTime.parse(json['reset_locked_until'])
        : null;
    final DateTime? lastResetDoneAt = json['last_reset_done_at'] != null
        ? DateTime.parse(json['last_reset_done_at'])
        : null;
    final DateTime? loginLockedUntil = json['login_locked_until'] != null
        ? DateTime.parse(json['login_locked_until'])
        : null;
    final DateTime? lastLoginDoneAt = json['last_login_done_at'] != null
        ? DateTime.parse(json['last_login_done_at'])
        : null;
    final DateTime? lastRefreshAt = json['last_refresh_at'] != null
        ? DateTime.parse(json['last_refresh_at'])
        : null;
    final DateTime? creatAt = json['created_at'] != null
        ? DateTime.parse(json['created_at'])
        : null;
    final String? authBy = json['authorized_by'];
    final DateTime? authAt = json['authorized_at'] != null
        ? DateTime.parse(json['authorized_at'])
        : null;
    final DateTime? updAt = json['updated_at'] != null
        ? DateTime.parse(json['updated_at'])
        : null;
    final String? updBy = json['updated_by'];
    final String street = json['street'] ?? '';
    final String postalCode = json['postal_code'] ?? '';
    final String city = json['city'] ?? '';
    final String province = json['province'] ?? '';
    final String country = json['country'] ?? '';
    final String birthDate = json['birthdate'] ?? '';
    final String phone = json['phone'] ?? '';
    final String notes = json['notes'] ?? '';
    return User(
      id: id,
      email: email,
      firstname: fname,
      surname: sname,
      language: lang,
      type: t,
      role: role,
      status: st,
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
      notes: notes,
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
    final String id = json['id'] ?? '';
    final String userId = json['user_id'] ?? '';
    final bool isClosed = json['is_closed'] ?? false;
    String status;
    if (isClosed) {
      status = "closed";
    } else {
      status = "open";
    }
    final DateTime? createdAt = json['created_at'] != null
        ? DateTime.parse(json['created_at'])
        : null;
    final int severity = json['severity'] ?? 0;
    final String description = json['description'] ?? '';
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
