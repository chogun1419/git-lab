# Transistor DC Bias Simulator

เว็บแอปพลิเคชัน Flask สำหรับคำนวณจุดการทำงาน (Q-point) ของวงจรไบแอสทรานซิสเตอร์
แบบแบ่งแรงดัน (voltage-divider bias) พร้อมบอกช่วงการทำงาน Active / Saturation / Cutoff

## ฟีเจอร์

- รับค่า V<sub>CC</sub>, R<sub>1</sub>, R<sub>2</sub>, R<sub>C</sub>, R<sub>E</sub>, β และ V<sub>BE</sub>
- คำนวณ I<sub>B</sub>, I<sub>C</sub>, I<sub>E</sub>, V<sub>B</sub>, V<sub>E</sub>, V<sub>C</sub>, V<sub>CE</sub> และ P<sub>D</sub>
- ตรวจสอบช่วงการทำงานและเตือนเมื่อวงจรอิ่มตัวหรือตัดขาด
- ตรวจสอบค่าอินพุตและแสดงข้อผิดพลาดโดยไม่ล้างค่าที่กรอก
- หน้าจอ responsive ใช้ได้ทั้งคอมพิวเตอร์และมือถือ

## การติดตั้ง

ต้องใช้ Python 3.10 ขึ้นไป

```bash
cd transistor-simulator
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
python -m pip install -r requirements.txt
```

## การรัน

```bash
python app.py
```

แล้วเปิด <http://127.0.0.1:5000>

หรือใช้ Flask CLI:

```bash
flask --app app run --debug
```

## การทดสอบ

```bash
python -m unittest discover -s tests -v
```

ชุดทดสอบครอบคลุมทั้งสูตรวิศวกรรม (`tests/test_dc_bias.py`) และ HTTP route
(`tests/test_web.py`) โดยไม่ต้องเปิดเซิร์ฟเวอร์จริง

## โครงสร้างโปรเจกต์

```
transistor-simulator/
├── app.py              # Flask application & HTTP routes
├── dc_bias.py          # independent engineering calculations
├── templates/
│   └── index.html      # input form + DC results (Jinja)
├── static/
│   └── style.css       # responsive layout and presentation
├── tests/
│   ├── test_dc_bias.py # unit tests for engineering logic
│   └── test_web.py     # Flask HTTP route tests
├── requirements.txt
├── README.md
├── AGENTS.md
└── docs/
    ├── design-note.md
    ├── validation.md
    └── reflection.md
```

## เอกสารเพิ่มเติม

- [docs/design-note.md](docs/design-note.md) — เหตุผลการออกแบบ สมการ และข้อจำกัด
- [docs/validation.md](docs/validation.md) — ผลทดสอบและการตรวจสอบด้วยมือ
- [docs/reflection.md](docs/reflection.md) — บันทึกการเรียนรู้และการใช้ AI
