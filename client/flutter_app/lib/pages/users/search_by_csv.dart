// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/utils/fileutils.dart';

class UsersSearchByCSVPage extends StatelessWidget {
  const UsersSearchByCSVPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuUsers, showBackButton: true),
      body: SafeArea(top: false, child: UsersSearchByCSVBody()),
    );
  }
}

class UsersSearchByCSVBody extends StatefulWidget {
  const UsersSearchByCSVBody({super.key});

  @override
  State<UsersSearchByCSVBody> createState() => _UsersSearchByCSVBodyState();
}

class _UsersSearchByCSVBodyState extends State<UsersSearchByCSVBody> {
  final _formKey = GlobalKey<FormState>();
  final _scrollController = ScrollController();
  PlatformFile? _pickedFile;

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ["csv", "txt"],
    );
    if (result != null) {
      setState(() {
        _pickedFile = result.files.first;
      });
    }
  }

  void submit() async {
    await _prepareSearchByCSV();
  }

  Future<void> _prepareSearchByCSV() async {
    final loc = AppLocalizations.of(context)!;
    String? retMessage;
    String? retTitle;
    List<String> emailsToSearch = [];
    showLoadingDialog(context, loc.labelWaitPlease);
    if (_pickedFile != null) {
      await Future.delayed(const Duration(seconds: 2));
      final filePath = _pickedFile!.path;
      if (filePath != null) {
        try {
          emailsToSearch = readEmailsFromFile(filePath);
        } catch (e) {
          retTitle = loc.errorError;
          retMessage = loc.errorCannotReadFile;
        }
      }
    } else {
      retTitle = loc.errorError;
      retMessage = loc.errorNoFileSelected;
    }
    if ((retMessage != null) && (retTitle != null)) {
      setState(() {
        _pickedFile = null; // reset picked file
      });
      if (mounted) {
        await showSimpleAlertDialog(context, retTitle, retMessage);
      }
      if (mounted) {
        Navigator.pop(context); // close loading dialog
      }
    } else {
      if (mounted) {
        Navigator.pop(context); // close loading dialog
      }
      if (mounted) {
        Navigator.pushNamed(
          context,
          '/accounts/users/search-results',
          arguments: emailsToSearch,
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          Form(
            key: _formKey,
            child: Column(
              children: [
                buildSectionTitle(
                  '${loc.buttonSearch} ${loc.labelEmailsMany.toLowerCase()}',
                ),
                const SizedBox(height: 10),
                ElevatedButton(onPressed: _pickFile, child: Text("File CSV")),
                if (_pickedFile != null) ...[
                  const SizedBox(height: 10),
                  Text('${loc.labelFileSelected}: ${_pickedFile!.name}'),
                ],
                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton(
                      onPressed: () {
                        submit();
                      },
                      child: Text(loc.buttonSearch),
                    ),
                    const SizedBox(width: 15),
                    ElevatedButton(
                      onPressed: () => Navigator.pop(context),
                      child: Text(loc.buttonBack),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
