// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:quidalert_flutter/l10n/app_localizations.dart';
import 'package:quidalert_flutter/l10n/app_localizations_extension.dart';
import 'package:quidalert_flutter/widgets/components.dart';
import 'package:quidalert_flutter/models/general.dart';
import 'package:quidalert_flutter/utils/strings.dart';
import 'package:quidalert_flutter/services/auth.dart';
import 'package:quidalert_flutter/widgets/helpers.dart';

class AlertMessagesPage extends StatelessWidget {
  const AlertMessagesPage({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: CAppBar(title: loc.alertMessages, showBackButton: true),
      body: SafeArea(top: false, child: AlertMessagesBody()),
    );
  }
}

class AlertMessagesBody extends StatefulWidget {
  const AlertMessagesBody({super.key});

  @override
  State<AlertMessagesBody> createState() => _AlertMessagesBodyState();
}

class _AlertMessagesBodyState extends State<AlertMessagesBody> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _sendMessage(int alertId) async {
    String retMessage = "";
    bool loginIsRequired = false;
    final loc = AppLocalizations.of(context)!;
    final content = _messageController.text.trim();
    if (content.isEmpty) return;
    final authClient = context.read<AuthClient>();
    try {
      await authClient.doProtectedApiRequest(
        "post",
        '/alerts/$alertId/messages',
        body: {"content": content},
      );
    } on GenericNotAuthorizedException catch (_) {
      retMessage = loc.errorNotAuthorizedDoLogin;
      loginIsRequired = true;
    } on ForbiddenRequestException catch (e) {
      if (e.toString().contains("Alert is closed")) {
        retMessage = loc.errorAlertIsClosed;
      } else {
        retMessage = loc.errorPermissionsNotValid;
      }
    } on BadRequestException catch (e) {
      retMessage = loc.errorBadRequest;
      retMessage += ": ${e.toString()}";
    } on ServerException catch (_) {
      retMessage = loc.errorServer;
    } catch (e) {
      retMessage = loc.errorError;
      retMessage += ": ${e.toString()}";
    } finally {
      if (retMessage.isNotEmpty) {
        debugPrint("Error sending message: $retMessage");
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(retMessage),
              duration: const Duration(seconds: 4),
            ),
          );
          if (loginIsRequired) {
            goToLoginPagePostFrameCallback(context);
          }
        }
      } else {
        if (mounted) {
          setState(() {
            _messageController.clear();
          });
        }
      }
    }
  }

  Future<Map<String, dynamic>> _getMessages(int alertId) async {
    final authClient = context.read<AuthClient>();
    final response = await authClient.doProtectedApiRequest(
      "get",
      '/alerts/$alertId/messages',
    );
    final Map<String, dynamic> respObj = json.decode(response.body);
    if (respObj['messages'] == null) {
      throw NotFoundException();
    }
    final messages = (respObj['messages'] as List)
        .map((e) => Message.fromJson(e))
        .toList();
    final readOnly = respObj['readonly'] ?? true;
    return {"messages": messages, "readonly": readOnly};
  }

  @override
  Widget build(BuildContext context) {
    final alertId = ModalRoute.of(context)!.settings.arguments as int;
    final loc = AppLocalizations.of(context)!;
    return FutureBuilder<Map<String, dynamic>>(
      future: _getMessages(alertId),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          debugPrint("Error fetching alert messages: ${snapshot.error}");
          final exceptionName = snapshot.error.runtimeType.toString();
          final errorMessage =
              loc.getExceptionString(exceptionName) ?? loc.errorGeneric;
          if (snapshot.error.toString().startsWith("GenericNotAuthorized")) {
            goToLoginPagePostFrameCallback(context);
          }
          return Center(child: Text(errorMessage));
        }
        if (snapshot.hasData) {
          final messages = snapshot.data!['messages'] as List<Message>;
          final readOnly = snapshot.data!['readonly'] as bool;
          return buildChat(context, alertId, messages, readOnly);
        }
        return Center(child: Text(loc.errorGeneric));
      },
    );
  }

  Widget buildChat(
    BuildContext context,
    int alertId,
    List<Message> messages,
    bool readOnly,
  ) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _scrollToBottom(); // Scroll to bottom after the UI is built
    });
    final loc = AppLocalizations.of(context)!;
    return Column(
      children: [
        // Messages area
        if (messages.isEmpty)
          Expanded(
            child: Center(
              child: Text(
                loc.alertMessagesEmpty,
                style: const TextStyle(fontSize: 16, color: Colors.black54),
              ),
            ),
          )
        else
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.only(
                left: 15,
                right: 15,
                top: 15,
                bottom: 200, // Leave space for the input area
              ),
              itemCount: messages.length,
              itemBuilder: (context, index) {
                final message = messages[index];
                return _ChatBubble(message: message);
              },
            ),
          ),
        // Input area
        if (readOnly == false) _buildInputArea(alertId),
      ],
    );
  }

  Widget _buildInputArea(int alertId) {
    final loc = AppLocalizations.of(context)!;
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        color: Colors.transparent,
        child: Row(
          children: [
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(25),
                ),
                child: TextField(
                  controller: _messageController,
                  textCapitalization: TextCapitalization.sentences,
                  decoration: InputDecoration(
                    hintText: loc.alertMessagesWriteNew,
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 10,
                    ),
                  ),
                  onSubmitted: (_) => _sendMessage(alertId),
                ),
              ),
            ),
            const SizedBox(width: 6),
            GestureDetector(
              onTap: () => _sendMessage(alertId),
              child: const CircleAvatar(
                radius: 22,
                backgroundColor: Color(0xFF075E54),
                child: Icon(Icons.send, color: Colors.white, size: 20),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }
}

class _ChatBubble extends StatelessWidget {
  final Message message;

  const _ChatBubble({required this.message});

  Color getBubbleColor(Message message) {
    if (message.isCaller) {
      return const Color(0xFFD1FFC7); // Light green for caller
    } else if (message.isAlertManager) {
      return const Color(0xFFFFFAD1); // Light blue for alert manager
    } else {
      return Colors.white; // Default white for others
    }
  }

  @override
  Widget build(BuildContext context) {
    final createdAtStr = datetimeAsStringWithoutMilliseconds(message.createdAt);
    String msgSenderStr = message.isCaller
        ? ""
        : "${message.firstname} ${message.surname}";
    if (message.isAlertManager) {
      msgSenderStr += " (manager)";
    }
    msgSenderStr = msgSenderStr.trim();
    return Align(
      alignment: message.isCaller
          ? Alignment.centerRight
          : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        decoration: BoxDecoration(
          color: getBubbleColor(message),
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(12),
            topRight: const Radius.circular(12),
            bottomLeft: Radius.circular(message.isCaller ? 12 : 0),
            bottomRight: Radius.circular(message.isCaller ? 0 : 12),
          ),
          boxShadow: const [
            BoxShadow(
              color: Colors.black12,
              offset: Offset(0, 1),
              blurRadius: 1,
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (msgSenderStr.isNotEmpty)
              Text(
                msgSenderStr,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),
            SizedBox(height: 5),
            SelectableText(
              message.content,
              style: const TextStyle(fontSize: 15, color: Colors.black87),
            ),
            SizedBox(height: 5),
            Text(
              createdAtStr,
              style: const TextStyle(fontSize: 12, color: Colors.black54),
            ),
          ],
        ),
      ),
    );
  }
}
