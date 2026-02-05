// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';

class UserPage extends StatelessWidget {
  const UserPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.labelDetails, showBackButton: true),
      drawer: const CAppDrawer(),
      body: UserBody(),
    );
  }
}

class UserBody extends StatefulWidget {
  const UserBody({super.key});

  @override
  State<UserBody> createState() => _UserBodyState();
}

class _UserBodyState extends State<UserBody> {
  @override
  Widget build(BuildContext context) {
    return Scrollbar(
      thumbVisibility: true,
      child: CustomScrollView(
        slivers: [
          // --- SECTION 1: general info ---
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  buildSectionTitle("Section 1: General Info"),
                  _buildSimpleForm("Company Name", "Contact Email"),
                  const SizedBox(height: 20),
                  _buildSimpleForm("Address", "City"),
                  const Divider(height: 40, thickness: 2),
                ],
              ),
            ),
          ),

          // --- SECTION 2: alerts history ---
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  buildSectionTitle("Section 2: Alerts History"),
                  const SizedBox(height: 20),
                  // The Table
                  SingleChildScrollView(
                    scrollDirection: Axis
                        .horizontal, // Makes the table horizontally scrollable
                    child: DataTable(
                      columns: const [
                        DataColumn(label: Text('ID')),
                        DataColumn(label: Text('Date')),
                      ],
                      rows: List.generate(
                        10,
                        (index) => DataRow(
                          cells: [
                            DataCell(Text('#$index')),
                            DataCell(Text('Date $index')),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 40), // Spacing at the bottom
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Widget helper to create a simple form with two fields
  Widget _buildSimpleForm(String label1, String label2) {
    return Row(
      children: [
        Expanded(
          child: TextFormField(
            decoration: InputDecoration(
              labelText: label1,
              border: const OutlineInputBorder(),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: TextFormField(
            decoration: InputDecoration(
              labelText: label2,
              border: const OutlineInputBorder(),
            ),
          ),
        ),
      ],
    );
  }
}
