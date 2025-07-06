import cv2
import face_recognition
import numpy as np
import sqlite3
import pandas as pd
import os
from datetime import datetime
import hashlib
import time
import requests
from twilio.rest import Client

ADMIN_USER, ADMIN_PASS = "admin", "admin123"

#Add your twilio account details
#TWILIO_ACCOUNT_SID ="Your_twilio_account_sid"
#TWILIO_AUTH_TOKEN = "Your_twilio_account_auth_token"
#TWILIO_PHONE_NUMBER ="Your_twilio_number"

#Or add your fast2sms account details
#FAST2SMS_API_KEY = "your_fast2sms_api_key"


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = sqlite3.connect('attendance_system.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY, name TEXT, roll_number TEXT UNIQUE, 
        phone TEXT, face_encoding BLOB)''')

    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY, roll_number TEXT, name TEXT,
        entry_time TEXT, exit_time TEXT, date TEXT)''')

    conn.commit()
    return conn


def send_sms_twilio(phone_number, message):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        if not phone_number.startswith('+'):
            phone_number = '+91' + phone_number
        message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        print(f"✓ SMS sent via Twilio to {phone_number}")
        return True
    except Exception as e:
        print(f"❌ Twilio SMS failed: {e}")
        return False


def send_sms_fast2sms(phone_number, message):
    try:
        phone_number = phone_number.replace('+91', '').replace(' ', '')

        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = {
            'authorization': FAST2SMS_API_KEY,
            'sender_id': 'FSTSMS',
            'message': message,
            'language': 'english',
            'route': 'q',
            'numbers': phone_number,
        }

        response = requests.post(url, data=payload)
        if response.status_code == 200:
            result = response.json()
            if result.get('return'):
                print(f"✓ SMS sent via Fast2SMS to {phone_number}")
                return True

        print(f"❌ Fast2SMS failed: {response.text}")
        return False
    except Exception as e:
        print(f"❌ Fast2SMS error: {e}")
        return False


def send_notification(phone_number, message):
    if not phone_number:
        return False

    if TWILIO_ACCOUNT_SID != "your_twilio_account_sid":
        if send_sms_twilio(phone_number, message):
            return True

    if FAST2SMS_API_KEY != "your_fast2sms_api_key":
        if send_sms_fast2sms(phone_number, message):
            return True

    print(f"❌ No SMS service configured or all services failed for {phone_number}")
    return False


def setup_camera():
    print("Initializing camera...")

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Cannot open camera")
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    ret, frame = cap.read()
    if not ret or frame is None:
        print("❌ Cannot read from camera")
        cap.release()
        return None

    print("✓ Camera initialized successfully")
    return cap


def load_students(conn):
    c = conn.cursor()
    c.execute('SELECT name, roll_number, phone, face_encoding FROM students')

    metadata, encodings = [], []
    for name, roll, phone, enc_bytes in c.fetchall():
        metadata.append({'name': name, 'roll_number': roll, 'phone': phone})
        encodings.append(np.frombuffer(enc_bytes, dtype=np.float64))

    return metadata, encodings


def check_duplicate_entry(student, mode, conn):
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    roll = student['roll_number']

    if mode == "entry":
        c.execute('''SELECT id FROM attendance 
                    WHERE roll_number = ? AND date = ? 
                    AND entry_time IS NOT NULL AND exit_time IS NULL''',
                  (roll, today))
        result = c.fetchone()
        if result:
            print(f"⚠️ {student['name']} already has an active entry today!")
            return True

    else:
        c.execute('''SELECT entry_time, exit_time FROM attendance 
                    WHERE roll_number = ? AND date = ? 
                    ORDER BY id DESC LIMIT 1''',
                  (roll, today))
        result = c.fetchone()

        if not result or not result[0]:  # No entry found
            print(f"⚠️ {student['name']} must enter first before exit!")
            return True
        elif result[1]:
            print(f"⚠️ {student['name']} already exited today!")
            return True

    return False


def mark_attendance(student, mode, conn):
    if check_duplicate_entry(student, mode, conn):
        return False

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    date = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    c = conn.cursor()
    name, roll, phone = student['name'], student['roll_number'], student['phone']

    try:
        if mode == "entry":
            c.execute('INSERT INTO attendance (roll_number, name, entry_time, date) VALUES (?, ?, ?, ?)',
                      (roll, name, timestamp, date))
            print(f"✓ ENTRY: {name} at {timestamp}")

            message = f"Hello {name}! You have successfully entered at {time_str} on {date}. Have a great day!"
            send_notification(phone, message)

        else:
            c.execute('''SELECT id FROM attendance 
                           WHERE roll_number = ? AND date = ? AND exit_time IS NULL
                           ORDER BY id DESC LIMIT 1''',
                      (roll, date))
            entry_id = c.fetchone()

            if entry_id:
                entry_id = entry_id[0]
                c.execute('''UPDATE attendance SET exit_time = ? 
                               WHERE id = ?''',
                          (timestamp, entry_id))

                if c.rowcount > 0:
                    print(f"✓ EXIT: {name} at {timestamp}")
                else:
                    print(f"❌ Could not mark exit for {name}")
                    return False
            else:
                print(f"❌ No active entry found for {name} to mark exit")
                return False

        conn.commit()
        return True

    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


last_recognition = {}
COOLDOWN = 10


def recognize_faces(frame, known_encodings, known_metadata, mode, conn):
    if not known_encodings:
        cv2.putText(frame, "No students registered - Press 'a' for admin",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        return frame

    small = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)
    rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

    locations = face_recognition.face_locations(rgb_small, model="hog")[:2]
    if not locations:
        return frame

    encodings = face_recognition.face_encodings(rgb_small, locations, num_jitters=0)

    for (top, right, bottom, left), encoding in zip(locations, encodings):
        top, right, bottom, left = top * 3, right * 3, bottom * 3, left * 3

        matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.6)
        name = "Unknown"

        if True in matches:
            distances = face_recognition.face_distance(known_encodings, encoding)
            best_idx = np.argmin(distances)

            if matches[best_idx] and distances[best_idx] < 0.6:
                student = known_metadata[best_idx]
                name = student['name']

                key = f"{student['roll_number']}_{mode}"
                current_time = time.time()

                if key not in last_recognition or current_time - last_recognition[key] > COOLDOWN:
                    if mark_attendance(student, mode, conn):
                        last_recognition[key] = current_time

        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom - 25), (right, bottom), color, cv2.FILLED)
        cv2.putText(frame, name, (left + 3, bottom - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    return frame


def capture_student(conn):
    name = input("Name: ").strip()
    roll = input("Roll Number: ").strip()
    phone = input("Phone (with country code, e.g., +919876543210): ").strip()

    if not all([name, roll, phone]):
        print("All fields required!")
        return False

    cap = setup_camera()
    if not cap:
        return False

    print("Press SPACE to capture, ESC to cancel")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        cv2.putText(frame, f"Registering: {name}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "SPACE=capture, ESC=cancel", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.imshow('Register Student', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb_frame)

            if len(encodings) != 1:
                print("Please ensure exactly one face is visible")
                continue

            try:
                c = conn.cursor()
                c.execute('INSERT INTO students (name, roll_number, phone, face_encoding) VALUES (?, ?, ?, ?)',
                          (name, roll, phone, encodings[0].tobytes()))
                conn.commit()
                print(f"✓ {name} registered successfully!")
                cap.release()
                cv2.destroyAllWindows()
                return True
            except sqlite3.IntegrityError:
                print(f"Roll number {roll} already exists!")
                break
        elif key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    return False


def admin_menu(conn):
    while True:
        print("\n" + "=" * 50)
        print("ADMIN MENU")
        print("1. View Today's Attendance")
        print("2. View All Students")
        print("3. Add Student")
        print("4. Export CSV")
        print("5. View Student Status")
        print("6. Configure SMS Settings")
        print("7. Test SMS")
        print("8. Exit")

        choice = input("Choice (1-8): ").strip()

        if choice == "1":
            today = datetime.now().strftime("%Y-%m-%d")
            df = pd.read_sql_query(
                '''SELECT roll_number, name, entry_time, exit_time,
                   CASE 
                       WHEN entry_time IS NOT NULL AND exit_time IS NULL THEN 'INSIDE'
                       WHEN entry_time IS NOT NULL AND exit_time IS NOT NULL THEN 'COMPLETED'
                       ELSE 'NO ENTRY'
                   END as status
                   FROM attendance WHERE date = ? ORDER BY entry_time DESC''',
                conn, params=(today,))
            print(f"\nToday's Attendance ({today}):")
            print(df.to_string(index=False) if not df.empty else "No records")

        elif choice == "2":
            df = pd.read_sql_query('SELECT name, roll_number, phone FROM students ORDER BY name', conn)
            print(f"\nRegistered Students ({len(df)}):")
            print(df.to_string(index=False) if not df.empty else "No students")

        elif choice == "3":
            capture_student(conn)

        elif choice == "4":
            df = pd.read_sql_query('SELECT * FROM attendance ORDER BY date DESC', conn)
            if not df.empty:
                filename = f"attendance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(filename, index=False)
                print(f"✓ Exported to {filename}")
            else:
                print("No data to export")

        elif choice == "5":
            today = datetime.now().strftime("%Y-%m-%d")
            c = conn.cursor()
            c.execute('''SELECT s.name, s.roll_number, 
                           CASE 
                               WHEN a.entry_time IS NOT NULL AND a.exit_time IS NULL THEN 'INSIDE'
                               WHEN a.entry_time IS NOT NULL AND a.exit_time IS NOT NULL THEN 'EXITED'
                               ELSE 'NOT ENTERED'
                           END as status
                       FROM students s 
                       LEFT JOIN attendance a ON s.roll_number = a.roll_number AND a.date = ?
                       ORDER BY s.name''', (today,))

            print(f"\nStudent Status Today ({today}):")
            for name, roll, status in c.fetchall():
                status_color = "✓" if status == "EXITED" else "→" if status == "INSIDE" else "○"
                print(f"{status_color} {name} ({roll}): {status}")

        elif choice == "6":
            print("\nSMS Configuration:")
            print("1. Update SMS service configuration in the code:")
            print("   - For Twilio: Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER")
            print("   - For Fast2SMS: Set FAST2SMS_API_KEY")
            print("2. Current status:")
            twilio_configured = TWILIO_ACCOUNT_SID != "your_twilio_account_sid"
            fast2sms_configured = FAST2SMS_API_KEY != "your_fast2sms_api_key"
            print(f"   - Twilio: {'✓ Configured' if twilio_configured else '✗ Not configured'}")
            print(f"   - Fast2SMS: {'✓ Configured' if fast2sms_configured else '✗ Not configured'}")

        elif choice == "7":
            phone = input("Enter phone number to test: ").strip()
            message = "This is a test message from Attendance System!"
            if send_notification(phone, message):
                print("✓ Test SMS sent successfully!")
            else:
                print("❌ Test SMS failed!")

        elif choice == "8":
            break


def authenticate():
    try:
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        return username == ADMIN_USER and password == ADMIN_PASS
    except:
        return False


def main():
    print("ENHANCED FACE RECOGNITION ATTENDANCE SYSTEM")
    print("Features: Duplicate Prevention + SMS Notifications")
    print("Controls: 'e'=switch mode, 'a'=admin, 'q'=quit")

    conn = init_db()
    cap = setup_camera()
    if not cap:
        return

    metadata, encodings = load_students(conn)
    print(f"Loaded {len(encodings)} students")

    mode = "entry"
    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            frame_count += 1

            if frame_count % 3 == 0:
                frame = recognize_faces(frame, encodings, metadata, mode, conn)

            color = (0, 255, 0) if mode == "entry" else (0, 0, 255)
            cv2.putText(frame, f"Mode: {mode.upper()}", (10, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(frame, f"Students: {len(encodings)}", (300, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (255, 255, 255), 1)

            cv2.imshow('Attendance System', frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('e'):
                mode = "exit" if mode == "entry" else "entry"
                print(f"Mode: {mode.upper()}")
            elif key == ord('a'):
                if authenticate():
                    admin_menu(conn)
                    metadata, encodings = load_students(conn)
                    print(f"Reloaded {len(encodings)} students")
                else:
                    print("Authentication failed!")
            elif key == ord('q'):
                break

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        conn.close()
        print("System closed")


if __name__ == "__main__":
    main()