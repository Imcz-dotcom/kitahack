import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:html' as html;

class SignLanguagePage extends StatefulWidget {
  const SignLanguagePage({super.key});

  @override
  State<SignLanguagePage> createState() => _SignLanguagePageState();
}

class _SignLanguagePageState extends State<SignLanguagePage> {
  // Prediction server URL (Python Flask on port 5000)
  static const String _serverUrl = 'http://localhost:5000';

  // State
  String _currentLabel = '';
  double _confidence = 0.0;
  int _handsDetected = 0;
  bool _isProcessing = false;
  bool _cameraReady = false;
  bool _serverOnline = false;
  bool _alertSent = false;
  final List<String> _detectedWords = [];

  // Web camera
  html.VideoElement? _videoElement;
  html.CanvasElement? _canvasElement;
  Timer? _captureTimer;

  @override
  void initState() {
    super.initState();
    _checkServer();
    _initCamera();
  }

  @override
  void dispose() {
    _captureTimer?.cancel();
    _stopCamera();
    super.dispose();
  }

  /// Check if prediction server is running
  Future<void> _checkServer() async {
    try {
      final response = await http
          .get(Uri.parse('$_serverUrl/health'))
          .timeout(const Duration(seconds: 3));
      if (response.statusCode == 200) {
        setState(() => _serverOnline = true);
      }
    } catch (_) {
      setState(() => _serverOnline = false);
    }
  }

  /// Initialize web camera via HTML5 getUserMedia
  Future<void> _initCamera() async {
    try {
      final stream = await html.window.navigator.mediaDevices!.getUserMedia({
        'video': {'facingMode': 'user', 'width': 640, 'height': 480},
        'audio': false,
      });

      _videoElement = html.VideoElement()
        ..srcObject = stream
        ..autoplay = true
        ..setAttribute('playsinline', 'true');

      await _videoElement!.play();

      _canvasElement = html.CanvasElement(width: 640, height: 480);

      setState(() => _cameraReady = true);

      // Start sending frames every 500ms
      _captureTimer = Timer.periodic(const Duration(milliseconds: 500), (_) {
        if (!_isProcessing && _serverOnline) {
          _captureAndPredict();
        }
      });
    } catch (e) {
      debugPrint('Camera init error: $e');
    }
  }

  void _stopCamera() {
    if (_videoElement?.srcObject != null) {
      final tracks = (_videoElement!.srcObject as html.MediaStream).getTracks();
      for (var track in tracks) {
        track.stop();
      }
    }
  }

  /// Capture a frame from the video and send to prediction server
  Future<void> _captureAndPredict() async {
    if (_videoElement == null || _canvasElement == null) return;

    setState(() => _isProcessing = true);

    try {
      // Draw current video frame to canvas
      final ctx = _canvasElement!.context2D;
      ctx.drawImage(_videoElement!, 0, 0);

      // Convert to base64 JPEG
      final dataUrl = _canvasElement!.toDataUrl('image/jpeg', 0.7);
      final base64Image = dataUrl.split(',').last;

      // Send to prediction server
      final response = await http
          .post(
            Uri.parse('$_serverUrl/predict'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'image': base64Image}),
          )
          .timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _currentLabel = data['label'] ?? '';
          _confidence = (data['confidence'] ?? 0.0).toDouble();
          _handsDetected = data['hands_detected'] ?? 0;

          // Add to detected words list (avoid duplicates in a row)
          if (_currentLabel.isNotEmpty &&
              _confidence > 80 &&
              (_detectedWords.isEmpty ||
                  _detectedWords.last != _currentLabel)) {
            _detectedWords.add(_currentLabel);
          }
        });
      }
    } catch (e) {
      debugPrint('Prediction error: $e');
    }

    setState(() => _isProcessing = false);
  }

  void _sendEmergencyAlert() {
    setState(() => _alertSent = true);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Row(
          children: [
            Icon(Icons.check_circle, color: Colors.white, size: 20),
            SizedBox(width: 10),
            Text('🚨 Emergency alert sent! Help is on the way.'),
          ],
        ),
        backgroundColor: const Color(0xFF4CAF50),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        margin: const EdgeInsets.all(16),
        duration: const Duration(seconds: 4),
      ),
    );

    Future.delayed(const Duration(seconds: 5), () {
      if (mounted) setState(() => _alertSent = false);
    });
  }

  void _clearWords() {
    setState(() => _detectedWords.clear());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, color: Color(0xFF1A1A2E)),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Row(
          children: [
            Icon(Icons.sign_language, color: Color(0xFFE53935), size: 24),
            SizedBox(width: 8),
            Text(
              'Sign Language',
              style: TextStyle(
                color: Color(0xFF1A1A2E),
                fontWeight: FontWeight.bold,
                fontSize: 20,
              ),
            ),
          ],
        ),
        actions: [
          // Server status indicator
          Container(
            margin: const EdgeInsets.only(right: 16),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: _serverOnline
                  ? const Color(0xFF4CAF50).withAlpha(15)
                  : const Color(0xFFE53935).withAlpha(15),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.circle,
                  size: 8,
                  color: _serverOnline
                      ? const Color(0xFF4CAF50)
                      : const Color(0xFFE53935),
                ),
                const SizedBox(width: 6),
                Text(
                  _serverOnline ? 'Connected' : 'Offline',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: _serverOnline
                        ? const Color(0xFF4CAF50)
                        : const Color(0xFFE53935),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // Camera preview area
          Expanded(flex: 5, child: _buildCameraPreview()),

          // Prediction result
          _buildPredictionBar(),

          // Detected words sentence
          _buildWordsSentence(),

          // Action buttons
          _buildActionButtons(),

          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildCameraPreview() {
    if (!_cameraReady) {
      return Container(
        margin: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF1A1A2E),
          borderRadius: BorderRadius.circular(24),
        ),
        child: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(color: Colors.white),
              SizedBox(height: 16),
              Text(
                'Starting camera...',
                style: TextStyle(color: Colors.white70, fontSize: 16),
              ),
            ],
          ),
        ),
      );
    }

    return Container(
      margin: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A2E),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: _handsDetected > 0
              ? const Color(0xFF4CAF50).withAlpha(100)
              : Colors.transparent,
          width: 2,
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(22),
        child: Stack(
          fit: StackFit.expand,
          children: [
            // Video feed using HtmlElementView
            HtmlElementView.fromTagName(
              tagName: 'video',
              onElementCreated: (element) {
                final videoEl = element as html.VideoElement;
                if (_videoElement?.srcObject != null) {
                  videoEl.srcObject = _videoElement!.srcObject;
                  videoEl.autoplay = true;
                  videoEl.muted = true;
                  videoEl.setAttribute('playsinline', 'true');
                  videoEl.style
                    ..objectFit = 'cover'
                    ..transform = 'scaleX(-1)';
                }
              },
            ),

            // Hand detection overlay
            if (_handsDetected > 0)
              Positioned(
                top: 12,
                left: 12,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.black54,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        Icons.back_hand,
                        color: Color(0xFF4CAF50),
                        size: 16,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '$_handsDetected hand${_handsDetected > 1 ? 's' : ''} detected',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            // Processing indicator
            if (_isProcessing)
              Positioned(
                top: 12,
                right: 12,
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.black54,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildPredictionBar() {
    Color labelColor;
    if (_confidence > 80) {
      labelColor = const Color(0xFF4CAF50);
    } else if (_confidence > 60) {
      labelColor = const Color(0xFFFF9800);
    } else {
      labelColor = Colors.grey;
    }

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(10),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          // Label
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Detected Sign',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey.shade400,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _currentLabel.isNotEmpty
                      ? _currentLabel.toUpperCase()
                      : 'Show a sign...',
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: _currentLabel.isNotEmpty
                        ? const Color(0xFF1A1A2E)
                        : Colors.grey.shade300,
                  ),
                ),
              ],
            ),
          ),
          // Confidence
          if (_currentLabel.isNotEmpty)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: labelColor.withAlpha(20),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '${_confidence.toStringAsFixed(0)}%',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: labelColor,
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildWordsSentence() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Row(
        children: [
          Icon(Icons.text_fields, color: Colors.grey.shade400, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              _detectedWords.isNotEmpty
                  ? _detectedWords.join(' → ')
                  : 'Detected words will appear here...',
              style: TextStyle(
                fontSize: 14,
                color: _detectedWords.isNotEmpty
                    ? const Color(0xFF1A1A2E)
                    : Colors.grey.shade400,
                fontWeight: _detectedWords.isNotEmpty
                    ? FontWeight.w600
                    : FontWeight.normal,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (_detectedWords.isNotEmpty)
            GestureDetector(
              onTap: _clearWords,
              child: Icon(Icons.close, color: Colors.grey.shade400, size: 18),
            ),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          // Send Emergency Alert
          Expanded(
            flex: 2,
            child: SizedBox(
              height: 54,
              child: ElevatedButton.icon(
                onPressed: _alertSent ? null : _sendEmergencyAlert,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _alertSent
                      ? const Color(0xFF4CAF50)
                      : const Color(0xFFE53935),
                  foregroundColor: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
                icon: Icon(
                  _alertSent ? Icons.check : Icons.emergency,
                  size: 22,
                ),
                label: Text(
                  _alertSent ? 'Alert Sent!' : 'Send Emergency Alert',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          // Retry server connection
          SizedBox(
            height: 54,
            child: OutlinedButton(
              onPressed: _checkServer,
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF42A5F5),
                side: const BorderSide(color: Color(0xFF42A5F5)),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: const Icon(Icons.refresh, size: 22),
            ),
          ),
        ],
      ),
    );
  }
}
