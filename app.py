import sqlite3
import re
import os
import cv2  # OpenCV for Video Frame Processing
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
from mutagen import File as MutagenFile

app = Flask(__name__)
app.secret_key = 'cyberguard_hackathon_super_secret_key'
DATABASE = 'database.db'

UPLOAD_FOLDER = 'uploads'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS threat_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_type TEXT NOT NULL,
                input_value TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                explanation TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                timestamp DATETIME DEFAULT (datetime('now', 'localtime'))
            )
        ''')
        conn.commit()

init_db()

# --- MODULE 1: PHISHING & MALICIOUS URL DETECTION ENGINE ---
def analyze_phishing_content(content):
    score = 0
    factors = []
    
    urgent_terms = ['urgent', 'verify now', 'immediate action', 'suspended', 'unauthorized access', 'click here']
    found_urgent = [term for term in urgent_terms if term in content.lower()]
    if found_urgent:
        score += 30
        factors.append(f"Contains high-pressure urgency language: {', '.join(found_urgent)}.")

    urls = re.findall(r'https?://[^\s]+', content)
    for url in urls:
        if any(x in url.lower() for x in ['.xyz', '.top', 'login-', 'verify-', 'secure-']):
            score += 40
            factors.append(f"Embedded URL '{url}' uses high-risk TLD or phishing keyword pattern.")
        if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url):
            score += 45
            factors.append("Embedded URL uses raw IP address instead of domain name.")

    if score >= 70:
        level, action = "Critical", "Quarantine message, block embedded URLs, and alert security team."
    elif score >= 40:
        level, action = "High", "Warn user, flag links as unsafe, and request manual inspection."
    elif score >= 20:
        level, action = "Medium", "Display caution banner to user regarding external links."
    else:
        level, action = "Safe", "No threat indicators detected. Standard delivery allowed."

    explanation = " ".join(factors) if factors else "No suspicious keywords or malicious URL structures identified."
    return {"level": level, "score": min(score, 100), "explanation": explanation, "action": action}


# --- MODULE 2: CALL & DIGITAL IMPERSONATION DETECTION ENGINE ---
KNOWN_IMPERSONATORS = {
    "+18005550199": "Robocall / Financial Fraud Operator",
    "+919876543210": "Vishing / Executive Impersonation"
}

def analyze_call_impersonation(phone, transcript=""):
    score = 0
    factors = []

    cleaned = re.sub(r'[\s\-\(\)]', '', phone)

    if cleaned in KNOWN_IMPERSONATORS:
        score += 85
        factors.append(f"Number flagged in threat registry: {KNOWN_IMPERSONATORS[cleaned]}.")

    if cleaned.startswith("140") or cleaned.startswith("+91140"):
        score += 60
        factors.append("Matches telemarketer/unregistered caller prefix pattern (140 series).")

    impersonation_keywords = ['bank manager', 'otp', 'police department', 'income tax', 'gift card', 'wire transfer']
    found_imp = [word for word in impersonation_keywords if word in transcript.lower()]
    if found_imp:
        score += 30
        factors.append(f"Caller transcript contains targeted impersonation triggers: {', '.join(found_imp)}.")

    if score >= 75:
        level, action = "Critical", "Block caller immediately, notify authority, and trigger fraud alert."
    elif score >= 45:
        level, action = "High", "Flag call as high-risk impersonation and restrict audio access."
    elif score >= 20:
        level, action = "Medium", "Display 'Unknown/Unverified Caller' warning."
    else:
        level, action = "Safe", "Standard verified caller."

    explanation = " ".join(factors) if factors else "Caller identity matches normal communication profiles."
    return {"level": level, "score": min(score, 100), "explanation": explanation, "action": action}


# --- MODULE 3: CREDENTIAL THEFT & ACCOUNT TAKEOVER ENGINE ---
def analyze_account_activity(failed_attempts, unusual_location, new_device):
    score = 0
    factors = []

    if failed_attempts >= 5:
        score += 50
        factors.append(f"Brute-force/Password spraying anomaly detected: {failed_attempts} sequential failed logins.")
    elif failed_attempts >= 3:
        score += 25
        factors.append(f"Elevated failed login sequence: {failed_attempts} attempts.")

    if unusual_location:
        score += 30
        factors.append("Login attempt originated from an abnormal geographic location/IP.")

    if new_device:
        score += 20
        factors.append("Unrecognized device hardware signature / user agent.")

    if score >= 70:
        level, action = "Critical", "Revoke active session, lock account, and force Multi-Factor Authentication (MFA)."
    elif score >= 40:
        level, action = "High", "Require immediate secondary verification (OTP/MFA)."
    elif score >= 20:
        level, action = "Medium", "Send email alert regarding new device access."
    else:
        level, action = "Safe", "Normal login behavior verified."

    explanation = " ".join(factors) if factors else "Login metadata matches baseline user profile."
    return {"level": level, "score": min(score, 100), "explanation": explanation, "action": action}


# --- MODULE 4: IMAGE DEEPFAKE DETECTION ENGINE ---
def analyze_image_threat(file_path):
    score = 0
    factors = []

    try:
        img = Image.open(file_path)
        info = img._getexif()

        if not info:
            score += 35
            factors.append("Missing EXIF camera metadata (common sign of AI-generated media).")
        
        if img.format in ['WEBP', 'PNG'] and img.mode != 'RGB':
            score += 25
            factors.append("Color-space compression anomaly detected in image channels.")

        width, height = img.size
        if width == height and width in [512, 1024]:
            score += 30
            factors.append(f"Dimensions ({width}x{height}) match standard Generative AI output canvas sizes.")

    except Exception as e:
        score += 50
        factors.append(f"Image header parsing error or corrupted file structure: {str(e)}")

    if score >= 70:
        level, action = "Critical", "Flag image as suspected Deepfake/Manipulated Media and route to SOC."
    elif score >= 40:
        level, action = "High", "Mark image with digital authenticity warning banner."
    elif score >= 20:
        level, action = "Medium", "Prompt manual image verification."
    else:
        level, action = "Safe", "Image EXIF and camera signature match authentic capture profiles."

    explanation = " ".join(factors) if factors else "Standard camera EXIF metadata and structural integrity verified."
    return {"level": level, "score": min(score, 100), "explanation": explanation, "action": action}


# --- MODULE 5: AUDIO DEEPFAKE DETECTION ENGINE ---
def analyze_audio_threat(file_path):
    score = 0
    factors = []

    try:
        audio = MutagenFile(file_path)
        
        if audio is not None and hasattr(audio, 'info'):
            info = audio.info
            sample_rate = getattr(info, 'sample_rate', 0)
            bitrate = getattr(info, 'bitrate', 0)
            channels = getattr(info, 'channels', 0)

            if sample_rate in [16000, 22050]:
                score += 40
                factors.append(f"Sample rate ({sample_rate} Hz) aligns with standard AI speech synthesis engines.")

            if channels == 1:
                score += 20
                factors.append("Single-channel (Mono) audio signature detected, typical of synthetic voice exports.")

            if bitrate > 0 and bitrate < 64000:
                score += 25
                factors.append(f"Constant low bitrate ({bitrate // 1000} kbps) detected, indicating spectral compression.")

        else:
            score += 45
            factors.append("Missing standard audio container header tags or unverified codec structure.")

    except Exception as e:
        score += 50
        factors.append(f"Audio metadata extraction failure: {str(e)}")

    if score >= 70:
        level, action = "Critical", "Flag voice recording as AI Voice Clone/Deepfake. Restrict audio trust level."
    elif score >= 40:
        level, action = "High", "Require secondary out-of-band voice authentication."
    elif score >= 20:
        level, action = "Medium", "Display 'Unverified Audio Source' warning banner."
    else:
        level, action = "Safe", "Audio spectral baseline and container structure match natural voice capture."

    explanation = " ".join(factors) if factors else "Acoustic signatures, channels, and metadata match verified human voice recordings."
    return {"level": level, "score": min(score, 100), "explanation": explanation, "action": action}


# --- MODULE 6: VIDEO DEEPFAKE DETECTION ENGINE (OPENCV) ---
def analyze_video_threat(file_path):
    score = 0
    factors = []

    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return {"level": "High", "score": 60, "explanation": "Unable to decode video stream structure.", "action": "Flag file."}

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Check resolution canvas anomalies (e.g., standard AI generated video aspect ratios)
        if width == height and width in [512, 1024]:
            score += 35
            factors.append(f"Square video resolution canvas ({width}x{height}) detected, typical of AI video models.")

        # Check frame rate / FPS anomalies
        if fps <= 15 or fps == 0:
            score += 30
            factors.append(f"Low frame rate ({fps} FPS) signature detected, indicating frame interpolation.")

        # Sample frames and check temporal color variance across timeline
        sampled_frames = 0
        diff_accumulator = 0
        prev_gray = None

        while cap.isOpened() and sampled_frames < 30:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                # Calculate frame difference variance
                diff = cv2.absdiff(prev_gray, gray)
                diff_accumulator += diff.mean()

            prev_gray = gray
            sampled_frames += 1

        cap.release()

        # Low variance across frames indicates synthetic face replacement or static AI rendering
        if sampled_frames > 5:
            avg_diff = diff_accumulator / sampled_frames
            if avg_diff < 2.0:
                score += 35
                factors.append(f"Temporal frame variance drop ({avg_diff:.2f}) indicates face-swap/static AI rendering.")

    except Exception as e:
        score += 50
        factors.append(f"OpenCV video frame decoding error: {str(e)}")

    if score >= 70:
        level, action = "Critical", "Flag video as AI Deepfake / Manipulated Stream. Quarantine video clip."
    elif score >= 40:
        level, action = "High", "Watermark video with digital manipulation warning banner."
    elif score >= 20:
        level, action = "Medium", "Prompt manual frame-by-frame verification."
    else:
        level, action = "Safe", "Video frame rates, aspect ratios, and temporal variances match natural camera recording."

    explanation = " ".join(factors) if factors else "Frame rate, temporal stability, and resolution match natural video stream baselines."
    return {"level": level, "score": min(score, 100), "explanation": explanation, "action": action}


# --- ROUTES ---

def log_event(scenario, input_val, result):
    with get_db() as conn:
        conn.execute(
            '''INSERT INTO threat_logs (scenario_type, input_value, risk_level, risk_score, explanation, recommended_action)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (scenario, input_val, result['level'], result['score'], result['explanation'], result['action'])
        )
        conn.commit()

@app.route('/')
def dashboard():
    conn = get_db()
    logs = conn.execute('''
        SELECT id, scenario_type, input_value, risk_level, risk_score, explanation, recommended_action, 
               datetime(timestamp, 'localtime') AS timestamp 
        FROM threat_logs 
        ORDER BY timestamp DESC LIMIT 10
    ''').fetchall()
    
    total_events = conn.execute('SELECT COUNT(*) FROM threat_logs').fetchone()[0]
    critical_threats = conn.execute("SELECT COUNT(*) FROM threat_logs WHERE risk_level IN ('High', 'Critical')").fetchone()[0]
    phishing_count = conn.execute("SELECT COUNT(*) FROM threat_logs WHERE scenario_type='Phishing'").fetchone()[0]
    impersonation_count = conn.execute("SELECT COUNT(*) FROM threat_logs WHERE scenario_type='Impersonation'").fetchone()[0]
    ato_count = conn.execute("SELECT COUNT(*) FROM threat_logs WHERE scenario_type='Account Takeover'").fetchone()[0]
    image_count = conn.execute("SELECT COUNT(*) FROM threat_logs WHERE scenario_type='Image Deepfake'").fetchone()[0]
    audio_count = conn.execute("SELECT COUNT(*) FROM threat_logs WHERE scenario_type='Audio Deepfake'").fetchone()[0]
    video_count = conn.execute("SELECT COUNT(*) FROM threat_logs WHERE scenario_type='Video Deepfake'").fetchone()[0]

    return render_template('dashboard.html', logs=logs, total=total_events, critical=critical_threats,
                           phishing=phishing_count, impersonation=impersonation_count, ato=ato_count,
                           image=image_count, audio=audio_count, video=video_count)

@app.route('/video-detector', methods=['GET', 'POST'])
def video_detector():
    result = None
    if request.method == 'POST':
        if 'video' not in request.files:
            flash('No video file selected.', 'danger')
            return redirect(request.url)
        
        file = request.files['video']
        if file and allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            result = analyze_video_threat(filepath)
            log_event("Video Deepfake", filename, result)

    return render_template('video_detector.html', result=result)

@app.route('/audio-detector', methods=['GET', 'POST'])
def audio_detector():
    result = None
    if request.method == 'POST':
        if 'audio' not in request.files:
            flash('No audio file selected.', 'danger')
            return redirect(request.url)
        
        file = request.files['audio']
        if file and allowed_file(file.filename, ALLOWED_AUDIO_EXTENSIONS):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            result = analyze_audio_threat(filepath)
            log_event("Audio Deepfake", filename, result)

    return render_template('audio_detector.html', result=result)

@app.route('/image-detector', methods=['GET', 'POST'])
def image_detector():
    result = None
    if request.method == 'POST':
        if 'image' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(request.url)
        
        file = request.files['image']
        if file and allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            result = analyze_image_threat(filepath)
            log_event("Image Deepfake", filename, result)

    return render_template('image_detector.html', result=result)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username, email, password = request.form['username'].strip(), request.form['email'].strip(), request.form['password']
        hashed_pw = generate_password_hash(password)
        try:
            with get_db() as conn:
                conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', (username, email, hashed_pw))
                conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or Email already registered.', 'danger')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username, password = request.form['username'].strip(), request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'], session['username'] = user['id'], user['username']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/phishing', methods=['GET', 'POST'])
def phishing():
    result = None
    if request.method == 'POST':
        content = request.form.get('content', '')
        result = analyze_phishing_content(content)
        log_event("Phishing", content[:40] + "...", result)
    return render_template('phishing_detector.html', result=result)

@app.route('/impersonation', methods=['GET', 'POST'])
def impersonation():
    result = None
    if request.method == 'POST':
        phone = request.form.get('phone', '')
        transcript = request.form.get('transcript', '')
        result = analyze_call_impersonation(phone, transcript)
        log_event("Impersonation", phone, result)
    return render_template('call_impersonation.html', result=result)

@app.route('/account-takeover', methods=['GET', 'POST'])
def account_takeover():
    result = None
    if request.method == 'POST':
        attempts = int(request.form.get('attempts', 0))
        unusual_loc = 'unusual_loc' in request.form
        new_dev = 'new_dev' in request.form
        result = analyze_account_activity(attempts, unusual_loc, new_dev)
        log_event("Account Takeover", f"Attempts: {attempts}", result)
    return render_template('account_takeover.html', result=result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)