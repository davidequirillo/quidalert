// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class AccountsPage extends StatelessWidget {
  const AccountsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CAppBar(title: "Accounts"),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: AccountsBody()),
    ); // build
  }
}

class AccountsBody extends StatelessWidget {
  const AccountsBody({super.key});

  @override
  Widget build(BuildContext context) {
    final primaryController = PrimaryScrollController.of(context);
    final authClient = context.read<AuthClient>();
    final loc = AppLocalizations.of(context)!;
    return Scrollbar(
      thumbVisibility: true,
      controller: primaryController,
      child: SingleChildScrollView(
        controller: primaryController,
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.start,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            buildSectionLink(
              context,
              '${loc.menuWhiteList} (${loc.buttonAdd.toLowerCase()})',
              "/accounts/whitelist/add-entries",
            ),
            buildSectionLink(
              context,
              '${loc.menuWhiteList} (${loc.buttonSearch.toLowerCase()})',
              "/accounts/whitelist/search-entries",
            ),
            buildSectionLink(
              context,
              '${loc.menuWhiteList} (${loc.buttonDelete.toLowerCase()})',
              "/accounts/whitelist/delete-entries",
            ),
            buildSectionLink(
              context,
              '${loc.menuUsers} (${loc.buttonSearch.toLowerCase()})',
              "/accounts/users/search-module",
            ),
            buildSectionLink(
              context,
              '${loc.menuUsers} (${loc.labelSearchByCSV.toLowerCase()})',
              "/accounts/users/search-by-csv",
            ),
            if (authClient.isAdmin())
              buildSectionLink(
                context,
                loc.menuUploadTerms,
                "/accounts/upload-terms",
              ),
          ],
        ),
      ),
    );
  }
}
