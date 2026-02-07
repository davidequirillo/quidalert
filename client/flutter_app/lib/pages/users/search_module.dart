// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class UsersSearchModulePage extends StatelessWidget {
  const UsersSearchModulePage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuUsers, showBackButton: true),
      drawer: const CAppDrawer(),
      body: UsersSearchModuleBody(),
    );
  }
}

class UsersSearchModuleBody extends StatefulWidget {
  const UsersSearchModuleBody({super.key});

  @override
  State<UsersSearchModuleBody> createState() => _UsersSearchModuleBodyState();
}

class _UsersSearchModuleBodyState extends State<UsersSearchModuleBody> {
  @override
  Widget build(BuildContext context) {
    return Text("Users search module page content - To be implemented");
  }
}
