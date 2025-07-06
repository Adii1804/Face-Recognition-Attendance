#Face Recognition Attendance System  
An intelligent and secure face recognition-based attendance system using Python, OpenCV, face_recognition, SQLite, and optional SMS integration via Twilio or Fast2SMS. Ideal for classrooms, offices, and controlled-entry systems. This project includes features such as an admin panel with password protection, real-time face recognition using a webcam, auto-attendance marking for both entry and exit modes, duplicate prevention logic, and SMS notifications via Twilio or Fast2SMS. Users can export attendance logs as CSV files, view and manage registered students, and check real-time student status. The project automatically initializes the SQLite database and webcam, storing facial encodings for future recognition. The main components are `sam.py` (the main application), `attendance_system.db` (SQLite database), and a `requirements.txt` file for dependencies. To use it, install Python 3.7 or above, ensure a webcam is connected, and run `pip install -r requirements.txt` to install dependencies. After cloning the repository, update the SMS credentials in the code. Uncomment and fill in your Twilio or Fast2SMS credentials: for Twilio, set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_PHONE_NUMBER`; for Fast2SMS, set `FAST2SMS_API_KEY`. Do not commit sensitive credentials to GitHub—use environment variables in production. Run the system using `python sam.py`. Admin login credentials are `admin` / `admin123`, which you can change in the source code. System controls include pressing 'e' to switch between entry/exit modes, 'a' for admin login, and 'q' to quit. Optional SMS alerts can be configured via Twilio (global) or Fast2SMS (India). When a student is marked for entry or exit, an SMS notification is sent to their registered number. Face recognition uses the `hog` model with a 10-second cooldown to prevent repeat marking. You can export attendance data via the admin panel as `attendance_YYYYMMDD_HHMMSS.csv`. Limitations include single-face recognition per student, lighting dependency, and hardcoded credentials (should be improved for production).
🧠 Enhanced Face Recognition Attendance System

An intelligent and secure face recognition-based attendance system using Python, OpenCV, face_recognition, SQLite, and optional SMS integration via Twilio or Fast2SMS. Ideal for classrooms, offices, and controlled-entry systems.

---

## 🔍 Features

- 🔐 **Admin Panel** with password protection  
- 🧠 **Real-time Face Recognition** using webcam  
- 📅 **Auto-attendance marking** (Entry & Exit modes)  
- 🔄 **Duplicate prevention logic**  
- 📱 **SMS notifications** on entry/exit using:
  - Twilio API
  - Fast2SMS API (for India)
- 📤 **CSV Export** of attendance logs  
- 📋 **View & manage registered students**  
- ⚠️ **Handles entry/exit validations**
- ✅ **Status View**: See who’s inside, exited, or not entered yet  
- 🎥 Webcam auto-setup and face encoding storage

---

## 📁 Project Structure

📦 Face-Recognition-Attendance
├── sam.py # Main attendance application
├── attendance_system.db # SQLite DB (auto-created)
├── captured_faces/ # (optional) for saved face images
├── requirements.txt # Python dependencies
└── README.md # This file

markdown
Copy
Edit

---

## ⚙️ Requirements

- Python 3.7+
- Webcam
- Internet (for SMS functionality)
- Libraries:
  - `opencv-python`
  - `face_recognition`
  - `numpy`
  - `pandas`
  - `requests`
  - `twilio`

Install dependencies:

```bash
pip install -r requirements.txt
🔧 Setup Instructions
Clone the repository:

bash
Copy
Edit
git clone https://github.com/YourUsername/Face-Recognition-Attendance.git
cd Face-Recognition-Attendance
Update credentials:
Uncomment and edit the following in sam.py:

python
Copy
Edit
# For Twilio:
TWILIO_ACCOUNT_SID = "your_twilio_sid"
TWILIO_AUTH_TOKEN = "your_twilio_token"
TWILIO_PHONE_NUMBER = "your_twilio_phone_number"

# For Fast2SMS:
FAST2SMS_API_KEY = "your_fast2sms_api_key"
⚠️ Do NOT commit your secrets to GitHub. Use .env or environment variables in production.

Run the application:

bash
Copy
Edit
python sam.py
🧑‍💼 Admin Access
Username: admin

Password: admin123

You can change it in the source code:

python
Copy
Edit
ADMIN_USER, ADMIN_PASS = "admin", "admin123"
🖥️ Controls
e → Switch between Entry/Exit mode

a → Admin login for managing system

q → Quit the system

📲 SMS Setup (Optional)
You can choose one of the following:

Twilio
Create an account at twilio.com

Get your Account SID, Auth Token, and Phone Number

Paste them in the code as shown above

Fast2SMS (India only)
Sign up at fast2sms.com

Get your API key and paste it in the code

📊 Output Sample
yaml
Copy
Edit
✓ ENTRY: Aman at 2025-07-06 09:45:21
✓ SMS sent via Twilio to +919876543210

✓ EXIT: Aman at 2025-07-06 13:01:56
✓ SMS sent via Twilio to +919876543210
🧠 Face Recognition Notes
Uses face_recognition with the hog model

Cooldown of 10 seconds between recognitions

Each student is registered with one facial encoding

📤 Export Attendance
Use Admin option to export logs in .csv format:

Copy
Edit
attendance_YYYYMMDD_HHMMSS.csv
🙅‍♂️ Known Limitations
Only one face per student allowed

Requires good lighting for accuracy

Credentials should not be hard-coded in production

👨‍💻 Author
Aditya Pratap Singh
📫 GitHub Profile

📜 License
MIT License — Free to use, modify, and distribute

