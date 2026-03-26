// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class AdvicePage extends StatelessWidget {
  const AdvicePage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.labelAdvice, showBackButton: true),
      drawer: const CAppDrawer(),
      body: AdviceBody(),
    ); // build
  }
}

class AdviceBody extends StatelessWidget {
  const AdviceBody({super.key});

  Future<String> _fetchMarkdown({String? lang}) async {
    final String assetPath = 'assets/advice_$lang.md';
    final text = await rootBundle.loadString(assetPath);
    return text;
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    final locale = Localizations.localeOf(context);
    final languageCode = locale.languageCode;
    return FutureBuilder<String>(
      future: _fetchMarkdown(lang: languageCode),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          debugPrint("Error: ${snapshot.error}");
          return Center(child: Text(loc.errorLoading));
        }
        return Padding(
          padding: EdgeInsets.all(16.0),
          child: Column(
            children: [Expanded(child: Markdown(data: snapshot.data!))],
          ),
        );
      },
    );
  }
}
