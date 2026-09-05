import os
import sys
import json
import logging
import smtplib
import socket
import threading
import urllib.request
import urllib.error
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, jsonify, request, send_from_directory
from dotenv import load_dotenv

# Force unbuffered stdout so all print & logging statements appear instantly in Render logs
os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted = f"[{timestamp}] [{level}] {msg}"
    try:
        print(formatted, flush=True)
    except UnicodeEncodeError:
        # Fallback for Windows CP1252 terminal encoding limits
        print(formatted.encode('ascii', errors='replace').decode('ascii'), flush=True)
    try:
        sys.stdout.flush()
    except Exception:
        pass

# Helper to force IPv4 DNS resolution for cloud hosting environments (e.g. Render) without IPv6 egress
class force_ipv4:
    def __enter__(self):
        self.old_getaddrinfo = socket.getaddrinfo
        def allowed_gai(*args, **kwargs):
            responses = self.old_getaddrinfo(*args, **kwargs)
            v4_responses = [r for r in responses if r[0] == socket.AF_INET]
            return v4_responses if v4_responses else responses
        socket.getaddrinfo = allowed_gai

    def __exit__(self, exc_type, exc_val, exc_tb):
        socket.getaddrinfo = self.old_getaddrinfo

# Load environment variables from .env file for local development
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'exhibition_guru_default_secret_key_2026')

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
INQUIRIES_FILE = os.path.join(os.path.dirname(__file__), 'inquiries.json')

def load_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error reading config.json: {e}")

    email_cfg = config.get("email_config", {})

    smtp_server = os.environ.get("SMTP_SERVER", email_cfg.get("smtp_server", "smtp.gmail.com")).strip()
    email_cfg["smtp_server"] = smtp_server
    
    default_port = 465 if smtp_server == "smtp.gmail.com" else 587
    smtp_port_val = str(os.environ.get("SMTP_PORT", email_cfg.get("smtp_port", default_port))).strip()
    email_cfg["smtp_port"] = int(smtp_port_val) if smtp_port_val.isdigit() else default_port
    
    sender_email = (os.environ.get("SENDER_EMAIL") or os.environ.get("EMAIL_USER") or email_cfg.get("sender_email", "exhibitionguru4u@gmail.com")).strip()
    email_cfg["sender_email"] = sender_email
    
    # Check SENDER_PASSWORD, GMAIL_APP_PASSWORD, APP_PASSWORD, or SMTP_PASSWORD
    env_password = (
        os.environ.get("SENDER_PASSWORD") or 
        os.environ.get("GMAIL_APP_PASSWORD") or 
        os.environ.get("APP_PASSWORD") or 
        os.environ.get("SMTP_PASSWORD")
    )
    if env_password:
        email_cfg["sender_password"] = env_password.strip()
    else:
        email_cfg["sender_password"] = str(email_cfg.get("sender_password", "")).strip()
    
    recipient_email = (os.environ.get("RECIPIENT_EMAIL") or email_cfg.get("recipient_email", "marketing.exhibitionguru@gmail.com")).strip()
    email_cfg["recipient_email"] = recipient_email

    enable_email_env = os.environ.get("ENABLE_EMAIL")
    if enable_email_env is not None:
        email_cfg["enable_email"] = enable_email_env.strip().lower() in ("true", "1", "yes")
    elif "enable_email" not in email_cfg:
        email_cfg["enable_email"] = True

    config["email_config"] = email_cfg
    return config

import urllib.request
import urllib.error

def send_via_resend(name, phone, email, requirements, recipient, resend_key):
    url = "https://api.resend.com/emails"
    from_address = os.environ.get("RESEND_FROM_EMAIL", "Exhibition Guru <onboarding@resend.dev>").strip()
    resend_to = os.environ.get("RESEND_TO_EMAIL", recipient).strip()

    log(f"📤 [RESEND SEND] Initiating API request to https://api.resend.com/emails", "INFO")
    log(f"   Payload -> From: '{from_address}' | To: ['{resend_to}'] | Subject: 'NEW EXHIBITION ENQUIRY: {name}'", "INFO")

    headers = {
        "Authorization": f"Bearer {resend_key}",
        "Content-Type": "application/json",
        "User-Agent": "ExhibitionGuruApp/1.0"
    }
    payload = {
        "from": from_address,
        "to": [resend_to],
        "subject": f"NEW EXHIBITION ENQUIRY: {name}",
        "html": f"""
        <h3>New Exhibition Stall Inquiry Received!</h3>
        <p><strong>Client Name:</strong> {name}</p>
        <p><strong>Phone:</strong> {phone}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Requirements:</strong><br>{requirements}</p>
        <hr>
        <p><small>Sent from Exhibition Guru Web App on Render</small></p>
        """
    }
    try:
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            response_body = resp.read().decode('utf-8')
            log(f"✅ [RESEND SUCCESS] HTTP {resp.status} OK - Email delivered to {resend_to}. Response: {response_body}", "SUCCESS")
            return True, f"Success via Resend HTTPS API (to {resend_to})"
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')
        log(f"⚠️ [RESEND HTTP ERROR] Status {e.code}: {e.reason} - Payload: {err_body}", "WARN")
        
        # If using onboarding domain and received validation error, try sending to registered account email
        if "onboarding@resend.dev" in from_address and "validation_error" in err_body:
            alt_to = os.environ.get("RESEND_FALLBACK_TO", "rajat.aistack@gmail.com").strip()
            if alt_to and alt_to != resend_to:
                log(f"🔄 [RESEND RETRY] Sandbox restricted delivery to registered email. Retrying with fallback target: {alt_to}", "INFO")
                payload["to"] = [alt_to]
                try:
                    data_bytes = json.dumps(payload).encode('utf-8')
                    req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        resp_body = resp.read().decode('utf-8')
                        log(f"✅ [RESEND RETRY SUCCESS] HTTP {resp.status} OK - Email delivered to fallback address {alt_to}. Response: {resp_body}", "SUCCESS")
                        return True, f"Success via Resend HTTPS API (to fallback {alt_to})"
                except Exception as retry_err:
                    log(f"❌ [RESEND RETRY ERROR] Failed sending to fallback address: {retry_err}", "ERROR")

        return False, f"Resend API error HTTP {e.code}: {err_body}"
    except Exception as e:
        log(f"❌ [RESEND EXCEPTION] {e}", "ERROR")
        return False, str(e)

def send_via_brevo(name, phone, email, requirements, sender_email, recipient, brevo_key):
    url = "https://api.brevo.com/v3/smtp/email"
    log(f"📤 [BREVO SEND] Initiating API request to https://api.brevo.com/v3/smtp/email", "INFO")
    log(f"   Payload -> Sender: '{sender_email}' | To: ['{recipient}']", "INFO")

    headers = {
        "api-key": brevo_key,
        "Content-Type": "application/json",
        "User-Agent": "ExhibitionGuruApp/1.0"
    }
    payload = {
        "sender": {"name": "Exhibition Guru", "email": sender_email},
        "to": [{"email": recipient}],
        "subject": f"NEW EXHIBITION ENQUIRY: {name}",
        "textContent": f"New Exhibition Stall Inquiry Received!\n\nClient Name: {name}\nPhone: {phone}\nEmail: {email}\nRequirements:\n{requirements}"
    }
    try:
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            response_body = resp.read().decode('utf-8')
            log(f"✅ [BREVO SUCCESS] HTTP {resp.status} OK - Response: {response_body}", "SUCCESS")
            return True, "Success via Brevo HTTPS API"
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')
        log(f"❌ [BREVO HTTP ERROR] Status {e.code}: {e.reason} - Payload: {err_body}", "ERROR")
        return False, f"Brevo API error HTTP {e.code}: {err_body}"
    except Exception as e:
        log(f"❌ [BREVO EXCEPTION] {e}", "ERROR")
        return False, str(e)

def send_inquiry_email(inquiry_data, config):
    email_cfg = config.get("email_config", {})
    if not email_cfg.get("enable_email", True):
        log("⏸️ [EMAIL DISABLED] Auto email notification is disabled in configuration.", "WARN")
        return False, "Disabled in environment configuration"

    name = inquiry_data.get("name", "N/A")
    phone = inquiry_data.get("phone", "N/A")
    email = inquiry_data.get("email", "N/A")
    requirements = inquiry_data.get("requirements", "N/A")

    recipient_email = email_cfg.get("recipient_email", "marketing.exhibitionguru@gmail.com").strip()
    sender_email = email_cfg.get("sender_email", "exhibitionguru4u@gmail.com").strip()

    log(f"✉️ [EMAIL TASK START] Preparing notification for client '{name}' (Phone: {phone}, Email: {email})", "INFO")

    # 1. Check for RESEND_API_KEY (HTTPS Port 443 - Never blocked on Render)
    resend_key = os.environ.get("RESEND_API_KEY")
    if resend_key and resend_key.strip():
        log("🌐 [EMAIL PROVIDER] Using Resend HTTPS API (Port 443)...", "INFO")
        success, msg = send_via_resend(name, phone, email, requirements, recipient_email, resend_key.strip())
        if success:
            return True, msg

    # 2. Check for BREVO_API_KEY (HTTPS Port 443 - Never blocked on Render)
    brevo_key = os.environ.get("BREVO_API_KEY")
    if brevo_key and brevo_key.strip():
        log("🌐 [EMAIL PROVIDER] Using Brevo HTTPS API (Port 443)...", "INFO")
        success, msg = send_via_brevo(name, phone, email, requirements, sender_email, recipient_email, brevo_key.strip())
        if success:
            return True, msg

    # 3. Fallback to Direct Gmail SMTP (try multiple ports; Render may block some)
    smtp_server = email_cfg.get("smtp_server", "smtp.gmail.com").strip()
    sender_password = email_cfg.get("sender_password", "").strip()

    log(f"🔌 [SMTP FALLBACK] Attempting direct Gmail SMTP | Sender: '{sender_email}' | Recipient: '{recipient_email}' | Server: '{smtp_server}'", "INFO")

    if not sender_password or sender_password == "YOUR_GMAIL_APP_PASSWORD":
        log("⚠️ [SMTP WARNING] Password is empty or not set in environment. Skipping SMTP delivery.", "WARN")
        return False, "Password environment variable not configured"

    subject = f"NEW EXHIBITION ENQUIRY: {name}"
    body = f"""New Exhibition Stall Inquiry Received!

--------------------------------------------------
Client Name : {name}
Phone       : {phone}
Email       : {email}
Requirements:
{requirements}
--------------------------------------------------

Received At: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}
Website    : Exhibition Guru Web App
"""

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Force IPv4 socket resolution to prevent Render IPv6 network unreachable errors
    with force_ipv4():
        # Attempt 1: STARTTLS on port 587
        try:
            log(f"   [SMTP Attempt 1] STARTTLS on port 587 to {smtp_server} (forcing IPv4)...", "INFO")
            server = smtplib.SMTP(smtp_server, 587, timeout=8)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            server.quit()
            log("✅ [SMTP SUCCESS] Sent via STARTTLS port 587!", "SUCCESS")
            return True, "Success via STARTTLS 587"
        except Exception as e1:
            log(f"⚠️ [SMTP WARN] Port 587 failed: {e1}", "WARN")

        # Attempt 2: SMTP_SSL on port 465
        try:
            log(f"   [SMTP Attempt 2] SMTP_SSL on port 465 to {smtp_server} (forcing IPv4)...", "INFO")
            server = smtplib.SMTP_SSL(smtp_server, 465, timeout=8)
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            server.quit()
            log("✅ [SMTP SUCCESS] Sent via SMTP_SSL port 465!", "SUCCESS")
            return True, "Success via SSL 465"
        except Exception as e2:
            log(f"⚠️ [SMTP WARN] Port 465 failed: {e2}", "WARN")

        # Attempt 3: Plain SMTP on port 25 (last resort)
        try:
            log(f"   [SMTP Attempt 3] Plain SMTP on port 25 to {smtp_server} (forcing IPv4)...", "INFO")
            server = smtplib.SMTP(smtp_server, 25, timeout=8)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            server.quit()
            log("✅ [SMTP SUCCESS] Sent via port 25!", "SUCCESS")
            return True, "Success via port 25"
        except Exception as e3:
            log(f"⚠️ [SMTP WARN] Port 25 failed: {e3}", "WARN")

    log("❌ [EMAIL ERROR] All SMTP ports (587, 465, 25) are blocked on Render. Ensure RESEND_API_KEY is configured.", "ERROR")
    return False, "All SMTP ports blocked by hosting provider. Add RESEND_API_KEY or BREVO_API_KEY env variable."

@app.route('/')
def index():
    config = load_config()
    return render_template('index.html', config=config)

@app.route('/api/config', methods=['GET'])
def get_config():
    config = load_config()
    return jsonify(config)

@app.route('/api/quote', methods=['POST'])
def handle_quote():
    data = request.get_json() or request.form.to_dict()
    data['timestamp'] = datetime.now().isoformat()
    
    log(f"📥 [QUOTE API CALL] Received inquiry submission from '{data.get('name', 'Unknown')}' | Phone: '{data.get('phone', 'N/A')}' | Email: '{data.get('email', 'N/A')}'", "INFO")

    # 1. Save inquiry locally in inquiries.json
    inquiries = []
    if os.path.exists(INQUIRIES_FILE):
        try:
            with open(INQUIRIES_FILE, 'r', encoding='utf-8') as f:
                inquiries = json.load(f)
        except Exception:
            inquiries = []
            
    inquiries.append(data)
    
    try:
        with open(INQUIRIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(inquiries, f, indent=2)
        log(f"💾 [INQUIRY STORED] Successfully appended inquiry to inquiries.json (Total entries: {len(inquiries)})", "INFO")
    except Exception as e:
        log(f"❌ [STORAGE ERROR] Failed writing to inquiries.json: {e}", "ERROR")

    # 2. Trigger auto email notification in background thread
    config = load_config()
    def _send_email_bg():
        try:
            success, msg = send_inquiry_email(data, config)
            log(f"🏁 [EMAIL THREAD COMPLETE] Email delivery result -> success={success}, details='{msg}'", "INFO" if success else "WARN")
        except Exception as e:
            log(f"❌ [EMAIL THREAD EXCEPTION] Unhandled error in background thread: {e}", "ERROR")
    
    email_thread = threading.Thread(target=_send_email_bg, daemon=True)
    email_thread.start()
    log("🧵 [EMAIL THREAD LAUNCHED] Background thread spawned for non-blocking email delivery", "INFO")

    return jsonify({
        "status": "success",
        "message": "Thank you! Your quote request has been received. Our exhibition design team will contact you within 2 hours.",
        "email_sent": True,
        "email_note": "Email notification queued"
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    log(f"🚀 Exhibition Guru server starting on http://127.0.0.1:{port}", "INFO")
    app.run(host='0.0.0.0', port=port, debug=True)
