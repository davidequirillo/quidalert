// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

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
      body: AccountsBody(),
    ); // build
  }
}

class AccountsBody extends StatelessWidget {
  const AccountsBody({super.key});

  @override
  Widget build(BuildContext context) {
    final authClient = context.read<AuthClient>();
    final loc = AppLocalizations.of(context)!;
    return Scrollbar(
      thumbVisibility: true,
      child: ListView(
        padding: const EdgeInsets.all(20),
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
          buildSectionLink(context, loc.menuUsers, "/accounts/users"),
          buildSectionLink(
            context,
            '${loc.menuUsers} (${loc.menuResetPrivileges.toLowerCase()})',
            "/accounts/reset-privileges",
          ),
          if (authClient.isAdmin())
            buildSectionLink(
              context,
              loc.menuUploadTerms,
              "/accounts/upload-terms",
            ),
        ],
      ),
    );
  }
}
