import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

class SpeechToTextPage extends StatefulWidget {
  const SpeechToTextPage({super.key});

  @override
  State<SpeechToTextPage> createState() => _SpeechToTextPageState();
}

class _SpeechToTextPageState extends State<SpeechToTextPage> {
  // Step 4: Initialize the SpeechToText object and state variables
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _isListening = false;
  bool _speechAvailable = false;
  String _text = 'Press the button to start speaking';
  double _confidence = 1.0;

  // Step 5: Initialize speech recognition in initState
  @override
  void initState() {
    super.initState();
    _initSpeech();
  }

  /// Check if the device supports speech recognition.
  /// Must be called before listen() — otherwise it will fail.
  void _initSpeech() async {
    try {
      bool available = await _speech.initialize(
        onStatus: (val) => debugPrint('Status: $val'),
        onError: (val) {
          try {
            debugPrint('Error: ${val.errorMsg}');
          } catch (e) {
            debugPrint('Speech error (raw): $val — $e');
          }
        },
      );
      setState(() {
        _speechAvailable = available;
      });
      if (available) {
        debugPrint('Speech recognition is available!');
      } else {
        debugPrint('Speech recognition not available.');
      }
    } catch (e) {
      debugPrint('Speech init failed: $e');
      setState(() {
        _speechAvailable = false;
      });
    }
  }

  // Step 6: Start listening — updates _text live as the user speaks
  void _startListening() async {
    if (!_speechAvailable) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Speech recognition not available')),
      );
      return;
    }

    setState(() {
      _isListening = true;
    });

    await _speech.listen(
      onResult: (val) => setState(() {
        _text = val.recognizedWords;
        if (val.hasConfidenceRating && val.confidence > 0) {
          _confidence = val.confidence;
        }
      }),
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      partialResults: true,
      localeId: 'en_US',
      onSoundLevelChange: (level) => debugPrint('Sound level: $level'),
      cancelOnError: true,
    );
  }

  // Step 7: Stop listening — releases the microphone
  void _stopListening() async {
    await _speech.stop();
    setState(() {
      _isListening = false;
    });
  }

  // Step 9 (Optional): List available locales for multi-language support
  void _listLocales() async {
    var locales = await _speech.locales();
    if (!mounted) return;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Available Languages'),
        content: SizedBox(
          width: double.maxFinite,
          height: 300,
          child: ListView.builder(
            itemCount: locales.length,
            itemBuilder: (context, index) {
              final locale = locales[index];
              return ListTile(
                title: Text(locale.name),
                subtitle: Text(locale.localeId),
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  // Step 8: Build the UI
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Speech to Text'),
        actions: [
          IconButton(
            icon: const Icon(Icons.language),
            tooltip: 'Available Languages',
            onPressed: _listLocales,
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            // Status indicator
            AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: _isListening ? Colors.red.shade50 : Colors.grey.shade100,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: _isListening ? Colors.red : Colors.grey.shade300,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    _isListening ? Icons.hearing : Icons.hearing_disabled,
                    color: _isListening ? Colors.red : Colors.grey,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    _isListening ? 'Listening...' : 'Not listening',
                    style: TextStyle(
                      color: _isListening ? Colors.red : Colors.grey,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),

            // Recognized text display
            Expanded(
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surfaceContainerLow,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: theme.colorScheme.outlineVariant),
                ),
                child: SingleChildScrollView(
                  child: Text(
                    _text,
                    style: const TextStyle(fontSize: 22.0, height: 1.5),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Confidence display
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.insights,
                    color: theme.colorScheme.onPrimaryContainer,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Confidence: ${(_confidence * 100.0).toStringAsFixed(1)}%',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: theme.colorScheme.onPrimaryContainer,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.large(
        onPressed: _isListening ? _stopListening : _startListening,
        backgroundColor: _isListening ? Colors.red : theme.colorScheme.primary,
        foregroundColor: Colors.white,
        child: Icon(_isListening ? Icons.mic_off : Icons.mic),
      ),
    );
  }
}
