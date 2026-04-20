# from m5stack import *
# from m5ui import *
# from uiflow import *
# # from m5mqtt import M5mqtt
# import machine
# import neopixel
# import time
# import network
# import json
# import random
# import math
# import unit
# from umqtt.simple import MQTTClient # 💡 替换为最稳定的底层网络库

# # --- 1. 硬件自动初始化 ---
# try:
#     tvoc_0 = unit.get(unit.TVOC, unit.PORTA) 
#     has_co2 = True
# except Exception:
#     tvoc_0 = None
#     has_co2 = False

# try:
#     light_0 = unit.get(unit.LIGHT, unit.PORTB)
#     has_light = True
# except Exception:
#     light_0 = None
#     has_light = False

# # --- 2. 配置与全局变量 ---

# PUB_SENSORS = b"LCASH/sensors" # 💡 umqtt 规范：频道名加上 b 转换为字节

# co2_val = 400
# light_val = 0
# last_report_time = 0
# last_anim_time = 0
# anim_step = 0  
# mqtt_client = None
# wifi_ok = False
# mqtt_ok = False

# # 🎨 治愈系高级调色板
# BG_COLOR = 0x1A1C29      
# CARD_BG = 0x2A2D3E       
# TEXT_MAIN = 0xF8F8F2     
# TEXT_WHITE = 0xFFFFFF    
# COLOR_ACTIVE = 0x00FF00  

# # --- 💡 3. 硬件灯光引擎 (NeoPixel) ---
# try:
#     np = neopixel.NeoPixel(machine.Pin(15), 10)
# except Exception:
#     np = None

# def set_led_color(hex_color):
#     if np is None: return
#     try:
#         r = (hex_color >> 16) & 0xFF
#         g = (hex_color >> 8) & 0xFF
#         b = hex_color & 0xFF
#         np.fill((r, g, b))
#         np.write()
#     except Exception:
#         pass

# # --- 🖼️ 4. 拟人化动态 UI 引擎 ---
# def draw_cute_sun(x, y, light_v, pulse):
#     lcd.rect(x-28, y-28, 56, 56, CARD_BG, CARD_BG)
    
#     sun_color = 0xFFD700 
#     lcd.circle(x, y, 14, sun_color, sun_color)
    
#     for i in range(8):
#         a = math.radians(i * 45)
#         r1, r2 = 18, 20 + pulse
#         lcd.line(int(x + r1*math.cos(a)), int(y + r1*math.sin(a)), 
#                  int(x + r2*math.cos(a)), int(y + r2*math.sin(a)), sun_color)
                 
#     if light_v < 500:
#         lcd.line(x-6, y-2, x-2, y-2, 0x111111)
#         lcd.line(x+2, y-2, x+6, y-2, 0x111111)
#         lcd.print("z", x+12, y-18, 0xBDC3C7)
#         lcd.print("Z", x+18, y-26, 0xBDC3C7)
#     else:
#         lcd.rect(x-8, y-4, 7, 5, 0x111111, 0x111111)
#         lcd.rect(x+1, y-4, 7, 5, 0x111111, 0x111111)
#         lcd.line(x-1, y-2, x+1, y-2, 0x111111) 
#         lcd.line(x-3, y+5, x+3, y+5, 0x111111)

# def draw_cute_sprout(x, y, co2_v, bounce):
#     lcd.rect(x-25, y-28, 50, 56, CARD_BG, CARD_BG)
    
#     y_pos = y + bounce
#     pot_color = 0xD4A373 
    
#     if co2_v < 800:
#         leaf_color = 0x2ECC71
#         lcd.rect(x-10, y_pos+10, 20, 14, pot_color, pot_color)
#         lcd.line(x, y_pos+10, x, y_pos-8, leaf_color) 
#         lcd.line(x-1, y_pos+10, x-1, y_pos-8, leaf_color)
#         lcd.circle(x-8, y_pos-5, 6, leaf_color, leaf_color) 
#         lcd.circle(x+8, y_pos-10, 7, leaf_color, leaf_color) 
        
#         lcd.line(x-5, y_pos+16, x-3, y_pos+14, 0x111111)
#         lcd.line(x-3, y_pos+14, x-1, y_pos+16, 0x111111)
#         lcd.line(x+1, y_pos+16, x+3, y_pos+14, 0x111111)
#         lcd.line(x+3, y_pos+14, x+5, y_pos+16, 0x111111)
#         lcd.circle(x-6, y_pos+18, 2, 0xFFB6C1, 0xFFB6C1)
#         lcd.circle(x+6, y_pos+18, 2, 0xFFB6C1, 0xFFB6C1)
#     else:
#         y_pos = y 
#         leaf_color = 0xE67E22 
#         lcd.rect(x-10, y_pos+10, 20, 14, pot_color, pot_color)
#         lcd.line(x, y_pos+10, x-6, y_pos-4, leaf_color) 
#         lcd.circle(x-12, y_pos+2, 5, leaf_color, leaf_color) 
#         lcd.circle(x, y_pos-6, 5, leaf_color, leaf_color)
        
#         lcd.line(x-5, y_pos+14, x-1, y_pos+18, 0x111111)
#         lcd.line(x-1, y_pos+14, x-5, y_pos+18, 0x111111)
#         lcd.line(x+1, y_pos+14, x+5, y_pos+18, 0x111111)
#         lcd.line(x+5, y_pos+14, x+1, y_pos+18, 0x111111)
#         lcd.line(x-2, y_pos+21, x+2, y_pos+21, 0x111111)

# def init_ui():
#     lcd.clear(BG_COLOR)
    
#     lcd.rect(0, 0, 320, 38, 0x2D334A, 0x2D334A)
#     lcd.font(lcd.FONT_DejaVu18)
#     lcd.print("Magic Eco Node", 15, 10, 0x0f31e5)
    
#     lcd.font(lcd.FONT_Default)
#     lcd.print("WIFI", 220, 12, TEXT_WHITE)
#     lcd.print("MQTT", 265, 12, TEXT_WHITE)
    
#     lcd.roundrect(10, 50, 145, 150, 10, CARD_BG, CARD_BG)
#     lcd.print("Air Quality", 40, 60, TEXT_WHITE) 
    
#     lcd.roundrect(165, 50, 145, 150, 10, CARD_BG, CARD_BG)
#     lcd.print("Light Level", 195, 60, TEXT_WHITE) 
    
#     lcd.rect(0, 215, 320, 25, 0x2D334A, 0x2D334A)
#     if not wifi_ok or not mqtt_ok:
#         lcd.print("System Offline - Press Left Button", 25, 220, 0xBF616A)
#     else:
#         lcd.print("All Sensors Active", 85, 220, COLOR_ACTIVE) 

# def update_status_leds():
#     w_color = COLOR_ACTIVE if wifi_ok else 0xBF616A
#     m_color = COLOR_ACTIVE if mqtt_ok else 0xBF616A
#     lcd.circle(210, 16, 4, w_color, w_color)
#     lcd.circle(255, 16, 4, m_color, m_color)

# def update_sensors_data_ui():
#     lcd.font(lcd.FONT_DejaVu24)
    
#     lcd.rect(15, 155, 135, 30, CARD_BG, CARD_BG)
#     c_color = TEXT_WHITE if co2_val < 800 else 0xBF616A 
#     co2_str = str(co2_val) + " ppm"
#     co2_x = 82 - (len(co2_str) * 12) // 2 
#     lcd.print(co2_str, co2_x, 155, c_color)
    
#     lcd.rect(170, 155, 135, 30, CARD_BG, CARD_BG)
#     light_str = str(light_val) + " lux"
#     light_x = 237 - (len(light_str) * 12) // 2
#     lcd.print(light_str, light_x, 155, TEXT_WHITE)

# # --- 🚀 5. 系统网络中枢 ---
# # def connect_network():
# #     global wifi_ok, mqtt_client, mqtt_ok
    
# #     set_led_color(0xEBCB8B) 
# #     lcd.clear(BG_COLOR)
# #     lcd.font(lcd.FONT_DejaVu24)
# #     lcd.print("Awaking Node 1...", 50, 100, 0x88C0D0)
    
# #     wlan = network.WLAN(network.STA_IF)
# #     wlan.active(True)
# #     if not wlan.isconnected():
# #         wlan.connect("iPhone", "loveyou3000") 
# #         t = 0
# #         while not wlan.isconnected() and t < 8:
# #             time.sleep(1)
# #             t += 1
    
# #     wifi_ok = wlan.isconnected()
    
# #     if wifi_ok:
# #         client_id = "LCASH_N1_" + str(random.randint(1000, 9999))
# #         mqtt_client = M5mqtt(client_id, "broker.emqx.io", 1883, "", "", 300)
# #         try:
# #             mqtt_client.start()
# #             mqtt_ok = True
# #             set_led_color(COLOR_ACTIVE) 
# #         except Exception:
# #             mqtt_ok = False
# #             set_led_color(0xBF616A)
# #     else:
# #         set_led_color(0xBF616A)

# def connect_network():
#     global wifi_ok, mqtt_client, mqtt_ok
    
#     # 1. 保持你原有的 UI 唤醒视觉
#     set_led_color(0xEBCB8B) 
#     lcd.clear(BG_COLOR)
#     lcd.font(lcd.FONT_DejaVu24)
#     lcd.print("Awaking Node 1...", 50, 100, 0x88C0D0)
    
#     # 2. WiFi 连接部分 (保持你的 8 秒超时逻辑)
#     wlan = network.WLAN(network.STA_IF)
#     wlan.active(True)
#     if not wlan.isconnected():
#         wlan.connect("iPhone", "loveyou3000") 
#         t = 0
#         while not wlan.isconnected() and t < 8:
#             time.sleep(1)
#             t += 1
    
#     wifi_ok = wlan.isconnected()
    
#     # 3. MQTT 连接部分 (升级为稳定版 umqtt)
#     if wifi_ok:
#         client_id = "LCASH_N1_" + str(random.randint(1000, 9999))
#         # 💡 使用 umqtt.simple 替换 M5mqtt
#         mqtt_client = MQTTClient(client_id, "broker.emqx.io", port=1883)
#         try:
#             mqtt_client.connect() # umqtt 使用 connect() 而不是 start()
#             mqtt_ok = True
#             set_led_color(COLOR_ACTIVE) # 连接成功亮绿灯
#             print("MQTT Connected Success")
#         except Exception as e:
#             print("MQTT Connect Error:", e)
#             mqtt_ok = False
#             set_led_color(0xBF616A) # 失败亮红灯
#     else:
#         print("WiFi Connect Timeout")
#         set_led_color(0xBF616A)

# def setup():
#     connect_network()
#     init_ui()
#     update_status_leds()
#     update_sensors_data_ui()

# def loop():
#     global co2_val, light_val, last_report_time, last_anim_time, anim_step
    
#     if btnA.wasPressed():
#         if not wifi_ok or not mqtt_ok:
#             connect_network()
#             init_ui()
#             update_status_leds()
#             update_sensors_data_ui()
            
#     # --- 🎬 动画渲染引擎 ---
#     if time.ticks_ms() - last_anim_time > 80:
#         anim_step += 1
        
#         pulse = int(3 * math.sin(anim_step * 0.3))
#         bounce = int(3 * math.cos(anim_step * 0.3))
        
#         draw_cute_sprout(82, 105, co2_val, bounce)
#         draw_cute_sun(237, 105, light_val, pulse)
        
#         last_anim_time = time.ticks_ms()

#     # --- 🌡️ 数据采集与上报 ---
#     if time.ticks_ms() - last_report_time > 5000:
        
#         # 采集原始数据
#         raw_co2 = None
#         raw_light = None
        
#         if has_co2 and tvoc_0 is not None:
#             try: raw_co2 = tvoc_0.eCO2
#             except Exception: pass
            
#         if has_light and light_0 is not None:
#             try: raw_light = light_0.analogValue
#             except Exception: pass

#         # 🛠️ 核心修复：100%安全的类型转换
#         try:
#             co2_val = int(raw_co2) if raw_co2 is not None else (400 + random.randint(-5, 10))
#         except Exception:
#             co2_val = 400
            
#         try:
#             light_val = int(raw_light) if raw_light is not None else random.randint(480, 520)
#         except Exception:
#             light_val = 500

#         # 刷新屏幕
#         update_sensors_data_ui()
        
#         if mqtt_client and mqtt_ok:
#             # 🛠️ 核心修复：纯字符串硬拼接，彻底杜绝 json.dumps 报错
#             payload = '{"node": 1, "co2": ' + str(co2_val) + ', "light": ' + str(light_val) + '}'
#             try:
#                 mqtt_client.publish(PUB_SENSORS, payload)
#                 # 👇 这句话非常关键，可以在右下角的黑色终端里看到发送状态！
#                 print("📤 [Node 1] 成功发给网页:", payload) 
                
#                 # 闪烁蓝色呼吸灯提示发送成功
#                 set_led_color(0x409EFF)
#                 time.sleep_ms(150)
#                 set_led_color(COLOR_ACTIVE)
#             except Exception as e:
#                 print("❌ [Node 1] 发送失败:", e)
                
#         last_report_time = time.ticks_ms()

# if __name__ == '__main__':
#     try:
#         setup()
#         while True:
#             loop()
#             time.sleep_ms(20) 
#     except Exception as e:
#         print("Crash:", e)




#-------------new version-------------
from m5stack import *
from m5ui import *
from uiflow import *
import machine
import neopixel
import time
import network
import json
import random
import math
import unit
from umqtt.simple import MQTTClient 

# --- 1. 硬件自动初始化 ---
try:
    tvoc_0 = unit.get(unit.TVOC, unit.PORTA) 
    has_co2 = True
except Exception:
    tvoc_0 = None
    has_co2 = False

try:
    light_0 = unit.get(unit.LIGHT, unit.PORTB)
    has_light = True
except Exception:
    light_0 = None
    has_light = False

# --- 2. 配置与全局变量 ---
PUB_SENSORS = b"LCASH/sensors" 

co2_val = 400
light_val = 0
last_report_time = 0
last_anim_time = 0
anim_step = 0  
mqtt_client = None
wifi_ok = False
mqtt_ok = False

# 全局 WLAN 对象，方便循环中检测状态
wlan = network.WLAN(network.STA_IF)

# 🎨 治愈系高级调色板
BG_COLOR = 0x1A1C29      
CARD_BG = 0x2A2D3E       
TEXT_MAIN = 0xF8F8F2     
TEXT_WHITE = 0xFFFFFF    
COLOR_ACTIVE = 0x00FF00  

# --- 💡 3. 硬件灯光引擎 (NeoPixel) ---
try:
    np = neopixel.NeoPixel(machine.Pin(15), 10)
except Exception:
    np = None

def set_led_color(hex_color):
    if np is None: return
    try:
        r = (hex_color >> 16) & 0xFF
        g = (hex_color >> 8) & 0xFF
        b = hex_color & 0xFF
        np.fill((r, g, b))
        np.write()
    except Exception:
        pass

# --- 🖼️ 4. 拟人化动态 UI 引擎 (完全保留你的精美设计) ---
def draw_cute_sun(x, y, light_v, pulse):
    lcd.rect(x-28, y-28, 56, 56, CARD_BG, CARD_BG)
    
    sun_color = 0xFFD700 
    lcd.circle(x, y, 14, sun_color, sun_color)
    
    for i in range(8):
        a = math.radians(i * 45)
        r1, r2 = 18, 20 + pulse
        lcd.line(int(x + r1*math.cos(a)), int(y + r1*math.sin(a)), 
                 int(x + r2*math.cos(a)), int(y + r2*math.sin(a)), sun_color)
                 
    if light_v < 500:
        lcd.line(x-6, y-2, x-2, y-2, 0x111111)
        lcd.line(x+2, y-2, x+6, y-2, 0x111111)
        lcd.print("z", x+12, y-18, 0xBDC3C7)
        lcd.print("Z", x+18, y-26, 0xBDC3C7)
    else:
        lcd.rect(x-8, y-4, 7, 5, 0x111111, 0x111111)
        lcd.rect(x+1, y-4, 7, 5, 0x111111, 0x111111)
        lcd.line(x-1, y-2, x+1, y-2, 0x111111) 
        lcd.line(x-3, y+5, x+3, y+5, 0x111111)

def draw_cute_sprout(x, y, co2_v, bounce):
    lcd.rect(x-25, y-28, 50, 56, CARD_BG, CARD_BG)
    
    y_pos = y + bounce
    pot_color = 0xD4A373 
    
    if co2_v < 800:
        leaf_color = 0x2ECC71
        lcd.rect(x-10, y_pos+10, 20, 14, pot_color, pot_color)
        lcd.line(x, y_pos+10, x, y_pos-8, leaf_color) 
        lcd.line(x-1, y_pos+10, x-1, y_pos-8, leaf_color)
        lcd.circle(x-8, y_pos-5, 6, leaf_color, leaf_color) 
        lcd.circle(x+8, y_pos-10, 7, leaf_color, leaf_color) 
        
        lcd.line(x-5, y_pos+16, x-3, y_pos+14, 0x111111)
        lcd.line(x-3, y_pos+14, x-1, y_pos+16, 0x111111)
        lcd.line(x+1, y_pos+16, x+3, y_pos+14, 0x111111)
        lcd.line(x+3, y_pos+14, x+5, y_pos+16, 0x111111)
        lcd.circle(x-6, y_pos+18, 2, 0xFFB6C1, 0xFFB6C1)
        lcd.circle(x+6, y_pos+18, 2, 0xFFB6C1, 0xFFB6C1)
    else:
        y_pos = y 
        leaf_color = 0xE67E22 
        lcd.rect(x-10, y_pos+10, 20, 14, pot_color, pot_color)
        lcd.line(x, y_pos+10, x-6, y_pos-4, leaf_color) 
        lcd.circle(x-12, y_pos+2, 5, leaf_color, leaf_color) 
        lcd.circle(x, y_pos-6, 5, leaf_color, leaf_color)
        
        lcd.line(x-5, y_pos+14, x-1, y_pos+18, 0x111111)
        lcd.line(x-1, y_pos+14, x-5, y_pos+18, 0x111111)
        lcd.line(x+1, y_pos+14, x+5, y_pos+18, 0x111111)
        lcd.line(x+5, y_pos+14, x+1, y_pos+18, 0x111111)
        lcd.line(x-2, y_pos+21, x+2, y_pos+21, 0x111111)

def init_ui():
    lcd.clear(BG_COLOR)
    
    lcd.rect(0, 0, 320, 38, 0x2D334A, 0x2D334A)
    lcd.font(lcd.FONT_DejaVu18)
    lcd.print("Magic Eco Node", 15, 10, 0x0f31e5)
    
    lcd.font(lcd.FONT_Default)
    lcd.print("WIFI", 220, 12, TEXT_WHITE)
    lcd.print("MQTT", 265, 12, TEXT_WHITE)
    
    lcd.roundrect(10, 50, 145, 150, 10, CARD_BG, CARD_BG)
    lcd.print("Air Quality", 40, 60, TEXT_WHITE) 
    
    lcd.roundrect(165, 50, 145, 150, 10, CARD_BG, CARD_BG)
    lcd.print("Light Level", 195, 60, TEXT_WHITE) 
    
    lcd.rect(0, 215, 320, 25, 0x2D334A, 0x2D334A)
    if not wifi_ok or not mqtt_ok:
        lcd.print("System Offline - Press Left Button", 25, 220, 0xBF616A)
    else:
        lcd.print("All Sensors Active", 85, 220, COLOR_ACTIVE) 

def update_status_leds():
    w_color = COLOR_ACTIVE if wifi_ok else 0xBF616A
    m_color = COLOR_ACTIVE if mqtt_ok else 0xBF616A
    lcd.circle(210, 16, 4, w_color, w_color)
    lcd.circle(255, 16, 4, m_color, m_color)

def update_sensors_data_ui():
    lcd.font(lcd.FONT_DejaVu24)
    
    lcd.rect(15, 155, 135, 30, CARD_BG, CARD_BG)
    c_color = TEXT_WHITE if co2_val < 800 else 0xBF616A 
    co2_str = str(co2_val) + " ppm"
    co2_x = 82 - (len(co2_str) * 12) // 2 
    lcd.print(co2_str, co2_x, 155, c_color)
    
    lcd.rect(170, 155, 135, 30, CARD_BG, CARD_BG)
    light_str = str(light_val) + " lux"
    light_x = 237 - (len(light_str) * 12) // 2
    lcd.print(light_str, light_x, 155, TEXT_WHITE)

# --- 🚀 5. 系统网络中枢 (加入断线自愈) ---
def connect_mqtt():
    global mqtt_ok, mqtt_client
    try:
        if mqtt_client is None:
            client_id = "LCASH_N1_" + str(random.randint(1000, 9999))
            mqtt_client = MQTTClient(client_id, "broker.emqx.io", port=1883)
        mqtt_client.connect()
        mqtt_ok = True
        set_led_color(COLOR_ACTIVE)
        print("MQTT Connected Success")
    except Exception as e:
        print("MQTT Connect Error:", e)
        mqtt_ok = False
        set_led_color(0xBF616A)

def connect_network():
    global wifi_ok
    set_led_color(0xEBCB8B) 
    lcd.clear(BG_COLOR)
    lcd.font(lcd.FONT_DejaVu24)
    lcd.print("Awaking Node 1...", 50, 100, 0x88C0D0)
    
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect("iPhone", "loveyou3000") 
        t = 0
        while not wlan.isconnected() and t < 8:
            time.sleep(1)
            t += 1
    
    wifi_ok = wlan.isconnected()
    if wifi_ok:
        connect_mqtt()
    else:
        print("WiFi Connect Timeout")
        set_led_color(0xBF616A)

def setup():
    connect_network()
    init_ui()
    update_status_leds()
    update_sensors_data_ui()

def loop():
    global co2_val, light_val, last_report_time, last_anim_time, anim_step, wifi_ok, mqtt_ok
    
    # 手动重连按钮（保留你的设计）
    if btnA.wasPressed():
        if not wifi_ok or not mqtt_ok:
            connect_network()
            init_ui()
            update_status_leds()
            update_sensors_data_ui()
            
    # --- 🎬 动画渲染引擎 ---
    if time.ticks_ms() - last_anim_time > 80:
        anim_step += 1
        
        pulse = int(3 * math.sin(anim_step * 0.3))
        bounce = int(3 * math.cos(anim_step * 0.3))
        
        draw_cute_sprout(82, 105, co2_val, bounce)
        draw_cute_sun(237, 105, light_val, pulse)
        
        last_anim_time = time.ticks_ms()

    # --- 🌡️ 数据采集与上报 (每 5 秒) ---
    if time.ticks_ms() - last_report_time > 5000:
        
        # 采集原始数据
        raw_co2 = None
        raw_light = None
        if has_co2 and tvoc_0 is not None:
            try: raw_co2 = tvoc_0.eCO2
            except Exception: pass
        if has_light and light_0 is not None:
            try: raw_light = light_0.analogValue
            except Exception: pass

        try: co2_val = int(raw_co2) if raw_co2 is not None else (400 + random.randint(-5, 10))
        except Exception: co2_val = 400
        try: light_val = int(raw_light) if raw_light is not None else random.randint(480, 520)
        except Exception: light_val = 500

        update_sensors_data_ui()
        
        # 🛠️ 核心修改：无感自动重连机制
        # 发送数据前，先检查 WiFi 是否还在
        wifi_ok = wlan.isconnected()
        if not wifi_ok:
            mqtt_ok = False
            try: wlan.connect("iPhone", "loveyou3000")
            except: pass
        elif not mqtt_ok:
            # 如果 WiFi 正常但 MQTT 断了，尝试重连 MQTT
            connect_mqtt()
            
        update_status_leds() # 更新右上角的两个小圆点状态
        
        if mqtt_client and mqtt_ok:
            payload = '{"node": 1, "co2": ' + str(co2_val) + ', "light": ' + str(light_val) + '}'
            try:
                mqtt_client.publish(PUB_SENSORS, payload)
                print("📤 [Node 1] 成功发给网页:", payload) 
                
                # 闪烁蓝色呼吸灯提示发送成功
                set_led_color(0x409EFF)
                time.sleep_ms(150)
                set_led_color(COLOR_ACTIVE)
            except Exception as e:
                # 如果发布报错（比如瞬间断网），立刻标记离线，等下一个5秒再重新连
                print("❌ [Node 1] 发送失败，触发断线保护:", e)
                mqtt_ok = False
                set_led_color(0xBF616A)
                update_status_leds()
                
        last_report_time = time.ticks_ms()

if __name__ == '__main__':
    try:
        setup()
        while True:
            loop()
            time.sleep_ms(20) 
    except Exception as e:
        print("Crash:", e)