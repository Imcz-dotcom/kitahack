import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

class SpeechToTextPage extends StatefulWidget {
  const SpeechToTextPage({super.key});

  @override
  State<SpeechToTextPage> createState() => _SpeechToTextPageState();
}

class _SpeechToTextPageState extends State<SpeechToTextPage>
    with SingleTickerProviderStateMixin {
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _isListening = false;
  bool _speechAvailable = false;
  String _currentText = '';
  String _okuMessage = '';

  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  final List<Map<String, dynamic>> _messages = [];
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _initSpeech();

    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.15).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final args = ModalRoute.of(context)?.settings.arguments;
      if (args is String && args.isNotEmpty) {
        setState(() => _okuMessage = args);
      }
    });
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _initSpeech() async {
    try {
      bool available = await _speech.initialize(
        onStatus: (val) {
          debugPrint('Status: $val');
          if (val == 'notListening' || val == 'done') {
            _finishMessage();
          }
        },
        onError: (val) {
          try {
            debugPrint('Error: ${val.errorMsg}');
          } catch (e) {
            debugPrint('Speech error (raw): $val — $e');
          }
        },
      );
      setState(() => _speechAvailable = available);
    } catch (e) {
      debugPrint('Speech init failed: $e');
      setState(() => _speechAvailable = false);
    }
  }

  void _startListening() async {
    if (!_speechAvailable) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Speech recognition not available'),
          backgroundColor: const Color(0xFFE53935),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      );
      return;
    }

    setState(() {
      _isListening = true;
      _currentText = '';
    });

    await _speech.listen(
      onResult: (val) {
        setState(() => _currentText = val.recognizedWords);
        _scrollToBottom();
      },
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      partialResults: true,
      localeId: 'en_US',
      cancelOnError: true,
    );
  }

  void _stopListening() async {
    await _speech.stop();
    _finishMessage();
  }

  void _finishMessage() {
    if (_currentText.isNotEmpty && _isListening) {
      setState(() {
        _messages.add({'text': _currentText, 'time': DateTime.now()});
        _currentText = '';
        _isListening = false;
      });
      _scrollToBottom();
    } else {
      setState(() => _isListening = false);
    }
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  String _formatTime(DateTime time) {
    final hour = time.hour > 12
        ? time.hour - 12
        : (time.hour == 0 ? 12 : time.hour);
    final minute = time.minute.toString().padLeft(2, '0');
    final period = time.hour >= 12 ? 'PM' : 'AM';
    return '$hour:$minute $period';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      body: SafeArea(
        child: Column(
          children: [
            // ── App Bar ──
            _buildAppBar(),

            // ── OKU Message ──
            if (_okuMessage.isNotEmpty) _buildOkuMessage(),

            // ── Chat Area ──
            Expanded(child: _buildChatArea()),

            // ── Mic Section ──
            _buildMicSection(),
          ],
        ),
      ),
    );
  }

  Widget _buildAppBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(8),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 20),
            color: const Color(0xFF1A1A2E),
            onPressed: () => Navigator.pushReplacementNamed(context, '/sos'),
          ),
          const SizedBox(width: 4),
          // Nurse avatar
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFFE53935), Color(0xFFFF6F61)],
              ),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(
              Icons.support_agent,
              color: Colors.white,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Nurse Chat',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1A1A2E),
                  ),
                ),
                Row(
                  children: [
                    Container(
                      width: 7,
                      height: 7,
                      decoration: const BoxDecoration(
                        color: Color(0xFF4CAF50),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      'Online',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey.shade500,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Container(
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(12),
            ),
            child: IconButton(
              icon: Icon(
                Icons.more_vert_rounded,
                color: Colors.grey.shade600,
                size: 20,
              ),
              onPressed: () {},
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOkuMessage() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            const Color(0xFFE53935).withAlpha(12),
            const Color(0xFFFF6F61).withAlpha(8),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE53935).withAlpha(40)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: const Color(0xFFE53935).withAlpha(20),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(
              Icons.sign_language,
              color: Color(0xFFE53935),
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Patient signed',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: Colors.grey.shade500,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _okuMessage.toUpperCase(),
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1A1A2E),
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildChatArea() {
    if (_messages.isEmpty && !_isListening) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 90,
              height: 90,
              decoration: BoxDecoration(
                color: const Color(0xFFE53935).withAlpha(12),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.mic_none_rounded,
                size: 44,
                color: Colors.grey.shade300,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'Start a conversation',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade400,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Tap the mic button below to speak',
              style: TextStyle(fontSize: 13, color: Colors.grey.shade400),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      itemCount: _messages.length + (_isListening ? 1 : 0),
      itemBuilder: (context, index) {
        if (_isListening && index == _messages.length) {
          return _buildMessageBubble(
            _currentText.isNotEmpty ? _currentText : 'Listening...',
            DateTime.now(),
            isLive: true,
          );
        }
        final msg = _messages[index];
        return _buildMessageBubble(msg['text'], msg['time']);
      },
    );
  }

  Widget _buildMicSection() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 28, top: 12),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Status text with animation
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 200),
            child: _isListening
                ? Row(
                    key: const ValueKey('listening'),
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                          color: Color(0xFFE53935),
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Text(
                        'Listening...',
                        style: TextStyle(
                          fontSize: 14,
                          color: Color(0xFFE53935),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  )
                : Text(
                    key: const ValueKey('tap'),
                    'Tap to speak',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey.shade500,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
          ),
          const SizedBox(height: 16),

          // Mic button with pulse animation
          GestureDetector(
            onTap: _isListening ? _stopListening : _startListening,
            child: AnimatedBuilder(
              animation: _pulseAnimation,
              builder: (context, child) {
                return Transform.scale(
                  scale: _isListening ? _pulseAnimation.value : 1.0,
                  child: child,
                );
              },
              child: Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: _isListening
                        ? [const Color(0xFFFF5252), const Color(0xFFC62828)]
                        : [const Color(0xFFE53935), const Color(0xFFD32F2F)],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(
                        0xFFE53935,
                      ).withAlpha(_isListening ? 100 : 50),
                      blurRadius: _isListening ? 24 : 12,
                      spreadRadius: _isListening ? 4 : 0,
                    ),
                  ],
                ),
                child: Icon(
                  _isListening ? Icons.stop_rounded : Icons.mic_rounded,
                  color: Colors.white,
                  size: 32,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(
    String text,
    DateTime time, {
    bool isLive = false,
  }) {
    final timeStr = _formatTime(time);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Align(
        alignment: Alignment.centerRight,
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.75,
          ),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              gradient: isLive
                  ? null
                  : const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color(0xFFE53935), Color(0xFFD32F2F)],
                    ),
              color: isLive ? Colors.white : null,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(20),
                topRight: Radius.circular(20),
                bottomLeft: Radius.circular(20),
                bottomRight: Radius.circular(6),
              ),
              border: isLive
                  ? Border.all(color: const Color(0xFFE53935).withAlpha(60))
                  : null,
              boxShadow: [
                BoxShadow(
                  color: isLive
                      ? Colors.black.withAlpha(5)
                      : const Color(0xFFE53935).withAlpha(30),
                  blurRadius: 8,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  text,
                  style: TextStyle(
                    fontSize: 15,
                    height: 1.4,
                    color: isLive ? const Color(0xFFE53935) : Colors.white,
                    fontStyle: isLive ? FontStyle.italic : FontStyle.normal,
                  ),
                ),
                const SizedBox(height: 6),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (!isLive)
                      const Icon(
                        Icons.done_all,
                        size: 14,
                        color: Colors.white70,
                      ),
                    if (!isLive) const SizedBox(width: 4),
                    Text(
                      isLive ? 'speaking...' : timeStr,
                      style: TextStyle(
                        fontSize: 11,
                        color: isLive ? Colors.grey.shade400 : Colors.white70,
                      ),
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
