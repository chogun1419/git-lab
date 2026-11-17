# Transistor DC Bias Simulator (Lab 3)

เว็บแอปพลิเคชัน Flask สำหรับคำนวณจุดการทำงาน (Q-point) ของวงจรไบแอสทรานซิสเตอร์
รองรับ **3 โหมด**: Voltage Divider Bias, Fixed Bias และ Emitter Bias (แหล่งจ่ายเดียว)
พร้อมบอกช่วงการทำงาน Active / Saturation / Cutoff

## ฟีเจอร์

- เลือกโหมดไบแอสได้ 3 โหมดจากแถบด้านบนฟอร์ม
- รับค่า V<sub>CC</sub>, R<sub>B</sub>, R<sub>1</sub>, R<sub>2</sub>, R<sub>C</sub>,
  R<sub>E</sub>, β และ V<sub>BE</sub> ตามโหมดที่เลือก
- คำนวณ I<sub>B</sub>, I<sub>C</sub>, I<sub>E</sub>, V<sub>B</sub>, V<sub>E</sub>,
  V<sub>C</sub>, V<sub>CE</sub> และ P<sub>D</sub>
- แสดงภาพวงจร inline SVG 3 แบบ (divider / fixed / emitter) ป้ายค่าอัปเดตตามอินพุต
- เลือกหน่วยตัวต้านทานได้ระหว่าง Ω และ kΩ
- ตรวจอินพุตผิด: ช่องว่าง / ไม่ใช่ตัวเลข / ติดลบ / ศูนย์ / หน่วยผิด
- แจ้ง **Warning** เมื่อไม่อยู่ใน Forward Active (`I_B ≤ 0` หรือ `V_CE ≤ 0.2 V`)
- หน้าจอ 3 คอลัมน์ (Input / Circuit / Results) ยุบเป็นคอลัมน์เดียวบนมือถือ

ค่าเริ่มต้น (โหมด Voltage Divider): V<sub>CC</sub>=12 V, R<sub>1</sub>=100 kΩ,
R<sub>2</sub>=22 kΩ, R<sub>C</sub>=2.2 kΩ, R<sub>E</sub>=1 kΩ, β=100, V<sub>BE</sub>=0.7 V
(ได้ V<sub>CE</sub> ≈ 8.05 V อยู่ในช่วง Active)

## ลิงก์ส่งงาน Lab 3

| รายการ | ลิงก์ / ค่า |
|---|---|
| GitHub repository | <https://github.com/chogun1419/git-lab> |
| โฟลเดอร์โปรเจกต์ | <https://github.com/chogun1419/git-lab/tree/main/transistor-simulator> |
| **Commit SHA (Lab 3)** | `SHA_PLACEHOLDER_LAB3` |
| เว็บ (local) | <http://127.0.0.1:5000/> |

## วิธีรันและเปิดเว็บ

```bash
cd transistor-simulator
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
python -m pip install -r requirements.txt
python app.py
```

แล้วเปิด <http://127.0.0.1:5000> — เลือกโหมด → กรอกค่า → กด **Calculate DC Bias**

หรือใช้ Flask CLI:

```bash
flask --app app run --debug
```

## โหมดการทำงาน

| โหมด | ฟิลด์ที่ใช้ | ค่ากลาง |
|---|---|---|
| Voltage Divider | V_CC, R1, R2, R_C, R_E, β, V_BE | 12 V, 100k, 22k, 2.2k, 1k, 100, 0.7 V |
| Fixed Bias | V_CC, R_B, R_C, β, V_BE | 12 V, 470k, 2.2k, 100, 0.7 V |
| Emitter Bias | V_CC, R_B, R_C, R_E, β, V_BE | 12 V, 470k, 2.2k, 1k, 100, 0.7 V |

สมการทั้งหมดอยู่ใน `dc_bias.py`:

```
Fixed:   I_B = (V_CC − V_BE)/R_B
         I_C = β·I_B,  I_E = (β+1)·I_B
         V_B = V_BE, V_E = 0, V_C = V_CC − I_C·R_C, V_CE = V_C

Emitter: I_B = (V_CC − V_BE)/(R_B + (β+1)·R_E)
         I_C = β·I_B,  I_E = (β+1)·I_B
         V_E = I_E·R_E, V_B = V_BE + V_E
         V_C = V_CC − I_C·R_C, V_CE = V_C − V_E
```

**เลือกฟังก์ชันที่ไหน:** `dc_bias.py` → `BIAS_FUNCTIONS` + `calculate_bias(mode, **values)`
**แปลงหน่วยที่ไหน:** `app.py` → `_parse_form()` (Ω/kΩ → Ω ก่อนเรียก `dc_bias.py`)

## การทดสอบ

```bash
python -m unittest discover -s tests -v
```

ผลล่าสุด: **40 tests OK** (19 สูตรวิศวกรรม + 21 HTTP route) — ไม่ได้เพิ่มไฟล์เทสต์ใหม่
ใน Lab 3 ตามคำสั่งของโจทย์ ใช้การตรวจผ่าน Browser ร่วมกับตาราง A1–A5

ตาราง A1–A5 (อินพุต / ค่าคาดหมาย / ผลจริง / หน่วย / วิธีตรวจ / สถานะ),
ค่าอ้างอิงอิสระ, หลักฐานจากหน้าเว็บ และคำถามปิด Lab:
[docs/validation.md](docs/validation.md)

ภาพหลักฐาน A2 (Fixed Bias): [docs/evidence/a2-fixed-bias.jpeg](docs/evidence/a2-fixed-bias.jpeg)

## AI ช่วยส่วนไหน / นักศึกษาตรวจอะไร

| ส่วน | ผู้รับผิดชอบ |
|---|---|
| โครง Flask, `_parse_form()`, dispatch, template, CSS, SVG | AI (OpenCode) ร่างให้ |
| สูตรใน `dc_bias.py` (3 โหมด) | AI ร่างตามใบงาน |
| เลือกค่ากลาง V_CC=12 V, R_C=2.2 kΩ, β=100, V_BE=0.7 V, R_B=470 kΩ | นักศึกษา |
| ตรวจสมการกับใบงาน (`I_C = β·I_B`, `I_E = (β+1)·I_B`) | นักศึกษา |
| รันตาราง A1–A5 ผ่าน Browser และเทียบค่าคาดหมาย | นักศึกษา |
| ตรวจว่า Divider เดิมไม่เปลี่ยน (V_CE 8.05 V) | นักศึกษา |
| ตรวจ error (ว่าง/ติดลบ/ศูนย์) และ Warning (saturation) | นักศึกษา |
| รัน `python -m unittest discover -s tests -v` (40 OK) | นักศึกษา |

## โครงสร้างโปรเจกต์

```
transistor-simulator/
├── app.py              # Flask routes, form parsing, unit conversion, dispatch
├── dc_bias.py          # 3 bias functions + BIAS_FUNCTIONS + calculate_bias
├── opencode.json       # Playwright MCP config ที่ใช้ตรวจผ่าน Browser
├── templates/
│   └── index.html      # form + 3 circuit SVGs + results (Jinja)
├── static/
│   └── style.css       # layout, mode picker, responsive
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
    ├── evidence/
    │   └── a2-fixed-bias.jpeg
    ├── superpowers/plans/
    │   └── 2026-11-17-fixed-and-emitter-bias.md
    └── reflection.md
```

## เอกสารเพิ่มเติม

- [WEB-URL.txt](WEB-URL.txt) — ลิงก์เว็บแอป (local) และ repository
- [docs/design-note.md](docs/design-note.md) — เหตุผลการออกแบบ สมการ 3 โหมด และข้อจำกัด
- [docs/validation.md](docs/validation.md) — ผลทดสอบ ตาราง A1–A5 และค่าอ้างอิงอิสระ
- [docs/test-log.txt](docs/test-log.txt) — log การรันเทสต์จริง
- [docs/reflection.md](docs/reflection.md) — บันทึกการเรียนรู้และการใช้ AI
