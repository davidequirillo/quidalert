// Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
// Copyright (C) 2025  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/widgets/common.dart';
import 'package:quidalert_flutter/services/auth.dart';

class UploadTermsPage extends StatelessWidget {
  const UploadTermsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.menuUploadTerms, showBackButton: true),
      drawer: const CAppDrawer(),
      body: UploadTermsBody(),
    ); // build
  }
}

class UploadTermsBody extends StatefulWidget {
  const UploadTermsBody({super.key});

  @override
  State<UploadTermsBody> createState() => _UploadTermsBodyState();
}

class _UploadTermsBodyState extends State<UploadTermsBody> {
  String _selectedLanguage = 'en';
  PlatformFile? _pickedFile;

  Future<void> _pickFile() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['md'],
    );

    if (result != null) {
      setState(() {
        _pickedFile = result.files.first;
      });
    }
  }

  void submit() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );
    _uploadToServer().whenComplete(() {
      if (mounted) {
        Navigator.pop(context);
      }
    });
  }

  Future<void> _uploadToServer() async {
    String? retMessage;
    Color retColor = Colors.blue;
    final loc = AppLocalizations.of(context)!;
    final authClient = context.read<AuthClient>();
    if (_pickedFile == null || _pickedFile!.path == null) return;
    try {
      await authClient.doProtectedApiRequest(
        'POST',
        '/terms',
        headers: {"Content-Type": "text/markdown"},
        body: {'language': _selectedLanguage},
        file: _pickedFile!.path!,
      );
      await Future.delayed(const Duration(seconds: 2));
      retMessage = loc.successUpload;
    } on GenericNotAuthorizedException catch (_) {
      retMessage = loc.errorNotAuthorizedDoLogin;
      retColor = Colors.red;
    } on BadRequestException catch (_) {
      retMessage = loc.errorBadRequest;
      retColor = Colors.red;
    } on NetworkException catch (_) {
      retMessage = loc.errorNetwork;
      retColor = Colors.red;
    } catch (e) {
      retMessage = "Error: $e";
      retColor = Colors.red;
    } finally {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(retMessage!),
            backgroundColor: retColor,
            duration: const Duration(seconds: 4),
          ),
        );
        setState(() {
          _pickedFile = null;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.all(20.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(
                value: "en",
                label: Text('EN'),
                icon: Icon(Icons.language),
              ),
              ButtonSegment(
                value: "it",
                label: Text('IT'),
                icon: Icon(Icons.language),
              ),
            ],
            selected: {_selectedLanguage},
            onSelectionChanged: (Set<String> newSelection) {
              setState(() {
                _selectedLanguage = newSelection.first;
              });
            },
          ),
          const SizedBox(height: 10),
          Text(
            '${loc.labelSelect} file:',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          // Area di Drag & Drop / Click to Select
          InkWell(
            onTap: _pickFile,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                border: Border.all(
                  color: Colors.blueAccent,
                  style: BorderStyle.solid,
                ),
                borderRadius: BorderRadius.circular(10),
                color: Colors.blueAccent.withValues(alpha: 0.05),
              ),
              child: Column(
                children: [
                  const Icon(
                    Icons.cloud_upload,
                    size: 25,
                    color: Colors.blueAccent,
                  ),
                  const SizedBox(height: 5),
                  Text(_pickedFile?.name ?? loc.labelClickToSelectFile),
                ],
              ),
            ),
          ),
          SizedBox(height: 15),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton(
              onPressed: (_pickedFile != null)
                  ? () {
                      submit();
                    }
                  : null,
              style: ElevatedButton.styleFrom(backgroundColor: Colors.blue),
              child: const Text(
                "Upload",
                style: TextStyle(color: Colors.white),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
