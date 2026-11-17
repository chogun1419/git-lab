# Validation — Transistor DC Bias Simulator

วันที่ตรวจสอบ: 2026-11-10 (Lab 02) · 2026-11-17 (Lab 3 — Fixed / Emitter Bias)

## 1. สภาพแวดล้อม

| รายการ | ค่า |
|---|---|
| Python | 3.12.7 |
| Flask | 3.1.3 |
| ระบบปฏิบัติการ | Windows |
| คำสั่งทดสอบ | `python -m unittest discover -s tests -v` |

## 2. ผลการทดสอบอัตโนมัติ

```
Ran 40 tests in 0.336s

OK
```

| ไฟล์ | จำนวน | ครอบคลุม |
|---|---:|---|
| `tests/test_dc_bias.py` | 19 | สูตร Thevenin, กระแส/แรงดัน, กำลัง, ช่วงการทำงาน, การตรวจสอบอินพุต |
| `tests/test_web.py` | 21 | ฟอร์ม, ภาพวงจร, การแปลงหน่วย Ω/kΩ, POST คำนวณสำเร็จ, 3 ช่วงการทำงาน, error 400 |
| **รวม** | **40** | |

## 3. การตรวจสอบด้วยมือ (hand calculation)

กรณีตัวอย่างค่าเริ่มต้นของ Lab 02

```
V_CC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, R_C = 2.2 kΩ, R_E = 1 kΩ,
β = 100, V_BE = 0.7 V
```

| ขั้น | สมการ | ผลที่คำนวณมือ | ผลจากโปรแกรม |
|---|---|---|---|
| V_BB | 12 · 22 / (100 + 22) | 2.16393 V | 2.16393 V |
| R_B | 100k ‖ 22k | 18.03279 kΩ | 18032.79 Ω |
| I_B | (2.16393 − 0.7) / (18032.79 + 101·1000) | 12.2986 µA | 12.2986 µA |
| I_C | 100 · I_B | 1.22986 mA | 1.22986 mA |
| I_E | 101 · I_B | 1.24216 mA | 1.24216 mA |
| V_B | V_BB − I_B·R_B | 1.94216 V | 1.94216 V |
| V_E | I_E·R_E | 1.24216 V | 1.24216 V |
| V_C | 12 − I_C·R_C | 9.29431 V | 9.29431 V |
| V_CE | V_C − V_E | 8.05216 V | 8.05216 V |
| P_D | V_CE·I_C | 9.903 mW | 9.903 mW |
| ช่วงการทำงาน | V_CE > 0.2 V | Active | Active |

ตัวเลขตรงกันทุกหลักที่แสดง ผลต่างที่เหลือเกิดจากการปัดเศษทศนิยมเท่านั้น

## 4. กรณีขอบเขต

| กรณี | อินพุต | ผลที่คาดหวัง | ผลจริง |
|---|---|---|---|
| Cutoff | R1 = 100k, R2 = 1k | V_BB = 0.1188 V < V_BE → กระแสเป็น 0, V_CE = 12 V | ตรง |
| Saturation | R_C = 47k, R_E = 100 | I_C ถูกจำกัดที่ 0.25053 mA, V_CE ≈ 0.2 V, แรงดันไม่ติดลบ | ตรง |
| R1 = 0 | — | `ValueError: r1_ohm must be greater than zero.` | ตรง |
| β = 0 | — | `ValueError: beta must be greater than zero.` | ตรง |
| V_BE ≥ V_CC | — | `ValueError` | ตรง |
| ช่องว่าง | ไม่กรอก β | HTTP 400 และข้อความ `beta is required.` | ตรง |
| ข้อความไม่ใช่ตัวเลข | V_CC = "abc" | HTTP 400 และข้อความ `vcc_v must be a number.` | ตรง |
| ค่าที่กรอกผิด | R1 = 0 | ฟอร์มยังแสดงค่าเดิมทั้งหมด | ตรง |

## 5. การตรวจสอบหน้าเว็บ

1. รัน `python app.py` แล้วเปิด <http://127.0.0.1:5000>
2. ค่าเริ่มต้น → เห็น 3 คอลัมน์ และภาพวงจรแสดง 100 kΩ / 22 kΩ / 2.2 kΩ / 1.0 kΩ
   กด **Calculate DC Bias** → V_CE = 8.05 V และกล่องสีเขียว "Active region OK"
3. เปลี่ยน R1 = 47 kΩ → ป้ายในภาพวงจรเปลี่ยนเป็น 47 kΩ และผลลัพธ์อัปเดตตาม
4. เปลี่ยนหน่วย R1 เป็น Ω แล้วกรอก 47000 → ผลลัพธ์เหมือนข้อ 3 (แปลงหน่วยถูกต้อง)
5. ตั้ง R1 = 100 kΩ, R2 = 1 kΩ → กล่องสีแดง "Cutoff region"
6. ตั้ง R_C = 47 kΩ, R_E = 0.1 kΩ → กล่องสีเหลือง "Saturation region"
   พร้อมข้อความ I_C(sat)
7. กรอก R1 = 0 → เห็นข้อความแจ้งข้อผิดพลาดและค่าที่กรอกยังอยู่
8. ย่อหน้าต่างให้กว้างน้อยกว่า 1000 px → 3 คอลัมน์ยุบเป็นคอลัมน์เดียว
   และต่ำกว่า 560 px → ฟอร์มและตารางยังอ่านได้

## 6. ข้อจำกัดที่ยังไม่ได้ตรวจสอบ

- ไม่ได้ทดสอบกับค่าองค์ประกอบจริงจาก datasheet หรือการวัดในห้องแล็บ
- ไม่ได้จำลองอุณหภูมิ, Early effect หรือความคลาดเคลื่อนของ β
- ไม่ได้ทดสอบบนเบราว์เซอร์อื่นนอกจาก Chromium ที่มากับเครื่องมือพัฒนา

---

# Lab 3 — เพิ่มโหมด Fixed Bias และ Emitter Bias

## 7. ผลการทดสอบอัตโนมัติ (Lab 3)

ไม่ได้เพิ่มไฟล์ unittest ใหม่ตามคำสั่งของโจทย์ ใช้ชุดเดิมทั้งหมดและต้องผ่านครบ:

```
Ran 40 tests in 0.590s

OK
```

## 8. ตาราง A1–A5 (ตรวจผ่าน Browser)

ค่ากลางที่ใช้ทุกกรณี: V_CC = 12 V, R_C = 2.2 kΩ, β = 100, V_BE = 0.70 V

| เคส | โหมด | อินพุตเพิ่มเติม | ค่าคาดหมาย | ผลจริง | หน่วย | วิธีตรวจ | สถานะ |
|---|---|---|---|---|---|---|---|
| A1 | Voltage Divider | R1 = 39 kΩ, R2 = 3.9 kΩ, R_E = 1.5 kΩ | I_C ≈ 0.258 mA, V_CE ≈ 11.04 V | I_C = 0.2521 mA, V_CE = 11.0634 V, I_B = 2.5213 µA, V_E = 0.3820 V, V_C = 11.4453 V | mA / V / µA | Browser (Chrome) → ฟอร์ม → Calculate | ผ่านตามสูตร exact (ต่างจากค่าประมาณในตาราง 0.006 mA / 0.02 V — ดูหมายเหตุ) |
| A2 | Fixed Bias | R_B = 1 MΩ | I_C ≈ 1.13 mA, V_CE ≈ 9.51 V | I_C = 1.1300 mA, V_CE = 9.5140 V, I_B = 11.30 µA, V_B = 0.70 V, V_E = 0 V | mA / V / µA | Browser + Flask test client | ผ่าน |
| A3 | Emitter Bias | R_B = 1 MΩ, R_E = 1 kΩ | I_C ≈ 1.026 mA, V_CE ≈ 8.71 V | I_C = 1.0263 mA, V_CE = 8.7054 V, I_B = 10.263 µA, V_E = 1.0366 V, V_C = 9.7420 V | mA / V / µA | Browser + Flask test client | ผ่าน |
| A4 | Emitter Bias | R_B = 1 MΩ, R_E = 2 kΩ | I_C ≈ 0.940 mA, V_CE ≈ 8.03 V (ลดลงจาก A3) | I_C = 0.9401 mA, V_CE = 8.0328 V, I_B = 9.401 µA, V_E = 1.8990 V | mA / V / µA | Browser + Flask test client | ผ่าน (I_C ลดลงตาม R_E ที่เพิ่มขึ้น) |
| A5 | Fixed Bias | R_B = 0 | แจ้ง Error และไม่ค้างผลลัพธ์เก่า | HTTP 400 + `rb_ohm must be greater than zero.` ตารางผลถูกล้าง ไม่มีค่าเก่าค้าง | — | Browser + Flask test client | ผ่าน |

**หมายเหตุ A1:** ตารางอ้างอิงของผู้ใช้ใช้วิธีประมาณ (ไม่คิด I_B ไหลผ่าน R_B):
`V_E = V_BB − V_BE = 0.3909 V → I_E = 0.2606 mA → I_C = β/(β+1)·I_E = 0.2580 mA`
โปรแกรมใช้ Thevenin exact ตาม Lab 02: `I_B = 2.5213 µA` ทำให้ `V_E = I_E·R_E = 0.3820 V`
และ `V_CE = 11.0634 V` ถ้าเปลี่ยน Divider เป็นวิธีประมาณ ค่า default จะกลายเป็น V_CE 7.35 V
และ test เดิมที่ยืนยัน 8.05 V จะพัง จึงคงวิธี exact ไว้ตามข้อกำหนด "Divider ต้องคงเดิม"

## 9. หลักฐานจากหน้าเว็บ

คัดข้อความจากหน้าเว็บ (A2 — Fixed Bias, R_B = 1 MΩ):

```text
V_B   0.70 V
V_E   0.00 V
V_C   9.51 V
V_CE  9.51 V
I_B   11.30 µA
I_C   1.13 mA
I_E   1.14 mA
Active region OK — V_CE = 9.51 V > 0.2 V (transistor in active region)
```

คัดข้อความจากหน้าเว็บ (A3 — Emitter Bias, R_B = 1 MΩ, R_E = 1 kΩ):

```text
V_B   1.74 V
V_E   1.04 V
V_C   9.74 V
V_CE  8.71 V
I_B   10.26 µA
I_C   1.03 mA
I_E   1.04 mA
Active region OK — V_CE = 8.71 V > 0.2 V (transistor in active region)
```

ภาพหน้าจอ A2: [`docs/evidence/a2-fixed-bias.jpeg`](evidence/a2-fixed-bias.jpeg)

## 10. ค่าอ้างอิงอิสระ (คำนวณมือ ไม่ใช้โค้ด)

### 10.1 Fixed Bias

```
V_CC = 12 V, R_B = 240 kΩ, R_C = 2.2 kΩ, β = 50, V_BE = 0.7 V
I_B  = (V_CC − V_BE) / R_B = (12 − 0.7) / 240 000 = 47.083 µA
I_C  = β · I_B            = 50 × 47.083 µA        = 2.3542 mA
I_E  = (β + 1) · I_B      = 51 × 47.083 µA        = 2.4013 mA
V_CE = V_CC − I_C · R_C   = 12 − 2.3542 mA × 2.2 kΩ = 6.8208 V
```

ผลจากโปรแกรม: I_B = 47.0833 µA, I_C = 2.3542 mA, I_E = 2.4013 mA, V_CE = 6.8208 V → ตรงกัน

### 10.2 Emitter Bias

```
V_CC = 12 V, R_B = 470 kΩ, R_C = 2.2 kΩ, R_E = 1 kΩ, β = 100, V_BE = 0.7 V
I_B  = (V_CC − V_BE) / (R_B + (β+1)·R_E)
     = (12 − 0.7) / (470 000 + 101 × 1000) = 11.3 / 571 000 = 19.7898 µA
I_C  = β · I_B        = 1.9790 mA
I_E  = (β + 1) · I_B  = 1.9988 mA
V_E  = I_E · R_E      = 1.9988 mA × 1 kΩ = 1.9988 V
V_C  = V_CC − I_C·R_C = 12 − 1.9790 mA × 2.2 kΩ = 7.6462 V
V_CE = V_C − V_E      = 5.6475 V
```

ผลจากโปรแกรม: I_B = 19.7898 µA, I_C = 1.9790 mA, I_E = 1.9988 mA, V_E = 1.9988 V,
V_C = 7.6462 V, V_CE = 5.6475 V → ตรงกัน

## 11. การตรวจอินพุตผิดและ Warning (Lab 3)

| กรณี | อินพุต | ผลจริง |
|---|---|---|
| ค่าเป็นศูนย์ | Fixed, R_B = 0 | HTTP 400 `rb_ohm must be greater than zero.` |
| ค่าติดลบ | Fixed, R_B = −5 | HTTP 400 `rb must not be negative.` |
| ช่องว่าง | Fixed, R_B ว่าง | HTTP 400 `rb is required.` |
| V_BE ≥ V_CC | Fixed, V_BE = 12 V | HTTP 400 `vbe_v must be less than vcc_v.` |
| Saturation | Fixed, R_B = 10 kΩ | กล่องเหลือง + `Warning: transistor saturated; I_C limited to I_C(sat) ≈ 5.36 mA, V_CE ≤ 0.2 V` |
| Saturation | Emitter, R_B = 10 kΩ, R_E = 0.1 kΩ | กล่องเหลือง + `Warning: transistor saturated; I_C limited to I_C(sat) ≈ 5.13 mA, V_CE ≤ 0.2 V` |

หมายเหตุ: สาขา `cutoff` (I_B ≤ 0) มีโค้ดรองรับ แต่ผู้ใช้ทั่วไปเข้าไม่ถึงเพราะ `V_BE ≥ V_CC`
ถูกปฏิเสธเป็น error ก่อนตามที่ระบุในแผน

## 12. คำถามปิด Lab

**คำถาม:** ถ้าตัวเลขคำนวณมือถูก แต่เปลี่ยน R_E แล้วผลบนหน้าเว็บไม่เปลี่ยน จะตรวจค่าที่ส่งจากฟอร์ม
และค่าที่เข้าไปในฟังก์ชันอย่างไร?

**วิธีตรวจ (ไล่จากต้นทางไปปลายทาง):**

1. **ตรวจว่าเบราว์เซอร์ส่งค่าอะไร** — เปิด DevTools → แท็บ Network → เลือก request `POST /calculate`
   → แท็บ Payload/Payload Form Data ต้องเห็น `re=<ค่าที่พิมพ์>` และ `re_unit=<kohm|ohm>`
   ถ้าไม่มีคีย์ `re` แปลว่า input อยู่นอก `<form>` หรือ `name` สะกดผิด
2. **ตรวจว่าฟอร์มเก็บค่านั้นจริง** — ใน Console: `document.querySelector('[name=re]').value`
   และ `new FormData(document.querySelector('form')).get('re')`
   ถ้าได้ค่าว่าง แปลว่า input ถูก disable/ไม่มี name
3. **ตรวจว่าฝั่ง Flask อ่านค่าถูก** — ใส่ breakpoint หรือรันชั่วคราว
   `print(request.form.get("re"), request.form.get("re_unit"))` ใน `calculate()`
4. **ตรวจผลหลังแปลงหน่วย** — ตรวจค่าที่ `_parse_form()` คืนกลับมา (`numbers["re_ohm"]`)
   ต้องเท่ากับ `re × 1000` เมื่อหน่วยเป็น kΩ และต้องมีคีย์ `re_ohm` ใน dict
5. **ตรวจว่าโหมดนั้นใช้ R_E จริง** — ดู `MODE_FIELDS[mode]` ว่ามี `"re"` อยู่หรือไม่
   (fixed bias ไม่มี R_E จึงถูกต้องที่ผลไม่เปลี่ยน) และดูว่า `calculate_bias()` ส่งต่อไปยัง
   `calculate_emitter_bias(..., re_ohm=...)` ไม่ใช่ `calculate_fixed_bias`
6. **ตรวจว่าแม่แบบแสดงผลจากคีย์ที่ถูก** — ตารางผลลัพธ์อ่าน `result.ve_v`/`result.vce_v`
   ถ้าค่าที่คำนวณเปลี่ยนแต่หน้าจอไม่เปลี่ยน ให้ดูว่าเทมเพลตอ่านคีย์ผิดหรือถูก cache

สาเหตุที่พบบ่อยที่สุดในงานนี้: เลือกโหมดผิด (R_E ถูกซ่อนในโหมด Fixed) หรือหน่วยเป็น Ω
แต่ผู้ใช้คิดเป็น kΩ ทำให้ค่าที่ส่งต่างกัน 1000 เท่า
