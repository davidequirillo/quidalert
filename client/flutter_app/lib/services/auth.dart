// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:jose/jose.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:quidalert_flutter/config.dart' as config;

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

class PermissionDeniedException implements Exception {
  final String message;
  PermissionDeniedException([this.message = 'Permission denied']);
  @override
  String toString() => 'PermissionDeniedException: $message';
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
  bool initDone = false;

  AuthClient({FlutterSecureStorage? storage})
    : _secureStorage = storage ?? FlutterSecureStorage(),
      super() {
    refreshToken = null;
    accessToken = null;
    loginToken = null;
    _init();
  }

  Future<void> _init() async {
    await loadRefreshToken(); // load local refresh token
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
    initDone = true;
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

  Future<void> deleteLoginToken() async {
    await _secureStorage.delete(key: 'loginToken');
    if (kDebugMode) {
      debugPrint('Login token deleted');
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
    // Get new refresh and access tokens (api/auth/refresh),
    // using current refresh token as api input
    if (refreshToken == null) {
      if (kDebugMode) {
        debugPrint('Try refresh tokens, refresh_token is null');
      }
      accessToken = null;
      return;
    }
    if (_isTokenExpired(refreshToken!)) {
      if (kDebugMode) {
        debugPrint('Try refresh tokens, local check, refresh_token expired)');
      }
      setAuthTokens(null, null);
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
          setAuthTokens(null, null);
          if (kDebugMode) {
            debugPrint('Try refresh tokens, refresh_token expired');
          }
          throw ExpiredTokenException();
        } else if (resp.statusCode == 401 && respMessage == msgTokenNotValid) {
          setAuthTokens(null, null);
          if (kDebugMode) {
            debugPrint('Try refresh tokens, refresh_token not valid');
          }
          throw InvalidTokenException();
        } else if (resp.statusCode == 401) {
          setAuthTokens(null, null);
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
          throw BadRequestException;
        }
      }
      if (kDebugMode) {
        debugPrint('Try refresh tokens, tokens refreshed successfully');
      }
      String? rToken = jsonResp['refresh_token'];
      String? aToken = jsonResp['access_token'];
      setAuthTokens(rToken, aToken);
      if (kDebugMode) {
        debugPrint('The refresh token is: $refreshToken');
      }
    } catch (e) {
      if (kDebugMode) {
        debugPrint('Try refresh tokens, network error: $e');
      }
      throw NetworkException;
    }
  }

  void setAuthTokens(String? rtok, String? atok) {
    // Set refresh token and access token (from login, or refresh api)
    if (rtok != null) {
      refreshToken = rtok;
      accessToken = atok;
      saveRefreshToken();
    } else {
      if (refreshToken != null) {
        deleteRefreshToken();
      }
      accessToken = refreshToken = null;
    }
  }

  void setLoginToken(String? ltok) {
    if (ltok != null) {
      loginToken = ltok;
      saveLoginToken();
    } else {
      if (loginToken != null) {
        deleteLoginToken();
      }
      loginToken = null;
    }
  }

  bool isLoggedIn() {
    return (refreshToken != null) &&
        (!_isTokenExpired(refreshToken!)) &&
        (accessToken != null);
  }

  Future<http.Response> sendRawFileUploadRequest(
    String url,
    File file, {
    Map<String, String> headers = const {},
  }) async {
    final uri = Uri.parse(url);
    final fileBytes = await file.readAsBytes();
    headers.putIfAbsent('content-type', () => 'application/octet-stream');
    final resp = await http.post(uri, headers: headers, body: fileBytes);
    return resp;
  }

  Future<http.Response> sendJsonRequest(
    String method,
    String url, {
    Map<String, String> headers = const {},
    Map<String, dynamic> body = const {},
  }) async {
    final payload = jsonEncode(body);
    headers.putIfAbsent(
      'content-type',
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
        resp = await http.delete(uri, headers: headers);
        break;
      default:
        throw ArgumentError('Unsupported HTTP method: $method');
    }
    return resp;
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
    final fields = {
      "email": email,
      "password": password,
      if (code != null) "login_code": code,
      if (loginToken != null) "login_token": loginToken,
    };
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
        setLoginToken(
          null,
        ); // clear old login token if present, because it's invalid
      }
      return resp;
    }
    final data = jsonDecode(resp.body);
    String? rtoken = data['refresh_token'];
    String? atoken = data['access_token'];
    String? ltoken = data['login_token'];
    if (kDebugMode) {
      debugPrint('Login successful');
    }
    setAuthTokens(rtoken, atoken);
    if ((ltoken != null) && (ltoken != "")) {
      setLoginToken(ltoken);
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
    setAuthTokens(null, null);
    setLoginToken(null);
    return resp;
  }

  Future<http.Response> doProtectedApiRequest(
    String method,
    String relPath, {
    Map<String, String>? headers,
    Map<String, dynamic>? body,
    File? file,
  }) async {
    final m = method.toUpperCase();
    late http.Response resp;
    final merged = {..._authHeaders(), if (headers != null) ...headers};
    final b = body ?? {};
    final url = '$baseUrl$relPath';
    try {
      if (file != null) {
        resp = await sendRawFileUploadRequest(url, file, headers: merged);
      } else {
        resp = await sendJsonRequest(method, url, headers: merged, body: b);
      }
      final jsonResp = jsonDecode(resp.body);
      final String respMessage = jsonResp['detail'] ?? '';
      bool isNotAuthorized = (resp.statusCode == 401);
      final bool isExpired =
          (resp.statusCode == 401) && (respMessage == msgTokenExpired);
      bool isForbidden = (resp.statusCode == 403);
      if ((!isExpired) && (isNotAuthorized)) {
        throw InvalidTokenException('$m (auth), access token not valid');
      } else if (isForbidden) {
        throw PermissionDeniedException('$m (auth), permission denied');
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
          resp = await sendRawFileUploadRequest(url, file, headers: newMerged);
        } else {
          resp = await sendJsonRequest(
            method,
            url,
            headers: newMerged,
            body: b,
          );
        }
        bool isNotAuthorized = (resp.statusCode == 401);
        bool isForbidden = (resp.statusCode == 403);
        if (isNotAuthorized) {
          throw InvalidTokenException(
            '$m (retry auth), access token not valid',
          );
        } else if (isForbidden) {
          throw PermissionDeniedException('$m (retry auth), permission denied');
        } else if (resp.statusCode < 200 || resp.statusCode >= 300) {
          throw BadRequestException('$m (retry auth), bad request');
        }
      }
      if (kDebugMode) {
        debugPrint("$m (response), ${jsonDecode(resp.body)}");
      }
      return resp;
    } on ExpiredTokenException catch (_) {
      throw GenericNotAuthorizedException();
    } on InvalidTokenException catch (_) {
      throw GenericNotAuthorizedException();
    } on PermissionDeniedException catch (_) {
      throw GenericNotAuthorizedException();
    } on BadRequestException catch (_) {
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
}
