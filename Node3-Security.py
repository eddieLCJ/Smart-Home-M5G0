from m5stack import *
from m5ui import *
from uiflow import *
import machine
import neopixel
import time
import unit
import network
import random
from m5mqtt import M5mqtt

# ==========================================
# 0. 网络与 MQTT 初始化 (终极防崩溃版)
# ==========================================
WIFI_SSID = "iPhone"
WIFI_PASS = "loveyou3000"

m5mqtt = None
wifi_ok = False

lcd.clear(0x141414)
lcd.font(lcd.FONT_DejaVu18)
lcd.print("Awaking Node 3...", 10, 10, 0x88C0D0)
lcd.print("Connecting WiFi", 10, 35, 0xFFFFFF)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# 核心修复 1：清空 ESP32 底层残留的死锁状态
try:
    wlan.disconnect()
    time.sleep_ms(500)
except Exception:
    pass

if not wlan.isconnected():
    try:
        wlan.connect(WIFI_SSID, WIFI_PASS) 
    except Exception:
        pass
        
    # 核心修复 2：彻底抛弃导致静默崩溃的 lcd.LAST_X，改用手动坐标
    dot_x = 160
    for t in range(10): # 强制最多只循环 10 次 (10秒超时)
        if wlan.isconnected():
            break
        lcd.print(".", dot_x, 35, 0xFFFFFF)
        dot_x += 10
        time.sleep(1)

wifi_ok = wlan.isconnected()

if wifi_ok:
    lcd.clear(0x141414)
    lcd.print("Wi-Fi Connected!", 10, 10, 0x2ECC71)
    client_id = "LCASH_N3_" + str(random.randint(1000, 9999))
    try:
        m5mqtt = M5mqtt(client_id, 'broker.emqx.io', 1883, '', '', 300)
        m5mqtt.start()
        lcd.print("MQTT Started!", 10, 35, 0x2ECC71)
        time.sleep(1)
    except Exception as e:
        lcd.print("MQTT Error!", 10, 35, 0xE74C3C)
        time.sleep(2)
else:
    lcd.clear(0x141414)
    lcd.print("Wi-Fi Failed!", 10, 10, 0xE74C3C)
    lcd.print("Start Offline Mode", 10, 35, 0xF39C12)
    time.sleep(2)

def publish_security_event(event_type, detail):
    """向主控台发送安防状态 (硬拼接)"""
    global m5mqtt
    if m5mqtt is None: 
        return
    payload = '{"node": 3, "event": "' + str(event_type) + '", "detail": "' + str(detail) + '"}'
    try:
        m5mqtt.publish('LCASH/security', payload)
        print("📤 [Node 3] 发送成功:", payload)
    except Exception as e:
        pass


# ==========================================
# 1. 硬件初始化
# ==========================================
try: tof_0 = unit.get(unit.TOF, unit.PORTA) 
except: tof_0 = None
try: finger_0 = unit.get(unit.FINGER, unit.PORTC)
except: finger_0 = None
try: np = neopixel.NeoPixel(machine.Pin(15), 10)
except: np = None

def set_led_color(hex_color):
    if np is None: return
    try:
        r = (hex_color >> 16) & 0xFF
        g = (hex_color >> 8) & 0xFF
        b = hex_color & 0xFF
        np.fill((r, g, b))
        np.write()
    except: pass


# ==========================================
# 2. 底层 UI 绘制引擎 
# ==========================================
def draw_shield(x, y):
    lcd.triangle(x, y, x+20, y, x+10, y+25, 0xF1C40F, 0xF1C40F)
    lcd.rect(x+2, y+2, 16, 8, 0xE67E22, 0xE67E22)

def draw_person_icon(x, y):
    lcd.circle(x+10, y+5, 5, 0x00BFFF, 0x00BFFF)
    lcd.rect(x+5, y+12, 10, 15, 0x00BFFF, 0x00BFFF)

def draw_fingerprint_icon(x, y):
    c = 0x00BFFF; bg = 0x2C3E50
    lcd.circle(x+10, y+10, 8, c); lcd.circle(x+10, y+10, 5, c); lcd.circle(x+10, y+10, 2, c)
    lcd.rect(x, y+10, 20, 12, bg, bg)
    lcd.line(x+2, y+10, x+2, y+18, c); lcd.line(x+6, y+10, x+6, y+22, c)
    lcd.line(x+10, y+10, x+10, y+20, c); lcd.line(x+14, y+10, x+14, y+22, c)
    lcd.line(x+18, y+10, x+18, y+18, c)

def init_ui():
    lcd.clear(0x141414) 
    lcd.rect(0, 0, 320, 35, 0x2980B9, 0x2980B9)
    draw_shield(10, 5)
    lcd.font(lcd.FONT_DejaVu18)
    lcd.print("Security Node", 40, 8, 0xFFFFFF)
    
    lcd.rect(10, 45, 145, 80, 0x2C3E50, 0x2C3E50)
    draw_person_icon(20, 65)
    lcd.font(lcd.FONT_Default) 
    lcd.print("PROXIMITY", 50, 55, 0xBDC3C7)
    
    lcd.rect(165, 45, 145, 80, 0x2C3E50, 0x2C3E50)
    draw_fingerprint_icon(175, 65) 
    lcd.font(lcd.FONT_Default) 
    lcd.print("FINGERPRINT", 205, 55, 0xBDC3C7)
    
    lcd.rect(10, 135, 300, 95, 0x34495E, 0x34495E)

def update_dist_ui(txt):
    lcd.rect(45, 80, 110, 35, 0x2C3E50, 0x2C3E50) 
    lcd.font(lcd.FONT_DejaVu18)
    lcd.print(txt, 50, 85, 0xFFFFFF)

def update_finger_ui(txt, color=0xFFFFFF):
    lcd.rect(180, 80, 150, 35, 0x2C3E50, 0x2C3E50) 
    lcd.font(lcd.FONT_DejaVu18)
    lcd.print(str(txt)[:11], 195, 85, color) 

def update_mode_ui_text(txt, color):
    lcd.rect(20, 140, 285, 35, 0x34495E, 0x34495E) 
    lcd.font(lcd.FONT_DejaVu18)
    lcd.print(txt, 25, 145, color)

def update_hint_ui(txt, color=0x95A5A6):
    lcd.rect(20, 200, 290, 35, 0x34495E, 0x34495E) 
    lcd.font(lcd.FONT_Default)
    lcd.print(txt, 25, 205, color)


# ==========================================
# 3. 核心逻辑与按键绑定
# ==========================================
sys_mode = "SECURITY" 
is_alarming = False      
is_processing = False    
last_dist_str = ""       

def refresh_mode_state():
    global is_alarming, is_processing
    is_alarming = False
    is_processing = False
    if sys_mode == "SECURITY":
        update_mode_ui_text("MODE: SECURITY", 0x2ECC71)
        update_hint_ui("Btn A: Config | ToF Guarding", 0x95A5A6)
        update_finger_ui("READY", 0xFFFFFF)
        set_led_color(0x000000)
    else:
        update_mode_ui_text("MODE: CONFIG", 0xF39C12)
        update_hint_ui("B: Clear All | C: Add Finger", 0x95A5A6)
        update_finger_ui("PAUSED", 0x7F8C8D)
        set_led_color(0xF39C12)

def btnA_press():
    global sys_mode
    if not is_processing:
        sys_mode = "CONFIG" if sys_mode == "SECURITY" else "SECURITY"
        refresh_mode_state()

def btnB_press():
    global is_processing
    if sys_mode == "CONFIG" and finger_0 is not None and not is_processing:
        is_processing = True
        update_hint_ui("Clearing All Fingerprints...", 0xE74C3C)
        set_led_color(0xE74C3C)
        try:
            finger_0.removeAllUser() 
            time.sleep(1)
            update_hint_ui("All Cleared Successfully!", 0x2ECC71)
        except Exception:
            pass
        time.sleep(2)
        refresh_mode_state()

def btnC_press():
    global is_processing
    if sys_mode == "CONFIG" and finger_0 is not None and not is_processing:
        is_processing = True
        update_hint_ui("Place Finger NOW! (10s)", 0x3498DB)
        set_led_color(0x3498DB)
        
        try:
            try: finger_0.addUser(1, 1) 
            except TypeError: finger_0.addUser(1)    
        except Exception:
            pass
            
        start_t = time.ticks_ms()
        last_state = None
        is_success = False
        
        while time.ticks_ms() - start_t < 10000:
            try: current_state = finger_0.state
            except Exception: current_state = "Err"
                
            if str(current_state) != str(last_state):
                update_finger_ui("ST:" + str(current_state), 0xF1C40F)
                last_state = current_state
                
            if current_state == 1 or "success" in str(current_state).lower():
                is_success = True
                break
            if "fail" in str(current_state).lower() or current_state == 2:
                break
            time.sleep_ms(100)
            
        if is_success:
            update_hint_ui("Success! Fingerprint ID 1 Added.", 0x2ECC71)
            update_finger_ui("OK", 0x2ECC71)
            set_led_color(0x2ECC71)
        else:
            update_hint_ui("Failed. Final State: " + str(last_state), 0xE74C3C)
            set_led_color(0xE74C3C)
            
        time.sleep(3)
        refresh_mode_state()

btnA.wasPressed(btnA_press)
btnB.wasPressed(btnB_press)
btnC.wasPressed(btnC_press)

# --- 指纹识别回调 ---
def finger_matched(*args):
    if sys_mode == "SECURITY":
        uid = args[0] if len(args) > 0 else 1
        update_finger_ui("ID: " + str(uid), 0x2ECC71)
        update_hint_ui("Access Granted!", 0x2ECC71)
        set_led_color(0x2ECC71)
        publish_security_event("unlock_success", "ID_" + str(uid))
        time.sleep(2)
        refresh_mode_state() 

def finger_unknown(*args):
    if sys_mode == "SECURITY":
        update_finger_ui("UNKNOWN", 0xE74C3C)
        update_hint_ui("Access Denied!", 0xE74C3C)
        set_led_color(0xE74C3C)
        publish_security_event("unlock_failed", "Unknown_Finger") 
        time.sleep(2)
        refresh_mode_state()

if finger_0 is not None:
    try:
        try: finger_0.getUnknownCb(finger_unknown)
        except: pass
        finger_0.readFingerCb(finger_matched)
    except: pass


# ==========================================
# 4. 主循环 
# ==========================================
init_ui()
refresh_mode_state()

while True:
    try:
        if tof_0 is not None:
            dist = tof_0.distance
            current_dist_str = str(dist) + " mm"
            
            if current_dist_str != last_dist_str:
                update_dist_ui(current_dist_str) 
                last_dist_str = current_dist_str
            
            if sys_mode == "SECURITY" and not is_processing:
                if dist < 300:
                    if not is_alarming:
                        update_hint_ui("Warning: Proximity Alert!", 0xE74C3C)
                        set_led_color(0xE74C3C)
                        publish_security_event("intrusion_alert", str(dist) + "mm") 
                        is_alarming = True
                else:
                    if is_alarming:
                        update_hint_ui("Btn A: Config | ToF Guarding", 0x95A5A6)
                        set_led_color(0x000000)
                        publish_security_event("safe", "Area_Clear") 
                        is_alarming = False
    except Exception:
        pass

    wait_ms(100)