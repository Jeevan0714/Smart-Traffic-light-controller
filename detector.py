import cv2
import numpy as np
import threading
import time
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

class TrafficSignalDetector:
    def __init__(self, camera_url=None):
        self.camera_url = camera_url
        self.cap = None
        self.connection_status = "Initializing"
        self.init_camera()
        
        self.current_state = "None"
        self.latest_frame = None
        self.stopped = False
        
        # Color boundaries
        self.red_lower1 = np.array([0, 100, 100])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([160, 100, 100])
        self.red_upper2 = np.array([180, 255, 255])
        
        self.yellow_lower = np.array([15, 100, 100])
        self.yellow_upper = np.array([35, 255, 255])
        
        self.green_lower = np.array([40, 50, 50])
        self.green_upper = np.array([90, 255, 255])
        
        # Start the background thread to constantly read frames
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True # Daemon thread exits when main program exits
        self.thread.start()

    def init_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        if self.camera_url:
            url = self.camera_url
            log.info(f"Connecting to IP Webcam: {url}")
            self.connection_status = "Connecting"
            # Use FFMPEG backend with reduced buffering for lower latency
            self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            # Set a short open timeout (in milliseconds) to fail fast if unreachable
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
            # Reduce internal buffer to 1 frame to avoid stale-frame lag
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if self.cap.isOpened():
                log.info("IP Webcam connected successfully.")
                self.connection_status = "Connected"
            else:
                log.error(f"Failed to connect to {url}. Will retry in background thread.")
                self.connection_status = "Disconnected"
        else:
            log.info("Using local webcam (device 0).")
            self.connection_status = "Local"
            self.cap = cv2.VideoCapture(0)

    def set_camera_url(self, url):
        self.camera_url = url
        self.connection_status = "Connecting"
        self.latest_frame = None  # Clear stale frame on camera change
        self.init_camera()

    def update(self):
        # Constantly pull the newest frame to avoid network buffer lag
        retry_delay = 2  # seconds before first retry
        while not self.stopped:
            if self.cap and self.cap.isOpened():
                success, frame = self.cap.read()
                if success:
                    # Immediately downscale to save bandwidth and processing power
                    self.latest_frame = cv2.resize(frame, (320, 240))
                    self.connection_status = "Connected"
                    retry_delay = 2  # reset backoff on success
                else:
                    # Read failed — camera may have dropped
                    log.warning("Frame read failed. Camera may have disconnected.")
                    self.connection_status = "Disconnected"
                    self.latest_frame = None
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 30)  # exponential backoff, max 30s
                    if self.camera_url:  # only auto-reconnect for IP cameras
                        log.info(f"Attempting to reconnect to {self.camera_url}...")
                        self.init_camera()
            else:
                self.connection_status = "Disconnected"
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)
                if self.camera_url:
                    log.info(f"Camera not open. Retrying connection to {self.camera_url}...")
                    self.init_camera()

    def detect_color(self, frame):
        # Process on the smaller frame size
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        mask_red1 = cv2.inRange(hsv, self.red_lower1, self.red_upper1)
        mask_red2 = cv2.inRange(hsv, self.red_lower2, self.red_upper2)
        mask_red = cv2.add(mask_red1, mask_red2)
        
        mask_yellow = cv2.inRange(hsv, self.yellow_lower, self.yellow_upper)
        mask_green = cv2.inRange(hsv, self.green_lower, self.green_upper)
        
        colors = {
            "Red": self.get_max_contour_area(mask_red),
            "Yellow": self.get_max_contour_area(mask_yellow),
            "Green": self.get_max_contour_area(mask_green)
        }
        
        min_area_threshold = 500
        
        # Collect ALL colors that pass the minimum area check
        active_colors = [color for color, area in colors.items() if area > min_area_threshold]
        
        if len(active_colors) > 1:
            # Multiple signals visible at once — this is a malfunction
            detected = "ERROR"
        elif len(active_colors) == 1:
            detected = active_colors[0]
        else:
            detected = "None"
                
        self.current_state = detected
        return detected, colors

    def get_max_contour_area(self, mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0
        max_contour = max(contours, key=cv2.contourArea)
        return cv2.contourArea(max_contour)

    def draw_status(self, frame, status):
        color_map = {
            "Red":    (0, 0, 255),
            "Yellow": (0, 255, 255),
            "Green":  (0, 255, 0),
            "ERROR":  (0, 0, 200),   # Bright red-orange for error
            "None":   (255, 255, 255)
        }
        text_color = color_map.get(status, (255, 255, 255))
        label = f"Signal: {status}" if status != "ERROR" else "⚠ ERROR: Multiple Signals!"
        cv2.putText(frame, label, (10, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, text_color, 2)
        return frame

    def generate_frames(self):
        while True:
            if self.latest_frame is None:
                time.sleep(0.1) # Wait for camera to initialize and grab first frame
                continue
                
            # Copy to prevent modification during processing
            frame = self.latest_frame.copy()
            
            # Detect
            status, _ = self.detect_color(frame)
            
            # Annotate
            frame = self.draw_status(frame, status)
            
            # Compress JPEG quality to reduce network latency (50% quality)
            # Aggressive compression (30% quality) for lowest possible latency
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 30])
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Limit the yield rate to 30 FPS to save server CPU
            time.sleep(1/30.0)

    def close(self):
        self.stopped = True
        self.thread.join(timeout=1)
        if self.cap:
            self.cap.release()
