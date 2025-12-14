import 'package:flutter/material.dart';

void main() {
  print('Hello from main()'); // a debug log
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    print('Building MyApp'); // another log
    return const MaterialApp(
      home: Scaffold(
        body: Center(
          child: Text('Hello World 👋', style: TextStyle(fontSize: 28)),
        ),
      ),
    );
  }
}
