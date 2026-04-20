import requests

# Flask 接口地址
url = "http://127.0.0.1:5050/api/v1/smart_home/command"

# 模拟客户端传过去的动态环境数据和指令
payload = {
    "command": "现在二氧化碳浓度多少？顺便开下风扇",
    "env_status": {
        "temp": 28.5,
        "humi": 70,
        "co2": 800,
        "fan": "OFF",
        "curtain": "ON"
    }
}

# 🛡️ 核心修复：强制忽略 Windows 的系统代理（Clash/VPN等），直接走内网直连！
proxies = {
    "http": None,
    "https": None
}

print("🚀 正在向 Flask 中控发送指令，等待大模型思考 (可能需要几秒钟)...")

try:
    # 加上 proxies 参数，并设置 60 秒的超时时间，防止大模型算得慢导致连接断开
    response = requests.post(url, json=payload, proxies=proxies, timeout=60)

    # 检查 HTTP 状态码
    if response.status_code == 200:
        result = response.json()
        print("\n✅ 请求成功！")
        print("🔊 需要播报的语音:", result.get("broadcast"))
        print("🔌 需要执行的硬件动作:", result.get("hardware_actions"))
        print("🧠 底层大模型意图:", result.get("intent_debug"))
    else:
        print(f"\n⚠️ 失败！Flask 返回了错误码: {response.status_code}")
        print("内容:", response.text)

except Exception as e:
    print(f"\n❌ 网络连接彻底失败: {e}")