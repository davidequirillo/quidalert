// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
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

class AuthClient extends ChangeNotifier {
  final String baseUrl = config.apiBaseUrl;
  final FlutterSecureStorage _secureStorage;
  String? refreshToken;
  String? accessToken;
  bool initDone = false;

  AuthClient({FlutterSecureStorage? storage})
    : _secureStorage = storage ?? FlutterSecureStorage(),
      super() {
    refreshToken = null;
    accessToken = null;
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
      refreshToken = null;
      accessToken = null;
    } on ExpiredTokenException catch (_) {
      if (kDebugMode) {
        debugPrint('AuthClient init, refresh token expired');
      }
      refreshToken = null;
      accessToken = null;
    } catch (e) {
      if (kDebugMode) {
        debugPrint('AuthClient init, cannot refresh tokens: $e');
      }
    }
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
      debugPrint('Refresh token loaded: $refreshToken');
    }
    refreshToken = token;
  }

  Future<void> deleteRefreshToken() async {
    await _secureStorage.delete(key: 'refreshToken');
    if (kDebugMode) {
      debugPrint('Refresh token deleted');
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
      await deleteRefreshToken();
      refreshToken = null;
      accessToken = null;
      throw ExpiredTokenException();
    }
    final uri = Uri.parse('$baseUrl/auth/refresh');
    try {
      final resp = await http.post(
        uri,
        headers: {"Content-Type": "application/json"},
        body: json.encode({'refresh_token': refreshToken}),
      );
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        await deleteRefreshToken();
        refreshToken = null;
        accessToken = null;
        if (_isTokenNotValidResponse(resp)) {
          if (kDebugMode) {
            debugPrint('Try refresh tokens, refresh_token not valid');
          }
          throw InvalidTokenException();
        } else if (_isTokenExpiredResponse(resp)) {
          if (kDebugMode) {
            debugPrint('Try refresh tokens, refresh_token expired');
          }
          throw ExpiredTokenException();
        } else {
          if (kDebugMode) {
            debugPrint(
              "Try refresh tokens, cannot refresh tokens, HTTP ${resp.statusCode}: ${resp.body}",
            );
          }
          throw Exception('Cannot refresh tokens');
        }
      }
      final response = jsonDecode(resp.body);
      if (kDebugMode) {
        debugPrint('Try refresh tokens, tokens refreshed successfully');
      }
      String? rToken = response['refresh_token'];
      String? aToken = response['access_token'];
      setTokens(rToken, aToken);
    } catch (e) {
      if (kDebugMode) {
        debugPrint('Try refresh tokens, network error: $e');
      }
      throw Exception('Network error during token refresh');
    }
  }

  void setTokens(String? rtok, String? atok) {
    // Set refresh token and access token (from login, or refresh api)
    refreshToken = rtok;
    accessToken = atok;
    if (refreshToken != null) {
      saveRefreshToken();
    } else {
      deleteRefreshToken();
    }
  }

  bool isLoggedIn() {
    return (refreshToken != null) &&
        (!_isTokenExpired(refreshToken!)) &&
        (accessToken != null);
  }

  Future<http.Response> get(
    String relPath,
    Map<String, String>? headers,
  ) async {
    final merged = {..._authHeaders(), if (headers != null) ...headers};
    final uri = Uri.parse('$baseUrl$relPath');
    final resp = await http.get(uri, headers: merged);
    if (kDebugMode) {
      debugPrint('GET (auth), access token used: $accessToken');
    }
    if (_isTokenExpiredResponse(resp)) {
      await refreshTokens();
      final newMerged = {..._authHeaders(), if (headers != null) ...headers};
      if (kDebugMode) {
        debugPrint('GET (auth), access token used: $accessToken');
      }
      final retryResp = await http.get(uri, headers: newMerged);
      if (kDebugMode) {
        debugPrint("GET (auth), ${jsonDecode(retryResp.body)}");
      }
      return retryResp;
    }
    if (kDebugMode) {
      debugPrint("GET (auth), ${jsonDecode(resp.body)}");
    }
    return resp;
  }

  Future<http.Response> delete(
    String relPath,
    Map<String, String>? headers,
  ) async {
    final merged = {..._authHeaders(), if (headers != null) ...headers};
    final uri = Uri.parse('$baseUrl$relPath');
    final resp = await http.delete(uri, headers: merged);
    if (_isTokenExpiredResponse(resp)) {
      await refreshTokens();
      final newMerged = {..._authHeaders(), if (headers != null) ...headers};
      final retryResp = await http.get(uri, headers: newMerged);
      return retryResp;
    }
    return resp;
  }

  Future<http.Response> put(
    BuildContext context,
    String relPath, {
    Map<String, String>? headers,
    Object? body,
  }) async {
    final merged = {..._authHeaders(), if (headers != null) ...headers};
    final uri = Uri.parse('$baseUrl$relPath');
    final resp = await http.put(uri, headers: merged, body: body);
    if (_isTokenExpiredResponse(resp)) {
      await refreshTokens();
      final newMerged = {..._authHeaders(), if (headers != null) ...headers};
      final retryResp = await http.put(uri, headers: newMerged, body: body);
      return retryResp;
    }
    return resp;
  }

  Future<http.Response> post(
    String relPath, {
    Map<String, String>? headers,
    Object? body,
  }) async {
    final merged = {..._authHeaders(), if (headers != null) ...headers};
    final uri = Uri.parse('$baseUrl$relPath');
    final resp = await http.post(uri, headers: merged, body: body);
    if (_isTokenExpiredResponse(resp)) {
      await refreshTokens();
      final newMerged = {..._authHeaders(), if (headers != null) ...headers};
      final retryResp = await http.post(uri, headers: newMerged, body: body);
      return retryResp;
    }
    return resp;
  }

  Map<String, String> _authHeaders() =>
      (accessToken == null) ? {} : {'Authorization': 'Bearer $accessToken'};

  bool _isTokenExpiredResponse(http.Response resp) {
    if (resp.statusCode != 401) return false;
    try {
      final data = jsonDecode(resp.body);
      return (data['detail'] == 'Token expired');
    } catch (_) {
      return false;
    }
  }

  bool _isTokenNotValidResponse(http.Response resp) {
    if (resp.statusCode != 401) return false;
    try {
      final data = jsonDecode(resp.body);
      return (data['detail'] == 'Token not valid');
    } catch (_) {
      return false;
    }
  }

  Future<http.Response> login(String email, String password) async {
    const relPath = "/auth/login";
    final uri = Uri.parse('$baseUrl$relPath');
    final resp = await http.post(
      uri,
      body: json.encode({'email': email, 'password': password}),
      headers: {"Content-Type": "application/json"},
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      if (kDebugMode) {
        debugPrint("Login, HTTP ${resp.statusCode}: ${resp.body}");
      }
      return resp;
    }
    final data = jsonDecode(resp.body);
    String? rtoken = data['refresh_token'];
    String? atoken = data['access_token'];
    if (kDebugMode) {
      debugPrint('Login successful');
    }
    setTokens(rtoken, atoken);
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
        debugPrint("Logout, HTTP ${resp.statusCode}: ${resp.body}");
      }
      return resp;
    }
    setTokens(null, null);
    return resp;
  }
}
