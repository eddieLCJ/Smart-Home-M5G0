from flask import Flask, request, jsonify
import urllib.request
import json
import re
import random

app = Flask(__name__)

# =====================================================================
# 1. 配置区 & 话术库
# =====================================================================
LLM_URL = "http://127.0.0.1:8080/v1/chat/completions"
SYSTEM_PROMPT = "NLU mode. Output JSON only."

VOICE_RESPONSES = {
    # "STATE_CONFLICT_FAN_ON": ["风扇已经开着啦", "风扇呼呼转着呢，不需要再开啦。"],
    # "STATE_CONFLICT_FAN_OFF": ["风扇本来就是关着的哦。", "风扇已经在休息了。"],
    # "STATE_CONFLICT_CURTAIN_ON": ["窗帘已经是打开的啦。", "窗帘开着呢，视野很棒吧。"],
    # "STATE_CONFLICT_CURTAIN_OFF": ["窗帘已经拉上啦，安心休息吧。", "窗帘关得严严实实的呢。"],

    # "ACTION_SUCCESS_FAN_ON": ["风扇已为您打开！", "风扇已经转起来啦！"],
    # "ACTION_SUCCESS_FAN_OFF": ["风扇已关闭，让它休息一下吧。", "好的，这就把风扇关掉。"],
    # "ACTION_SUCCESS_CURTAIN_ON": ["这就为您拉开窗帘，享受阳光吧！", "窗帘已经拉开啦。"],
    # "ACTION_SUCCESS_CURTAIN_OFF": ["窗帘已拉上，给您保留私密空间。", "这就帮您把窗帘合上。"],

    # "QUERY_TEMP": ["室温是{temp}度。"],
    # "QUERY_HUMIDITY": ["湿度是百分之{humidity}。", "室内湿度{humidity}%。"],
    # "QUERY_CO2": ["当前二氧化碳浓度是{co2} ppm。", "屋里的CO2浓度是{co2}。"],

    # "UNSUPPORTED": ["抱歉主人，{devices}还没接入我的系统呢。"],
    # "CHAT": ["哈哈，这个话题很有意思，不过我们可以聊聊怎么控制家电哦。"],
    # "ERROR_FALLBACK": ["哎呀，我刚才走神了，脑回路好像短路了，能再说一遍吗？"],
    # "EMPTY_INPUT": ["没有收到指令，我先退下咯。"]
    
    "STATE_CONFLICT_FAN_ON": ["风扇仲开紧喎。", "风扇转紧喇，唔使再开喇。"],
    "STATE_CONFLICT_FAN_OFF": ["风扇本来就熄咗喇。", "风扇仲休息紧呀。"],
    "STATE_CONFLICT_CURTAIN_ON": ["窗帘已经开咗喇。", "窗帘开咗喇，睇风景啱晒啦。"],
    "STATE_CONFLICT_CURTAIN_OFF": ["窗帘已经拉埋喇，安心休息啦。", "窗帘关得实一实呀。"],

    "ACTION_SUCCESS_FAN_ON": ["帮你开咗风扇喇！", "风扇转紧喇！"],
    "ACTION_SUCCESS_FAN_OFF": ["熄咗风扇喇，俾佢休息下。", "好，即刻帮你熄咗风扇。"],
    "ACTION_SUCCESS_CURTAIN_ON": ["即刻帮你拉开窗帘，晒下太阳喇！", "窗帘已经拉开喇。"],
    "ACTION_SUCCESS_CURTAIN_OFF": ["窗帘拉埋喇，帮你保留私隐空间。", "即刻帮你拉埋窗帘。"],

    "QUERY_TEMP": ["室温系 {temp} 度呀。"],
    "QUERY_HUMIDITY": ["湿度系 {humidity}%。", "室内湿度 {humidity}%。"],
    "QUERY_CO2": ["而家二氧化碳浓度系 {co2} ppm。", "屋企二氧化碳浓度系 {co2}。"],

    "UNSUPPORTED": ["唔好意思主人，{devices} 仲未连接到我系统呀。"],
    "CHAT": ["哈哈，呢个话题好得意，不过不如我哋倾下点样控制家电啦。"],
    "ERROR_FALLBACK": ["哎呀，头先走咗神，好似短咗路咁，可以讲多次吗？"],
    "EMPTY_INPUT": ["收唔到指令喎，我休息阵先。"]

}


def get_random_voice(key, **kwargs):
    pool = VOICE_RESPONSES.get(key, ["指令已收到，但我还没学习该怎么做呢！"])
    return random.choice(pool).format(**kwargs)


# =====================================================================
# 2. 大模型调用与解析
# =====================================================================
def analyze_intent_via_llm(user_text):
    data = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.1,
        "max_tokens": 256
    }

    req = urllib.request.Request(
        LLM_URL,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            raw_output = result["choices"][0]["message"]["content"]

            clean_str = re.sub(r'<think>.*?</think>', '', raw_output, flags=re.DOTALL)
            clean_str = re.sub(r'^```json', '', clean_str, flags=re.IGNORECASE | re.MULTILINE)
            clean_str = re.sub(r'```$', '', clean_str, flags=re.MULTILINE)
            clean_str = clean_str.strip()
            return json.loads(clean_str)
    except Exception as e:
        print(f"[-] AI 解析异常: {e}")
        return None


# =====================================================================
# 3. 核心 API 路由
# =====================================================================
@app.route('/api/v1/smart_home/command', methods=['POST'])
def handle_command():
    # 1. 获取客户端传来的 JSON 数据
    req_data = request.json
    if not req_data:
        return jsonify({"error": "Missing JSON payload"}), 400

    user_command = req_data.get("command", "").strip()
    env_status = req_data.get("env_status", {})

    # 返回给客户端的结果容器
    response_payload = {
        "broadcast": "",  # 最终要播报的话术
        "hardware_actions": [],  # 真正需要让单片机去执行的动作
        "intent_debug": {}  # 方便调试查看的大模型原始输出
    }

    if not user_command:
        response_payload["broadcast"] = get_random_voice('EMPTY_INPUT')
        return jsonify(response_payload)

    # 2. 调用大模型分析意图
    parsed_json = analyze_intent_via_llm(user_command)

    if not parsed_json:
        response_payload["broadcast"] = get_random_voice('ERROR_FALLBACK')
        return jsonify(response_payload)

    response_payload["intent_debug"] = parsed_json
    intent = parsed_json.get("intent", "UNKNOWN")
    voice_segments = []

    # 3. 业务逻辑处理
    if intent == "UNSUPPORTED":
        voice_segments.append(get_random_voice('UNSUPPORTED', devices='和'.join(parsed_json.get('unsupported', []))))
    elif intent == "CHAT":
        voice_segments.append(get_random_voice('CHAT'))
    else:
        # 查询逻辑
        if intent in ["QUERY", "MIXED"] and "query" in parsed_json:
            for q in parsed_json.get("query", []):
                q = str(q).lower()  # 容错转小写
                if q == 'temp' and 'temp' in env_status:
                    voice_segments.append(get_random_voice('QUERY_TEMP', temp=env_status['temp']))
                elif (q == 'humi' or q == 'humidity') and 'humi' in env_status:
                    voice_segments.append(get_random_voice('QUERY_HUMIDITY', humidity=env_status['humi']))
                elif (q == 'co2' or q == 'carbon') and 'co2' in env_status:
                    voice_segments.append(get_random_voice('QUERY_CO2', co2=env_status['co2']))

        # 控制逻辑
        if intent in ["CONTROL", "MIXED"] and "control" in parsed_json:
            for action in parsed_json.get("control", []):
                if ":" not in action:
                    continue
                device, target_state = action.split(":", 1)

                # 检查状态冲突
                if env_status.get(device.lower(), "UNKNOWN") == target_state:
                    voice_segments.append(get_random_voice(f'STATE_CONFLICT_{device}_{target_state}'))
                else:
                    voice_segments.append(get_random_voice(f'ACTION_SUCCESS_{device}_{target_state}'))
                    # 如果状态不冲突，才真正下发硬件控制指令！
                    response_payload["hardware_actions"].append(action)

    # 4. 组装话术并返回
    if voice_segments:
        response_payload["broadcast"] = " ".join(voice_segments)

    return jsonify(response_payload)


if __name__ == '__main__':
    # 监听 5000 端口
    print("🚀 Flask 智能中控服务已启动，监听端口 5050...")
    app.run(host='0.0.0.0', port=5050, debug=True)