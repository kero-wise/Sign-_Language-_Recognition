import os
import random
import smtplib
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

db_folder = os.path.abspath("database")   
db_path = os.path.join(db_folder, "DATABASE.db")
if not os.path.exists(db_folder):
    os.makedirs(db_folder)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False   

db = SQLAlchemy(app)

EMAIL_SENDER = "signlanguagerecognition60@gmail.com"  
EMAIL_PASSWORD = "bedn mqhq gxah rxwc"  

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    otp = db.Column(db.String(6), nullable=True)  

with app.app_context():
    db.create_all()

def send_email(to_email, otp_code):
    subject = "Reset Your Password - OTP Code"
    message = f"""
    <html>
    <body>
        <h2>Reset Your Password</h2>
        <p>Your OTP code is: <b>{otp_code}</b></p>
        <p>Please use this code to reset your password.</p>
    </body>
    </html>
    """
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'html'))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
    new_user = User(username=username, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully!'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email, password=password).first()
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    return jsonify("Login successful"), 200

@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Email not found'}), 404
    otp_code = str(random.randint(100000, 999999))
    user.otp = otp_code
    db.session.commit()
    if send_email(email, otp_code):
        return jsonify({'message': 'OTP sent to your email'}), 200
    else:
        return jsonify({'error': 'Failed to send OTP. Please try again'}), 500

@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.json
    otp = data.get('otp')
    new_password = data.get('new_password')
    email = data.get('email')  
    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long'}), 400

    user = User.query.filter_by(email=email, otp=otp).first() 
    if not user:
        return jsonify({'error': 'Invalid OTP or OTP has expired'}), 400

    user.password = new_password
    user.otp = None  
    db.session.commit()
    return jsonify({'message': 'Password updated successfully!'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=9000)
