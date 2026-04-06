document.addEventListener('DOMContentLoaded', () => {

    // ── Toast Notification System ────────────────────────────
    (function injectToastStyles() {
        const s = document.createElement('style');
        s.textContent = `
            #toast-container {
                position: fixed;
                bottom: 24px;
                right: 24px;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 10px;
                pointer-events: none;
            }
            .toast {
                display: flex;
                align-items: center;
                gap: 12px;
                min-width: 280px;
                max-width: 360px;
                padding: 14px 18px;
                border-radius: 14px;
                background: rgba(15, 15, 30, 0.92);
                backdrop-filter: blur(16px);
                border: 1px solid rgba(255,255,255,0.08);
                box-shadow: 0 8px 32px rgba(0,0,0,0.5);
                font-family: 'Outfit', sans-serif;
                font-size: 0.9rem;
                color: #f0f0f0;
                pointer-events: auto;
                position: relative;
                overflow: hidden;
                animation: toastIn 0.35s cubic-bezier(0.34,1.56,0.64,1) both;
            }
            .toast.toast-out {
                animation: toastOut 0.3s ease forwards;
            }
            .toast-icon {
                font-size: 1.5rem;
                flex-shrink: 0;
            }
            .toast-body { flex: 1; }
            .toast-title {
                font-weight: 700;
                font-size: 0.88rem;
                margin-bottom: 2px;
            }
            .toast-msg {
                font-size: 0.78rem;
                color: rgba(255,255,255,0.6);
            }
            .toast-bar {
                position: absolute;
                bottom: 0; left: 0;
                height: 3px;
                border-radius: 0 0 14px 14px;
                animation: toastBar var(--toast-dur, 4s) linear forwards;
            }
            .toast-close {
                cursor: pointer;
                opacity: 0.5;
                font-size: 1rem;
                background: none;
                border: none;
                color: #fff;
                padding: 0;
                line-height: 1;
                flex-shrink: 0;
            }
            .toast-close:hover { opacity: 1; }
            @keyframes toastIn {
                from { transform: translateX(120%); opacity: 0; }
                to   { transform: translateX(0);    opacity: 1; }
            }
            @keyframes toastOut {
                from { transform: translateX(0);    opacity: 1; }
                to   { transform: translateX(120%); opacity: 0; }
            }
            @keyframes toastBar {
                from { width: 100%; }
                to   { width: 0%; }
            }
        `;
        document.head.appendChild(s);
        const c = document.createElement('div');
        c.id = 'toast-container';
        document.body.appendChild(c);
    })();

    const TOAST_THEMES = {
        red:      { border: '#ff3b30', bar: '#ff3b30', glow: 'rgba(255,59,48,0.25)' },
        green:    { border: '#34c759', bar: '#34c759', glow: 'rgba(52,199,89,0.25)' },
        yellow:   { border: '#ffcc00', bar: '#ffcc00', glow: 'rgba(255,204,0,0.25)' },
        ambulance:{ border: '#ff9f0a', bar: '#ff9f0a', glow: 'rgba(255,159,10,0.3)' },
        info:     { border: '#4f6ef7', bar: '#4f6ef7', glow: 'rgba(79,110,247,0.25)' },
    };

    function showNotification(icon, title, message, theme = 'info', duration = 4000) {
        const container = document.getElementById('toast-container');
        const t = TOAST_THEMES[theme] || TOAST_THEMES.info;
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.style.cssText = `
            border-color: ${t.border};
            box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px ${t.border}40, 0 0 20px ${t.glow};
            --toast-dur: ${duration}ms;
        `;
        toast.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <div class="toast-body">
                <div class="toast-title">${title}</div>
                <div class="toast-msg">${message}</div>
            </div>
            <button class="toast-close" aria-label="Dismiss">✕</button>
            <div class="toast-bar" style="background:${t.bar};"></div>
        `;
        const dismiss = () => {
            toast.classList.add('toast-out');
            setTimeout(() => toast.remove(), 300);
        };
        toast.querySelector('.toast-close').addEventListener('click', dismiss);
        container.appendChild(toast);
        setTimeout(dismiss, duration);
    }


    // ── Element refs ─────────────────────────────────────────
    const statusText     = document.getElementById('status-text');
    const signalSub      = document.getElementById('signal-sub');
    const statusPanel    = document.getElementById('status-panel');
    const updateCamBtn   = document.getElementById('update-cam-btn');
    const cameraIpInput  = document.getElementById('camera-ip');
    const toggleAudioBtn = document.getElementById('toggle-audio-btn');
    const videoStream    = document.getElementById('videoStream');

    // Ambulance panel
    const ambulancePanel = document.getElementById('ambulance-panel');
    const ambIndicator   = document.getElementById('amb-indicator');
    const ambLabel       = document.getElementById('amb-label');
    const ambSublabel    = document.getElementById('amb-sublabel');
    const micDot         = document.getElementById('mic-dot');
    const micStatusText  = document.getElementById('mic-status-text');
    const demoToggleBtn  = document.getElementById('demo-toggle-btn');

    // ESP32 panel
    const espCommandBadge = document.getElementById('esp-command-badge');
    const espConnDot      = document.getElementById('esp-conn-dot');
    const espConnText     = document.getElementById('esp-conn-text');
    const hwLed           = document.getElementById('hw-led');
    const hwMotor         = document.getElementById('hw-motor');
    const hwBuzzer        = document.getElementById('hw-buzzer');
    const forceMoveBtn    = document.getElementById('force-move-btn');
    const forceStopBtn    = document.getElementById('force-stop-btn');
    const forceIdleBtn    = document.getElementById('force-idle-btn');
    const esp32IpInput    = document.getElementById('esp32-ip');
    const setEspBtn       = document.getElementById('set-esp-btn');

    // ── Floating particles ───────────────────────────────────
    const particleContainer = document.getElementById('particles');
    const PARTICLE_COLORS = ['#4f6ef7', '#ff3b30', '#ffcc00', '#34c759', '#a78bfa'];
    function spawnParticle() {
        const p = document.createElement('div');
        p.className = 'particle';
        const size = Math.random() * 10 + 4;
        p.style.cssText = `
            width: ${size}px; height: ${size}px;
            left: ${Math.random() * 100}vw;
            background: ${PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)]};
            animation-duration: ${Math.random() * 8 + 6}s;
            animation-delay: ${Math.random() * 4}s;
            opacity: 0;
        `;
        particleContainer.appendChild(p);
        setTimeout(() => p.remove(), 14000);
    }
    for (let i = 0; i < 15; i++) setTimeout(spawnParticle, i * 600);
    setInterval(spawnParticle, 1200);

    // ── State ────────────────────────────────────────────────
    let currentSignal    = 'None';
    let currentAmbulance = false;
    let currentCommand   = 'IDLE';
    let audioEnabled     = false;
    let synth            = window.speechSynthesis;

    // ── Voice helper ─────────────────────────────────────────
    window.currentUtterance = null;
    function speak(text) {
        if (!audioEnabled || !synth) return;
        if (synth.speaking) synth.cancel();
        window.currentUtterance = new SpeechSynthesisUtterance(text);
        window.currentUtterance.rate  = 1.0;
        window.currentUtterance.pitch = 1.1;
        window.currentUtterance.onerror = e => console.error('Speech error:', e);
        synth.speak(window.currentUtterance);
    }

    // ── UI helpers ───────────────────────────────────────────

    function updateSignalUI(detected) {
        statusPanel.classList.remove('state-Red', 'state-Yellow', 'state-Green', 'state-None', 'state-ERROR');
        let label = '', sublabel = '', message = '';

        if (detected === 'None') {
            label    = 'Detecting...';
            sublabel = 'Scanning for signals...';
        } else if (detected === 'ERROR') {
            label    = '⚠ ERROR';
            sublabel = 'Multiple signals detected!';
            message  = 'Warning! Signal malfunction detected.';
            statusPanel.classList.add('state-ERROR');
        } else if (detected === 'Red') {
            label    = 'Red';
            sublabel = '🚗 Stop — Red Signal';
            message  = 'Red light detected. Please stop.';
            statusPanel.classList.add('state-Red');
        } else if (detected === 'Yellow') {
            label    = 'Yellow';
            sublabel = '⚠️ Caution — Slow Down';
            message  = 'Yellow light. Prepare to stop.';
            statusPanel.classList.add('state-Yellow');
        } else if (detected === 'Green') {
            label    = 'Green';
            sublabel = '✅ Go — Safe to Proceed';
            message  = 'Green light detected. You may proceed.';
            statusPanel.classList.add('state-Green');
        }

        statusText.innerText = label;
        if (signalSub) signalSub.innerText = sublabel;
        if (message) speak(message);
    }

    function updateAmbulanceUI(detected, micAvailable, micStatus) {
        // Mic status badge
        if (micAvailable) {
            micDot.className = 'mic-dot active';
            micStatusText.textContent = '🎤 Mic Active';
        } else {
            micDot.className = 'mic-dot error';
            micStatusText.textContent = micStatus || 'Mic Unavailable';
        }

        if (detected) {
            ambulancePanel.classList.add('amb-active');
            document.getElementById('amb-icon') && (document.getElementById('amb-icon').textContent = '🚨');
            ambLabel.textContent    = '🚨 SIREN DETECTED!';
            ambSublabel.textContent = 'Ambulance approaching — processing decision...';
            if (!currentAmbulance) speak('Ambulance siren detected! Processing traffic priority.');
        } else {
            ambulancePanel.classList.remove('amb-active');
            ambLabel.textContent    = 'Not Detected';
            ambSublabel.textContent = micAvailable ? 'Listening on microphone...' : 'Use Demo Toggle for testing';
        }
        currentAmbulance = detected;
    }

    function updateESP32UI(command, esp32Status) {
        // Command badge
        espCommandBadge.className = `esp-command-badge cmd-${command}`;
        espCommandBadge.textContent = command;

        // Connection dot
        const isOnline = esp32Status === 'ok';
        espConnDot.className = isOnline ? 'esp-conn-dot online' : 'esp-conn-dot offline';
        espConnText.textContent = isOnline ? 'Connected' : (esp32Status || 'Unknown');

        // Hardware indicator pills
        hwLed.className   = 'hw-item';
        hwMotor.className = 'hw-item';
        hwBuzzer.className = 'hw-item';

        if (command === 'MOVE') {
            hwLed.classList.add('hw-on');
            hwMotor.classList.add('hw-on');
            // Buzzer just beeps momentarily on MOVE, show as dim
        } else if (command === 'STOP') {
            hwLed.classList.add('hw-on-red');
            hwBuzzer.classList.add('hw-on-red');
        }

        currentCommand = command;
    }

    // ── Main polling loop ────────────────────────────────────
    async function fetchStatus() {
        try {
            const res  = await fetch('/status');
            const data = await res.json();

            // Camera badge
            const camBadge  = document.getElementById('cam-status-badge');
            const camStatus = data.camera || 'Unknown';
            if (camBadge) {
                if (camStatus === 'Connected' || camStatus === 'Local') {
                    camBadge.style.display = 'none';
                } else {
                    camBadge.style.display = 'inline-flex';
                    camBadge.textContent = camStatus === 'Connecting'
                        ? '📡 Connecting to Camera...'
                        : '⚠️ Camera Disconnected — Check IP & Wi-Fi';
                }
            }

            // Signal
            if (data.signal !== currentSignal) {
                const prevSig = currentSignal;
                currentSignal = data.signal;
                updateSignalUI(currentSignal);
                // Toast on signal change
                const sigMap = {
                    'Red':    { icon: '🔴', title: 'The signal is Red.',    theme: 'red'    },
                    'Yellow': { icon: '🟡', title: 'The signal is Yellow.',  theme: 'yellow' },
                    'Green':  { icon: '🟢', title: 'The signal is Green.',   theme: 'green'  },
                    'ERROR':  { icon: '⚠️', title: 'Signal error detected!', theme: 'red'    },
                };
                const n = sigMap[currentSignal];
                if (n) showNotification(n.icon, n.title, '', n.theme);
            }

            // Ambulance
            if (data.ambulance !== currentAmbulance) {
                updateAmbulanceUI(data.ambulance, data.mic_available, data.mic_status);
                if (data.ambulance) {
                    showNotification('🚨', 'Heard an Ambulance!', '', 'ambulance', 5000);
                } else {
                    showNotification('🔇', 'Ambulance siren cleared.', '', 'info');
                }
            } else {
                // Always refresh mic status even if ambulance flag unchanged
                if (micStatusText) {
                    if (data.mic_available) {
                        micDot.className = 'mic-dot active';
                        micStatusText.textContent = '🎤 Mic Active';
                    } else {
                        micDot.className = 'mic-dot error';
                        micStatusText.textContent = data.mic_status || 'Mic Unavailable';
                    }
                }
            }

            // ESP32 command
            if (data.command !== currentCommand || data.esp32_status !== espConnText.textContent) {
                updateESP32UI(data.command, data.esp32_status);
            }

        } catch (err) {
            console.error('Status fetch error:', err);
        }
    }

    setInterval(fetchStatus, 500);
    fetchStatus(); // immediate first call

    // ── Camera settings ──────────────────────────────────────
    updateCamBtn.addEventListener('click', async () => {
        const url = cameraIpInput.value.trim();
        updateCamBtn.innerText = 'Connecting...';
        try {
            const res  = await fetch('/set_camera', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const data = await res.json();
            if (data.status === 'success') {
                updateCamBtn.innerText = 'Connected ✓';
                videoStream.src = `/video_feed?t=${Date.now()}`;
            } else {
                updateCamBtn.innerText = 'Failed';
            }
        } catch (e) {
            console.error(e);
            updateCamBtn.innerText = 'Error';
        }
        setTimeout(() => updateCamBtn.innerText = '🔗 Connect Camera', 3000);
    });

    // ── Voice toggle ─────────────────────────────────────────
    toggleAudioBtn.addEventListener('click', () => {
        audioEnabled = !audioEnabled;
        if (audioEnabled) {
            toggleAudioBtn.classList.add('active');
            toggleAudioBtn.innerText = 'Voice ON';
            synth.cancel();
            const u = new SpeechSynthesisUtterance('Audio warnings enabled.');
            u.volume = 0;
            synth.speak(u);
        } else {
            toggleAudioBtn.classList.remove('active');
            toggleAudioBtn.innerText = 'Voice OFF';
            synth.cancel();
        }
    });
    toggleAudioBtn.classList.remove('active');
    toggleAudioBtn.innerText = 'Voice OFF';
    statusText.innerText = 'Detecting...';

    // ── Demo Toggle (ambulance) ──────────────────────────────
    demoToggleBtn.addEventListener('click', async () => {
        demoToggleBtn.disabled = true;
        try {
            const res  = await fetch('/toggle_ambulance', { method: 'POST' });
            const data = await res.json();
            updateAmbulanceUI(data.ambulance, true, 'Demo Mode');
            updateESP32UI(data.command, 'ok');
        } catch (e) {
            console.error('Demo toggle error:', e);
        }
        setTimeout(() => demoToggleBtn.disabled = false, 600);
    });

    // ── ESP32 manual override buttons ────────────────────────
    async function sendESP32Command(command) {
        try {
            const res  = await fetch('/control_esp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command })
            });
            const data = await res.json();
            updateESP32UI(command, data.status === 'ok' ? 'ok' : 'error');
        } catch (e) {
            console.error('ESP32 override error:', e);
        }
    }

    forceMoveBtn.addEventListener('click', () => sendESP32Command('MOVE'));
    forceStopBtn.addEventListener('click', () => sendESP32Command('STOP'));
    forceIdleBtn.addEventListener('click', () => sendESP32Command('IDLE'));

    // ── Set ESP32 IP ─────────────────────────────────────────
    setEspBtn.addEventListener('click', async () => {
        const ip = esp32IpInput.value.trim();
        if (!ip) return;
        setEspBtn.textContent = 'Saving...';
        try {
            const res  = await fetch('/set_esp32', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                setEspBtn.textContent = 'Saved ✓';
            } else {
                setEspBtn.textContent = 'Error';
            }
        } catch (e) {
            setEspBtn.textContent = 'Error';
        }
        setTimeout(() => setEspBtn.textContent = 'Set IP', 2500);
    });
});
