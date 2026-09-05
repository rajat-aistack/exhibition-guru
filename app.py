import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, jsonify, request, send_from_directory
from dotenv import load_dotenv

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

    # Override / populate sensitive settings from environment variables (.env locally or platform environment in deployment)
    email_cfg = config.get("email_config", {})

    email_cfg["smtp_server"] = os.environ.get("SMTP_SERVER", email_cfg.get("smtp_server", "smtp.gmail.com"))
    
    # Default to 465 for Gmail SSL reliability on cloud platforms like Render
    default_port = 465 if email_cfg.get("smtp_server", "smtp.gmail.com") == "smtp.gmail.com" else 587
    email_cfg["smtp_port"] = int(os.environ.get("SMTP_PORT", email_cfg.get("smtp_port", default_port)))
    
    email_cfg["sender_email"] = os.environ.get("SENDER_EMAIL") or os.environ.get("EMAIL_USER") or email_cfg.get("sender_email", "exhibitionguru4u@gmail.com")
    
    # Check SENDER_PASSWORD, GMAIL_APP_PASSWORD, APP_PASSWORD, or SMTP_PASSWORD
    env_password = (
        os.environ.get("SENDER_PASSWORD") or 
        os.environ.get("GMAIL_APP_PASSWORD") or 
        os.environ.get("APP_PASSWORD") or 
        os.environ.get("SMTP_PASSWORD")
    )
    email_cfg["sender_password"] = env_password if env_password is not None else email_cfg.get("sender_password", "")
    
    email_cfg["recipient_email"] = os.environ.get("RECIPIENT_EMAIL") or email_cfg.get("recipient_email", "marketing.exhibitionguru@gmail.com")

    enable_email_env = os.environ.get("ENABLE_EMAIL")
    if enable_email_env is not None:
        email_cfg["enable_email"] = enable_email_env.lower() in ("true", "1", "yes")
    elif "enable_email" not in email_cfg:
        email_cfg["enable_email"] = True

    config["email_config"] = email_cfg
    return config

def send_inquiry_email(inquiry_data, config):
    email_cfg = config.get("email_config", {})
    if not email_cfg.get("enable_email", True):
        print("[EMAIL] Auto email notification is disabled.")
        return False, "Disabled in environment configuration"

    smtp_server = email_cfg.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(email_cfg.get("smtp_port", 465))
    sender_email = email_cfg.get("sender_email", "exhibitionguru4u@gmail.com")
    sender_password = email_cfg.get("sender_password", "")
    recipient_email = email_cfg.get("recipient_email", "marketing.exhibitionguru@gmail.com")

    if not sender_password or sender_password == "YOUR_GMAIL_APP_PASSWORD":
        print("[EMAIL WARNING] Password is not set in environment or .env. Skipping email delivery.")
        return False, "Password environment variable not configured"

    name = inquiry_data.get("name", "N/A")
    phone = inquiry_data.get("phone", "N/A")
    email = inquiry_data.get("email", "N/A")
    requirements = inquiry_data.get("requirements", "N/A")

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

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        print(f"[EMAIL] Connecting to SMTP server {smtp_server} (Configured Port: {smtp_port})...")

        # For Gmail, SMTP_SSL on port 465 is required on cloud hosting providers like Render
        if smtp_server == "smtp.gmail.com" or int(smtp_port) == 465:
            try:
                print(f"[EMAIL] Attempting SMTP_SSL on port 465 for {sender_email}...")
                server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())
                server.quit()
                print("Success: Enquiry email sent successfully via SMTP_SSL (465)!")
                return True, "Success"
            except Exception as e_ssl:
                print(f"[EMAIL WARN] SMTP_SSL on 465 failed: {e_ssl}. Retrying with STARTTLS on port {smtp_port}...")

        # Fallback to standard SMTP with STARTTLS
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()

        print("Success: Enquiry email sent successfully!")
        return True, "Success"
    except Exception as e:
        print(f"Error: Something went wrong sending email... {e}")
        return False, str(e)

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
    except Exception as e:
        print(f"Error saving inquiry: {e}")

    # 2. Trigger auto email notification
    config = load_config()
    email_sent, email_msg = send_inquiry_email(data, config)

    return jsonify({
        "status": "success",
        "message": "Thank you! Your quote request has been received. Our exhibition design team will contact you within 2 hours.",
        "email_sent": email_sent,
        "email_note": email_msg
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[INFO] Exhibition Guru server starting on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
