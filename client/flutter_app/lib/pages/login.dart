// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';

class LoginPage extends StatelessWidget {
  final VoidCallback cbLoginSuccess;

  const LoginPage({super.key, required this.cbLoginSuccess});

  @override
  Widget build(BuildContext context) {
    return Text("This is the login page");
  }
}
