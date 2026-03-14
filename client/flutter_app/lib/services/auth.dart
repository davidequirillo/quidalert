// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:jose/jose.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:quidalert_flutter/config.dart' as config;
import 'package:quidalert_flutter/l10n/app_localizations.dart';

class ExpiredTokenException implements Exception {
  final String message;
  ExpiredTokenException([this.message = 'Token has expired']);
  @override
  String toString() => 'ExpiredTokenException: $message';
}

class InvalidTokenException implements Exception {
  final String message;
  InvalidTokenException([this.message = 'Token is not valid']);
  @override
  String toString() => 'InvalidTokenException: $message';
}

class ForbiddenRequestException implements Exception {
  final String message;
  ForbiddenRequestException([this.message = 'Forbidden request']);
  @override
  String toString() => 'ForbiddenRequestException: $message';
}

class GenericNotAuthorizedException implements Exception {
  final String message;
  GenericNotAuthorizedException([this.message = 'Not authorized']);
  @override
  String toString() => 'GenericNotAuthorizedException: $message';
}

class BadRequestException implements Exception {
  final String message;
  BadRequestException([this.message = 'Bad request']);
  @override
  String toString() => 'BadRequestException: $message';
}

class NetworkException implements Exception {
  final String message;
  NetworkException([this.message = 'Network error']);
  @override
  String toString() => 'NetworkException: $message';
}

class AuthClient extends ChangeNotifier {
  static String msgTokenExpired = 'Token expired';
  static String msgTokenNotValid = 'Token not valid';
  final String baseUrl = config.apiBaseUrl;
  final FlutterSecureStorage _secureStorage;
  String? refreshToken;
  String? accessToken;
  String? loginToken;
  String? gpsToken;
  bool initDone = false;
  Map<String, dynamic> userInfo = {};
  DateTime? lastFcmTokenRegistrationAt;

  AuthClient({FlutterSecureStorage? storage})
    : _secureStorage = storage ?? FlutterSecureStorage(),
      super() {
    refreshToken = null;
    accessToken = null;
    loginToken = null;
    gpsToken = null;
    lastFcmTokenRegistrationAt = null;
    _init();
  }

  Future<void> _init() async {
    if (kDebugMode) {
      debugPrint('AuthClient initialization started');
    }
    await loadRefreshToken(); // load local refresh token
    await loadGpsToken(); // load local GPS token
    try {
      await refreshTokens(); // get new auth tokens if needed
    } on InvalidTokenException catch (_) {
      if (kDebugMode) {
        debugPrint('AuthClient init, refresh token not valid');
      }
    } on ExpiredTokenException catch (_) {
      if (kDebugMode) {
        debugPrint('AuthClient init, refresh token expired');
      }
    } on BadRequestException catch (_) {
      if (kDebugMode) {
        debugPrint('AuthClient init, bad request during token refresh');
      }
    } catch (e) {
      if (kDebugMode) {
        debugPrint('AuthClient init, cannot refresh tokens: $e');
      }
    }
    await loadLoginToken();
    await checkLoginTokenValidity();
    lastFcmTokenRegistrationAt = null;
    initDone = true;
    if (kDebugMode) {
      debugPrint('AuthClient initialization completed');
    }
    notifyListeners();
  }

  Future<void> saveRefreshToken() async {
    await _secureStorage.write(key: 'refreshToken', value: refreshToken);
    if (kDebugMode) {
      debugPrint('Refresh token saved');
    }
  }

  Future<void> loadRefreshToken() async {
    final token = await _secureStorage.read(key: 'refreshToken');
    if (kDebugMode) {
      debugPrint('Refresh token loaded: $token');
    }
    refreshToken = token;
  }

  Future<void> deleteRefreshToken() async {
    await _secureStorage.delete(key: 'refreshToken');
    if (kDebugMode) {
      debugPrint('Refresh token deleted');
    }
  }

  Future<void> saveLoginToken() async {
    await _secureStorage.write(key: 'loginToken', value: loginToken);
    if (kDebugMode) {
      debugPrint('Login token saved');
    }
  }

  Future<void> loadLoginToken() async {
    final token = await _secureStorage.read(key: 'loginToken');
    if (kDebugMode) {
      debugPrint('Login token loaded: $token');
    }
    loginToken = token;
  }

  Future<void> deleteLoginToken() async {
    await _secureStorage.delete(key: 'loginToken');
    if (kDebugMode) {
      debugPrint('Login token deleted');
    }
  }

  Future<void> saveGpsToken() async {
    await _secureStorage.write(key: 'gpsToken', value: gpsToken);
    if (kDebugMode) {
      debugPrint('GPS token saved');
    }
  }

  Future<void> loadGpsToken() async {
    final token = await _secureStorage.read(key: 'gpsToken');
    if (kDebugMode) {
      debugPrint('GPS token loaded: $token');
    }
    gpsToken = token;
  }

  Future<void> deleteGpsToken() async {
    await _secureStorage.delete(key: 'gpsToken');
    if (kDebugMode) {
      debugPrint('GPS token deleted');
    }
  }

  Future<void> checkLoginTokenValidity() async {
    if (loginToken == null) {
      if (kDebugMode) {
        debugPrint('Check login token: is null');
      }
      return;
    }
    if (_isTokenExpired(loginToken!)) {
      if (kDebugMode) {
        debugPrint('Check login token: expired, deleting it');
      }
      await deleteLoginToken();
      loginToken = null;
    }
  }

  bool _isTokenExpired(String token) {
    final jwt = JsonWebToken.unverified(token);
    final exp = jwt.claims.getTyped('exp');
    if (exp == null) return true;
    final expiry = DateTime.fromMillisecondsSinceEpoch(exp * 1000, isUtc: true);
    return DateTime.now().toUtc().isAfter(expiry);
  }

  Future<void> refreshTokens() async {
    // Get new refresh, access, and GPS tokens (api/auth/refresh),
    // using current refresh token as api input
    if (refreshToken == null) {
      if (kDebugMode) {
        debugPrint('Try refresh tokens: refresh_token is null');
      }
      accessToken = null;
      gpsToken = null;
      return;
    }
    if (_isTokenExpired(refreshToken!)) {
      if (kDebugMode) {
        debugPrint('Try refresh tokens: local check, refresh_token expired)');
      }
      await setAuthTokens(null, null, null);
      throw ExpiredTokenException();
    }
    final uri = Uri.parse('$baseUrl/auth/refresh');
    try {
      final resp = await http.post(
        uri,
        headers: {"Content-Type": "application/json"},
        body: json.encode({'refresh_token': refreshToken}),
      );
      final jsonResp = jsonDecode(resp.body);
      final String respMessage = jsonResp['detail'] ?? '';
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        if (resp.statusCode == 401 && respMessage == msgTokenExpired) {
          await setAuthTokens(null, null, null);
          if (kDebugMode) {
            debugPrint('Try refresh tokens, refresh_token expired');
          }
          throw ExpiredTokenException();
        } else if (resp.statusCode == 401 && respMessage == msgTokenNotValid) {
          await setAuthTokens(null, null, null);
          if (kDebugMode) {
            debugPrint('Try refresh tokens, refresh_token not valid');
          }
          throw InvalidTokenException();
        } else if (resp.statusCode == 401) {
          await setAuthTokens(null, null, null);
          if (kDebugMode) {
            debugPrint('Try refresh tokens, refresh_token wrong or null');
          }
          throw InvalidTokenException();
        } else {
          if (kDebugMode) {
            debugPrint(
              "Try refresh tokens, cannot refresh tokens, HTTP ${resp.statusCode}: ${resp.body}",
            );
          }
          throw BadRequestException();
        }
      }
      if (kDebugMode) {
        debugPrint('Try refresh tokens, tokens refreshed successfully');
      }
      String? rToken = jsonResp['refresh_token'];
      String? aToken = jsonResp['access_token'];
      String? gToken = jsonResp['gps_token'];
      await setAuthTokens(rToken, aToken, gToken);
      if (kDebugMode) {
        debugPrint('The refresh token is: $refreshToken');
      }
    } catch (e) {
      if (kDebugMode) {
        debugPrint('Try refresh tokens, network error: $e');
      }
      throw NetworkException();
    }
  }

  Future<void> setAuthTokens(String? rtok, String? atok, String? gtok) async {
    // Set refresh token and access token (from login, or refresh api)
    // Set gps token too, useful for background periodic position update
    if ((rtok != null) && (atok != null) && (gtok != null)) {
      refreshToken = rtok;
      accessToken = atok;
      gpsToken = gtok;
      await saveRefreshToken();
      await saveGpsToken();
    } else {
      if (refreshToken != null) {
        await deleteRefreshToken();
      }
      if (gpsToken != null) {
        await deleteGpsToken();
      }
      accessToken = refreshToken = null;
      gpsToken = null;
    }
  }

  Future<void> setLoginToken(String? ltok) async {
    if (ltok != null) {
      loginToken = ltok;
      await saveLoginToken();
    } else {
      if (loginToken != null) {
        await deleteLoginToken();
      }
      loginToken = null;
    }
  }

  bool isLoggedIn() {
    return (refreshToken != null) &&
        (!_isTokenExpired(refreshToken!)) &&
        (accessToken != null);
  }

  Map<String, String> _authHeaders() =>
      (accessToken == null) ? {} : {'Authorization': 'Bearer $accessToken'};

  Future<http.Response> login(
    String email,
    String password, {
    String? code,
  }) async {
    const relPath = "/auth/login";
    final uri = Uri.parse('$baseUrl$relPath');
    final fields = {"email": email, "password": password};
    if (code != null) {
      fields['2fa_code'] = code;
    }
    if (loginToken != null) {
      fields['login_token'] = loginToken!;
    }
    final resp = await http.post(
      uri,
      body: json.encode(fields),
      headers: {"Content-Type": "application/json"},
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      if (kDebugMode) {
        debugPrint("Login, HTTP ${resp.statusCode}: ${resp.body}");
      }
      if ((resp.statusCode == 401) && resp.body.contains('2FA required')) {
        await setLoginToken(
          null,
        ); // clear old login token if present, because it's invalid
      }
      return resp;
    }
    final data = jsonDecode(resp.body);
    String? rtoken = data['refresh_token'];
    String? atoken = data['access_token'];
    String? gtoken = data['gps_token'];
    String? ltoken = data['login_token'];
    lastFcmTokenRegistrationAt = null;
    if (kDebugMode) {
      debugPrint('Login successful');
    }
    await setAuthTokens(rtoken, atoken, gtoken);
    if ((ltoken != null) && (ltoken != "")) {
      await setLoginToken(ltoken);
    } else {
      // Login api can legitimately not return a login token
      // It happens when our local login token was valid
      // So we do no operations in this scope.
    }
    return resp;
  }

  Future<http.Response> logout() async {
    const relPath = "/auth/revoke";
    final uri = Uri.parse('$baseUrl$relPath');
    final resp = await http.post(
      uri,
      body: json.encode({'refresh_token': refreshToken}),
      headers: {"Content-Type": "application/json"},
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      if (kDebugMode) {
        debugPrint("Logout error, HTTP ${resp.statusCode}: ${resp.body}");
      }
      return resp;
    }
    await setAuthTokens(null, null, null);
    lastFcmTokenRegistrationAt = null;
    setUserInfo({});
    return resp;
  }

  Future<http.Response> sendMultipartFileUploadRequest(
    String url, {
    Map<String, String> headers = const {},
    Map<String, String> fields = const {},
    required String file,
  }) async {
    final String fileContentType =
        headers['Content-Type'] ?? 'application/octet-stream';
    headers.remove("Content-Type");
    final uri = Uri.parse(url);
    var request = http.MultipartRequest('POST', uri);
    request.headers.addAll(headers);
    request.fields.addAll(
      fields.map((key, value) => MapEntry(key, value.toString())),
    );
    request.files.add(
      await http.MultipartFile.fromPath(
        'file',
        file,
        contentType: http.MediaType.parse(fileContentType),
      ),
    );
    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);
    return response;
  }

  Future<http.Response> sendRawFileUploadRequest(
    String url, {
    Map<String, String> headers = const {},
    required String file,
  }) async {
    final uri = Uri.parse(url);
    final fileBytes = await File(file).readAsBytes();
    headers.putIfAbsent('Content-Type', () => 'application/octet-stream');
    final resp = await http.post(uri, headers: headers, body: fileBytes);
    return resp;
  }

  Future<http.Response> sendJsonRequest(
    String method,
    String url, {
    Map<String, String> headers = const {},
    dynamic body = const {},
  }) async {
    final payload = jsonEncode(body);
    headers.putIfAbsent(
      'Content-Type',
      () => 'application/json; charset=utf-8',
    );
    final uri = Uri.parse(url);
    late http.Response resp;
    switch (method.toUpperCase()) {
      case 'GET':
        resp = await http.get(uri, headers: headers);
        break;
      case 'POST':
        resp = await http.post(uri, headers: headers, body: payload);
        break;
      case 'PUT':
        resp = await http.put(uri, headers: headers, body: payload);
        break;
      case 'DELETE':
        resp = await http.delete(uri, headers: headers, body: payload);
        break;
      default:
        throw ArgumentError('Unsupported HTTP method: $method');
    }
    return resp;
  }

  Future<http.Response> doProtectedApiRequest(
    String method,
    String relPath, {
    Map<String, String>? headers,
    dynamic body = const {},
    String? file,
  }) async {
    final m = method.toUpperCase();
    late http.Response resp;
    final merged = {..._authHeaders(), if (headers != null) ...headers};
    if (kDebugMode) {
      debugPrint('$m (auth), url: $baseUrl$relPath, headers: $merged');
    }
    final url = '$baseUrl$relPath';
    try {
      if (file != null) {
        if (body is Map<String, String>) {
          resp = await sendMultipartFileUploadRequest(
            url,
            headers: merged,
            fields: body,
            file: file,
          );
        } else {
          resp = await sendRawFileUploadRequest(
            url,
            headers: merged,
            file: file,
          );
        }
      } else {
        resp = await sendJsonRequest(method, url, headers: merged, body: body);
      }
      String respMessage = '';
      String respMessageKey = '';
      if (kDebugMode) {
        debugPrint('$m (auth), response headers: ${resp.headers}');
      }
      if (resp.headers.containsKey('Content-Type')) {
        respMessageKey = 'Content-Type';
      } else if (resp.headers.containsKey('content-type')) {
        respMessageKey = 'content-type';
      }
      if (respMessageKey.isNotEmpty &&
          resp.headers[respMessageKey]?.contains('application/json') == true) {
        final jsonResp = jsonDecode(resp.body);
        if (jsonResp is Map<String, dynamic>) {
          respMessage = jsonResp['detail'] ?? '';
        }
      }
      bool isNotAuthorized = (resp.statusCode == 401);
      final bool isExpired =
          (resp.statusCode == 401) && (respMessage == msgTokenExpired);
      bool isForbidden = (resp.statusCode == 403);
      if ((!isExpired) && (isNotAuthorized)) {
        throw InvalidTokenException('$m (auth), access token not valid');
      } else if (isForbidden) {
        throw ForbiddenRequestException('$m (auth), forbidden request');
      } else if ((!isExpired) &&
          (resp.statusCode < 200 || resp.statusCode >= 300)) {
        throw BadRequestException('$m (auth), bad request');
      }
      if (kDebugMode) {
        debugPrint('$m (auth), access token: $accessToken');
      }
      if (isExpired) {
        await refreshTokens();
        final newMerged = {..._authHeaders(), if (headers != null) ...headers};
        if (kDebugMode) {
          debugPrint('$m (retry auth), access token: $accessToken');
        }
        if (file != null) {
          if ((body is Map<String, String>)) {
            await sendMultipartFileUploadRequest(
              url,
              headers: newMerged,
              fields: body,
              file: file,
            );
          } else {
            resp = await sendRawFileUploadRequest(
              url,
              headers: newMerged,
              file: file,
            );
          }
        } else {
          resp = await sendJsonRequest(
            method,
            url,
            headers: newMerged,
            body: body,
          );
        }
        bool isNotAuthorized = (resp.statusCode == 401);
        bool isForbidden = (resp.statusCode == 403);
        if (isNotAuthorized) {
          throw InvalidTokenException(
            '$m (retry auth), access token not valid',
          );
        } else if (isForbidden) {
          throw ForbiddenRequestException('$m (retry auth), forbidden request');
        } else if (resp.statusCode < 200 || resp.statusCode >= 300) {
          throw BadRequestException('$m (retry auth), bad request');
        }
      }
      if (kDebugMode) {
        debugPrint("$m (response), HTTP ${resp.statusCode}");
      }
      return resp;
    } on ExpiredTokenException catch (_) {
      throw GenericNotAuthorizedException();
    } on InvalidTokenException catch (_) {
      throw GenericNotAuthorizedException();
    } on ForbiddenRequestException catch (_) {
      rethrow;
    } on BadRequestException catch (_) {
      if (kDebugMode) {
        debugPrint("$m (auth), bad request exception");
      }
      rethrow;
    } on NetworkException catch (_) {
      rethrow;
    } catch (e) {
      if (kDebugMode) {
        debugPrint('$m (auth), unexpected error: $e');
      }
      throw Exception("$m (auth), unexpected error: $e");
    }
  }

  void setUserInfo(Map<String, dynamic> info) {
    userInfo = info;
  }

  bool isAdmin() {
    return userInfo['is_admin'] == true;
  }

  bool isOfficer() {
    return userInfo['is_officer'] == true;
  }

  bool isChief() {
    return userInfo['is_chief'] == true;
  }

  // This method is called by the home page (profile page),
  // to send fcm token to backend when user logs in successfully,
  // to register the device for push notifications.
  Future<void> registerFcmTokenForPushNotifications(
    String? fcmToken, {
    required BuildContext context,
    required AppLocalizations localizations,
  }) async {
    bool isError = false;
    bool alreadyRegistered = false;
    if (kDebugMode) {
      debugPrint(
        'Registering device for push notifications with token: $fcmToken',
      );
    }
    try {
      if ((fcmToken == null) || (fcmToken.isEmpty)) {
        if (kDebugMode) {
          debugPrint(
            'FCM token is null or empty, cannot register for push notifications',
          );
        }
        throw BadRequestException('FCM token is empty');
      }
      if (lastFcmTokenRegistrationAt != null &&
          DateTime.now().difference(lastFcmTokenRegistrationAt!) <
              const Duration(hours: 24)) {
        if (kDebugMode) {
          debugPrint(
            'FCM token was registered recently, skipping registration',
          );
        }
        alreadyRegistered = true;
        return;
      }
      await doProtectedApiRequest(
        "post",
        '/auth/register-device',
        body: {'fcm_token': fcmToken},
      );
      lastFcmTokenRegistrationAt = DateTime.now();
      if (kDebugMode) {
        debugPrint('Ok, device registered for push notifications');
      }
    } on GenericNotAuthorizedException catch (_) {
      if (kDebugMode) {
        debugPrint('Not authorized');
      }
      isError = true;
    } on ForbiddenRequestException catch (_) {
      if (kDebugMode) {
        debugPrint('Forbidden request');
      }
      isError = true;
    } on BadRequestException catch (_) {
      if (kDebugMode) {
        debugPrint('Bad request');
      }
      isError = true;
    } on NetworkException catch (_) {
      if (kDebugMode) {
        debugPrint('Network error');
      }
      isError = true;
    } catch (e) {
      if (kDebugMode) {
        debugPrint('Unexpected error: $e');
      }
      isError = true;
    } finally {
      final successColor = Colors.green;
      final errorColor = Colors.red;
      final successMessage =
          localizations.successDeviceRegisteredForPushNotifications;
      final errorMessage =
          localizations.errorRegisteringDeviceForPushNotifications;
      if (!alreadyRegistered && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(isError ? errorMessage : successMessage),
            backgroundColor: isError ? errorColor : successColor,
            duration: const Duration(seconds: 4),
          ),
        );
      }
    }
  }

  // This method is automatically called by NotificationProvider listener, when FCM token is refreshed, to keep our backend updated with the latest token.
  Future<void> syncFcmTokenWithBackend(String? fcmToken) async {
    try {
      await doProtectedApiRequest(
        "post",
        '/auth/register-device',
        body: {'fcm_token': fcmToken},
      );
      lastFcmTokenRegistrationAt = DateTime.now();
      if (kDebugMode) {
        debugPrint('FCM token synced with backend successfully');
      }
    } catch (e) {
      if (kDebugMode) {
        debugPrint('Error syncing FCM token with backend: $e');
      }
    }
  }
}
