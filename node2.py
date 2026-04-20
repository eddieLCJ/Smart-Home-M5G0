from m5stack import *
from m5ui import *
import machine
import time
import network
import random
import math
import unit
import json
from umqtt.simple import MQTTClient 

# --- 系统配置 ---
WIFI_SSID = "iPhone"
WIFI_PASS = "loveyou3000"
PUB_CMD = b"LCASH/commands"  # 💡 统一为 Web 端的指令频道
PUB_SENSORS = b"LCASH/sensors" # 💡 传感器上报频道
PUB_STATUS = b"LCASH/status"   # 💡 状态同步频道

try: env_0 = unit.get(unit.ENV, unit.PORTA)
except: env_0 = None

btn_red_pin = machine.Pin(16, machine.Pin.IN, machine.Pin.PULL_UP)
btn_blue_pin = machine.Pin(17, machine.Pin.IN, machine.Pin.PULL_UP)

try:
    servo_curtain = machine.PWM(machine.Pin(26), freq=50)
    servo_curtain.duty(0)
except: servo_curtain = None

curtain_status = "IDLE"
curtain_start_time = 0
fan_state = False

last_env_time = 0
last_anim_time = 0
fan_angle = 0
temp_val = 26.0
hum_val = 50.0

# --- 🎨 矢量图形绘制引擎 (保持不变) ---
def draw_cloud(x, y, color):
    lcd.circle(x, y, 10, color, color)
    lcd.circle(x+12, y-6, 14, color, color)
    lcd.circle(x+25, y, 12, color, color)
    lcd.rect(x, y-10, 26, 21, color, color)

def draw_thermometer(x, y):
    lcd.rect(x, y, 8, 20, 0xFF4500, 0xFF4500)
    lcd.circle(x+4, y+22, 8, 0xFF4500, 0xFF4500)
    lcd.rect(x+3, y+2, 2, 18, 0xFFFFFF, 0xFFFFFF)

def draw_water_drop(x, y):
    lcd.circle(x, y, 8, 0x00BFFF, 0x00BFFF)
    lcd.triangle(x-8, y, x+8, y, x, y-12, 0x00BFFF, 0x00BFFF)

def init_ui():
    lcd.clear(0x141414)
    lcd.rect(0, 0, 320, 35, 0x2980B9, 0x2980B9)
    draw_cloud(15, 20, 0xFFFFFF)
    lcd.font(lcd.FONT_DejaVu18)
    lcd.print("Node 2: Climate Hub", 60, 8, 0xFFFFFF)
    lcd.rect(10, 45, 145, 80, 0x2C3E50, 0x2C3E50)
    draw_thermometer(25, 65)
    lcd.rect(165, 45, 145, 80, 0x2C3E50, 0x2C3E50)
    draw_water_drop(185, 85)
    lcd.rect(10, 135, 145, 95, 0x34495E, 0x34495E)
    lcd.font(lcd.FONT_DejaVu18)
    lcd.print("CURTAIN", 40, 145, 0xFF6B6B)
    lcd.rect(165, 135, 145, 95, 0x34495E, 0x34495E)
    lcd.print("FAN", 220, 145, 0x4D96FF)

def update_sensors_ui():
    lcd.font(lcd.FONT_DejaVu24)
    lcd.rect(50, 75, 95, 30, 0x2C3E50, 0x2C3E50) 
    lcd.print(str(round(temp_val, 1)) + "C", 50, 75, 0xFFFFFF)
    lcd.rect(205, 75, 95, 30, 0x2C3E50, 0x2C3E50)
    lcd.print(str(round(hum_val, 1)) + "%", 205, 75, 0xFFFFFF)

def update_curtain_ui():
    cx, cy = 82, 195
    lcd.rect(cx-20, cy-15, 40, 30, 0x34495E, 0x34495E) 
    if curtain_status == "RUNNING":
        lcd.rect(cx-20, cy-15, 40, 30, 0x2ECC71, 0x2ECC71)
        lcd.rect(cx-20, cy-15, 10, 30, 0xBDC3C7, 0xBDC3C7)
        lcd.rect(cx+10, cy-15, 10, 30, 0xBDC3C7, 0xBDC3C7)
    else:
        lcd.rect(cx-20, cy-15, 40, 30, 0xBDC3C7, 0xBDC3C7)
        lcd.line(cx, cy-15, cx, cy+15, 0x7F8C8D)

def update_fan_anim():
    cx, cy, r = 237, 195, 20
    lcd.circle(cx, cy, r+2, 0x34495E, 0x34495E) 
    lcd.circle(cx, cy, r+1, 0x7F8C8D) 
    color = 0x00FF00 if fan_state else 0x95A5A6
    for i in range(3):
        a = math.radians(fan_angle + i * 120)
        x2 = int(cx + r * math.cos(a))
        y2 = int(cy + r * math.sin(a))
        lcd.line(cx, cy, x2, y2, color)
    lcd.circle(cx, cy, 4, color, color) 

# --- 💡 接收 Web 端控制指令 ---
def mqtt_cb(topic, msg):
    global curtain_status, curtain_start_time
    try:
        raw = msg.decode('utf-8').strip().upper()
        if "CURTAIN:ON" in raw and curtain_status == "IDLE":
            curtain_status = "RUNNING"
            curtain_start_time = time.ticks_ms()
            if servo_curtain: servo_curtain.duty(10)
            update_curtain_ui()
            try: mqtt.publish(PUB_STATUS, '{"curtain": true}')
            except: pass
        elif "CURTAIN:OFF" in raw and curtain_status == "RUNNING":
            curtain_status = "IDLE"
            curtain_start_time = 0
            if servo_curtain: servo_curtain.duty(0)
            update_curtain_ui()
            try: mqtt.publish(PUB_STATUS, '{"curtain": false}')
            except: pass
    except: pass

# --- 联网与初始化 ---
lcd.clear(0x141414)
lcd.font(lcd.FONT_DejaVu18)
lcd.print("Connecting WiFi...", 10, 100, 0x00BFFF)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASS)
while not wlan.isconnected(): time.sleep(0.1)

client_id = "N2_PRO_" + str(random.randint(1000, 9999))
mqtt = MQTTClient(client_id, "broker.emqx.io", port=1883)
mqtt.set_callback(mqtt_cb) # 挂载监听
try: 
    mqtt.connect()
    mqtt.subscribe(PUB_CMD)
    mqtt.sock.setblocking(False)
except: pass

init_ui()
update_sensors_ui()
update_curtain_ui()
update_fan_anim()

last_red = 0
last_blue = 0

# --- 主循环 ---
while True:
    now = time.ticks_ms()
    
    try: mqtt.check_msg() # 检查 Web 端指令
    except: pass
    
    # --- 1. 环境数据更新与上报 (每3秒) ---
    if now - last_env_time > 3000:
        if env_0:
            try:
                temp_val = env_0.temperature
                hum_val = env_0.humidity
            except: pass
        update_sensors_ui()
        
        # 💡 将数据发送到 Web 端
        try:
            sensor_data = json.dumps({"node": 2, "temp": round(temp_val, 1), "hum": round(hum_val, 1)})
            mqtt.publish(PUB_SENSORS, sensor_data)
        except: pass
        
        last_env_time = now

    # --- 2. 动画帧更新 (每60ms) ---
    if now - last_anim_time > 60:
        if fan_state:
            fan_angle = (fan_angle + 20) % 360
            update_fan_anim()
        last_anim_time = now

    # --- 3. 🔴 红色按钮：本地窗帘 ---
    if btn_red_pin.value() == 0 and (now - last_red > 500):
        last_red = now
        if curtain_status == "IDLE":
            curtain_status = "RUNNING"
            curtain_start_time = now
            if servo_curtain: servo_curtain.duty(10)
            try: mqtt.publish(PUB_STATUS, '{"curtain": true}') # 同步网页状态
            except: pass
        else:
            curtain_status = "IDLE"
            curtain_start_time = 0
            if servo_curtain: servo_curtain.duty(0)
            try: mqtt.publish(PUB_STATUS, '{"curtain": false}')
            except: pass
        update_curtain_ui()

    # --- 4. 🔵 蓝色按钮：远程风扇 ---
    if btn_blue_pin.value() == 0 and (now - last_blue > 500):
        last_blue = now
        fan_state = not fan_state
        update_fan_anim() 
        cmd = b"FAN:ON" if fan_state else b"FAN:OFF"
        try: mqtt.publish(PUB_CMD, cmd)
        except: pass
        
    # --- 5. 窗帘自动停止逻辑 (5秒闹钟) ---
    if curtain_start_time > 0 and time.ticks_diff(now, curtain_start_time) > 5000:
        if servo_curtain: servo_curtain.duty(0)
        curtain_start_time = 0
        curtain_status = "IDLE"
        update_curtain_ui() 
        try: mqtt.publish(PUB_STATUS, '{"curtain": false}') # 同步网页状态
        except: pass

    time.sleep_ms(20)