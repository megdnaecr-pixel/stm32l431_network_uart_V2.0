#!/usr/bin/env python3
"""
=============================================================
  اختبار CAN مع STM32L431 - بروتوكول [0xCC][0xBA][CMD][CRC_L][CRC_H]

  المحوّل: USB↔CAN (SLCAN على /dev/ttyACM* أو ttyUSB*) — مثل أجهزة CAN_LIN /
  Mingruisheng class. ملخص مرجعي من صفحة Alibaba المحفوظة:
  adapter_alibaba_extract.txt

  اتصال ذكي:
    • CAN_TEST_CHANNEL=/dev/ttyACM2  أو  --channel /dev/ttyACM2
    • إن فشل المنفذ الافتراضي يُجرّب بقية ttyACM* / ttyUSB* تلقائيًا
    • سرعات تسلسل شائعة للـ SLCAN: 2000000، 115200، 500000، 921600

  ليد TX على المحوّل: --pulse-tx (وميض عند إرسال الـ PC على CAN)
=============================================================
"""

import can
import glob
import os
import time
import sys

# يُضبط من main() عند وجود --debug-rx
DEBUG_BUS = False

# ─── إعدادات ────────────────────────────────────────────────
CAN_INTERFACE  = 'slcan'
CAN_CHANNEL    = '/dev/ttyACM2'  # الأفضل: CAN_TEST_CHANNEL أو --channel ثم يُكمّل باقي المنافذ
CAN_BITRATE    = 500000          # 500 kbps — يطابق can.c بعد التعديل
CAN_TTY_BRATE  = 2000000         # مفضّل لبعض محوّلات CDC؛ يُجرّب غيره تلقائيًا
CAN_TX_ID      = 0x011           # ID ترسل إليه STM32 (أي ID تقبله الفلتر)
CAN_RX_ID      = 0x100           # ID يرسل منه STM32 (CAN_TX_STD_ID)
TIMEOUT        = 3.0             # ثواني انتظار الرد

# سرعات UART لمحاولة فتح SLCAN (الأولى = CAN_TTY_BRATE ثم الباقي)
TTY_BAUD_TRIES = [CAN_TTY_BRATE, 115200, 500000, 921600]


def discover_serial_ports():
    """منافذ محتملة لمحوّل USB↔CAN (Linux)."""
    ports = []
    for pattern in ("/dev/ttyACM*", "/dev/ttyUSB*"):
        ports.extend(glob.glob(pattern))
    return sorted(set(ports))


def parse_channel_from_argv():
    """--channel /dev/ttyACM2  أو  --channel=/dev/ttyACM2"""
    for i, a in enumerate(sys.argv):
        if a.startswith("--channel="):
            return a.split("=", 1)[1].strip()
        if a == "--channel" and i + 1 < len(sys.argv):
            return sys.argv[i + 1].strip()
    return None


def build_channel_list():
    """
    ترتيب المحاولات: وسيط سطر أوامر، ثم البيئة، ثم الافتراضي، ثم بقية المنافذ المكتشفة.
    """
    override = parse_channel_from_argv()
    env_ch = (os.environ.get("CAN_TEST_CHANNEL") or "").strip()
    seen = set()
    out = []
    for ch in (override, env_ch, CAN_CHANNEL):
        if ch and ch not in seen:
            seen.add(ch)
            out.append(ch)
    for p in discover_serial_ports():
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def open_can_bus():
    """
    يفتح can.interface.Bus مع slcan: يجرّب كل منفذ مرشّح وعدة ttyBitrate.
    يعيد (bus, channel_used, kwargs_ok) أو (None, None, None).
    """
    channels = build_channel_list()

    for ch in channels:
        # 1) مع ttyBitrate صريح
        for ttyb in TTY_BAUD_TRIES:
            kwargs = dict(
                interface=CAN_INTERFACE,
                channel=ch,
                bitrate=CAN_BITRATE,
                ttyBitrate=ttyb,
                sleep_after_open=1.0,
            )
            try:
                print(f"  محاولة: {kwargs}")
                bus = can.interface.Bus(**kwargs)
                print(f"✅ تم فتح قناة CAN: {ch}  (ttyBitrate={ttyb})\n")
                return bus, ch, kwargs
            except Exception as e:
                print(f"  ❌ فشل: {e}")
        # 2) بدون ttyBitrate
        kwargs = dict(
            interface=CAN_INTERFACE,
            channel=ch,
            bitrate=CAN_BITRATE,
            sleep_after_open=1.0,
        )
        try:
            print(f"  محاولة: {kwargs}")
            bus = can.interface.Bus(**kwargs)
            print(f"✅ تم فتح قناة CAN: {ch}  (بدون ttyBitrate)\n")
            return bus, ch, kwargs
        except Exception as e:
            print(f"  ❌ فشل: {e}")

    return None, None, None

# ─── قاموس الأوامر الكاملة ──────────────────────────────────
COMMANDS = {
    0x01: 'CMD_1_On',
    0x02: 'CMD_1_Off',
    0x03: 'CMD_2_On',
    0x04: 'CMD_2_Off',
    0x05: 'CMD_3_On',
    0x06: 'CMD_3_Off',
    0x07: 'CMD_4_On',
    0x08: 'CMD_4_Off',
    0x09: 'CMD_5_On',
    0x0A: 'CMD_5_Off',
    0x0B: 'CMD_6_On',
    0x0C: 'CMD_6_Off',
    0x0D: 'CMD_7_Off',
    0x0E: 'CMD_7_On',
    0x0F: 'CMD_8_Off',
    0x10: 'CMD_9_Off',
    0x11: 'CMD_9_On',
}

# قائمة الأوامر مرتبة للاختبار التسلسلي
ALL_CMDS = list(COMMANDS.keys())  # 0x01 .. 0x11

# ─── حساب CRC-CCITT (0x1021) مطابق لكود STM32 ───────────────
def calc_crc16(data: bytes) -> tuple:
    """إرجاع (crcLow2, crcHigh1) مطابق لدالة CRC_16_Calc_TX في STM32"""
    crc = 0
    for byte in data:
        temp = byte << 8
        crc ^= temp
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
    crc &= 0x3FFF
    crc_low1  = crc & 0x7F
    crc_high1 = (crc >> 7) & 0x7F
    crc = crc_high1
    crc = (crc << 8) | crc_low1
    crc_low2 = crc & 0xFF
    return crc_low2, crc_high1

# ─── التحقق الذاتي من CRC ────────────────────────────────────
def self_test_crc():
    """اختبار دالة CRC بقيم ثابتة معروفة"""
    print("\n🔬 اختبار CRC الذاتي...")
    errors = 0
    # نحسب CRC لكل أمر ونتحقق من ثباته
    for cmd, name in COMMANDS.items():
        header = bytes([0xCC, 0xBA, cmd])
        l1, h1 = calc_crc16(header)
        l2, h2 = calc_crc16(header)   # نفس الحساب مرتين يجب أن يعطي نفس النتيجة
        if l1 != l2 or h1 != h2:
            print(f"  ❌ {name}: CRC غير ثابت!")
            errors += 1
        else:
            print(f"  ✅ {name} (0x{cmd:02X}): CRC_L=0x{l1:02X}  CRC_H=0x{h1:02X}")
    if errors == 0:
        print("✅ جميع قيم CRC ثابتة ومتسقة\n")
    else:
        print(f"❌ {errors} خطأ في CRC!\n")
    return errors == 0

# ─── نبضات إرسال لرؤية ليد TX على المحوّل USB-CAN ─────────────
def pulse_adapter_tx_led(bus: can.BusABC, count: int = 40, interval_s: float = 0.08):
    """
    يرسل إطارات CAN بسيطة من الكمبيوتر؛ المحوّل يمرّرها على CANH/CANL
    وغالبًا يومض ليد الإرسال (TX) على اللوحة الزرقاء إن ربطه السوفت وير كذلك.
    """
    print("\n" + "═"*55)
    print("  🔆 اختبار ليد إرسال المحوّل (USB→CAN)")
    print("═"*55)
    print("  ملاحظة: هذا لا يستخدم بروتوكول STM32؛ فقط إطارات عادية لإجبار الـ TX.")
    print(f"  ID=0x{CAN_TX_ID:03X}  العدد={count}  فاصل≈{interval_s*1000:.0f} ms\n")

    ok = 0
    for i in range(count):
        msg = can.Message(
            arbitration_id=CAN_TX_ID,
            data=bytes([i & 0xFF]),
            is_extended_id=False,
        )
        try:
            bus.send(msg)
            ok += 1
        except Exception as e:
            print(f"  ❌ فشل الإرسال #{i + 1}: {e}")
            break
        time.sleep(interval_s)

    print(f"\n  ✅ أُرسل {ok}/{count} إطارًا — راقب ليد TX على المحوّل (غالبًا D2/D3 بجانب USB).")
    print("═"*55)

# ─── بناء إطار البروتوكول ────────────────────────────────────
def build_frame(cmd: int) -> bytes:
    header = bytes([0xCC, 0xBA, cmd])
    crc_l, crc_h = calc_crc16(header)
    return header + bytes([crc_l, crc_h])

# ─── إرسال أمر واستقبال الرد ────────────────────────────────
def send_command(bus: can.BusABC, cmd: int, verbose: bool = True) -> bool:
    frame = build_frame(cmd)
    cmd_name = COMMANDS.get(cmd, f'Unknown(0x{cmd:02X})')

    if verbose:
        print(f"\n{'─'*55}")
        print(f"📤 إرسال: {cmd_name} (0x{cmd:02X})")
        print(f"   البيانات: {' '.join(f'{b:02X}' for b in frame)}")
        print(f"   CAN ID  : 0x{CAN_TX_ID:03X}")

    msg = can.Message(
        arbitration_id=CAN_TX_ID,
        data=frame,
        is_extended_id=False
    )
    try:
        bus.send(msg)
    except Exception as e:
        if verbose:
            print(f"   ❌ خطأ في الإرسال: {e}")
        return False
    if verbose:
        print(f"   ✅ تم الإرسال")

    # انتظار الرد من STM32
    if verbose:
        print(f"⏳ انتظار الرد (timeout={TIMEOUT}s)...")
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        try:
            reply = bus.recv(timeout=0.1)
        except Exception:
            break
        if reply is None:
            continue
        if DEBUG_BUS:
            print(f"   [bus] ID=0x{reply.arbitration_id:03X} DLC={reply.dlc} "
                  f"data={' '.join(f'{b:02X}' for b in reply.data)}")
        if reply.arbitration_id == CAN_RX_ID:
            data = reply.data
            if verbose:
                print(f"📥 رد مستقبَل:")
                print(f"   CAN ID  : 0x{reply.arbitration_id:03X}")
                print(f"   البيانات: {' '.join(f'{b:02X}' for b in data)}")
            if len(data) >= 3 and data[0] == 0xCC and data[1] == 0xBA:
                ack_cmd = data[2]
                ack_name = COMMANDS.get(ack_cmd, f'Unknown(0x{ack_cmd:02X})')
                if verbose:
                    print(f"   ✅ ACK لأمر: {ack_name} (0x{ack_cmd:02X})")
                if ack_cmd != cmd:
                    if verbose:
                        print(f"   ⚠️  ACK لأمر مختلف! أُرسل=0x{cmd:02X} ACK=0x{ack_cmd:02X}")
                return True
            else:
                if verbose:
                    print(f"   ⚠️  رسالة بدون رأس صحيح")
        else:
            if verbose and not DEBUG_BUS:
                print(f"   [أخرى] ID=0x{reply.arbitration_id:03X} "
                      f"data={' '.join(f'{b:02X}' for b in reply.data)}")

    if verbose:
        print(f"   ❌ لا يوجد رد خلال {TIMEOUT}s")
    return False

def send_raw_and_expect(bus: can.BusABC, data: bytes, expected_ack_cmd: int | None,
                        timeout: float = TIMEOUT, verbose: bool = True) -> bool:
    """
    إرسال إطار خام والتحقق من نتيجة ACK.
    - expected_ack_cmd = قيمة أمر متوقعة في ACK
    - expected_ack_cmd = None => نتوقع عدم وجود ACK
    """
    if verbose:
        print(f"\n📤 إرسال خام: {' '.join(f'{b:02X}' for b in data)}  (ID=0x{CAN_TX_ID:03X})")

    msg = can.Message(arbitration_id=CAN_TX_ID, data=data, is_extended_id=False)
    try:
        bus.send(msg)
    except Exception as e:
        if verbose:
            print(f"   ❌ خطأ في الإرسال: {e}")
        return False

    deadline = time.time() + timeout
    rx_count = 0
    while time.time() < deadline:
        try:
            reply = bus.recv(timeout=0.1)
        except Exception:
            break
        if reply is None:
            continue
        rx_count += 1
        if DEBUG_BUS:
            print(f"   [bus] ID=0x{reply.arbitration_id:03X} DLC={reply.dlc} "
                  f"data={' '.join(f'{b:02X}' for b in reply.data)}")
        if reply.arbitration_id != CAN_RX_ID:
            continue

        rx = bytes(reply.data)
        if len(rx) < 3 or rx[0] != 0xCC or rx[1] != 0xBA:
            continue

        ack_cmd = rx[2]
        if expected_ack_cmd is None:
            if verbose:
                print(f"   ❌ وُجد ACK غير متوقع: CMD=0x{ack_cmd:02X}")
            return False

        if ack_cmd == expected_ack_cmd:
            if verbose:
                print(f"   ✅ ACK صحيح: CMD=0x{ack_cmd:02X}")
            return True

        if verbose:
            print(f"   ❌ ACK مختلف: متوقع 0x{expected_ack_cmd:02X}, مستلم 0x{ack_cmd:02X}")
        return False

    if DEBUG_BUS and rx_count == 0 and verbose:
        print("   ⚠️ debug: لم يُستقبل أي إطار على الـ host خلال المهلة — غالبًا الـ bus صامت")
        print("      من جهة المحلل، أو CANH/CANL غير موصولين، أو bitrate مختلف، أو المنفذ خطأ.")

    if expected_ack_cmd is None:
        if verbose:
            print("   ✅ لا يوجد ACK (كما هو متوقع)")
        return True

    if verbose:
        print("   ❌ لم يصل ACK")
    return False

# ─── الاستماع فقط ────────────────────────────────────────────
def listen_mode(bus: can.BusABC, duration: float = 10.0):
    print(f"\n👂 وضع الاستماع لمدة {duration} ثانية... (Ctrl+C للخروج)")
    deadline = time.time() + duration
    count = 0
    try:
        while time.time() < deadline:
            msg = bus.recv(timeout=0.5)
            if msg:
                count += 1
                ts = time.strftime('%H:%M:%S')
                print(f"[{ts}][{count:04d}] ID=0x{msg.arbitration_id:03X}  "
                      f"DLC={msg.dlc}  "
                      f"data={' '.join(f'{b:02X}' for b in msg.data)}")
    except KeyboardInterrupt:
        pass
    print(f"تم استقبال {count} رسالة.")

# ─── اختبار جميع الأوامر تلقائياً مع إحصائيات ───────────────
def test_all_commands(bus: can.BusABC, delay: float = 0.5):
    print("\n" + "═"*55)
    print("  🔄 اختبار جميع الأوامر الـ 17 تلقائياً")
    print("═"*55)
    results = {}
    for i, cmd_val in enumerate(ALL_CMDS, 1):
        cmd_name = COMMANDS[cmd_val]
        print(f"\n[{i:02d}/{len(ALL_CMDS)}] {cmd_name} (0x{cmd_val:02X})", end='  ', flush=True)
        ok = send_command(bus, cmd_val, verbose=False)
        results[cmd_val] = ok
        status = "✅ OK" if ok else "❌ TIMEOUT"
        print(status)
        time.sleep(delay)

    # ─── ملخص النتائج ───────────────────────────────────────
    print("\n" + "═"*55)
    print("  📊 ملخص نتائج الاختبار")
    print("═"*55)
    passed = sum(1 for v in results.values() if v)
    failed = len(results) - passed

    for cmd_val, ok in results.items():
        icon = "✅" if ok else "❌"
        print(f"  {icon}  0x{cmd_val:02X}  {COMMANDS[cmd_val]}")

    print("─"*55)
    print(f"  إجمالي: {len(results)}  |  نجح: {passed}  |  فشل: {failed}")
    if failed == 0:
        print("  🎉 جميع الأوامر نجحت!")
    else:
        print(f"  ⚠️  {failed} أمر لم يستجب. تحقق من التوصيلات.")
    print("═"*55)
    return passed, failed

# ─── اختبار أزواج الأوامر (تشغيل/إيقاف) ────────────────────
def test_pairs(bus: can.BusABC, delay: float = 1.0, verbose: bool = True):
    """اختبار أزواج On/Off بفاصل زمني"""
    pairs = [
        (0x01, 0x02, 'CMD_1'),
        (0x03, 0x04, 'CMD_2'),
        (0x05, 0x06, 'CMD_3'),
        (0x07, 0x08, 'CMD_4'),
        (0x09, 0x0A, 'CMD_5'),
        (0x0B, 0x0C, 'CMD_6'),
        (0x0D, 0x0E, 'CMD_7'),
        (0x10, 0x11, 'CMD_9'),
    ]
    print("\n" + "═"*55)
    print("  🔀 اختبار أزواج On/Off")
    print("═"*55)
    for cmd_on, cmd_off, label in pairs:
        print(f"\n  ▶ {label}:")
        ok_on = send_command(bus, cmd_on, verbose=verbose)
        if not verbose:
            print(f"    ON (0x{cmd_on:02X})  : {'✅ OK' if ok_on else '❌ TIMEOUT'}")
        time.sleep(delay)
        ok_off = send_command(bus, cmd_off, verbose=verbose)
        if not verbose:
            print(f"    OFF(0x{cmd_off:02X}) : {'✅ OK' if ok_off else '❌ TIMEOUT'}")
        time.sleep(delay)

def test_protocol_sanity(bus: can.BusABC):
    """اختبار 3 حالات: valid, bad_crc, unknown_cmd."""
    print("\n" + "═"*55)
    print("  🧪 Protocol Sanity Tests (3 حالات)")
    print("═"*55)

    results = {}

    # 1) valid: أمر معروف + CRC صحيح => ACK متوقع
    valid_cmd = 0x01
    valid_frame = build_frame(valid_cmd)
    print("\n[1/3] valid frame (known cmd + good CRC)")
    results["valid"] = send_raw_and_expect(bus, valid_frame, expected_ack_cmd=valid_cmd, verbose=True)

    # 2) bad_crc: نفس الأمر لكن CRC فاسد => لا ACK
    bad_crc = bytearray(valid_frame)
    bad_crc[3] ^= 0x01
    print("\n[2/3] bad CRC frame")
    results["bad_crc"] = send_raw_and_expect(bus, bytes(bad_crc), expected_ack_cmd=None, verbose=True)

    # 3) unknown_cmd: أمر غير معروف لكن CRC صحيح => ACK بنفس القيمة (حسب firmware الحالي)
    unknown_cmd = 0x55
    unknown_frame = build_frame(unknown_cmd)
    print("\n[3/3] unknown command (0x55) + good CRC")
    results["unknown_cmd"] = send_raw_and_expect(bus, unknown_frame, expected_ack_cmd=unknown_cmd, verbose=True)

    print("\n" + "─"*55)
    passed = sum(1 for ok in results.values() if ok)
    for k, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {k}")
    print(f"  النتيجة: {passed}/{len(results)}")
    print("═"*55)
    if passed < len(results):
        print("\n  💡 تشخيص سريع إذا فشل valid أو unknown_cmd:")
        print("     • شغّل: python3 can_test.py --sanity --debug-rx")
        print("     • إن لم يظهر أي [bus] أثناء الانتظار: المحلل لا يرى حركة أو منفذ/Bitrate خاطئ.")
        print("     • إن ظهر 0x011 فقط بدون 0x100: الـ MCU لا يرد — تحقق من CANH/L، المقاومة 120Ω،")
        print("       ومزود الـ transceiver على الـ STM32، وعدم وضع المحلل على «listen-only»")
        print("       (في وضع listen-only قد لا يُقرّ إطارات الـ MCU في خانة ACK فتفشل الإرسال).")
    return passed, len(results) - passed

# ─── القائمة التفاعلية ───────────────────────────────────────
def interactive_menu(bus: can.BusABC):
    print("\n" + "═"*55)
    print("  قائمة الاختبار التفاعلي - جميع الأوامر")
    print("═"*55)
    print("  0  - استماع (Monitor) لمدة 10 ثواني")
    print("  ── الأوامر الفردية ──")
    for cmd_val, name in COMMANDS.items():
        print(f"  {cmd_val:02X}  - {name}")
    print("  ─────────────────────────────────────────────")
    print("  A  - اختبار جميع الأوامر الـ 17 تلقائياً")
    print("  P  - اختبار أزواج On/Off")
    print("  N  - اختبار 3 حالات (valid / bad_crc / unknown_cmd)")
    print("  T  - نبضات TX لرؤية ليد الإرسال على محوّل USB-CAN")
    print("  C  - اختبار CRC الذاتي")
    print("  Q  - خروج")
    print("═"*55)

    while True:
        choice = input("\nاختر (hex أو حرف) > ").strip().upper()
        if choice == 'Q':
            break
        elif choice == '0':
            listen_mode(bus, 10.0)
        elif choice == 'A':
            test_all_commands(bus, delay=0.5)
        elif choice == 'P':
            test_pairs(bus, delay=1.0)
        elif choice == 'N':
            test_protocol_sanity(bus)
        elif choice == 'T':
            pulse_adapter_tx_led(bus, count=40, interval_s=0.08)
        elif choice == 'C':
            self_test_crc()
        else:
            # محاولة تفسير الإدخال كرقم hex
            try:
                cmd_val = int(choice, 16)
                if cmd_val in COMMANDS:
                    send_command(bus, cmd_val, verbose=True)
                else:
                    print(f"❓ أمر غير معروف: 0x{cmd_val:02X}")
                    print(f"   الأوامر المتاحة: 0x01 .. 0x11")
            except ValueError:
                print("❓ اختيار غير معروف. اكتب رقم hex (مثل: 01) أو حرف (A/P/C/Q/0)")

# ─── نقطة الدخول ────────────────────────────────────────────
def main():
    global DEBUG_BUS
    DEBUG_BUS = '--debug-rx' in sys.argv

    if '--list-ports' in sys.argv:
        print("منافذ تسلسلية محتملة لمحوّل USB↔CAN:")
        pl = discover_serial_ports()
        for p in pl:
            print(f"  {p}")
        if not pl:
            print("  (لا يوجد /dev/ttyACM* أو /dev/ttyUSB*)")
        print("\nللإجبار على منفذ:  python3 can_test.py --channel /dev/ttyACM2")
        print("أو:  export CAN_TEST_CHANNEL=/dev/ttyACM2")
        return

    print("=" * 55)
    print("  CAN Test Tool - STM32L431  (v2.0 - Full Protocol)")
    print(f"  Interface : {CAN_INTERFACE}  (slcan)")
    print(f"  منافذ مرشّحة: أولًا {parse_channel_from_argv() or os.environ.get('CAN_TEST_CHANNEL') or CAN_CHANNEL} ثم المكتشفة")
    print(f"  Baud Rate : {CAN_BITRATE} bps")
    print(f"  TX CAN ID : 0x{CAN_TX_ID:03X}  |  RX CAN ID : 0x{CAN_RX_ID:03X}")
    print(f"  الأوامر   : {len(COMMANDS)} أمر (0x01 .. 0x{max(COMMANDS):02X})")
    if DEBUG_BUS:
        print("  🐞 --debug-rx : طباعة كل إطار يُستقبل على الـ bus أثناء انتظار الـ ACK")
    if '--pulse-tx' in sys.argv:
        print("  🔆 --pulse-tx : نبضات إرسال لرؤية ليد TX على محوّل USB-CAN")
    print("=" * 55)

    # اختبار CRC الذاتي أولاً (لا يحتاج اتصال CAN)
    if '--no-crc-test' not in sys.argv:
        self_test_crc()

    # إذا أُعطي وسيط --auto نبدأ الاختبار الكامل مباشرة
    auto_mode = '--auto' in sys.argv
    sanity_mode = '--sanity' in sys.argv
    pulse_tx_mode = '--pulse-tx' in sys.argv

    bus, used_ch, _ = open_can_bus()

    if bus is None:
        print("\n❌ تعذّر فتح قناة CAN بعد كل المحاولات.")
        print("\nتأكد من:")
        print("  1. توصيل محوّل USB-CAN وتشغيله (انظر adapter_alibaba_extract.txt)")
        print("  2. صلاحيات المنفذ: sudo chmod a+rw /dev/ttyACM*")
        print("  3. تحديد المنفذ: --channel /dev/ttyACM0  أو  export CAN_TEST_CHANNEL=...")
        print("  4. python3 can_test.py --list-ports  لعرض المنافذ")
        print("  5. تركيب مقاومات الإنهاء 120Ω على CANH/CANL عند الحاجة")
        sys.exit(1)

    try:
        if auto_mode:
            test_all_commands(bus, delay=0.5)
        elif sanity_mode:
            test_protocol_sanity(bus)
        elif pulse_tx_mode:
            pulse_adapter_tx_led(bus, count=40, interval_s=0.08)
        else:
            interactive_menu(bus)
    finally:
        try:
            bus.shutdown()
        except Exception:
            pass
        print("\n🔌 تم إغلاق قناة CAN")

if __name__ == '__main__':
    main()
