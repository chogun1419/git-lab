# Transistor DC Bias Simulator

เว็บแอปพลิเคชัน Flask สำหรับคำนวณจุดการทำงาน (Q-point) ของวงจรไบแอสทรานซิสเตอร์
แบบแบ่งแรงดัน (voltage-divider bias) พร้อมบอกช่วงการทำงาน Active / Saturation / Cutoff

## ฟีเจอร์

- รับค่า V<sub>CC</sub>, R<sub>1</sub>, R<sub>2</sub>, R<sub>C</sub>, R<sub>E</sub>, β และ V<sub>BE</sub>
- คำนวณ I<sub>B</sub>, I<sub>C</sub>, I<sub>E</sub>, V<sub>B</sub>, V<sub>E</sub>, V<sub>C</sub>, V<sub>CE</sub> และ P<sub>D</sub>
- แสดงภาพวงจร Common-Emitter (inline SVG) โดยป้ายค่าองค์ประกอบอัปเดตตามอินพุต
- เลือกหน่วยตัวต้านทานได้ระหว่าง Ω และ kΩ
- ตรวจสอบช่วงการทำงานและเตือนเมื่อวงจรอิ่มตัวหรือตัดขาด
- ตรวจสอบค่าอินพุตและแสดงข้อผิดพลาดโดยไม่ล้างค่าที่กรอก
- หน้าจอ 3 คอลัมน์ (Input / Circuit / Results) ที่ยุบเป็นคอลัมน์เดียวบนมือถือ

ค่าเริ่มต้นเป็นตัวอย่างของ Lab 02: V<sub>CC</sub>=12 V, R<sub>1</sub>=100 kΩ,
R<sub>2</sub>=22 kΩ, R<sub>C</sub>=2.2 kΩ, R<sub>E</sub>=1 kΩ, β=100, V<sub>BE</sub>=0.7 V
(ได้ V<sub>CE</sub> ≈ 8.05 V อยู่ในช่วง Active)

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
(`tests/test_web.py`) โดยไม่ต้องเปิดเซิร์ฟเวอร์จริง — ปัจจุบันมี 40 tests
ผลการรันล่าสุดบันทึกไว้ที่ [docs/test-log.txt](docs/test-log.txt)

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
├── WEB-URL.txt
└── docs/
    ├── design-note.md
    ├── validation.md
    ├── test-log.txt
    └── reflection.md
```

## เอกสารเพิ่มเติม

- [WEB-URL.txt](WEB-URL.txt) — ลิงก์เว็บแอป (local) และ repository
- [docs/design-note.md](docs/design-note.md) — เหตุผลการออกแบบ สมการ และข้อจำกัด
- [docs/validation.md](docs/validation.md) — ผลทดสอบและการตรวจสอบด้วยมือ
- [docs/reflection.md](docs/reflection.md) — บันทึกการเรียนรู้และการใช้ AI
