// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/config.dart' as config;
import 'package:http/http.dart' as http;
import 'dart:convert';

class TermsPage extends StatelessWidget {
  const TermsPage({super.key});

  Future<String> _loadFromServer() async {
    final uri = Uri.parse('${config.apiBaseUrl}/terms');
    final http.Response response;
    try {
      response = await http.get(uri, headers: {"Accept": "application/json"});
    } catch (e) {
      debugPrint('Request error: cannot receive or read response');
      return 'Network error';
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      debugPrint('HTTP ${response.statusCode}: ${response.body}');
      return 'Network error';
    } else {
      final decoded = jsonDecode(response.body);
      final message = (decoded as Map<String, dynamic>)['message'];
      if (message is! String) {
        throw Exception(
          'JSON not valid: message not present or is not a string',
        );
      }
      return message;
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<String>(
      future: _loadFromServer(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return const Center(child: Text('Loading error'));
        }
        return Center(
          child: Text(snapshot.data!, style: const TextStyle(fontSize: 20)),
        );
      },
    );
  }
}
