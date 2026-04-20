from m5stack import *
from m5ui import *
from uiflow import *
import machine
import neopixel
import time
import unit
import network
import random
import math  # 💡 引入数学库，用于绘制圆形和旋转动画
from umqtt.simple import MQTTClient

# --- 配置信息 ---
WIFI_SSID = "iPhone"     
WIFI_PASS = "loveyou3000"   
PUB_CMD = b"LCASH/commands"  
PUB_STATUS = b"LCASH/status" 

DUTY_FREE = 0    
DUTY_FWD = 10    

# --- 硬件初始化 ---
try: 
    gesture_0 = unit.get(unit.GESTURE, unit.PORTA)
    gesture_0.begin()
except: gesture_0 = None

try:
    servo_fan = machine.PWM(machine.Pin(26), freq=50)
    servo_fan.duty(DUTY_FREE)
except: servo_fan = None

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

# --- 状态变量 ---
fan_on = False  
light_on = False
light_colors = [0xFFFFFF, 0xFFD700, 0x00BFFF, 0x2ECC71]
color_idx = 0
pending_msg = ""
fan_angle = 0         # 风扇旋转角度
last_anim_time = 0    # 动画刷新时间

# --- 🎨 可爱动画 UI 绘制引擎 ---

def init_ui():
    lcd.clear(0x141414) 
    # 顶部可爱的橘色厨房主题状态栏
    lcd.rect(0, 0, 320, 35, 0xE67E22, 0xE67E22) 
    lcd.font(lcd.FONT_DejaVu18)
    lcd.print("Node 4: Magic Kitchen", 55, 8, 0xFFFFFF)
    
    # 左侧风扇卡片
    lcd.rect(10, 45, 145, 180, 0x2C3E50, 0x2C3E50)
    lcd.print("FAN MOTOR", 20, 55, 0xFFFFFF)
    
    # 右侧手势灯光卡片
    lcd.rect(165, 45, 145, 180, 0x2C3E50, 0x2C3E50)
    lcd.print("MAGIC LED", 185, 55, 0xFFFFFF)

def draw_fan_anim():
    cx, cy, r = 82, 125, 30
    # 清空扇叶区域
    lcd.circle(cx, cy, r+2, 0x2C3E50, 0x2C3E50) 
    lcd.circle(cx, cy, r+1, 0x7F8C8D) # 外边框
    
    color = 0x2ECC71 if fan_on else 0x95A5A6
    # 绘制三片旋转扇叶
    for i in range(3):
        a = math.radians(fan_angle + i * 120)
        x2 = int(cx + r * math.cos(a))
        y2 = int(cy + r * math.sin(a))
        lcd.line(cx, cy, x2, y2, color)
    lcd.circle(cx, cy, 6, color, color) # 轴心
    
    # 底部状态文字
    lcd.rect(35, 180, 90, 30, 0x2C3E50, 0x2C3E50)
    lcd.font(lcd.FONT_DejaVu24)
    lcd.print("ON" if fan_on else "OFF", 60, 185, color)

def draw_lightbulb_anim():
    cx, cy = 237, 125
    bg_color = 0x2C3E50
    # 局部刷新右侧卡片中间区域
    lcd.rect(175, 80, 125, 100, bg_color, bg_color) 
    
    bulb_color = light_colors[color_idx] if light_on else 0x555555
    
    # 发光射线动画 (开灯时显示)
    if light_on:
        for a in range(0, 360, 45):
            rad = math.radians(a)
            # 射线距离
            x1 = cx + int(22 * math.cos(rad))
            y1 = cy + int(22 * math.sin(rad))
            x2 = cx + int(32 * math.cos(rad))
            y2 = cy + int(32 * math.sin(rad))
            lcd.line(x1, y1, x2, y2, bulb_color)
            
    # 灯泡底座
    lcd.rect(cx-12, cy+15, 24, 15, 0x7F8C8D, 0x7F8C8D)
    lcd.rect(cx-8, cy+30, 16, 6, 0x555555, 0x555555)
    # 灯泡玻璃主体
    lcd.circle(cx, cy, 20, bulb_color, bulb_color)
    
    # 给灯泡画个可爱的笑脸 :)
    if light_on:
        # 眼睛
        lcd.circle(cx-7, cy-3, 2, 0x000000, 0x000000)
        lcd.circle(cx+7, cy-3, 2, 0x000000, 0x000000)
        # 简单的微笑弧线 (用三个点模拟)
        lcd.circle(cx, cy+7, 4, 0x000000, 0x000000)
        lcd.circle(cx, cy+6, 4, bulb_color, bulb_color) # 遮挡上半部分形成微笑

    # 底部状态文字
    lcd.rect(185, 180, 90, 30, 0x2C3E50, 0x2C3E50)
    lcd.font(lcd.FONT_DejaVu24)
    lcd.print("ON" if light_on else "OFF", 215, 185, bulb_color if light_on else 0x95A5A6)

# --- 核心逻辑 ---

def do_fan(is_on):
    global fan_on
    fan_on = is_on
    if servo_fan:
        servo_fan.duty(DUTY_FWD if is_on else DUTY_FREE)
    draw_fan_anim() # 💡 更新风扇UI
    try: mqtt.publish(PUB_STATUS, '{"fan": true}' if is_on else '{"fan": false}')
    except: pass

def mqtt_cb(topic, msg):
    global pending_msg
    try: pending_msg = msg.decode('utf-8').strip().upper()
    except: pass

# --- 联网 ---
lcd.clear(0x141414)
lcd.font(lcd.FONT_DejaVu18)
lcd.print("Connecting WiFi...", 10, 50, 0xFFFFFF)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    wlan.connect(WIFI_SSID, WIFI_PASS)
    while not wlan.isconnected(): time.sleep(0.5)

mqtt = MQTTClient("N4_"+str(random.randint(1,9999)), "broker.emqx.io")
mqtt.set_callback(mqtt_cb)
try:
    mqtt.connect()
    mqtt.subscribe(PUB_CMD)
    mqtt.sock.setblocking(False)
    lcd.print("System Ready!", 10, 80, 0x00FF00)
    time.sleep(1)
except: pass

# 💡 初始化界面渲染
init_ui()
draw_fan_anim()
draw_lightbulb_anim()

# --- 主循环 ---
while True:
    now = time.ticks_ms()
    
    try: mqtt.check_msg()
    except: pass

    if pending_msg != "":
        raw = pending_msg
        pending_msg = "" 
        if "FAN:ON" in raw: do_fan(True)
        elif "FAN:OFF" in raw: do_fan(False)

    # 💡 动画高帧率刷新核心 (仅控制风扇旋转)
    if now - last_anim_time > 60:
        if fan_on:
            fan_angle = (fan_angle + 20) % 360
            draw_fan_anim()
        last_anim_time = now

    # 手势检测 (控制氛围灯与可爱的灯泡 UI)
    if gesture_0 is not None:
        try:
            raw_val = gesture_0.get_gesture()
            g_val = str(raw_val).lower().strip()
            if g_val not in ["0", "none", ""]:
                ui_changed = False
                if g_val in ["3", "up", "8"]: 
                    light_on = True
                    set_led_color(light_colors[color_idx])
                    ui_changed = True
                elif g_val in ["4", "down"]: 
                    light_on = False
                    set_led_color(0x000000)
                    ui_changed = True
                elif g_val in ["1", "2", "left", "right"]: 
                    color_idx = (color_idx + 1) % len(light_colors)
                    if light_on: set_led_color(light_colors[color_idx])
                    ui_changed = True
                
                # 只要手势改变了灯光，就刷新灯泡动画
                if ui_changed:
                    draw_lightbulb_anim()
        except: pass

    time.sleep_ms(20)