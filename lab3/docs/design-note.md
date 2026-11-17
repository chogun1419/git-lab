# Design Note — Transistor DC Bias Simulator

วันที่: 2026-11-10

## 1. เป้าหมายและเหตุผล

นักศึกษาต้องการเครื่องมือที่คำนวณจุดการทำงาน (Q-point) ของวงจรไบแอสทรานซิสเตอร์
ได้เร็ว แทนการไล่สูตรด้วยมือทุกครั้ง และต้องการเห็นทันทีว่าค่าที่ออกมานั้น
ทำให้ทรานซิสเตอร์อยู่ในช่วง Active, Saturation หรือ Cutoff

ความสำเร็จของงานนี้คือ:

- กรอกค่าองค์ประกอบแล้วได้ Q-point ที่ตรงกับการคำนวณมือ
- บอกช่วงการทำงานและเตือนเมื่อ Q-point ใช้งานไม่ได้จริง
- สูตรวิศวกรรมแยกออกจากส่วนเว็บ และมี unit test ครอบคลุม
- หน้าจอใช้งานได้บนมือถือโดยไม่ต้องมี JavaScript

## 2. ขอบเขต

**อยู่ในขอบเขต**

- วงจรไบแอสแบบแบ่งแรงดัน (voltage-divider bias) ที่มี R<sub>E</sub>
- BJT แบบ NPN, โหมด forward-active, V<sub>BE</sub> คงที่
- คำนวณ I<sub>B</sub>, I<sub>C</sub>, I<sub>E</sub>, V<sub>B</sub>, V<sub>E</sub>,
  V<sub>C</sub>, V<sub>CE</sub>, P<sub>D</sub>, V<sub>BB</sub>, R<sub>B</sub>
- จำแนกช่วงการทำงาน 3 ช่วง
- ตรวจสอบอินพุตและแสดงข้อผิดพลาด

**ไม่อยู่ในขอบเขต**

- วงจรไบแอสแบบอื่น (fixed bias, collector feedback, emitter-stabilized)
- การจำลองเชิงเวลา, AC analysis, load line graph, การวาด schematic
- ผลของ Early effect, temperature sweep, การเลือกค่ามาตรฐาน (E12/E24)
- ระบบล็อกอิน ฐานข้อมูล หรือการบันทึกประวัติ

**anti-goals** — งานนี้จะถือว่าล้มเหลวถ้า

- สูตรไปอยู่ใน route หรือ template จนทดสอบแยกไม่ได้
- ตัวเลขที่แสดงไม่ตรงกับสมการที่เขียนไว้ในเอกสาร
- หน้าจอพังหรืออ่านไม่ได้บนจอมือถือ

## 3. ทางเลือกที่พิจารณา

| ทางเลือก | ข้อดี | ข้อเสีย | สรุป |
|---|---|---|---|
| **A. Voltage-divider bias + สมการ Thevenin แบบแม่นยำ** | ตรงกับวงจรที่ใช้ในแล็บ, ปิดสวิตช์ได้ด้วยสูตรปิด, ทดสอบง่าย | ใช้ได้กับวงจรเดียว | **เลือกใช้** |
| B. Fixed bias ก่อน แล้วค่อยเพิ่มวงจรอื่น | ง่ายที่สุด | ไม่ตรงกับวงจรไบแอสที่เรียนและใช้งานจริง | ไม่เลือก |
| C. ตัวแก้สมการ Ebers–Moll แบบ iterative (คล้าย SPICE) | แม่นกว่าเมื่อมี Early effect | ซับซ้อน เกินขอบเขตแล็บ และตรวจสอบด้วยมือยาก | ไม่เลือก |

เลือก A เพราะเป็นวงจรมาตรฐานของบทไบแอส, สูตรปิดตรวจสอบด้วยมือได้
และยังแยกส่วนขยายวงจรอื่นออกไปได้โดยไม่ต้องรื้อโครงสร้าง

## 4. สมการที่ใช้

ให้ V<sub>BB</sub> และ R<sub>B</sub> เป็น Thevenin equivalent ของตัวแบ่งแรงดันที่ฐาน

```
V_BB = V_CC · R2 / (R1 + R2)
R_B  = R1 || R2 = R1·R2 / (R1 + R2)
I_B  = (V_BB − V_BE) / (R_B + (β + 1)·R_E)
I_C  = β · I_B
I_E  = (β + 1) · I_B
V_B  = V_BB − I_B·R_B
V_E  = I_E·R_E
V_C  = V_CC − I_C·R_C
V_CE = V_C − V_E
P_D  = V_CE · I_C
```

การจำแนกช่วง:

- **Cutoff** เมื่อ V<sub>BB</sub> ≤ V<sub>BE</sub> → กระแสทุกตัวเป็น 0,
  V<sub>CE</sub> = V<sub>CC</sub>
- **Saturation** เมื่อ V<sub>CE</sub> < 0.2 V
- **Active** เมื่อ 0.2 V ≤ V<sub>CE</sub>

## 5. สมมติฐานและข้อจำกัด

- V<sub>BE</sub> คงที่ (ค่าเริ่มต้น 0.7 V) ไม่ขึ้นกับอุณหภูมิหรือกระแส
- ไม่คิด Early effect จึงไม่มีความชันของกราฟเอาต์พุต
- ในช่วง Saturation ระบบจำกัดกระแสที่ `ic_sat_a = (V_CC − 0.2) / (R_C + R_E)`
  แล้วคำนวณแรงดันโหนดใหม่ ทำให้ V<sub>CE</sub> ≈ 0.2 V และไม่มีแรงดันติดลบ
  (ค่า V<sub>CE</sub> ที่ได้จะต่ำกว่า 0.2 V เล็กน้อยเพราะ I<sub>E</sub> มี I<sub>B</sub> รวมอยู่ด้วย)
- R<sub>C</sub>, R<sub>1</sub>, R<sub>2</sub>, β, V<sub>CC</sub> ต้องมากกว่าศูนย์;
  R<sub>E</sub> เป็นศูนย์ได้; V<sub>BE</sub> ต้องน้อยกว่า V<sub>CC</sub>

## 6. สถาปัตยกรรม

```
เบราว์เซอร์
   │  GET /            → ฟอร์มเริ่มต้น
   │  POST /calculate  → ฟอร์ม + ผลลัพธ์ (200) หรือฟอร์ม + error (400)
   ▼
app.py  (parse form → เรียก dc_bias → render)
   │
   ▼
dc_bias.calculate_voltage_divider_bias(...)  → dict[str, float | str]
   │
   ▼
templates/index.html + static/style.css
```

สัญญาณผลลัพธ์ (คีย์มีหน่วยต่อท้าย):

`vbb_v`, `rb_ohm`, `ib_a`, `ic_a`, `ie_a`, `vb_v`, `ve_v`, `vc_v`, `vce_v`,
`power_w`, `ic_sat_a`, `region` (`"active" | "saturation" | "cutoff"`)

## 7. สิ่งที่ตัดสินใจไว้แล้ว

- ใช้ Flask + Jinja แบบ server-rendered ไม่มี JavaScript
- ใช้ `unittest` จาก standard library ไม่เพิ่ม dependency นอกจาก Flask
- ใช้ `create_app()` factory เพื่อให้ test สร้างแอปแยกได้
- ข้อความบนหน้าจอเป็นภาษาไทย สัญลักษณ์ทางไฟฟ้าเป็นภาษาอังกฤษ
- เลือกค่าเริ่มต้น V<sub>CC</sub>=12 V, R<sub>1</sub>=100k, R<sub>2</sub>=22k,
  R<sub>C</sub>=2.2k, R<sub>E</sub>=1k, β=100 เป็นตัวอย่างของ Lab 02
  ที่ให้ Q-point อยู่ในช่วง Active

## 8. UI revision — Lab 02 layout

หลังสร้างเวอร์ชันแรก ได้ปรับหน้าจอให้คล้ายตัวอย่างของ Lab 02 โดยไม่แตะสูตร:

- Header: ชื่อ Lab 02, subtitle รายวิชา และ badge ด้านขวา
- 3 คอลัมน์: Input Parameters | Circuit | DC Bias Results
  (ยุบเป็นคอลัมน์เดียวเมื่อหน้าจอแคบกว่า 1000 px)
- ภาพวงจรเป็น inline SVG อยู่ใน template ค่า V<sub>CC</sub>, R<sub>1</sub>,
  R<sub>2</sub>, R<sub>C</sub>, R<sub>E</sub> และ β ในรูปผูกกับค่าที่ผู้ใช้กรอก
  จึงเห็นค่าที่เพิ่งคำนวณได้ทันทีโดยไม่ต้องใช้ JavaScript
- ตัวต้านทานมี dropdown หน่วย Ω / kΩ; `app.py` แปลงเป็นหน่วยฐานก่อนเรียก
  `dc_bias.py` เพื่อให้สูตรยังรับหน่วย SI เหมือนเดิม
- ผลลัพธ์แสดง 7 ค่า (V<sub>B</sub>, V<sub>E</sub>, V<sub>C</sub>,
  V<sub>CE</sub>, I<sub>B</sub>, I<sub>C</sub>, I<sub>E</sub>)
  พร้อมกล่องสถานะสีเขียว/เหลือง/แดงตาม region

**การตัดสินใจ:** ไม่แก้ `dc_bias.py` เลย เพื่อให้ตัวเลขยังตรวจสอบด้วยมือชุดเดิมได้
และไม่ปรับสูตรให้ตรงกับตัวเลขในภาพตัวอย่าง เพราะภาพนั้นใช้วิธี approximate
(V<sub>B</sub> = V<sub>CC</sub>·R2/(R1+R2), I<sub>C</sub> ≈ I<sub>E</sub>)
ซึ่งให้ผลต่างจากวิธี exact ที่งานนี้ใช้

## 9. Lab 3 — Fixed Bias และ Emitter Bias

เพิ่มสองโทโพโลยีโดยไม่แตะ `calculate_voltage_divider_bias` แม้แต่บรรทัดเดียว

### 9.1 สมการ

**Fixed bias** (R<sub>B</sub> จาก V<sub>CC</sub> มาที่เบส, อิมิตเตอร์ลงกราวด์)

```
I_B  = (V_CC − V_BE) / R_B
I_C  = β · I_B
I_E  = (β + 1) · I_B
V_B  = V_BE          V_E = 0
V_C  = V_CC − I_C · R_C
V_CE = V_C − V_E
I_C(sat) = (V_CC − 0.2) / R_C
```

**Emitter bias** (R<sub>B</sub> จาก V<sub>CC</sub> มาที่เบส, R<sub>E</sub> จากอิมิตเตอร์ลงกราวด์)

```
I_B  = (V_CC − V_BE) / (R_B + (β + 1) · R_E)
I_C  = β · I_B
I_E  = (β + 1) · I_B
V_E  = I_E · R_E
V_B  = V_BE + V_E
V_C  = V_CC − I_C · R_C
V_CE = V_C − V_E
I_C(sat) = (V_CC − 0.2) / (R_C + R_E)
```

### 9.2 การเลือกฟังก์ชัน

อยู่ใน `dc_bias.py` ไม่ใช่ route เพราะเป็นการเลือกสูตร:

```python
BIAS_FUNCTIONS = {
    "divider": calculate_voltage_divider_bias,
    "fixed": calculate_fixed_bias,
    "emitter": calculate_emitter_bias,
}

def calculate_bias(mode: str, **values: float) -> dict[str, float | str]:
    ...
```

`app.py` ทำหน้าที่อ่าน `mode` จากฟอร์ม ตรวจว่าอยู่ใน `MODE_FIELDS` แล้วเรียก
`calculate_bias(mode, **numbers)`

### 9.3 การแปลงหน่วย

อยู่ที่ `app.py` `_parse_form()` ที่เดียว: อ่าน `<field>_unit` (`ohm` / `kohm`)
แล้วคูณด้วย `UNIT_SCALE` (`1.0` / `1000.0`) ก่อนส่งเข้า `dc_bias.py`
โมดูลคำนวณจึงรับหน่วย SI เสมอ (Ω, V, A) และไม่รู้จักหน่วยที่ผู้ใช้เลือก

### 9.4 การตรวจอินพุตและ Warning

- ฟิลด์ว่าง → `<field> is required.` (ยกเว้น V_BE ที่ใช้ค่า 0.7 V)
- ค่าติดลบ → `<field> must not be negative.`
- ค่าเป็นศูนย์ → `<field> must be greater than zero.`
- `V_BE ≥ V_CC` → `vbe_v must be less than vcc_v.`
- `region`: `active` เมื่อ `V_CE > 0.2 V`; `saturation` เมื่อ `V_CE ≤ 0.2 V`
  (clamp กระแสที่ I_C(sat)); `cutoff` เมื่อ `I_B ≤ 0`
- โหมดใหม่แสดง `Warning:` ในกล่องสถานะเมื่อไม่อยู่ใน Forward Active
- Divider คงเงื่อนไข `V_CE < 0.2` และข้อความสถานะเดิมทุกตัวอักษร

### 9.5 UI

- แถบเลือกโหมด 3 ปุ่ม (radio) ใช้ CSS `:has()` แสดงเฉพาะฟิลด์ของโหมดนั้น
  ไม่ใช้ JavaScript และไม่เพิ่ม dependency
- ภาพวงจรเป็น SVG 3 แบบ (divider / fixed / emitter) ป้ายค่าผูกกับ `values`
- คีย์ผลลัพธ์ยังเป็นชุดเดียวกัน 12 คีย์ ทำให้ตารางผลลัพธ์ใช้ร่วมได้ทุกโหมด

## 10. สิ่งที่เหลือให้ผู้พัฒนาต่อ

- เพิ่มวงจรไบแอสแบบอื่นเป็นฟังก์ชันใหม่ใน `dc_bias.py`
- เพิ่มกราฟ load line และจุด Q บนกราฟ (ต้องใช้ JavaScript หรือ SVG)
- เพิ่มการ export ผลเป็น CSV/PDF
- เพิ่มการเลือกค่าตัวต้านทานมาตรฐานและการเทียบ β หลายค่า
