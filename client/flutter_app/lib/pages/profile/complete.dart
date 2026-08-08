// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/utils/validators.dart';

class CompleteProfilePage extends StatelessWidget {
  const CompleteProfilePage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.userCompleteProfile, showBackButton: true),
      drawer: const CAppDrawer(),
      body: SafeArea(top: false, child: CompleteProfileBody()),
    );
  }
}

class CompleteProfileBody extends StatefulWidget {
  const CompleteProfileBody({super.key});

  @override
  State<CompleteProfileBody> createState() => _CompleteProfileBodyState();
}

class _CompleteProfileBodyState extends State<CompleteProfileBody> {
  final _formKey = GlobalKey<FormState>();
  final _scrollController = ScrollController();
  final _firstnameController = TextEditingController();
  final _surnameController = TextEditingController();
  final _streetController = TextEditingController();
  final _postalCodeController = TextEditingController();
  final _cityController = TextEditingController();
  final _provinceController = TextEditingController();
  final _countryController = TextEditingController();
  final _birthdateController = TextEditingController();
  final _phoneNumberController = TextEditingController();
  DateTime? _selectedDate;
  bool showPasswordFlag = false;

  @override
  void dispose() {
    _firstnameController.dispose();
    _surnameController.dispose();
    _streetController.dispose();
    _postalCodeController.dispose();
    _cityController.dispose();
    _provinceController.dispose();
    _countryController.dispose();
    _birthdateController.dispose();
    _phoneNumberController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _selectDate() async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(1900),
      lastDate: DateTime.now(),
    );
    if (picked != null && picked != _selectedDate) {
      setState(() {
        _selectedDate = picked;
        // We format the date as DD-MM-YYYY for display purposes only
        _birthdateController.text =
            "${picked.day.toString().padLeft(2, '0')}-${picked.month.toString().padLeft(2, '0')}-${picked.year.toString().padLeft(4, '0')}";
      });
    }
  }

  Future<void> submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedDate == null) {
      await _selectDate();
      return;
    }
    String dateToSend = _selectedDate!.toIso8601String();
    dateToSend = dateToSend.substring(0, dateToSend.indexOf('T'));
    final fname = _firstnameController.text.trim();
    final sname = _surnameController.text.trim();
    final street = _streetController.text.trim();
    final postalCode = _postalCodeController.text.trim();
    final city = _cityController.text.trim();
    final province = _provinceController.text.trim();
    final country = _countryController.text.trim();
    final phone = _phoneNumberController.text.trim();
    final fields = {
      "firstname": fname,
      "surname": sname,
      "street": street,
      "postal_code": postalCode,
      "city": city,
      "province": province,
      "country": country,
      "birthdate": dateToSend,
      "phone": phone,
    };
    await _completeProfile(fields);
  }

  Future<void> _completeProfile(Map<String, String> data) async {
    AuthClient authClient = context.read<AuthClient>();
    final loc = AppLocalizations.of(context)!;
    String retTitle = "";
    String retMessage = "";
    bool error = false;
    bool newLoginRequired = false;
    try {
      final response = await authClient.doProtectedApiRequest(
        'PUT',
        '/profile',
        body: data,
      );
      final respObj = json.decode(response.body);
      retTitle = loc.successGeneric;
      retMessage = respObj['message'] ?? "Profile completed successfully";
    } on BadRequestException catch (_) {
      retTitle = loc.errorGeneric;
      retMessage = loc.errorBadRequest;
      error = true;
    } on ForbiddenRequestException catch (_) {
      retTitle = loc.errorPermissionsNotValid;
      retMessage = loc.errorPermissionsNotValid;
      error = true;
    } on GenericNotAuthorizedException catch (_) {
      retTitle = loc.errorGeneric;
      retMessage = loc.errorNotAuthorizedDoLogin;
      error = true;
      newLoginRequired = true;
    } on ServerException catch (_) {
      retTitle = loc.errorGeneric;
      retMessage = loc.errorServer;
      error = true;
    } catch (e) {
      debugPrint('Error: cannot receive or read response');
      retTitle = loc.errorGeneric;
      retMessage = e.toString();
      error = true;
    } finally {
      if (mounted) {
        await showSimpleAlertDialog(context, retTitle, retMessage);
      }
      if (error == false) {
        if (mounted) {
          goToHomePagePostFrameCallback(context);
        }
      } else if (newLoginRequired == true) {
        if (mounted) {
          goToLoginPagePostFrameCallback(context);
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scrollbar(
      controller: _scrollController,
      thumbVisibility: true,
      child: SingleChildScrollView(
        controller: _scrollController,
        padding: EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          autovalidateMode: AutovalidateMode.onUserInteraction,
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                TextFormField(
                  controller: _firstnameController,
                  decoration: InputDecoration(
                    labelText: loc.userFirstname,
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 64,
                  validator: (value) {
                    return validateName(context, value);
                  },
                ),
                SizedBox(height: 5),
                TextFormField(
                  controller: _surnameController,
                  decoration: InputDecoration(
                    labelText: loc.userSurname,
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 64,
                  validator: (value) {
                    return validateName(context, value);
                  },
                ),
                SizedBox(height: 5),
                TextFormField(
                  controller: _streetController,
                  decoration: InputDecoration(
                    labelText: loc.addressStreetAndNumber,
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 256,
                  validator: (value) {
                    return validateStreetAndNumber(context, value);
                  },
                ),
                SizedBox(height: 5),
                TextFormField(
                  controller: _postalCodeController,
                  decoration: InputDecoration(
                    labelText: loc.addressPostalCode,
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 16,
                  validator: (value) {
                    return validatePostalCode(context, value);
                  },
                ),
                SizedBox(height: 5),
                TextFormField(
                  controller: _cityController,
                  decoration: InputDecoration(
                    labelText: loc.addressCity,
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 128,
                  validator: (value) {
                    return validateCity(context, value);
                  },
                ),
                SizedBox(height: 5),
                TextFormField(
                  controller: _provinceController,
                  decoration: InputDecoration(
                    labelText: loc.addressProvince,
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 128,
                  validator: (value) {
                    return validateProvince(context, value);
                  },
                ),
                SizedBox(height: 5),
                TextFormField(
                  controller: _countryController,
                  decoration: InputDecoration(
                    labelText: loc.addressCountry,
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 128,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return null; // Country is optional
                    }
                    return validateCountry(context, value);
                  },
                ),
                SizedBox(height: 5),
                TextField(
                  controller: _birthdateController,
                  readOnly: true,
                  decoration: InputDecoration(
                    labelText: loc.userBirthdate,
                    border: OutlineInputBorder(),
                    suffixIcon: Icon(Icons.calendar_today),
                  ),
                  onTap: () => _selectDate(),
                ),
                SizedBox(height: 25),
                TextFormField(
                  controller: _phoneNumberController,
                  decoration: InputDecoration(
                    labelText: loc.userPhoneNumber,
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 16,
                  validator: (value) {
                    return validatePhoneNumber(context, value);
                  },
                ),
                SizedBox(height: 5),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton(
                      onPressed: () {
                        submit();
                      },
                      child: Text("OK"),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton(
                      onPressed: () => Navigator.pop(context),
                      child: Text(loc.buttonCancel),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
