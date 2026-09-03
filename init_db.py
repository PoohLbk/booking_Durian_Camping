import sqlite3

def init_db():
    conn = sqlite3.connect('camping.db')
    cursor = conn.cursor()

    # สร้างตารางห้องพัก
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT NOT NULL
        )
    ''')

    # สร้างตารางการจอง
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER,
            customer_name TEXT,
            check_in DATE,
            check_out DATE,
            FOREIGN KEY(room_id) REFERENCES rooms(id)
        )
    ''')

    # เพิ่มข้อมูลห้องพักเริ่มต้น (ถ้ายังไม่มี)
    cursor.execute("SELECT COUNT(*) FROM rooms")
    if cursor.fetchone()[0] == 0:
        rooms = [('เต็นท์ VIP 1',), ('เต็นท์ VIP 2',), ('ลานกางเต็นท์ โซน A',), ('ลานกางเต็นท์ โซน B',)]
        cursor.executemany("INSERT INTO rooms (room_name) VALUES (?)", rooms)

    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()
