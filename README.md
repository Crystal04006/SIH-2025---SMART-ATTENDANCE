🛡️ SmartAttend: Modernizing Classroom Engagement through AI & Biometrics

SmartAttend is a comprehensive, multi-tenant attendance management ecosystem designed to bridge the gap between traditional classroom administration and modern digital security. By moving away from vulnerable manual roll-calls, SmartAttend introduces a robust, dual-verification workflow utilizing Dynamic, Time-Sensitive QR Codes paired with Client-Side Biometric Verification.

✨ Core Features & Value Proposition

🏢 For Institutional Administrators

Scalable Multi-Tenancy: A unified infrastructure allowing multiple independent institutions to manage isolated, secure data environments.

Seamless Onboarding: High-efficiency tools for bulk-importing student rosters via CSV and managing faculty credentials.

Organizational Hierarchy: Structured management of Academic Years and Batches to mirror real-world institutional logic.

🧑‍🏫 For Educators

Time Recovery: Start an attendance session with a single click, reclaiming an estimated 10-15% of lecture time previously lost to administration.

Live Engagement Tracking: A real-time dashboard that displays student scans as they happen, providing instant visibility into classroom attendance.

Actionable Analytics: Generate comprehensive CSV reports and historical trend analyses to identify at-risk students earlier in the semester.

🎓 For Students

Transparency & Accountability: A personal dashboard allowing students to track their attendance percentages in real-time, fostering personal responsibility.

Frictionless Verification: A quick, 2-step scanning process that respects student time while ensuring high record integrity.

🔒 The "Anti-Proxy" Security Protocol

SmartAttend was engineered with a security-first mindset to eliminate the "proxy attendance" loophole common in digital systems.

Dynamic Time-to-Live (TTL): Every generated QR code contains an encrypted, time-stamped Session ID.

60-Second Validation Window: The server validates the latency between generation and scan. If the delta exceeds 60 seconds (preventing the use of shared photos or screenshots), the scan is automatically invalidated.

Biometric Grounding: By utilizing the cryptography library to enforce a secure HTTPS context, the system ensures that biometric verification happens in a trusted environment, preventing unauthorized injection of external media.

🛠️ Technical Architecture

Backend: Python (Flask), SQLAlchemy ORM, Flask-Login for secure session management.

Database: Relational SQLite, optimized for multi-tenant data isolation.

Frontend: Modern ES6+ JavaScript, styled with a custom "Vibrant Aurora" Tailwind CSS theme.

Intelligence Layer: qrcode-python for dynamic generation and Chart.js for sophisticated administrative data visualization.

🚀 Getting Started

Prerequisites

Python 3.8 or higher

A modern, camera-enabled web browser

1. Environment Configuration

# Clone the repository
git clone [https://github.com/yourusername/SmartAttend.git](https://github.com/yourusername/SmartAttend.git)
cd SmartAttend

# Initialize and activate the virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1


2. Dependency Installation

pip install flask flask-sqlalchemy flask-login qrcode[pil] cryptography


3. Launching the Server

python app.py


4. Secure Portal Access

To enable the biometric and camera features, you must access the application through a secure local context:

Navigate to: https://127.0.0.1:5000

Privacy Note: Because the app uses a self-signed certificate for local development, your browser will show a warning. Click Advanced and select "Proceed to 127.0.0.1 (unsafe)" to grant the necessary permissions for the camera.

🎨 Design Philosophy: "Vibrant Aurora"

The UI is built on a high-contrast, professional dark-mode design system:

Glassmorphism: Layered, translucent cards that provide visual depth and clarity.

Accessibility: Persistent theme support (Dark/Light) via localStorage.

Mobile-First: Fully responsive layouts designed for projectors, tablets, and smartphones.

👨‍💻 Developed By

[Crystal Shirin] CSE - AI Student & Project Creator | LinkedIn: https://www.linkedin.com/in/crystal-shirin-dsouza-b7086532a/
