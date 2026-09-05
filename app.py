import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='templates')

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
INQUIRIES_FILE = os.path.join(os.path.dirname(__file__), 'inquiries.json')

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading config.json: {e}")
    return {}

def send_inquiry_email(inquiry_data, config):
    email_cfg = config.get("email_config", {})
    if not email_cfg.get("enable_email", True):
        print("[EMAIL] Auto email notification is disabled in config.json")
        return False, "Disabled in config"

    smtp_server = email_cfg.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(email_cfg.get("smtp_port", 587))
    sender_email = email_cfg.get("sender_email", "rajat.aistack@gmail.com")
    sender_password = email_cfg.get("sender_password", "")
    recipient_email = email_cfg.get("recipient_email", sender_email)

    if not sender_password or sender_password == "YOUR_GMAIL_APP_PASSWORD":
        print("[EMAIL WARNING] sender_password is empty or set to placeholder in config.json. Skipping email delivery.")
        return False, "Password not set in config.json"

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

        print(f"[EMAIL] Connecting to SMTP server {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
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
