// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

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

enum UserRole {
  firefighter,
  wateroperator,
  usar,
  alpinerescuer,
  medic,
  military,
  policeman,
  volunteer,
}

enum UserRoleExtended {
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

enum UserStatus { unreliable, blocked }

enum UserStatusExtended { unreliable, blocked, ok }

enum UserType { admin, officer, chief }

enum UserTypeExtended { admin, officer, chief, base }

enum AlertType { local, managed, general, empty }

enum AlertStatus { open, closed }

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
  final String phone;

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
    required this.phone,
  });

  factory UserSmall.fromJson(Map<String, dynamic> json) {
    String t;
    String s;
    final String id = json['id'] ?? '';
    final String email = json['email'] ?? '';
    final String fname = json['firstname'] ?? '';
    final String sname = json['surname'] ?? '';
    final String? authBy = json['authorized_by'];
    final DateTime? authAt = json['authorized_at'] != null
        ? DateTime.parse(json['authorized_at'])
        : null;
    final String phone = json['phone'] ?? '';
    final bool isAdmin = json['is_admin'] ?? false;
    final bool isOfficer = json['is_officer'] ?? false;
    final bool isChief = json['is_chief'] ?? false;
    final String role =
        json['role'] ??
        UserRoleExtended.citizen.name; // default role is "citizen"
    final bool isReliable = json['is_reliable'] ?? true;
    final bool isBlocked = json['is_blocked'] ?? false;
    if (isAdmin == true) {
      t = UserTypeExtended.admin.name;
    } else if (isOfficer == true) {
      t = UserTypeExtended.officer.name;
    } else if (isChief == true) {
      t = UserTypeExtended.chief.name;
    } else {
      t = UserTypeExtended.base.name;
    }
    if (isBlocked == true) {
      s = UserStatusExtended.blocked.name;
    } else if (isReliable == false) {
      s = UserStatusExtended.unreliable.name;
    } else {
      s = UserStatusExtended.ok.name;
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
      status: s,
      phone: phone,
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
    String s;
    final String id = json['id'] ?? '';
    final String email = json['email'] ?? '';
    final String fname = json['firstname'] ?? '';
    final String sname = json['surname'] ?? '';
    final String lang = json['language'] ?? '';
    final bool isAdmin = json['is_admin'] ?? false;
    final bool isOfficer = json['is_officer'] ?? false;
    final bool isChief = json['is_chief'] ?? false;
    if (isAdmin == true) {
      t = UserTypeExtended.admin.name;
    } else if (isOfficer == true) {
      t = UserTypeExtended.officer.name;
    } else if (isChief == true) {
      t = UserTypeExtended.chief.name;
    } else {
      t = UserTypeExtended.base.name;
    }
    final String role =
        json['role'] ??
        UserRoleExtended.citizen.name; // default role is "citizen"
    final bool isReliable = json['is_reliable'] ?? true;
    final bool isBlocked = json['is_blocked'] ?? false;
    if (isBlocked == true) {
      s = UserStatusExtended.blocked.name;
    } else if (isReliable == false) {
      s = UserStatusExtended.unreliable.name;
    } else {
      s = UserStatusExtended.ok.name;
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
      status: s,
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
  final String type;
  final String description;
  final String status;
  final DateTime? createdAt;

  Alert({
    required this.id,
    required this.type,
    required this.description,
    required this.status,
    required this.createdAt,
  });

  factory Alert.fromJson(Map<String, dynamic> json) {
    final String id = json['id'].toString();
    final bool isClosed = json['is_closed'] ?? false;
    String status;
    if (isClosed) {
      status = AlertStatus.closed.name;
    } else {
      status = AlertStatus.open.name;
    }
    final DateTime? createdAt = json['created_at'] != null
        ? DateTime.parse(json['created_at'])
        : null;
    final String type = json['type'] ?? '';
    final String description = json['description'] ?? '';
    return Alert(
      id: id,
      type: type,
      description: description,
      status: status,
      createdAt: createdAt,
    );
  }
}
