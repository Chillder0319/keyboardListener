# 远程屏幕监控 + 键盘控制系统
跨平台客户端 + 服务端，支持实时画面、鼠标显示、远程键盘控制、心跳保活、日志记录、图片自动保存。

## 功能
- 服务端实时查看客户端屏幕（含鼠标指针）
- 服务端远程控制客户端键盘
- 客户端本地按键上传服务端
- 心跳 500ms，1 秒无心跳判定断开
- 服务端自动保存客户端屏幕到 client_screens 文件夹
- 干净日志（仅记录上线/离线/按键），输出到 server.log
- 浏览器实时流畅画面
- 跨平台：Windows / macOS

## 环境安装
```bash
pip install -r requirements.txt
```

## 启动方式
### 1. 启动服务端
```bash
python server.py
```

### 2. 启动客户端
```bash
python client.py
```

### 3. 查看实时画面
浏览器打开（替换为你的客户端ID）：
```
http://127.0.0.1:5800/live/客户端ID
```

## 打包成独立程序（无黑窗口）
### 服务端打包
```bash
pyinstaller -F -w server.py
```

### 客户端打包
```bash
pyinstaller -F -w client.py
```

生成文件在 `dist/` 目录下。

## 权限说明（macOS）
- 屏幕录制：必须开启
- 辅助功能：键盘监听必须开启
- 设置路径：系统设置 → 隐私与安全性

## 文件说明
- server.py：服务端
- client.py：客户端
- server.log：服务端日志
- client_screens/：客户端屏幕截图保存目录