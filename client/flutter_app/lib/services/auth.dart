// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:jose/jose.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:quidalert_flutter/config.dart' as config;
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/utils/strings.dart';

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

class ServerException implements Exception {
  final String message;
  ServerException([this.message = 'Server error']);
  @override
  String toString() => 'ServerException: $message';
}

class NotFoundException implements Exception {
  final String message;
  NotFoundException([this.message = 'Not found']);
  @override
  String toString() => 'NotFoundException: $message';
}

class UnknownException implements Exception {
  final String message;
  UnknownException([this.message = 'Unknown error']);
  @override
  String toString() => 'UnknownException: $message';
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
  String? lastFcmTokenSent;

  AuthClient({FlutterSecureStorage? storage})
    : _secureStorage = storage ?? FlutterSecureStorage(),
      super() {
    refreshToken = null;
    accessToken = null;
    loginToken = null;
    gpsToken = null;
    lastFcmTokenSent = null;
    _init();
  }

  Future<void> _init() async {
    debugPrintC('AuthClient initialization started');
    await loadRefreshToken(); // load local refresh token
    await loadGpsToken(); // load local GPS token
    try {
      await refreshTokens(); // get new auth tokens if needed
    } on InvalidTokenException catch (_) {
      debugPrintC('AuthClient init, refresh token not valid');
    } on ExpiredTokenException catch (_) {
      debugPrintC('AuthClient init, refresh token expired');
    } on BadRequestException catch (_) {
      debugPrintC('AuthClient init, bad request during token refresh');
    } on ServerException catch (_) {
      debugPrintC('AuthClient init, server error during token refresh');
    } on GenericNotAuthorizedException catch (_) {
      debugPrintC('AuthClient init, not authorized during token refresh');
    } catch (e) {
      debugPrintC('AuthClient init, cannot refresh tokens: $e');
    }
    await loadLoginToken();
    await checkLoginTokenValidity();
    initDone = true;
    debugPrintC('AuthClient initialization completed');
    notifyListeners();
  }

  Future<void> saveRefreshToken() async {
    await _secureStorage.write(key: 'refreshToken', value: refreshToken);
    debugPrintC('Refresh token saved');
  }

  Future<void> loadRefreshToken() async {
    final token = await _secureStorage.read(key: 'refreshToken');
    debugPrintC('Refresh token loaded: $token');
    refreshToken = token;
  }

  Future<void> deleteRefreshToken() async {
    await _secureStorage.delete(key: 'refreshToken');
    debugPrintC('Refresh token deleted');
  }

  Future<void> saveLoginToken() async {
    await _secureStorage.write(key: 'loginToken', value: loginToken);
    debugPrintC('Login token saved');
  }

  Future<void> loadLoginToken() async {
    final token = await _secureStorage.read(key: 'loginToken');
    debugPrintC('Login token loaded: $token');
    loginToken = token;
  }

  Future<void> deleteLoginToken() async {
    await _secureStorage.delete(key: 'loginToken');
    debugPrintC('Login token deleted');
  }

  Future<void> saveGpsToken() async {
    await _secureStorage.write(key: 'gpsToken', value: gpsToken);
    debugPrintC('GPS token saved');
  }

  Future<void> loadGpsToken() async {
    final token = await _secureStorage.read(key: 'gpsToken');
    debugPrintC('GPS token loaded: $token');
    gpsToken = token;
  }

  Future<void> deleteGpsToken() async {
    await _secureStorage.delete(key: 'gpsToken');
    debugPrintC('GPS token deleted');
  }

  Future<void> checkLoginTokenValidity() async {
    if (loginToken == null) {
      debugPrintC('Check login token: is null');
      return;
    }
    if (_isTokenExpired(loginToken!)) {
      debugPrintC('Check login token: expired, deleting it');
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
      debugPrintC('Try refresh tokens: refresh_token is null');
      accessToken = null;
      gpsToken = null;
      return;
    }
    final uri = Uri.parse('$baseUrl/auth/refresh');
    final resp = await http.post(
      uri,
      headers: {"Content-Type": "application/json"},
      body: json.encode({'refresh_token': refreshToken}),
    );
    final jsonResp = jsonDecode(resp.body);
    final String respMessage = jsonResp['detail'] ?? '';
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      if (resp.statusCode == 401 && respMessage == msgTokenExpired) {
        debugPrintC('Try refresh tokens, refresh_token expired');
        await setAuthTokens(null, null, null);
        throw ExpiredTokenException();
      } else if (resp.statusCode == 401 && respMessage == msgTokenNotValid) {
        debugPrintC('Try refresh tokens, refresh_token not valid');
        await setAuthTokens(null, null, null);
        throw InvalidTokenException();
      } else if (resp.statusCode == 401) {
        debugPrintC('Try refresh tokens, refresh_token wrong or null');
        await setAuthTokens(null, null, null);
        throw InvalidTokenException();
      } else {
        debugPrintC(
          "Try refresh tokens, cannot refresh tokens, HTTP ${resp.statusCode}: ${resp.body}",
        );
        if (resp.statusCode >= 500) {
          throw ServerException();
        }
        if (resp.statusCode >= 300) {
          throw BadRequestException();
        }
        throw BadRequestException();
      }
    }
    debugPrintC('Try refresh tokens, tokens refreshed successfully');
    String? rToken = jsonResp['refresh_token'];
    String? aToken = jsonResp['access_token'];
    String? gToken = jsonResp['gps_token'];
    debugPrintC('The refresh token is: $refreshToken');
    await setAuthTokens(rToken, aToken, gToken);
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
    return (refreshToken != null) && (accessToken != null);
  }

  Map<String, String> _authHeaders() =>
      (accessToken == null) ? {} : {'Authorization': 'Bearer $accessToken'};

  Future<http.Response> login(
    String email,
    String password, {
    String? loginCode,
    String? language,
  }) async {
    const relPath = "/auth/login";
    final uri = Uri.parse('$baseUrl$relPath');
    final fields = {"email": email, "password": password};
    if (loginCode != null) {
      fields['login_code'] = loginCode;
    }
    if (loginToken != null) {
      fields['login_token'] = loginToken!;
    }
    if (language != null) {
      fields['language'] = language;
    }
    final resp = await http.post(
      uri,
      body: json.encode(fields),
      headers: {"Content-Type": "application/json"},
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      debugPrintC("Login, HTTP ${resp.statusCode}: ${resp.body}");
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
    lastFcmTokenSent = null;
    debugPrintC('Login successful');
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
      debugPrintC("Logout error, HTTP ${resp.statusCode}: ${resp.body}");
      return resp;
    }
    await setAuthTokens(null, null, null);
    lastFcmTokenSent = null;
    setUserInfo({});
    debugPrintC('Logout successful');
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
    bool retrying = false,
  }) async {
    final m = method.toUpperCase();
    late http.Response resp;
    final merged = {..._authHeaders(), if (headers != null) ...headers};
    debugPrintC('$m (auth), url: $baseUrl$relPath, headers: $merged');
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
      String respContentTypeKey = '';
      String respMessage = '';
      debugPrintC('$m (auth), response headers: ${resp.headers}');
      if (resp.headers.containsKey('Content-Type')) {
        respContentTypeKey = 'Content-Type';
      } else if (resp.headers.containsKey('content-type')) {
        respContentTypeKey = 'content-type';
      } else {
        debugPrintC('$m (auth), response does not contain Content-Type header');
      }
      if (respContentTypeKey.isNotEmpty) {
        if (resp.headers[respContentTypeKey]!.contains('application/json')) {
          final jsonResp = jsonDecode(resp.body);
          if (jsonResp is Map<String, dynamic>) {
            debugPrintC(
              '$m (auth), response is a JSON map, keys: ${jsonResp.keys}',
            );
            final respDetail = jsonResp['detail'] ?? '';
            if (respDetail is String) {
              respMessage = respDetail;
              debugPrintC(
                '$m (auth), key "detail" value is a string: $respDetail',
              );
            } else if (respDetail is List) {
              debugPrintC(
                '$m (auth), key "detail" value is a list: $respDetail',
              );
            } else {
              debugPrintC(
                '$m (auth), key "detail" value is unknown type: $respDetail',
              );
            }
          } else {
            debugPrintC('$m (auth), response JSON is not a map');
          }
        }
      }
      bool isNotAuthorized = (resp.statusCode == 401);
      final bool isExpired =
          (resp.statusCode == 401) && (respMessage == msgTokenExpired);
      bool isForbidden = (resp.statusCode == 403);
      bool isNotFound = (resp.statusCode == 404);
      if ((!isExpired) && (isNotAuthorized)) {
        throw InvalidTokenException('Access token not valid');
      } else if (isForbidden) {
        final forbiddenRequestMsg = respMessage.isNotEmpty
            ? respMessage
            : 'Forbidden request';
        throw ForbiddenRequestException(forbiddenRequestMsg);
      } else if (isNotFound) {
        throw NotFoundException('Not found');
      } else if (!isExpired &&
          (resp.statusCode < 200 ||
              ((resp.statusCode >= 300) && (resp.statusCode < 500)))) {
        final badRequestMsg = respMessage.isNotEmpty
            ? respMessage
            : 'Bad request';
        throw BadRequestException(badRequestMsg);
      } else if (!isExpired && (resp.statusCode >= 500)) {
        throw ServerException('Server error');
      }
      debugPrintC('$m (auth), access token: $accessToken');
      if (isExpired) {
        if (retrying) {
          debugPrintC('$m (auth), token expired even after refresh, giving up');
          throw ExpiredTokenException(
            'Access token expired even after refresh',
          );
        } else {
          debugPrintC(
            '$m (retry auth), access token expired, refreshing tokens',
          );
          await refreshTokens();
          debugPrintC('$m (retry auth), access token: $accessToken');
          debugPrintC('$m (retry auth), retrying original request');
          return await doProtectedApiRequest(
            method,
            relPath,
            headers: headers,
            body: body,
            file: file,
            retrying: true,
          );
        }
      }
      debugPrintC("$m (response), HTTP ${resp.statusCode}");
      return resp;
    } on ExpiredTokenException catch (_) {
      throw GenericNotAuthorizedException();
    } on InvalidTokenException catch (e) {
      debugPrintC("$m (auth), invalid token exception caught: ${e.toString()}");
      throw GenericNotAuthorizedException();
    } on ForbiddenRequestException catch (_) {
      rethrow;
    } on NotFoundException catch (_) {
      rethrow;
    } on BadRequestException catch (e) {
      debugPrintC("$m (auth), bad request exception caught: ${e.toString()}");
      rethrow;
    } on ServerException catch (e) {
      debugPrintC("$m (auth), server exception caught: ${e.toString()}");
      rethrow;
    } on GenericNotAuthorizedException catch (_) {
      rethrow;
    } catch (e) {
      debugPrintC('$m (auth), unexpected error: ${e.toString()}');
      throw UnknownException(e.toString());
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
  Future<void> syncFcmTokenWithBackendinForeground(
    String fcmToken, {
    required BuildContext context,
    required AppLocalizations localizations,
  }) async {
    bool isError = false;
    bool alreadyRegistered = false;
    debugPrintC(
      'Registering device for push notifications with token: $fcmToken',
    );
    try {
      if ((lastFcmTokenSent != null) && (lastFcmTokenSent == fcmToken)) {
        debugPrintC('FCM token was registered recently, skipping registration');
        alreadyRegistered = true;
        return;
      }
      await doProtectedApiRequest(
        "post",
        '/register-device',
        body: {'fcm_token': fcmToken},
      );
      lastFcmTokenSent = fcmToken;
      debugPrintC('Ok, device registered for push notifications');
    } on GenericNotAuthorizedException catch (_) {
      debugPrintC('Not authorized');
      isError = true;
    } on ForbiddenRequestException catch (_) {
      debugPrintC('Forbidden request');
      isError = true;
    } on BadRequestException catch (_) {
      debugPrintC('Bad request');
      isError = true;
    } on ServerException catch (_) {
      debugPrintC('Server error');
      isError = true;
    } catch (e) {
      debugPrintC('Unexpected error: $e');
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

  // This method is called at startup (in NotificationProvider init function),
  // and also when the FCM token is refreshed locally (in NotificationProvider listener),
  // to keep our backend updated with the latest local fcm token,
  // so it can send push notifications to the client device.
  Future<void> syncFcmTokenWithBackendinBackground(String fcmToken) async {
    try {
      if ((lastFcmTokenSent != null) && (lastFcmTokenSent == fcmToken)) {
        debugPrintC('FCM token was registered recently, skipping registration');
        return;
      }
      await doProtectedApiRequest(
        "post",
        '/register-device',
        body: {'fcm_token': fcmToken},
      );
      lastFcmTokenSent = fcmToken;
      debugPrintC('FCM token synced with backend successfully');
      return;
    } on ServerException catch (_) {
      debugPrintC('Server error');
    } on BadRequestException catch (_) {
      debugPrintC('Bad request');
    } on ForbiddenRequestException catch (_) {
      debugPrintC('Forbidden request');
    } on GenericNotAuthorizedException catch (_) {
      debugPrintC('Not authorized');
    } on NotFoundException catch (_) {
      debugPrintC('Not found');
    } catch (e) {
      debugPrintC('Unexpected error: $e');
    }
  }
}
