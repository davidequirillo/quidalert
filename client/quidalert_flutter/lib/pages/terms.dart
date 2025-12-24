// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/config.dart' as config;
import 'package:http/http.dart' as http;

class TermsPage extends StatelessWidget {
  const TermsPage({super.key});

  Future<String> _loadFromServer() async {
    final uri = Uri.parse('${config.apiUrl}/terms');
    await Future.delayed(const Duration(seconds: 2));
    return 'Data from server';
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
