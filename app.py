from flask import Flask, request, jsonify, render_template
import sqlite3
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('camping.db')
    conn.row_factory = sqlite3.Row
    return conn

# ==========================================
# 1. API: สำหรับให้บริการ Frontend
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/availability', methods=['GET'])
def get_availability():
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')

    if not check_in or not check_out:
        return jsonify({"error": "กรุณาระบุวันที่เข้าพักและออก"}), 400

    conn = get_db_connection()
    # SQL หาห้องว่าง (ไม่มีการจองที่ทับซ้อนในช่วงเวลาที่เลือก)
    query = """
        SELECT id, room_name FROM rooms 
        WHERE id NOT IN (
            SELECT room_id FROM bookings 
            WHERE check_in < ? AND check_out > ?
        )
    """
    # ใช้ logic: check_in < วันออกที่ขอ AND check_out > วันเข้าที่ขอ
    rooms = conn.execute(query, (check_out, check_in)).fetchall()
    conn.close()

    return jsonify([dict(ix) for ix in rooms])

@app.route('/api/book', methods=['POST'])
def make_booking():
    data = request.json
    room_id = data.get('room_id')
    customer_name = data.get('customer_name')
    check_in = data.get('check_in')
    check_out = data.get('check_out')

    conn = get_db_connection()
    # เช็คซ้ำอีกรอบกันลูกค้ากดพร้อมกัน
    check_query = "SELECT id FROM bookings WHERE room_id = ? AND check_in < ? AND check_out > ?"
    conflict = conn.execute(check_query, (room_id, check_out, check_in)).fetchone()

    if conflict:
        conn.close()
        return jsonify({"error": "ขออภัย ห้องนี้ถูกจองไปแล้วในวันดังกล่าว"}), 400

    conn.execute(
        "INSERT INTO bookings (room_id, customer_name, check_in, check_out) VALUES (?, ?, ?, ?)",
        (room_id, customer_name, check_in, check_out)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "จองสำเร็จ!"}), 201

# ==========================================
# 2. ระบบอัตโนมัติ: สรุปงานส่งให้แม่บ้าน
# ==========================================

def send_maid_schedule_email():
    today = datetime.now().date()
    next_week = today + timedelta(days=7)

    conn = get_db_connection()
    # ดึงข้อมูลการจองของ 7 วันข้างหน้า
    query = """
        SELECT rooms.room_name, bookings.customer_name, bookings.check_in 
        FROM bookings 
        JOIN rooms ON bookings.room_id = rooms.id
        WHERE check_in >= ? AND check_in <= ?
        ORDER BY check_in ASC
    """
    upcoming_bookings = conn.execute(query, (today, next_week)).fetchall()
    conn.close()

    if not upcoming_bookings:
        email_body = "สัปดาห์นี้ ({} ถึง {}) ยังไม่มีลูกค้าระบุวันเข้าพักครับ".format(today, next_week)
    else:
        email_body = "ตารางลูกค้าเข้าพักสัปดาห์นี้ ({} ถึง {}):\n\n".format(today, next_week)
        for b in upcoming_bookings:
            email_body += f"- วันที่ {b['check_in']} | {b['room_name']} | ชื่อลูกค้า: {b['customer_name']}\n"

    # ตั้งค่าอีเมล (ใส่ Email และ App Password ของร้าน)
    sender = "durianhillside@gmail.com" 
    password = "YOUR_APP_PASSWORD_HERE" # สร้างจาก Google Account > App Passwords
    receiver = "maid_team@gmail.com"

    msg = MIMEText(email_body)
    msg['Subject'] = f'ตารางเตรียมห้องพัก Durian Hillside ({today})'
    msg['From'] = sender
    msg['To'] = receiver

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        print("ส่งอีเมลแจ้งแม่บ้านสำเร็จแล้ว")
    except Exception as e:
        print("ส่งอีเมลไม่สำเร็จ:", e)

# รันระบบอัตโนมัติทุกวันอาทิตย์ เวลา 8.00 น.
scheduler = BackgroundScheduler()
scheduler.add_job(send_maid_schedule_email, 'cron', day_of_week='sun', hour=8, minute=0)
scheduler.start()

if __name__ == '__main__':
    # รันเซิร์ฟเวอร์
    app.run(debug=True, use_reloader=False)
