# แผนงาน: เพิ่ม Fixed Bias และ Emitter Bias (แหล่งจ่ายเดียว)

วันที่: 2026-11-17
โปรเจกต์: `transistor-simulator/`
สถานะ: **รอผู้ใช้ตรวจแผน** (ยังไม่เขียนโค้ด)

## 1. เป้าหมาย

1. เพิ่มโหมดคำนวณ 2 โหมด: **Fixed Bias** และ **Emitter Bias (single supply)**
2. โหมด **Voltage Divider** เดิมต้องให้ผลเหมือนเดิมทุกหลัก (ไม่แก้สูตร)
3. สมการทั้งหมดอยู่ใน `dc_bias.py` คืนค่าเป็น `dict` ที่มีชื่อคีย์และหน่วยตรงกันทุกโหมด
4. เลือกฟังก์ชันตาม `mode` และตรวจอินพุตเฉพาะฟิลด์ของโหมดนั้น
5. ดัก error: ค่าว่าง / ติดลบ / ศูนย์ และแจ้ง warning เมื่อหลุด Forward Active
   (`I_B ≤ 0` หรือ `V_CE ≤ 0.2 V`)
6. ไม่สร้างไฟล์ unittest ใหม่ — ใช้ tests เดิม 40 ตัว + ตรวจผ่าน Browser ด้วยตารางของผู้ใช้

## 2. โครงปัจจุบัน (Lab 2)

| ไฟล์ | หน้าที่ |
|---|---|
| `dc_bias.py` | `calculate_voltage_divider_bias(...) -> dict` + `VCE_SAT_V=0.2`, `DEFAULT_VBE_V=0.7` |
| `app.py` | `_parse_form()` (Ω/kΩ → SI), `_unit_labels()`, `_status()`, `create_app()` |
| `templates/index.html` | 3 คอลัมน์: ฟอร์ม / SVG วงจร / ตารางผลลัพธ์ |
| `static/style.css` | ธีม Lab 02 |
| `tests/` | `test_dc_bias.py` 19 + `test_web.py` 21 = 40 (ห้ามแก้) |

ผลเดิม (12 V, 100k, 22k, 2.2k, 1k, β=100):
V_B 1.94, V_E 1.24, V_C 9.29, V_CE 8.05 V, I_B 12.30 µA, I_C 1.23 mA, I_E 1.24 mA, active

## 3. ค่ากลาง (defaults) ที่จะใช้

ค่าที่ผู้ใช้กำหนด: **V_CC = 12 V, R_C = 2.2 kΩ, β = 100, V_BE = 0.7 V**

| โหมด | ฟิลด์ | ค่ากลาง |
|---|---|---|
| divider | V_CC, R1, R2, R_C, R_E, β, V_BE | 12 V, 100k, 22k, 2.2k, 1k, 100, 0.7 V (เดิม) |
| fixed | V_CC, **R_B**, R_C, β, V_BE | 12 V, **470k**, 2.2k, 100, 0.7 V |
| emitter | V_CC, **R_B**, R_C, R_E, β, V_BE | 12 V, **470k**, 2.2k, 1k, 100, 0.7 V |

เหตุผลที่ R_B = 470 kΩ: ให้ทั้งสองโหมดอยู่ใน Forward Active ด้วยค่ากลาง
(fixed → I_C ≈ 2.40 mA, V_CE ≈ 6.71 V; emitter → I_C ≈ 1.98 mA, V_CE ≈ 5.65 V)

## 4. `dc_bias.py` — ฟังก์ชันที่จะเพิ่ม

### 4.1 `calculate_fixed_bias`

```python
def calculate_fixed_bias(
    vcc_v: float, rb_ohm: float, rc_ohm: float,
    beta: float, vbe_v: float = DEFAULT_VBE_V,
) -> dict[str, float | str]:
```

```
Ib  = (Vcc - Vbe) / Rb
Ic  = beta * Ib
Ie  = (beta + 1) * Ib
Vb  = Vbe          Ve = 0
Vc  = Vcc - Ic * Rc
Vce = Vc - Ve
Ic_sat = (Vcc - 0.2) / Rc
```

### 4.2 `calculate_emitter_bias`

```python
def calculate_emitter_bias(
    vcc_v: float, rb_ohm: float, rc_ohm: float, re_ohm: float,
    beta: float, vbe_v: float = DEFAULT_VBE_V,
) -> dict[str, float | str]:
```

```
Ib  = (Vcc - Vbe) / (Rb + (beta + 1) * Re)
Ic  = beta * Ib
Ie  = (beta + 1) * Ib
Ve  = Ie * Re
Vb  = Vbe + Ve
Vc  = Vcc - Ic * Rc
Vce = Vc - Ve
Ic_sat = (Vcc - 0.2) / (Rc + Re)
```

### 4.3 ตัวเลือกฟังก์ชัน

```python
BIAS_FUNCTIONS = {
    "divider": calculate_voltage_divider_bias,
    "fixed": calculate_fixed_bias,
    "emitter": calculate_emitter_bias,
}

def calculate_bias(mode: str, **values: float) -> dict[str, float | str]:
```

`mode` ไม่รู้จัก → `ValueError("mode must be divider, fixed, or emitter.")`
วาง dispatcher ใน `dc_bias.py` เพราะเงื่อนไขเลือกสูตรเป็นเรื่องวิศวกรรม ไม่ใช่ route

### 4.4 คีย์ผลลัพธ์ร่วม (เหมือน divider เดิม 12 คีย์)

| คีย์ | หน่วย | divider | fixed | emitter |
|---|---|---|---|---|
| `vbb_v` | V | V_CC·R2/(R1+R2) | V_CC | V_CC |
| `rb_ohm` | Ω | R1‖R2 | R_B | R_B |
| `ib_a` | A | สูตรเดิม | สูตร fixed | สูตร emitter |
| `ic_a` | A | β·I_B | β·I_B | β·I_B |
| `ie_a` | A | (β+1)·I_B | (β+1)·I_B | (β+1)·I_B |
| `vb_v` | V | V_BB − I_B·R_B | V_BE | V_BE + V_E |
| `ve_v` | V | I_E·R_E | 0 | I_E·R_E |
| `vc_v` | V | V_CC − I_C·R_C | V_CC − I_C·R_C | V_CC − I_C·R_C |
| `vce_v` | V | V_C − V_E | V_C − V_E | V_C − V_E |
| `power_w` | W | V_CE·I_C | V_CE·I_C | V_CE·I_C |
| `ic_sat_a` | A | (V_CC−0.2)/(R_C+R_E) | (V_CC−0.2)/R_C | (V_CC−0.2)/(R_C+R_E) |
| `region` | — | active/saturation/cutoff | เหมือนกัน | เหมือนกัน |

## 5. การตรวจอินพุต (ดัก Error)

ทำสองชั้น: `app.py` ตรวจรูปแบบ/หน่วย, `dc_bias.py` ตรวจความสมเหตุสมผลทางไฟฟ้า

| กรณี | ข้อความ | โหมดที่ใช้ |
|---|---|---|
| ช่องว่าง (ยกเว้น V_BE) | `"<field> is required."` | ทุกโหมด |
| ไม่ใช่ตัวเลข | `"<field> must be a number."` | ทุกโหมด |
| ค่าติดลบ | `"<field> must not be negative."` | ทุกโหมด |
| ค่าเป็นศูนย์ | `"<field> must be greater than zero."` | ทุกโหมด |
| หน่วยไม่ใช่ ohm/kohm | `"<field>_unit must be ohm or kohm."` | ทุกโหมด |
| `V_BE ≥ V_CC` | `"vbe_v must be less than vcc_v."` | ทุกโหมด |

ข้อยกเว้นที่ตั้งใจให้เป็นศูนย์ได้: `R_E = 0` เฉพาะโหมด **divider** (พฤติกรรมเดิม)
โหมด emitter บังคับ `R_E > 0` เพราะถ้าเป็น 0 จะกลายเป็น fixed bias

ค่าที่ต้อง `> 0`: `vcc_v`, `r1`, `r2` (divider), `rb` (fixed/emitter),
`rc` (ทุกโหมด), `re` (emitter), `beta`
ค่าที่ต้อง `≥ 0`: `vbe_v`

## 6. Warning / Region

| เงื่อนไข | region | ข้อความที่แสดง |
|---|---|---|
| `I_B ≤ 0` | `cutoff` | **Warning:** base drive too small (V_CC ≤ V_BE) → I_B = I_C = I_E = 0 |
| `V_CE ≤ 0.2 V` | `saturation` | **Warning:** transistor saturated → I_C limited to I_C(sat) ≈ … mA |
| อื่น ๆ | `active` | V_CE = … V > 0.2 V (transistor in active region) |

- โหมดใหม่ใช้ `V_CE <= 0.2` ตามที่ผู้ใช้ระบุ
- โหมด divider คงเงื่อนไขเดิม `V_CE < 0.2` และข้อความเดิมทุกตัวอักษร
  เพื่อไม่ให้ผลลัพธ์เปลี่ยน
- ค่าในตารางผลลัพธ์ยังเป็นตัวเลขจริงหลัง clamp (ไม่ติดลบ) และ `region` ใช้ทำสีกล่อง
  เขียว/เหลือง/แดงเหมือนเดิม

## 7. `app.py`

- `FIELD_NAMES` เพิ่ม `"mode"`, `"rb"`, `"rb_unit"`
- `DEFAULT_VALUES` เพิ่ม `mode="divider"`, `rb="470"`, `rb_unit="kohm"`
- `MODE_FIELDS`: divider / fixed / emitter ตามตารางข้อ 3
- `_parse_form(values)`:
  - `mode` ว่าง → `"divider"` (ให้ web test เดิมผ่าน)
  - ตรวจ `mode` อยู่ใน `BIAS_FUNCTIONS`
  - ตรวจช่องว่าง / ตัวเลข / ติดลบ ก่อนแปลงหน่วย
  - แปลง Ω/kΩ → SI เฉพาะตัวต้านทานของโหมดนั้น (`UNIT_SCALE` เดิม)
  - ส่งเข้า `dc_bias.py` เฉพาะฟิลด์ของโหมดนั้น
- `_status(result, mode)` ตามตารางข้อ 6
- `_unit_labels()` เติม `"—"` ให้ฟิลด์ที่โหมดนั้นไม่มี

## 8. `templates/index.html` + `static/style.css`

- แถบเลือกโหมด: radio 3 ตัว `name="mode"` (divider / fixed / emitter)
  ใช้ CSS `:checked ~ .fields-<mode>` แสดงเฉพาะกลุ่มฟิลด์ — ไม่ใช้ JavaScript
- เพิ่มฟิลด์ `rb` + `rb_unit` (R_B) ใช้ทั้ง fixed และ emitter
- ภาพวงจร 3 แบบ ทุกอันมี `data-testid="circuit"`
  - divider: markup เดิม **ไม่แก้** (test เดิมเช็ค 100 kΩ / 2.2 kΩ)
  - fixed: V_CC → R_B → เบส, R_C ที่คอลเลกเตอร์, อิมิตเตอร์ลงกราวด์
  - emitter: เพิ่ม R_E ระหว่างอิมิตเตอร์กับกราวด์
  - ป้ายทุกป้ายผูกกับ `values` + `unit_labels`
- ตารางผลลัพธ์ 7 แถวเดิม (V_B, V_E, V_C, V_CE, I_B, I_C, I_E) ใช้คีย์ร่วมได้ทุกโหมด
- หัวข้อการ์ดวงจรเปลี่ยนตามโหมด

## 9. ไฟล์ที่จะเปลี่ยน

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `dc_bias.py` | + `calculate_fixed_bias`, `calculate_emitter_bias`, `BIAS_FUNCTIONS`, `calculate_bias`; divider เดิมไม่แก้ |
| `app.py` | mode, per-mode fields, error handling, unit conversion, dispatch, `_status` |
| `templates/index.html` | mode picker, ฟิลด์ R_B, 3 SVG, หัวข้อตามโหมด |
| `static/style.css` | mode picker + กติกาแสดง/ซ่อนกลุ่มฟิลด์ |
| `docs/design-note.md` | สมการ 3 โหมด + ข้อสมมติ + กฎ warning |
| `docs/validation.md` | ตัวอย่างคำนวณมือของ fixed และ emitter + เคส error |
| `README.md` | ฟีเจอร์ 3 โหมด + ฟิลด์ R_B |

ไม่แตะ: `tests/`, `docs/test-log.txt`, `WEB-URL.txt`, `requirements.txt`

## 10. ลำดับงาน

1. เพิ่ม 2 ฟังก์ชัน + dispatcher ใน `dc_bias.py`
2. รัน `python -m unittest discover -s tests -v` → ต้องยัง 40 OK
3. ตรวจเลขด้วยสคริปต์ชั่วคราว (ไม่ commit) เทียบกับค่ามือ
4. แก้ `app.py` → รัน tests ซ้ำ
5. แก้ template + CSS
6. รัน tests ซ้ำ + ตรวจ Browser ทุกโหมด
7. อัปเดตเอกสาร → สรุปผลให้ผู้ใช้ตรวจ

## 11. การตรวจรับ

```bash
cd transistor-simulator
python -m unittest discover -s tests -v   # ต้องได้ 40 tests OK
```

Browser ที่ <http://127.0.0.1:5000/>:

| # | เคส | สิ่งที่ต้องเห็น |
|---|---|---|
| 1 | Divider (default) | V_CE 8.05 V, I_C 1.23 mA, I_B 12.30 µA, active (เหมือนเดิมเป๊ะ) |
| 2 | Fixed + ค่ากลาง | I_B ≈ 24.04 µA, I_C ≈ 2.40 mA, V_CE ≈ 6.71 V, active |
| 3 | Emitter + ค่ากลาง | V_E ≈ 2.00 V, V_C ≈ 7.65 V, V_CE ≈ 5.65 V, active |
| 4 | Fixed + R_C = 47k | กล่องเหลือง + Warning saturation + I_C(sat) |
| 5 | Fixed + V_BE ≥ V_CC | กล่องแดง + Warning cutoff |
| 6 | ช่องว่าง / 0 / ติดลบ | error 400 และค่าที่กรอกยังอยู่ |
| 7 | R_B = 0 (fixed) | error 400 ระบุ `rb` |

## 12. ต้องยืนยันก่อนลงมือ

1. **สมการในใบงาน** — แผนนี้ใช้ exact (`I_C = β·I_B`); ถ้าใบงานใช้ `I_C ≈ I_E`
   หรือ `V_CE(sat)` ค่าอื่น ผมจะแก้ตามใบงาน
2. **R_B ค่ากลาง = 470 kΩ** โอเคไหม (ถ้าอยากได้ค่าอื่นบอกได้)
3. **ตารางตรวจ Browser** (อินพุต + ผลคาดหวัง) ถ้ามี
4. ชื่อตัวต้านทานเบสในใบงานคือ `R_B` ใช่ไหม

## 13. ความเสี่ยง

- **Divider ต้องไม่ขยับ**: ไม่แตะบรรทัดสูตรและข้อความ `_status` ของ divider
- **Fixed bias ไม่มี R_E** → `ve_v = 0`, `Vce = Vc`
- **Saturation clamp** ของ fixed หารด้วย `R_C` เท่านั้น ต่างจากอีกสองโหมดที่ `R_C + R_E`
- ไม่มีเทสต์ใหม่ตามคำสั่ง → ความถูกต้องของโหมดใหม่พึ่ง Browser + ตารางผู้ใช้
  (เบี่ยงจาก `AGENTS.md` ที่ให้ topology ใหม่มีเทสต์ของตัวเอง)
