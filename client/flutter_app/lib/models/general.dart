// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:quidalert_flutter/utils/strings.dart';

class FromJsonObjException implements Exception {
  final String? message;
  FromJsonObjException([this.message = "Error parsing JSON object"]);
  @override
  String toString() => "FromJsonObjException: $message";
}

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
    final createdAt = json['created_at'] != null
        ? DateTime.parse("${json['created_at']}Z")
        : DateTime(0);
    return WhiteListEntry(
      id: json['id'],
      email: json['email'],
      createdBy: json['created_by'],
      createdAt: createdAt,
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

enum AlertStatus { pending, open, closed }

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
        ? DateTime.parse("${json['authorized_at']}Z")
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
  final int heroScore;
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
    required this.heroScore,
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
    final int heroScore = json['hero_score'] ?? 0;
    final bool isActive = json['is_active'] ?? false;
    final DateTime? resetLockedUntil = json['reset_locked_until'] != null
        ? DateTime.parse("${json['reset_locked_until']}Z")
        : null;
    final DateTime? lastResetDoneAt = json['last_reset_done_at'] != null
        ? DateTime.parse("${json['last_reset_done_at']}Z")
        : null;
    final DateTime? loginLockedUntil = json['login_locked_until'] != null
        ? DateTime.parse("${json['login_locked_until']}Z")
        : null;
    final DateTime? lastLoginDoneAt = json['last_login_done_at'] != null
        ? DateTime.parse("${json['last_login_done_at']}Z")
        : null;
    final DateTime? lastRefreshAt = json['last_refresh_at'] != null
        ? DateTime.parse("${json['last_refresh_at']}Z")
        : null;
    final DateTime? creatAt = json['created_at'] != null
        ? DateTime.parse("${json['created_at']}Z")
        : null;
    final String? authBy = json['authorized_by'];
    final DateTime? authAt = json['authorized_at'] != null
        ? DateTime.parse("${json['authorized_at']}Z")
        : null;
    final DateTime? updAt = json['updated_at'] != null
        ? DateTime.parse("${json['updated_at']}Z")
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
      heroScore: heroScore,
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
  final int id;
  final String type;
  final String description;
  String status; // it can be updated without reloading the whole object
  final bool isExpanded;
  final double latitude;
  final double longitude;
  final String? address;
  final double radius;
  final DateTime createdAt;

  Alert({
    required this.id,
    required this.type,
    required this.description,
    required this.status,
    required this.isExpanded,
    required this.latitude,
    required this.longitude,
    required this.address,
    required this.radius,
    required this.createdAt,
  });

  factory Alert.fromJson(Map<String, dynamic> json) {
    final int id = json['id'] ?? 0;
    final bool isClosed = json['is_closed'] ?? false;
    final bool isPending = json['is_pending'] ?? true;
    final bool isExpanded = json['is_expanded'] ?? false;
    String status;
    if (isClosed) {
      status = AlertStatus.closed.name;
    } else if (isPending) {
      status = AlertStatus.pending.name;
    } else {
      status = AlertStatus.open.name;
    }
    final DateTime createdAt = json['created_at'] != null
        ? DateTime.parse("${json['created_at']}Z").toLocal()
        : DateTime(0);
    final String type = json['type'] ?? '';
    final String description = json['description'] ?? '';
    final double latitude = json['latitude'] != null
        ? json['latitude'].toDouble()
        : 0.0;
    final double longitude = json['longitude'] != null
        ? json['longitude'].toDouble()
        : 0.0;
    final double radius = json['radius'] != null
        ? json['radius'].toDouble()
        : 0.0;
    final String? address = json['address'];
    return Alert(
      id: id,
      type: type,
      description: description,
      latitude: latitude,
      longitude: longitude,
      address: address,
      radius: radius,
      status: status,
      isExpanded: isExpanded,
      createdAt: createdAt,
    );
  }
}

class AlertWithInfo {
  final Alert alert;
  final User? sender;
  final String senderFirstname;
  final String senderSurname;
  final String? chiefFirstname;
  final String? chiefSurname;
  final int senderReliabilityScore;
  final int alertedUsersNum;
  int positiveVotesNum; // it can be updated without reloading the whole object
  int negativeVotesNum; // it can be updated without reloading the whole object
  int chiefClosingVote; // it can be updated without reloading the whole object
  final int messagesNum;
  final bool userIsSender;
  final bool userIsAlerted;
  final bool userIsManager;
  int userVote; // it can be updated without reloading the whole object

  AlertWithInfo({
    required this.alert,
    required this.sender,
    required this.senderFirstname,
    required this.senderSurname,
    required this.senderReliabilityScore,
    required this.chiefFirstname,
    required this.chiefSurname,
    required this.alertedUsersNum,
    required this.positiveVotesNum,
    required this.negativeVotesNum,
    required this.chiefClosingVote,
    required this.messagesNum,
    required this.userIsSender,
    required this.userIsAlerted,
    required this.userIsManager,
    required this.userVote,
  });

  factory AlertWithInfo.fromJson(Map<String, dynamic> json) {
    try {
      final alert = Alert.fromJson(json['alert']);
      return AlertWithInfo(
        alert: alert,
        sender: json['sender'] != null ? User.fromJson(json['sender']) : null,
        senderFirstname: json['sender_firstname'],
        senderSurname: json['sender_surname'],
        senderReliabilityScore: json['sender_reliability_score'],
        chiefFirstname: json['chief_firstname'],
        chiefSurname: json['chief_surname'],
        alertedUsersNum: json['alerted_users_num'],
        positiveVotesNum: json['positive_votes_num'],
        negativeVotesNum: json['negative_votes_num'],
        chiefClosingVote: json['chief_closing_vote'],
        messagesNum: json['messages_num'],
        userIsSender: json['user_is_sender'],
        userIsAlerted: json['user_is_alerted'],
        userIsManager: json['user_is_manager'],
        userVote: json['user_vote'],
      );
    } catch (e) {
      debugPrintC("Error parsing AlertWithInfo from JSON: $e");
      throw FromJsonObjException();
    }
  }
}

class AlertedUser {
  // Note: the related backend model is "AlertedUserJoined"
  final User user;
  final int alertId;
  final double distance; // in kilometers
  final bool isManager;
  final int vote;
  final int closingVote;

  AlertedUser({
    required this.user,
    required this.alertId,
    required this.distance,
    required this.isManager,
    required this.vote,
    required this.closingVote,
  });

  factory AlertedUser.fromJson(Map<String, dynamic> json) {
    try {
      final user = User.fromJson(json['user']);
      final alertId = json['alert_id'];
      final distance = json['distance'];
      final isManager = json['is_manager'];
      final vote = json['vote'];
      final closingVote = json['closing_vote'];
      return AlertedUser(
        user: user,
        alertId: alertId,
        distance: distance,
        isManager: isManager,
        vote: vote,
        closingVote: closingVote,
      );
    } catch (e) {
      debugPrintC("Error parsing AlertedUser from JSON: $e");
      throw FromJsonObjException();
    }
  }
}
