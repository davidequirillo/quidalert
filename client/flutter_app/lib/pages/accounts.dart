// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/common.dart';

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
    final loc = AppLocalizations.of(context)!;
    return Scrollbar(
      thumbVisibility: true,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          buildSectionLink(
            context,
            '${loc.menuWhiteList} (${loc.buttonAdd})',
            "/accounts/whitelist/add-entries",
          ),
          buildSectionLink(
            context,
            '${loc.menuWhiteList} (${loc.buttonSearch})',
            "/accounts/whitelist/search-entries",
          ),
          buildSectionLink(
            context,
            '${loc.menuWhiteList} (${loc.buttonDelete})',
            "/accounts/whitelist/delete-entries",
          ),
          buildSectionLink(context, loc.menuRegisteredUsers, "/accounts/users"),
          buildSectionLink(
            context,
            loc.menuUploadTerms,
            "/accounts/upload-terms",
          ),
          buildSectionLink(
            context,
            loc.menuResetPrivileges,
            "/accounts/reset-privileges",
          ),
        ],
      ),
    );
  }
}
