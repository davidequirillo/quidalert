// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class UsersSearchResultPage extends StatelessWidget {
  const UsersSearchResultPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuUsers, showBackButton: true),
      drawer: const CAppDrawer(),
      body: UsersSearchResultBody(),
    );
  }
}

class UsersSearchResultBody extends StatefulWidget {
  const UsersSearchResultBody({super.key});

  @override
  State<UsersSearchResultBody> createState() => _UsersSearchResultBodyState();
}

class _UsersSearchResultBodyState extends State<UsersSearchResultBody> {
  @override
  Widget build(BuildContext context) {
    return Text("Users search result page - To be implemented");
  }
}
