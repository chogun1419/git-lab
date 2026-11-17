# git-lab

ใช้สำหรับเรียนแล็ปคอมโปรไฟฟ้า

## 1. หมวดอิเล็กทรอนิกส์และเครื่องมือคำนวณ (Electronics & Tools)

### DC Circuit Calculator (Lab 01)

คำอธิบาย: โปรแกรมคำนวณค่าทางไฟฟ้าพื้นฐานในวงจรไฟฟ้ากระแสตรง (DC)

วัตถุประสงค์: คำนวณหากระแสไฟฟ้า แรงดัน และกำลังไฟฟ้าของวงจรตัวต้านทาน
ได้อย่างรวดเร็วและแม่นยำเพื่อใช้ในการออกแบบวงจร

ไฟล์: `electrical.py`, `test_electrical.py`

### Transistor DC Bias Simulator (Lab 02)

เว็บแอปพลิเคชัน Flask สำหรับคำนวณจุดการทำงาน (Q-point) ของวงจรไบแอสทรานซิสเตอร์
แบบแบ่งแรงดัน พร้อมบอกช่วง Active / Saturation / Cutoff

ไฟล์และวิธีรัน: ดู [transistor-simulator/README.md](transistor-simulator/README.md)

### Transistor Bias Modes (Lab 3)

เว็บแอปพลิเคชัน Flask เดียวกัน แต่เพิ่มโหมด **Fixed Bias** และ **Emitter Bias**
(แหล่งจ่ายเดียว) นอกเหนือจาก Voltage Divider โดยผลของ Divider เดิมคงเดิม

- โฟลเดอร์ส่งงานแยก: [`lab3/`](lab3/README.md)
- ตารางตรวจ A1–A5, ค่าอ้างอิงอิสระ และหลักฐาน: [lab3/docs/validation.md](lab3/docs/validation.md)
- รัน: `cd lab3` แล้ว `python app.py` → เปิด <http://127.0.0.1:5000>
