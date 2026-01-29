// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/widgets/common.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';

class WhiteListPage extends StatelessWidget {
  const WhiteListPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuWhiteList, showBackButton: true),
      drawer: const CAppDrawer(),
      body: WhiteListBody(),
    );
  }
}

class WhiteListBody extends StatefulWidget {
  const WhiteListBody({super.key});

  @override
  State<WhiteListBody> createState() => _WhiteListBodyState();
}

class _WhiteListBodyState extends State<WhiteListBody> {
  @override
  Widget build(BuildContext context) {
    return Text("Whitelist page content");
  }
}
