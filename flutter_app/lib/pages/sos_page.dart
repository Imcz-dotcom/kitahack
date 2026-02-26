import 'package:flutter/material.dart';

class SOSPage extends StatefulWidget {
  const SOSPage({super.key});

  @override
  State<SOSPage> createState() => _SOSPageState();
}

class _SOSPageState extends State<SOSPage> with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _ringController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _ringAnimation;
  final bool _alertSent = false;

  @override
  void initState() {
    super.initState();

    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.06).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _ringController = AnimationController(
      duration: const Duration(seconds: 3),
      vsync: this,
    )..repeat();

    _ringAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _ringController, curve: Curves.easeOut));
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _ringController.dispose();
    super.dispose();
  }

  void _triggerSOS() {
    // Navigate to sign language camera page
    Navigator.pushNamed(context, '/sign-language');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFFFFF8F0), Color(0xFFFFFFFF), Color(0xFFFFF0F0)],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Top bar
              _buildTopBar(),

              // Main content - centered SOS
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Status text
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 300),
                      child: _alertSent
                          ? _buildAlertSentBadge()
                          : _buildReadyBadge(),
                    ),
                    const SizedBox(height: 48),

                    // SOS Button with rings
                    _buildSOSButton(),
                    const SizedBox(height: 32),

                    // Instruction text
                    Text(
                      _alertSent
                          ? 'Help is on the way'
                          : 'Tap the button for emergency help',
                      style: TextStyle(
                        fontSize: 16,
                        color: Colors.grey.shade500,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _alertSent
                          ? 'Your location has been shared'
                          : 'Your location will be shared automatically',
                      style: TextStyle(
                        fontSize: 13,
                        color: Colors.grey.shade400,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTopBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Logo
          const Row(
            children: [
              Icon(Icons.sign_language, color: Color(0xFFE53935), size: 26),
              SizedBox(width: 8),
              Text(
                'SignSOS',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1A1A2E),
                  letterSpacing: 1,
                ),
              ),
            ],
          ),
          // Settings
          Container(
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(12),
            ),
            child: IconButton(
              onPressed: () {},
              icon: Icon(
                Icons.settings_outlined,
                color: Colors.grey.shade600,
                size: 22,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildReadyBadge() {
    return Container(
      key: const ValueKey('ready'),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF4CAF50).withAlpha(15),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: const Color(0xFF4CAF50).withAlpha(50)),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.circle, color: Color(0xFF4CAF50), size: 10),
          SizedBox(width: 8),
          Text(
            'System Ready',
            style: TextStyle(
              color: Color(0xFF4CAF50),
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAlertSentBadge() {
    return Container(
      key: const ValueKey('sent'),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFE53935).withAlpha(15),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: const Color(0xFFE53935).withAlpha(50)),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.emergency, color: Color(0xFFE53935), size: 16),
          SizedBox(width: 8),
          Text(
            'Alert Sent!',
            style: TextStyle(
              color: Color(0xFFE53935),
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSOSButton() {
    return SizedBox(
      width: 260,
      height: 260,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Animated rings
          AnimatedBuilder(
            animation: _ringAnimation,
            builder: (context, child) {
              return CustomPaint(
                size: const Size(260, 260),
                painter: _RingPainter(
                  progress: _ringAnimation.value,
                  color: _alertSent
                      ? const Color(0xFF4CAF50)
                      : const Color(0xFFE53935),
                ),
              );
            },
          ),

          // Main button
          AnimatedBuilder(
            animation: _pulseAnimation,
            builder: (context, child) {
              return Transform.scale(
                scale: _pulseAnimation.value,
                child: child,
              );
            },
            child: GestureDetector(
              onTap: _triggerSOS,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 500),
                width: 170,
                height: 170,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: _alertSent
                        ? [
                            const Color(0xFF66BB6A),
                            const Color(0xFF4CAF50),
                            const Color(0xFF388E3C),
                          ]
                        : [
                            const Color(0xFFFF5252),
                            const Color(0xFFE53935),
                            const Color(0xFFC62828),
                          ],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color:
                          (_alertSent
                                  ? const Color(0xFF4CAF50)
                                  : const Color(0xFFE53935))
                              .withAlpha(80),
                      blurRadius: 30,
                      spreadRadius: 5,
                    ),
                  ],
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      _alertSent ? Icons.check : Icons.emergency,
                      color: Colors.white,
                      size: 44,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _alertSent ? 'SENT' : 'SOS',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 32,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 6,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomInfo() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.grey.shade50,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.grey.shade200),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFF42A5F5).withAlpha(15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(
                Icons.info_outline,
                color: Color(0xFF42A5F5),
                size: 22,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Sign Language Mode',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                      color: Color(0xFF1A1A2E),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Use camera to communicate with sign language',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
                  ),
                ],
              ),
            ),
            GestureDetector(
              onTap: () => Navigator.pushNamed(context, '/sign-language'),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFFE53935),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text(
                  'Open',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// Custom painter for expanding ring animation
class _RingPainter extends CustomPainter {
  final double progress;
  final Color color;

  _RingPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.width / 2;

    // Draw 3 expanding rings
    for (int i = 0; i < 3; i++) {
      final ringProgress = ((progress + i * 0.33) % 1.0);
      final radius = 85 + (maxRadius - 85) * ringProgress;
      final opacity = (1.0 - ringProgress) * 0.3;

      final paint = Paint()
        ..color = color.withAlpha((opacity * 255).toInt())
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0;

      canvas.drawCircle(center, radius, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _RingPainter oldDelegate) {
    return oldDelegate.progress != progress || oldDelegate.color != color;
  }
}
