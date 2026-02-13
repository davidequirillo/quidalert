// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class UsersPromoteResultsPage extends StatelessWidget {
  const UsersPromoteResultsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuUsers, showBackButton: true),
      drawer: const CAppDrawer(),
      body: UsersPromoteResultsBody(),
    );
  }
}

class UsersPromoteResultsBody extends StatefulWidget {
  const UsersPromoteResultsBody({super.key});

  @override
  State<UsersPromoteResultsBody> createState() =>
      _UsersPromoteResultsBodyState();
}

class _UsersPromoteResultsBodyState extends State<UsersPromoteResultsBody> {
  final _formKey = GlobalKey<FormState>();
  final _scrollController = ScrollController();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scrollbar(
      thumbVisibility: true,
      controller: _scrollController,
      child: SingleChildScrollView(
        controller: _scrollController,
        padding: const EdgeInsets.all(16.0),
        child: SafeArea(
          top: false,
          child: Form(
            key: _formKey,
            child: Column(
              children: [
                Text("Users promote results page - To be implemented"),
                Text("We will add reset privileges results here as well"),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
