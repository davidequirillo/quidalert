// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class ResetPrivilegesPage extends StatelessWidget {
  const ResetPrivilegesPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuResetPrivileges, showBackButton: true),
      drawer: const CAppDrawer(),
      body: ResetPrivilegesBody(),
    ); // build
  }
}

class ResetPrivilegesBody extends StatelessWidget {
  const ResetPrivilegesBody({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Text('Reset Privileges Page - To be implemented'),
      ),
    );
  }
}
