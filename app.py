from flask import Flask, render_template, Response, jsonify, request
from detector import TrafficSignalDetector
from sound_detector import AmbulanceSoundDetector
import threading
import time
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    import requests as req_lib
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

log = logging.getLogger(__name__)

app = Flask(__name__)

# ── ESP32 Configuration ──────────────────────────────────────
# After the ESP32 boots, check Serial Monitor for its IP and paste it here.
# Example: "http://192.168.1.42"
ESP32_IP = "http://192.168.x.x"   # ← CHANGE THIS after ESP32 boots
ESP32_TIMEOUT = 2                  # seconds

# ── Email Alert Configuration ────────────────────────────────
ALERT_EMAIL_FROM     = "kiranseragara@gmail.com"
ALERT_EMAIL_PASSWORD = "tjxj osqq fopx kquw"   # Gmail App Password
ALERT_EMAIL_TO       = "kiranseragara@gmail.com"
EMAIL_ALERTS_ENABLED = True


def send_alert_email(subject: str, body: str):
    """Send an alert email via Gmail SMTP in a fire-and-forget thread."""
    if not EMAIL_ALERTS_ENABLED:
        return

    def _send():
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From']    = ALERT_EMAIL_FROM
            msg['To']      = ALERT_EMAIL_TO

            # Plain-text part
            text_part = MIMEText(body, 'plain')

            # HTML part — styled card
            html_body = f"""
            <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;
                        background:#0f0f1e;color:#f0f0f0;border-radius:14px;
                        padding:28px;border:1px solid #2a2a4a;">
                <h2 style="margin:0 0 8px;color:#a78bfa;font-size:1.1rem;
                           letter-spacing:1px;text-transform:uppercase;">🚦 SignalDetect Alert</h2>
                <p style="font-size:1.4rem;font-weight:700;margin:12px 0;color:#ffffff;">{subject}</p>
                <p style="color:#aaa;font-size:0.9rem;line-height:1.6;">{body}</p>
                <hr style="border:none;border-top:1px solid #2a2a4a;margin:20px 0;">
                <p style="font-size:0.75rem;color:#555;">Smart Ambulance Priority Traffic System · VKIT Hackathon</p>
            </div>
            """
            html_part = MIMEText(html_body, 'html')

            msg.attach(text_part)
            msg.attach(html_part)

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(ALERT_EMAIL_FROM, ALERT_EMAIL_PASSWORD)
                smtp.sendmail(ALERT_EMAIL_FROM, ALERT_EMAIL_TO, msg.as_string())

            log.info(f"[Email] Alert sent: {subject}")
        except Exception as e:
            log.error(f"[Email] Failed to send alert: {e}")

    threading.Thread(target=_send, daemon=True, name="EmailAlert").start()

# ── Detectors ────────────────────────────────────────────────
detector       = TrafficSignalDetector()
sound_detector = AmbulanceSoundDetector()

# ── Decision engine state ─────────────────────────────────────
_last_command_sent = "IDLE"
_esp32_status      = "Unknown"  # "ok", "error", "unreachable"


def get_current_command() -> str:
    """Combine signal + ambulance to decide hardware action."""
    sig = detector.current_state
    amb = sound_detector.ambulance_detected

    if sig == 'Yellow':
        return "YELLOW"          # always beep short on yellow regardless of ambulance
    if not amb:
        return "IDLE"
    if sig == "Green":
        return "MOVE"
    # Red, ERROR, or None → STOP when ambulance active
    return "STOP"


def send_to_esp32(command: str) -> dict:
    """Forward a command to the ESP32 HTTP server."""
    global _esp32_status

    if not REQUESTS_AVAILABLE:
        _esp32_status = "requests lib missing"
        return {"status": "error", "message": "requests library not installed"}

    endpoint_map = {"MOVE": "/move", "STOP": "/stop", "YELLOW": "/yellow", "IDLE": "/idle"}
    endpoint = endpoint_map.get(command, "/idle")
    url = ESP32_IP.rstrip("/") + endpoint

    try:
        r = req_lib.post(url, timeout=ESP32_TIMEOUT)
        _esp32_status = "ok"
        log.info(f"[ESP32] Sent {command} → {r.status_code}")
        return {"status": "ok", "command": command, "esp_response": r.text}
    except req_lib.exceptions.ConnectionError:
        _esp32_status = "unreachable"
        log.warning(f"[ESP32] Unreachable at {url}")
        return {"status": "error", "message": "ESP32 unreachable"}
    except Exception as e:
        _esp32_status = "error"
        log.error(f"[ESP32] Error: {e}")
        return {"status": "error", "message": str(e)}


def _auto_decision_loop():
    """Background thread: auto-sends command to ESP32 when decision changes."""
    global _last_command_sent
    while True:
        cmd = get_current_command()
        if cmd != _last_command_sent:
            log.info(f"[Decision] {_last_command_sent} → {cmd}  (signal={detector.current_state}, amb={sound_detector.ambulance_detected})")
            send_to_esp32(cmd)
            _last_command_sent = cmd
        time.sleep(0.8)


def _event_monitor_loop():
    """Background thread: watches for signal/ambulance changes and sends email alerts."""
    last_signal    = None
    last_ambulance = None

    # Brief startup delay so detectors can initialise before we log a spurious 'None'
    time.sleep(3)

    while True:
        sig = detector.current_state
        amb = sound_detector.ambulance_detected

        # ── Signal change ────────────────────────────────────
        if sig != last_signal and sig not in (None, 'None'):
            subject_map = {
                'Red':    '🔴 The signal is Red.',
                'Yellow': '🟡 The signal is Yellow.',
                'Green':  '🟢 The signal is Green.',
                'ERROR':  '⚠️ Signal error detected!',
            }
            body_map = {
                'Red':    'The traffic signal has turned RED. Vehicles must stop.',
                'Yellow': 'The traffic signal has turned YELLOW. Prepare to stop.',
                'Green':  'The traffic signal has turned GREEN. Safe to proceed.',
                'ERROR':  'Multiple signals detected simultaneously — possible camera error.',
            }
            subject = subject_map.get(sig, f'Signal changed to {sig}')
            body    = body_map.get(sig, f'Signal is now: {sig}')
            send_alert_email(subject, body)
            last_signal = sig

        # ── Ambulance change ─────────────────────────────────
        if amb != last_ambulance:
            if amb:
                send_alert_email(
                    '🚨 Heard an Ambulance!',
                    'An ambulance siren has been detected. Traffic priority override is now active.'
                )
            else:
                send_alert_email(
                    '🔇 Ambulance siren cleared.',
                    'The ambulance siren is no longer detected. Resuming normal traffic mode.'
                )
            last_ambulance = amb

        time.sleep(1)


# Start background threads
_decision_thread = threading.Thread(target=_auto_decision_loop, daemon=True, name="DecisionLoop")
_decision_thread.start()

_monitor_thread = threading.Thread(target=_event_monitor_loop, daemon=True, name="EventMonitor")
_monitor_thread.start()


# ── Routes ────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    return Response(detector.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/status')
def status():
    """Extended status: signal + camera + ambulance + current command + ESP32 state."""
    return jsonify({
        "signal":        detector.current_state,
        "camera":        detector.connection_status,
        "ambulance":     sound_detector.ambulance_detected,
        "mic_available": sound_detector.mic_available,
        "mic_status":    sound_detector.mic_status,
        "command":       get_current_command(),
        "esp32_status":  _esp32_status,
    })


@app.route('/set_camera', methods=['POST'])
def set_camera():
    """Update camera URL (IP webcam or local)."""
    data = request.get_json()
    camera_url = data.get('url', '')

    if camera_url == "0" or camera_url == "":
        detector.set_camera_url(0)
    else:
        if not camera_url.endswith('/video'):
            camera_url = camera_url.rstrip('/') + '/video'
        detector.set_camera_url(camera_url)

    return jsonify({"status": "success", "url": camera_url})


@app.route('/control_esp', methods=['POST'])
def control_esp():
    """Manual override: send a command directly to ESP32."""
    data    = request.get_json()
    command = data.get('command', 'IDLE').upper()
    if command not in ('MOVE', 'STOP', 'IDLE'):
        return jsonify({"status": "error", "message": "Invalid command"}), 400
    result = send_to_esp32(command)
    return jsonify(result)


@app.route('/toggle_ambulance', methods=['POST'])
def toggle_ambulance():
    """Demo toggle: manually flip ambulance_detected for hackathon demo."""
    state = sound_detector.manual_toggle()
    return jsonify({
        "status":    "ok",
        "ambulance": state,
        "command":   get_current_command()
    })


@app.route('/set_esp32', methods=['POST'])
def set_esp32():
    """Update ESP32 IP address at runtime (no server restart needed)."""
    global ESP32_IP
    data = request.get_json()
    ip = data.get('ip', '').strip()
    if not ip.startswith('http'):
        ip = 'http://' + ip
    ESP32_IP = ip.rstrip('/')
    log.info(f"[ESP32] IP updated to {ESP32_IP}")
    return jsonify({"status": "ok", "esp32_ip": ESP32_IP})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
