import threading
import time
import logging

log = logging.getLogger(__name__)

# Try importing pyaudio — gracefully degrade if not installed
try:
    import pyaudio
    import numpy as np
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    log.warning("pyaudio/numpy not available. Mic detection disabled. Use demo toggle.")


class AmbulanceSoundDetector:
    """
    Real-time ambulance siren detector using laptop microphone.
    Uses FFT to measure energy ratio in the siren frequency band (700–2500 Hz).
    Falls back gracefully if no mic or pyaudio is unavailable.
    """

    RATE          = 44100   # Sample rate (Hz)
    CHUNK         = 2048    # Samples per read
    SIREN_LOW     = 700     # Siren band lower bound (Hz)
    SIREN_HIGH    = 2500    # Siren band upper bound (Hz)
    ENERGY_RATIO  = 0.30    # 30% of total energy must be in siren band
    SILENCE_FLOOR = 300     # Minimum RMS to bother processing (ignore silence)
    HOLD_SECONDS  = 3.0     # Keep detected=True for 3s after siren disappears

    def __init__(self):
        self.ambulance_detected: bool = False
        self.mic_available: bool = False
        self.mic_status: str = "Initializing"

        self._last_detected_time: float = 0.0
        self._stopped: bool = False

        # Start background mic thread
        self._thread = threading.Thread(target=self._run, daemon=True, name="SoundDetector")
        self._thread.start()

    # ------------------------------------------------------------------
    # Background thread — continuously reads mic and analyses audio
    # ------------------------------------------------------------------
    def _run(self):
        if not PYAUDIO_AVAILABLE:
            self.mic_status = "No pyaudio — use demo toggle"
            log.warning("Mic detection disabled (pyaudio missing).")
            return

        try:
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )
            self.mic_available = True
            self.mic_status = "Listening"
            log.info("🎤 Mic initialised — listening for ambulance siren...")

            while not self._stopped:
                try:
                    raw = stream.read(self.CHUNK, exception_on_overflow=False)
                except OSError:
                    # Input overflow — skip chunk
                    continue

                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)

                # Skip silence
                rms = np.sqrt(np.mean(samples ** 2))
                if rms < self.SILENCE_FLOOR:
                    self._tick_hold()
                    continue

                # FFT frequency analysis
                fft_mag  = np.abs(np.fft.rfft(samples))
                freqs    = np.fft.rfftfreq(self.CHUNK, d=1.0 / self.RATE)

                total_energy = np.sum(fft_mag)
                if total_energy == 0:
                    self._tick_hold()
                    continue

                siren_mask   = (freqs >= self.SIREN_LOW) & (freqs <= self.SIREN_HIGH)
                siren_energy = np.sum(fft_mag[siren_mask])
                ratio        = siren_energy / total_energy

                if ratio >= self.ENERGY_RATIO:
                    if not self.ambulance_detected:
                        log.info(f"🚨 AMBULANCE SIREN DETECTED  (band ratio={ratio:.2f})")
                    self.ambulance_detected = True
                    self._last_detected_time = time.time()
                else:
                    self._tick_hold()

        except Exception as e:
            self.mic_status = f"Error: {e}"
            self.mic_available = False
            log.error(f"Sound detector error: {e}")
        finally:
            try:
                stream.stop_stream()
                stream.close()
                pa.terminate()
            except Exception:
                pass

    def _tick_hold(self):
        """Clear detection flag after hold window expires."""
        if self.ambulance_detected:
            elapsed = time.time() - self._last_detected_time
            if elapsed > self.HOLD_SECONDS:
                self.ambulance_detected = False
                log.info("✅ Siren no longer detected — clearing flag")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def manual_toggle(self) -> bool:
        """Toggle ambulance_detected manually (for demo / hackathon testing)."""
        self.ambulance_detected = not self.ambulance_detected
        if self.ambulance_detected:
            self._last_detected_time = time.time() + 3600  # hold 1 hour until toggled off
            log.info("🚨 [DEMO] Ambulance manually ACTIVATED")
        else:
            log.info("✅ [DEMO] Ambulance manually DEACTIVATED")
        return self.ambulance_detected

    def stop(self):
        self._stopped = True
