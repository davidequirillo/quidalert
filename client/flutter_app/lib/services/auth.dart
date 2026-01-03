// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:jose/jose.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:quidalert_flutter/config.dart' as config;

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
    await getRefreshToken(); // get new refresh token
    await getAccessToken(); // get access token
    initDone = true;
    notifyListeners();
  }

  Future<void> saveRefreshToken() async {
    if (refreshToken != null) {
      await _secureStorage.write(key: 'refreshToken', value: refreshToken);
      if (kDebugMode) {
        debugPrint('Refresh token saved');
      }
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

  Future<void> getRefreshToken() async {
    // Get a new refresh token (api/auth/refresh), using current refresh token as input
    if (refreshToken == null) return;
    if (_isTokenExpired(refreshToken!)) {
      if (kDebugMode) {
        debugPrint('Refresh token expired');
      }
      await deleteRefreshToken();
      refreshToken = null;
      return;
    }
    refreshToken = null; // from api result
    if (refreshToken != null) {
      await _secureStorage.write(key: 'refreshToken', value: refreshToken);
      if (kDebugMode) {
        debugPrint('Refresh token refreshed');
      }
    }
  }

  Future<void> setTokens(String rtok, String atok) async {
    // Set refresh token and access token (from login success)
    refreshToken = rtok;
    accessToken = atok;
    saveRefreshToken();
  }

  Future<void> getAccessToken() async {
    // Get a new access token (api/auth/access), using refresh token as input
    if ((refreshToken == null) || (_isTokenExpired(refreshToken!))) {
      if (refreshToken != null) {
        if (kDebugMode) {
          debugPrint('Error: cannot get access token (refresh token expired)');
        }
        await deleteRefreshToken();
        refreshToken = null;
      }
      accessToken = null;
    }
    final aToken = null; // from api result
    accessToken = aToken;
    if (kDebugMode) {
      debugPrint('Access token refreshed');
    }
  }

  bool isLoggedIn() {
    return (refreshToken != null) && (!_isTokenExpired(refreshToken!));
  }

  Future<http.Response> get(String relPath) async {
    final uri = Uri.parse('$baseUrl$relPath');
    final resp = await http.get(uri, headers: _authHeaders());
    if (_isAccessTokenExpiredResponse(resp)) {
      await getAccessToken();
      if (accessToken == null) {
        throw Exception('Error: cannot refresh access token');
      }
      final retryResp = await http.get(uri, headers: _authHeaders());
      return retryResp;
    }
    return resp;
  }

  Future<http.Response> delete(String relPath) async {
    final uri = Uri.parse('$baseUrl$relPath');
    final resp = await http.delete(uri, headers: _authHeaders());
    if (_isAccessTokenExpiredResponse(resp)) {
      await getAccessToken();
      if (accessToken == null) {
        throw Exception('Error: cannot refresh access token');
      }
      final retryResp = await http.delete(uri, headers: _authHeaders());
      return retryResp;
    }
    return resp;
  }

  Future<http.Response> put(
    String relPath, {
    Map<String, String>? headers,
    Object? body,
  }) async {
    final merged = {..._authHeaders(), if (headers != null) ...headers};
    final uri = Uri.parse('$baseUrl$relPath');
    final resp = await http.put(uri, headers: merged, body: body);
    if (_isAccessTokenExpiredResponse(resp)) {
      await getAccessToken();
      if (accessToken == null) {
        throw Exception('Error: cannot refresh access token');
      }
      final retryResp = await http.put(uri, headers: merged, body: body);
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
    if (_isAccessTokenExpiredResponse(resp)) {
      await getAccessToken();
      if (accessToken == null) {
        throw Exception('Error: cannot refresh access token');
      }
      final retryResp = await http.post(uri, headers: merged, body: body);
      return retryResp;
    }
    return resp;
  }

  Map<String, String> _authHeaders() =>
      accessToken == null ? {} : {'Authorization': 'Bearer $accessToken'};

  bool _isAccessTokenExpiredResponse(http.Response resp) {
    if (resp.statusCode != 401) return false;
    try {
      final data = jsonDecode(resp.body);
      return data['error'] == 'access_token_expired';
    } catch (_) {
      return false;
    }
  }

  Future<http.Response> login() async {
    const relPath = "/api/login";
    final uri = Uri.parse('$baseUrl$relPath');
    final resp = await http.get(uri);
    if (resp.body == "") {
      String? rtoken = null;
      String? atoken = null;
      if ((rtoken != null) && (atoken != null)) {
        refreshToken = rtoken; // we set auth tokens
        accessToken = atoken;
        saveRefreshToken();
      }
    }
    return resp;
  }

  Future<http.Response> logout() async {
    const relPath = "/api/logout";
    final uri = Uri.parse('$baseUrl$relPath');
    final resp = await http.get(uri);
    return resp;
  }
}
