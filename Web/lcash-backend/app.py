# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import paho.mqtt.publish as publish

# app = Flask(__name__)
# CORS(app)

# # =====================================================================
# # 🤖 【LLM 同学专属工作区】
# # =====================================================================
# def generate_llm_decision(user_text, current_sensors):
#     """
#     预留给 LLM 同学的核心函数！
    
#     📥 输入参数:
#       - user_text (str): 用户在网页端输入的文本，如 "我热了"、"开窗"
#       - current_sensors (dict): 当前传感器的实时数据，如 {"temp": 26.5, "hum": 60}
      
#     📤 输出要求 (API 契约):
#       - 必须返回一个 Python 字典 (dict)，包含两个固定字段：
#         1. "ai_reply": 字符串，展示在网页上的回复。
#         2. "executed_actions": 列表，包含要执行的硬件动作字符串。
#            (可选动作仅限: "FAN:ON", "FAN:OFF", "CURTAIN:ON", "CURTAIN:OFF")
#     """
    
#     # ---------------------------------------------------------
#     # TODO: 未来在这里接入真实的 Ollama / Qwen 等大模型 API
#     # ---------------------------------------------------------
    
#     # ⚠️ 当前为 Mock (模拟) 模式：用简单的关键词代替大模型，方便前端和硬件先跑通测试
#     print(f"[LLM 模拟器] 收到用户指令: {user_text}")
#     print(f"[LLM 模拟器] 收到环境数据: {current_sensors}")
    
#     reply_text = "抱歉，我的大模型尚未接入，现在是模拟回复阶段。"
#     actions = []
    
#     if "热" in user_text or "开风" in user_text:
#         reply_text = "检测到您觉得热，已为您打开排风扇降温！"
#         actions.append("FAN:ON")
#     elif "冷" in user_text or "关风" in user_text:
#         reply_text = "好的，这就为您关闭排风扇。"
#         actions.append("FAN:OFF")
#     elif "黑" in user_text or "开窗" in user_text:
#         reply_text = "为您拉开窗帘，让阳光进来。"
#         actions.append("CURTAIN:ON")
#     elif "关窗" in user_text:
#         reply_text = "好的，已关闭窗帘。"
#         actions.append("CURTAIN:OFF")
#     else:
#         reply_text = f"当前室温是 {current_sensors.get('temp')}度，等大模型同学把我写好，我就能听懂您的复杂指令啦！"

#     # 严格按照契约返回数据结构
#     return {
#         "ai_reply": reply_text,
#         "executed_actions": actions
#     }


# # =====================================================================
# # 🌐 Web 后端路由与 MQTT 发送器 (已完善，LLM同学无需修改)
# # =====================================================================
# @app.route('/api/chat', methods=['POST'])
# def chat_endpoint():
#     try:
#         # 1. 接收前端传来的数据
#         data = request.json
#         user_text = data.get('user_text', '')
#         sensors = data.get('current_sensors', {})
        
#         # 2. 扔给 LLM 处理（目前调用的是上面的模拟函数）
#         decision = generate_llm_decision(user_text, sensors)
        
#         # 3. 拦截 LLM 的决策，将硬件指令通过 MQTT 自动下发给 M5Stack
#         actions = decision.get("executed_actions", [])
#         for act in actions:
#             publish.single("LCASH/commands", payload=act, hostname="broker.emqx.io", port=1883)
#             print(f"📡 [MQTT 发送成功]: 已向硬件下发指令 {act}")
            
#         # 4. 将结果返回给 Web 网页显示
#         return jsonify(decision)

#     except Exception as e:
#         print(f"❌ 后端发生错误: {e}")
#         return jsonify({
#             "ai_reply": "抱歉，服务器端发生异常。",
#             "executed_actions": []
#         }), 500

# if __name__ == '__main__':
#     print("🚀 LCASH 后端服务已启动！等待 Web 端和硬件接入...")
#     app.run(host='0.0.0.0', port=5000, debug=True)






#Version 2
# =====================================================================

#----------------------带 ThingSpeak 转发功能
#---1. 增加了 requests 转发逻辑。
#---2. 在用户对话的同时，自动将网页收到的实时传感器数据同步到 ThingSpeak。
#----------------------


# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import paho.mqtt.publish as publish
# import requests                             # 💡 新增：用于发送数据给 ThingSpeak
# import random   
# import json

# app = Flask(__name__)
# CORS(app)

# # =====================================================================
# # 🛠️ 配置区：请把你的 Write API Key 填在这里
# # =====================================================================
# THINGSPEAK_WRITE_API_KEY = "KIBFQLT7FHMTFEXJ"
# THINGSPEAK_URL = "https://api.thingspeak.com/update"

# # =====================================================================
# # 🤖 【LLM 同学专属工作区】
# # =====================================================================
# def generate_llm_decision(user_text, current_sensors):
#     """
#     真正的对接函数：调用你本地跑在 8080 端口的大模型！
#     """
#     # 你的大模型本地地址
#     LLM_API_URL = "http://127.0.0.1:8080/v1/chat/completions"

#     # 1. 核心大脑指令 (System Prompt)：告诉模型它该干嘛
#     system_prompt = """你是一个智能家居管家。请根据用户的指令和当前环境数据，输出JSON格式控制设备。
# 可选动作：["FAN:ON", "FAN:OFF", "CURTAIN:ON", "CURTAIN:OFF"]。
# 如果用户表达“热”、“闷”或空气不好，请主动输出 ["FAN:ON"]。如果表达想透气或看风景，输出 ["CURTAIN:ON"]。
# 严格返回JSON格式，必须包含 "intent" (CONTROL/CHAT), "control" (动作列表), 和 "is_chat" (布尔值)。不要输出任何多余的解释。"""

#     # 2. 打包发给模型的数据
#     payload = {
#         "messages": [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": f"当前环境数据：{current_sensors}。用户对你说：{user_text}"}
#         ],
#         "temperature": 0.1, # 低温度让模型更稳定听话
#         "response_format": {"type": "json_object"} # 强制返回 JSON
#     }

#     try:
#         print("🧠 正在呼叫本地大模型进行决策...")
#         # 3. 发送网络请求给 8080 端口
#         response = requests.post(LLM_API_URL, json=payload, timeout=15)
#         response_data = response.json()
        
#         # 4. 剥离出模型的真实回复内容并转为字典
#         llm_content = response_data['choices'][0]['message']['content']
#         print(f"🤖 大模型原始输出: {llm_content}")
        
#         llm_data = json.loads(llm_content) 
        
#         actions = llm_data.get("control", [])
#         is_chat = llm_data.get("is_chat", False)
        
#     except Exception as e:
#         print(f"❌ 调用本地大模型失败: {e}")
#         return {"ai_reply": "哎呀，管家大脑连接超时了，请检查大模型黑窗口是否在运行。", "executed_actions": []}

#     # 5. 适配器：把模型干瘪的指令，变成给用户的“温暖回复”
#     reply_text = ""
#     if actions:
#         if "FAN:ON" in actions:
#             reply_text = random.choice(["检测到环境需要换气，马上为您开启风扇~", "好的，风扇已为您启动！"])
#         elif "CURTAIN:ON" in actions:
#             reply_text = "收到，正在为您拉开窗帘透透气。"
#         elif "FAN:OFF" in actions:
#             reply_text = "好的，风扇已为您关闭，节约用电。"
#         elif "CURTAIN:OFF" in actions:
#             reply_text = "窗帘已为您拉上，祝您休息愉快。"
#         else:
#             reply_text = "指令已为您执行。"
#     elif is_chat:
#         reply_text = "虽然我很想跟您聊天，但我目前的职责是管理设备哦。请给我下达控制指令吧！"
#     else:
#         reply_text = "我收到了您的信息，但没有发现需要控制的设备。"

#     # 6. 按照 Web 契约返回给网页前端和 MQTT 下发器
#     return {
#         "ai_reply": reply_text,
#         "executed_actions": actions
#     }

# # =====================================================================
# # ☁️ 【ThingSpeak 转发函数】
# # =====================================================================
# def sync_to_thingspeak(sensors):
#     """
#     将传感器数据转发至 ThingSpeak 云端
#     """
#     if not THINGSPEAK_WRITE_API_KEY or THINGSPEAK_WRITE_API_KEY == "KIBFQLT7FHMTFEXJ":
#         print("⚠️ 警告：未配置 ThingSpeak API Key，跳过上传")
#         return

#     # 对应你 Channel 里的 Field 设置
#     payload = {
#         "api_key": THINGSPEAK_WRITE_API_KEY,
#         "field1": sensors.get("co2"),   # Node 1
#         "field2": sensors.get("light"), # Node 1
#         "field3": sensors.get("temp"),  # Node 2
#         "field4": sensors.get("hum")    # Node 2
#     }
    
#     try:
#         r = requests.get(THINGSPEAK_URL, params=payload, timeout=5)
#         if r.status_code == 200:
#             print(f"✅ [ThingSpeak] 数据上传成功，响应值: {r.text}")
#         else:
#             print(f"❌ [ThingSpeak] 上传失败，状态码: {r.status_code}")
#     except Exception as e:
#         print(f"❌ [ThingSpeak] 网络连接错误: {e}")

# # =====================================================================
# # 🌐 Web 后端路由
# # =====================================================================
# @app.route('/api/chat', methods=['POST'])
# def chat_endpoint():
#     try:
#         data = request.json
#         user_text = data.get('user_text', '')
#         sensors = data.get('current_sensors', {})
        
#         # 1. 立即同步数据到 ThingSpeak (实现 Activity 10 的要求)
#         sync_to_thingspeak(sensors)
        
#         # 2. 调用大模型决策
#         decision = generate_llm_decision(user_text, sensors)
        
#         # 3. 硬件指令下发
#         actions = decision.get("executed_actions", [])
#         for act in actions:
#             publish.single("LCASH/commands", payload=act, hostname="broker.emqx.io", port=1883)
#             print(f"📡 [MQTT] 已发送指令: {act}")
            
#         return jsonify(decision)

#     except Exception as e:
#         print(f"🔥 系统崩溃: {e}")
#         return jsonify({"ai_reply": "抱歉，我的大脑连接好像出了一点问题。", "executed_actions": []})

# if __name__ == '__main__':
#     # 确保安装了 requests: pip install requests
#     app.run(port=5000, debug=True)


#=============================4.19 改动=============================
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import paho.mqtt.publish as publish
# import requests
# import random   
# import json

# app = Flask(__name__)
# CORS(app)

# # =====================================================================
# # 🛠️ 配置区
# # =====================================================================
# THINGSPEAK_WRITE_API_KEY = "KIBFQLT7FHMTFEXJ"
# THINGSPEAK_URL = "https://api.thingspeak.com/update"

# # =====================================================================
# # 🤖 【LLM 同学专属工作区】
# # =====================================================================
# def generate_llm_decision(user_text, current_sensors):
#     LLM_API_URL = "http://127.0.0.1:8080/v1/chat/completions"

#     system_prompt = """你是一个智能家居管家。请根据用户的指令和当前环境数据，输出JSON格式控制设备。
# 可选动作：["FAN:ON", "FAN:OFF", "CURTAIN:ON", "CURTAIN:OFF"]。
# 如果用户表达“热”、“闷”或空气不好，请主动输出 ["FAN:ON"]。如果表达想透气或看风景，输出 ["CURTAIN:ON"]。
# 严格返回JSON格式，必须包含 "intent" (CONTROL/CHAT), "control" (动作列表), 和 "is_chat" (布尔值)。不要输出任何多余的解释。"""

#     payload = {
#         "messages": [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": f"当前环境数据：{current_sensors}。用户对你说：{user_text}"}
#         ],
#         "temperature": 0.1,
#         "response_format": {"type": "json_object"}
#     }

#     try:
#         print("🧠 正在呼叫本地大模型进行决策...")
#         response = requests.post(LLM_API_URL, json=payload, timeout=15)
#         response_data = response.json()
        
#         # 核心改进：获取内容并清洗 JSON
#         raw_content = response_data['choices'][0]['message']['content']
#         print(f"🤖 大模型原始输出: {raw_content}")
        
#         # 🔍 自动截取 {} 之间的内容，剔除 <think> 等干扰信息
#         start_idx = raw_content.find('{')
#         end_idx = raw_content.rfind('}')
        
#         if start_idx == -1 or end_idx == -1:
#             raise ValueError("无法在模型输出中找到有效的 JSON 格式")
            
#         clean_json_str = raw_content[start_idx:end_idx+1]
#         llm_data = json.loads(clean_json_str) 
        
#         actions = llm_data.get("control", [])
#         is_chat = llm_data.get("is_chat", False)
        
#     except Exception as e:
#         print(f"❌ 调用本地大模型失败: {e}")
#         return {"ai_reply": "哎呀，管家大脑连接超时或格式解析出错，请检查终端日志。", "executed_actions": []}

#     # 适配器：把指令变成回复
#     reply_text = ""
#     if actions:
#         if "FAN:ON" in actions:
#             reply_text = random.choice(["检测到环境需要换气，马上为您开启风扇~", "好的，风扇已为您启动！"])
#         elif "CURTAIN:ON" in actions:
#             reply_text = "收到，正在为您拉开窗帘透透气。"
#         elif "FAN:OFF" in actions:
#             reply_text = "好的，风扇已为您关闭，节约用电。"
#         elif "CURTAIN:OFF" in actions:
#             reply_text = "窗帘已为您拉上，祝您休息愉快。"
#         else:
#             reply_text = "指令已为您执行。"
#     elif is_chat:
#         reply_text = "虽然我很想跟您聊天，但我目前的职责是管理设备哦。请给我下达控制指令吧！"
#     else:
#         reply_text = "我收到了您的信息，但没有发现需要控制的设备。"

#     return {
#         "ai_reply": reply_text,
#         "executed_actions": actions
#     }

# # =====================================================================
# # ☁️ 【ThingSpeak 转发函数】
# # =====================================================================
# def sync_to_thingspeak(sensors):
#     if not THINGSPEAK_WRITE_API_KEY or THINGSPEAK_WRITE_API_KEY == "KIBFQLT7FHMTFEXJ":
#         print("⚠️ 警告：未配置 ThingSpeak API Key，跳过上传")
#         return

#     payload = {
#         "api_key": THINGSPEAK_WRITE_API_KEY,
#         "field1": sensors.get("co2"),
#         "field2": sensors.get("light"),
#         "field3": sensors.get("temp"),
#         "field4": sensors.get("hum")
#     }
    
#     try:
#         r = requests.get(THINGSPEAK_URL, params=payload, timeout=5)
#         if r.status_code == 200:
#             print(f"✅ [ThingSpeak] 数据上传成功，响应值: {r.text}")
#         else:
#             print(f"❌ [ThingSpeak] 上传失败，状态码: {r.status_code}")
#     except Exception as e:
#         print(f"❌ [ThingSpeak] 网络连接错误: {e}")

# # =====================================================================
# # 🌐 Web 后端路由
# # =====================================================================
# @app.route('/api/chat', methods=['POST'])
# def chat_endpoint():
#     try:
#         data = request.json
#         user_text = data.get('user_text', '')
#         sensors = data.get('current_sensors', {})
        
#         sync_to_thingspeak(sensors)
#         decision = generate_llm_decision(user_text, sensors)
        
#         actions = decision.get("executed_actions", [])
#         for act in actions:
#             publish.single("LCASH/commands", payload=act, hostname="broker.emqx.io", port=1883)
#             print(f"📡 [MQTT] 已发送指令: {act}")
            
#         return jsonify(decision)

#     except Exception as e:
#         print(f"🔥 系统崩溃: {e}")
#         return jsonify({"ai_reply": "抱歉，我的大脑连接好像出了一点问题。", "executed_actions": []})

# if __name__ == '__main__':
#     app.run(port=5000, debug=True)




#================================4.19（15.56分改动）

# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import paho.mqtt.publish as publish
# import requests
# import json

# app = Flask(__name__)
# CORS(app)

# # =====================================================================
# # 🛠️ 配置区：对接你的 5050 中控服务
# # =====================================================================
# THINGSPEAK_WRITE_API_KEY = "KIBFQLT7FHMTFEXJ"
# THINGSPEAK_URL = "https://api.thingspeak.com/update"

# # 注意：这里指向你提供的那个 LLM py 文件运行的端口
# SMART_HOME_CONTROLLER_URL = "http://127.0.0.1:5050/api/v1/smart_home/command"

# # 全局变量：用于追踪硬件状态，辅助 LLM 进行“状态冲突检查”
# device_states = {
#     "fan": "OFF",
#     "curtain": "OFF"
# }

# # =====================================================================
# # 🧠 智能中控对接函数
# # =====================================================================
# def get_smart_decision(user_text, sensors):
#     """
#     完美适配 llm_api.py 的输入要求
#     """
#     # 1. 转换数据格式以适配你的 llm_api.py 逻辑
#     # 你的 llm_api 期望 env_status 里有 temp, humi, co2 以及设备名(小写)
#     env_status = {
#         "temp": sensors.get("temp", 25),
#         "humi": sensors.get("hum", 50),
#         "co2": sensors.get("co2", 400),
#         "fan": device_states["fan"],
#         "curtain": device_states["curtain"]
#     }

#     # 2. 构造请求 Payload
#     payload = {
#         "command": user_text,
#         "env_status": env_status
#     }

#     try:
#         print(f"📡 转发指令到中控 (5050): {user_text}")
#         response = requests.post(SMART_HOME_CONTROLLER_URL, json=payload, timeout=10)
#         res_data = response.json()

#         # 3. 提取中控处理后的结果
#         # res_data 格式: {"broadcast": "...", "hardware_actions": ["FAN:ON"], "intent_debug": {...}}
#         ai_reply = res_data.get("broadcast", "我收到了指令，但不知道怎么回复。")
#         actions = res_data.get("hardware_actions", [])

#         # 4. 更新本地状态追踪（为了下次调用时状态更准）
#         for act in actions:
#             if "FAN:ON" in act: device_states["fan"] = "ON"
#             if "FAN:OFF" in act: device_states["fan"] = "OFF"
#             if "CURTAIN:ON" in act: device_states["curtain"] = "ON"
#             if "CURTAIN:OFF" in act: device_states["curtain"] = "OFF"

#         return {
#             "ai_reply": ai_reply,
#             "executed_actions": actions
#         }

#     except Exception as e:
#         print(f"❌ 调用中控服务失败: {e}")
#         return {"ai_reply": "中控大脑(5050端口)好像没启动哦。", "executed_actions": []}

# # =====================================================================
# # ☁️ ThingSpeak 转发函数
# # =====================================================================
# def sync_to_thingspeak(sensors):
#     if not THINGSPEAK_WRITE_API_KEY or THINGSPEAK_WRITE_API_KEY == "KIBFQLT7FHMTFEXJ":
#         return
#     payload = {
#         "api_key": THINGSPEAK_WRITE_API_KEY,
#         "field1": sensors.get("co2"),
#         "field2": sensors.get("light"),
#         "field3": sensors.get("temp"),
#         "field4": sensors.get("hum")
#     }
#     try:
#         requests.get(THINGSPEAK_URL, params=payload, timeout=5)
#     except:
#         pass

# # =====================================================================
# # 🌐 Web 后端路由
# # =====================================================================
# @app.route('/api/chat', methods=['POST'])
# def chat_endpoint():
#     try:
#         data = request.json
#         user_text = data.get('user_text', '')
#         sensors = data.get('current_sensors', {})
        
#         # 1. 同步数据到云端
#         sync_to_thingspeak(sensors)
        
#         # 2. 获取中控决策（调用 5050 端口）
#         decision = get_smart_decision(user_text, sensors)
        
#         # 3. 硬件指令下发 MQTT
#         actions = decision.get("executed_actions", [])
#         for act in actions:
#             # 这里的 topic 必须和你的 M5Stack 订阅的一致
#             publish.single("LCASH/commands", payload=act, hostname="broker.emqx.io", port=1883)
#             print(f"📡 [MQTT] 已发送硬件指令: {act}")
            
#         return jsonify(decision)

#     except Exception as e:
#         print(f"🔥 系统崩溃: {e}")
#         return jsonify({"ai_reply": "后端出现异常，请检查控制台。", "executed_actions": []})

# if __name__ == '__main__':
#     # Web 运行在 5000 端口
#     print("🌟 Web 后端已启动，监听端口 5000...")
#     app.run(port=5000, debug=True)




#===============功能正常版

from flask import Flask, request, jsonify
from flask_cors import CORS
import paho.mqtt.publish as publish
import requests
import json
import threading # 1. 引入线程库
import time      # 2. 引入时间库

app = Flask(__name__)
CORS(app)

# ================= 配置区 =================
THINGSPEAK_WRITE_API_KEY = "KIBFQLT7FHMTFEXJ"
THINGSPEAK_URL = "https://api.thingspeak.com/update"
SMART_HOME_CONTROLLER_URL = "http://127.0.0.1:5050/api/v1/smart_home/command"

# 全局变量：存储最新的传感器数据
latest_sensors = {} 
device_states = {"fan": "OFF", "curtain": "OFF"}

# ================= 核心：后台上传线程 =================
def background_thingspeak_worker():
    """
    后台守护线程：每 60 秒检查一次，如果有新数据则上传
    """
    print("🚀 [System] ThingSpeak 后台同步线程已启动...")
    while True:
        try:
            # 只有在有数据的时候才上传
            if latest_sensors:
                # 复制一份当前数据避免线程冲突
                data_to_send = latest_sensors.copy()
                sync_to_thingspeak(data_to_send)
                print(f"📡 [Background] 已自动同步数据到云端: {data_to_send}")
            else:
                print("⏳ [Background] 等待传感器数据初始化...")
        except Exception as e:
            print(f"❌ [Background] 同步失败: {e}")
        
        time.sleep(30) # 核心：强制休息 60 秒

# 启动线程 (daemon=True 表示随主程序退出而退出)
threading.Thread(target=background_thingspeak_worker, daemon=True).start()

# ================= 其余功能函数 =================
def get_smart_decision(user_text, sensors):
    # ... (你的原代码保持不变) ...
    env_status = {
        "temp": sensors.get("temp", 25),
        "humi": sensors.get("hum", 50),
        "co2": sensors.get("co2", 400),
        "fan": device_states["fan"],
        "curtain": device_states["curtain"]
    }
    payload = {"command": user_text, "env_status": env_status}
    try:
        response = requests.post(SMART_HOME_CONTROLLER_URL, json=payload, timeout=10)
        res_data = response.json()
        ai_reply = res_data.get("broadcast", "我收到了指令，但不知道怎么回复。")
        actions = res_data.get("hardware_actions", [])
        for act in actions:
            if "FAN:ON" in act: device_states["fan"] = "ON"
            if "FAN:OFF" in act: device_states["fan"] = "OFF"
            if "CURTAIN:ON" in act: device_states["curtain"] = "ON"
            if "CURTAIN:OFF" in act: device_states["curtain"] = "OFF"
        return {"ai_reply": ai_reply, "executed_actions": actions}
    except Exception as e:
        return {"ai_reply": "中控大脑未响应。", "executed_actions": []}

def sync_to_thingspeak(sensors):
    if not THINGSPEAK_WRITE_API_KEY or THINGSPEAK_WRITE_API_KEY == "你的_WRITE_API_KEY":
        print("❌ [ThingSpeak] 错误: API Key 未配置")
        return

    payload = {
        "api_key": THINGSPEAK_WRITE_API_KEY,
        "field1": sensors.get("co2"),
        "field2": sensors.get("light"),
        "field3": sensors.get("temp"),
        "field4": sensors.get("hum")
    }
    
    try:
        # 使用 request.get 发送，并将响应状态打印出来
        response = requests.get(THINGSPEAK_URL, params=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ [ThingSpeak] 数据上传成功! 内容: {payload}")
        else:
            print(f"⚠️ [ThingSpeak] 上传失败，状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        print(f"❌ [ThingSpeak] 网络请求异常: {e}")

# ================= 路由 =================
@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.json
        user_text = data.get('user_text', '')
        sensors = data.get('current_sensors', {})
        
        # 3. 更新全局最新数据 (供后台线程使用)
        if sensors:
            global latest_sensors
            latest_sensors = sensors
        
        # 2. 获取决策
        decision = get_smart_decision(user_text, sensors)
        
        # 3. MQTT 下发
        actions = decision.get("executed_actions", [])
        for act in actions:
            publish.single("LCASH/commands", payload=act, hostname="broker.emqx.io", port=1883)
            
        return jsonify(decision)
    except Exception as e:
        return jsonify({"ai_reply": "异常", "executed_actions": []})

if __name__ == '__main__':
    app.run(port=5000, debug=True)





#==================增加晓晓语音版===
#================== 网页浏览器 TTS 优化版 ==================
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import paho.mqtt.publish as publish
# import requests
# import threading
# import time

# app = Flask(__name__)
# CORS(app)

# # ================= 配置区 =================
# THINGSPEAK_WRITE_API_KEY = "KIBFQLT7FHMTFEXJ"
# THINGSPEAK_URL = "https://api.thingspeak.com/update"
# SMART_HOME_CONTROLLER_URL = "http://127.0.0.1:5050/api/v1/smart_home/command"
# MQTT_BROKER = "broker.emqx.io"

# # 全局变量
# latest_sensors = {} 
# device_states = {"fan": "OFF", "curtain": "OFF"}

# # ================= 后台任务：ThingSpeak 同步 =================
# def background_thingspeak_worker():
#     print("🚀 [System] ThingSpeak 后台线程已启动...")
#     while True:
#         try:
#             if latest_sensors:
#                 data_to_send = latest_sensors.copy()
#                 sync_to_thingspeak(data_to_send)
#         except Exception as e:
#             print(f"❌ [Background] 同步失败: {e}")
#         time.sleep(60)

# threading.Thread(target=background_thingspeak_worker, daemon=True).start()

# # ================= 功能模块 =================
# def sync_to_thingspeak(sensors):
#     payload = {
#         "api_key": THINGSPEAK_WRITE_API_KEY,
#         "field1": sensors.get("co2"),
#         "field2": sensors.get("light"),
#         "field3": sensors.get("temp"),
#         "field4": sensors.get("hum")
#     }
#     try:
#         requests.get(THINGSPEAK_URL, params=payload, timeout=5)
#     except Exception as e:
#         print(f"❌ [ThingSpeak] 网络异常: {e}")

# def get_smart_decision(user_text, sensors):
#     env_status = {
#         "temp": sensors.get("temp", 25),
#         "humi": sensors.get("hum", 50),
#         "co2": sensors.get("co2", 400),
#         "fan": device_states["fan"],
#         "curtain": device_states["curtain"]
#     }
#     try:
#         response = requests.post(SMART_HOME_CONTROLLER_URL, json={"command": user_text, "env_status": env_status}, timeout=5)
#         res_data = response.json()
        
#         # 更新本地设备状态
#         actions = res_data.get("hardware_actions", [])
#         for act in actions:
#             if "FAN:ON" in act: device_states["fan"] = "ON"
#             if "FAN:OFF" in act: device_states["fan"] = "OFF"
#             if "CURTAIN:ON" in act: device_states["curtain"] = "ON"
#             if "CURTAIN:OFF" in act: device_states["curtain"] = "OFF"
            
#         return {"ai_reply": res_data.get("broadcast", "没听清，能再说一遍吗？"), "executed_actions": actions}
#     except Exception:
#         return {"ai_reply": "中枢大脑连接失败。", "executed_actions": []}

# # ================= 聊天主路由 =================
# @app.route('/api/chat', methods=['POST'])
# def chat_endpoint():
#     data = request.json
#     user_text = data.get('user_text', '')
#     sensors = data.get('current_sensors', {})
    
#     global latest_sensors
#     latest_sensors = sensors
    
#     # 获取智能决策与回复文本
#     decision = get_smart_decision(user_text, sensors)
    
#     # MQTT 下发控制
#     for act in decision.get("executed_actions", []):
#         try:
#             publish.single("LCASH/commands", payload=act, hostname=MQTT_BROKER, port=1883)
#         except Exception as e:
#             print(f"❌ [MQTT] 指令发送失败: {e}")
            
#     # 只返回文本与指令，语音合成由前端浏览器搞定
#     return jsonify(decision)

# if __name__ == '__main__':
#     app.run(port=5000, debug=True)