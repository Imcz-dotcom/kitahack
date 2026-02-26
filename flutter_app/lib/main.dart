import 'package:flutter/material.dart';
import 'pages/login_page.dart';
import 'pages/sos_page.dart';
import 'pages/sign_language_page.dart';
import 'pages/speech_to_text_page.dart';

void main() {
  runApp(const SignSOSApp());
}

class SignSOSApp extends StatelessWidget {
  const SignSOSApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SignSOS',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.light,
        fontFamily: 'Roboto',
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFE53935),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      initialRoute: '/login',
      routes: {
        '/login': (context) => const LoginPage(),
        '/sos': (context) => const SOSPage(),
        '/sign-language': (context) => const SignLanguagePage(),
        '/speech-to-text': (context) => const SpeechToTextPage(),
      },
    );
  }
}
