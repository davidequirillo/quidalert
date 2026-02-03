// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/widgets/common.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';

class WhiteListDeletePage extends StatelessWidget {
  const WhiteListDeletePage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuWhiteList, showBackButton: true),
      drawer: const CAppDrawer(),
      body: WhiteListDeleteBody(),
    );
  }
}

class WhiteListDeleteBody extends StatefulWidget {
  const WhiteListDeleteBody({super.key});

  @override
  State<WhiteListDeleteBody> createState() => _WhiteListDeleteBodyState();
}

class _WhiteListDeleteBodyState extends State<WhiteListDeleteBody> {
  @override
  void dispose() {
    super.dispose();
  }

  void submit() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );
    deleteEntries().whenComplete(() {
      if (mounted) {
        Navigator.pop(context);
      }
    });
  }

  Future<void> deleteEntries() async {
    // Implementation for deleting entries goes here
    return;
  }

  @override
  Widget build(BuildContext context) {
    // Implementation for building the UI goes here
    return Text("Delete Entries Body");
  }
}
