# WebSocket控制系统

一个基于WebSocket的远程控制系统，包含Python服务器端和HTML客户端。

## 功能特性

- **服务器端 (Python)**
  - 纯Python标准库实现，无第三方依赖
  - 支持WebSocket (WS) 和安全WebSocket (WSS)
  - 基于Token的身份验证
  - 支持后台线程运行
  - 完整的Shell终端访问
  - 文件上传/下载功能
  - 环境变量配置支持

- **客户端 (HTML/CSS/JavaScript)**
  - 现代化的用户界面
  - 服务器管理（添加、编辑、删除）
  - 搜索功能
  - localStorage持久化存储
  - xterm.js终端体验
  - 文件上传/下载
  - 响应式设计

## 项目结构

```
├── server/
│   └── main.py          # Python服务器主文件
├── client/
│   ├── index.html       # 客户端主页面
│   ├── styles.css       # 样式文件
│   └── app.js           # 客户端JavaScript逻辑
├── .env.example         # 环境变量模板
└── README.md           # 说明文档
```

## 快速开始

### 方式一：使用启动脚本（推荐）

```bash
# 克隆或下载项目后
./start.sh start    # 启动完整系统
./start.sh dev      # 开发模式启动（包含HTTP服务器）
./start.sh stop     # 停止所有服务器
./start.sh test     # 运行测试
./start.sh help     # 查看帮助
```

### 方式二：手动启动

#### 1. 配置服务器

复制环境变量模板：
```bash
cp .env.example .env
```

编辑 `.env` 文件：
```env
WS_HOST=localhost
WS_PORT=8765
WS_TOKEN=your-secret-token-here

# 可选：WSS配置
# CERT_FILE=/path/to/cert.pem
# KEY_FILE=/path/to/key.pem
```

#### 2. 启动服务器

```bash
cd server
python main.py
```

#### 3. 打开客户端

直接在浏览器中打开 `client/index.html` 文件。

### 方式三：作为模块导入

```python
from server.main import start_server, stop_server

# 启动服务器（后台运行）
server = start_server()

# 停止服务器
stop_server()
```

### 4. 添加服务器

1. 点击左上角的 "+" 按钮
2. 填写服务器信息：
   - Name: 服务器名称（用于显示）
   - Server: 服务器地址（格式：host:port）
   - Token: 认证令牌（与服务器端设置的一致）
3. 点击保存

### 5. 连接并使用

1. 在左侧列表中选择要连接的服务器
2. 系统会自动建立连接并进行身份验证
3. 验证成功后会显示终端界面
4. 可以在终端中执行任何命令
5. 使用 "Upload File" 和 "Download File" 按钮进行文件传输

## 协议说明

### WebSocket消息格式

所有消息都是JSON格式：

```json
{
  "type": "消息类型",
  "其他字段": "..."
}
```

### 消息类型

#### 客户端 → 服务器

- **认证**
```json
{
  "type": "auth",
  "token": "your-token-here"
}
```

- **Shell操作**
```json
{
  "type": "shell",
  "action": "start|input|resize|stop",
  "data": "输入数据",        // 仅input时需要
  "rows": 24,              // 仅resize时需要
  "cols": 80               // 仅resize时需要
}
```

- **文件上传**
```json
{
  "type": "file_upload",
  "path": "/tmp/filename",
  "content": "base64编码的文件内容"
}
```

- **文件下载**
```json
{
  "type": "file_download",
  "path": "/path/to/file"
}
```

#### 服务器 → 客户端

- **认证响应**
```json
{
  "type": "auth_response",
  "success": true|false,
  "message": "错误信息（可选）"
}
```

- **Shell事件**
```json
{
  "type": "shell_started|shell_stopped|shell_error",
  "message": "错误信息（可选）"
}
```

- **Shell输出**
```json
{
  "type": "shell_output",
  "data": "base64编码的输出数据"
}
```

- **文件操作响应**
```json
{
  "type": "file_upload_response|file_download_response",
  "success": true|false,
  "message": "错误信息（可选）",
  "content": "文件内容（仅下载成功时）",
  "filename": "文件名（仅下载成功时）"
}
```

## 安全说明

1. **Token认证**: 确保使用强Token，避免使用默认值
2. **WSS加密**: 在生产环境中建议使用WSS加密传输
3. **网络访问**: 服务器默认只监听localhost，如需远程访问请修改配置
4. **文件权限**: 注意文件上传/下载的路径权限控制

## 开发说明

### 服务器端扩展

服务器采用模块化设计，可以轻松扩展新功能：

1. 在 `_handle_message` 方法中添加新的消息类型处理
2. 实现对应的处理方法
3. 更新协议文档

### 客户端扩展

客户端使用面向对象设计，便于维护和扩展：

1. 在 `handleMessage` 方法中添加新的消息类型处理
2. 添加对应的UI组件和事件处理
3. 更新协议文档

## 注意事项

1. 服务器使用Python标准库实现，兼容Python 3.6+
2. 客户端需要现代浏览器支持WebSocket和ES6+
3. 文件传输使用Base64编码，大文件可能影响性能
4. Shell会话在断开连接时会自动终止

## 故障排除

### 连接失败
- 检查服务器是否启动
- 确认端口和地址配置正确
- 检查防火墙设置

### 认证失败
- 确认Token配置正确
- 检查环境变量是否正确加载

### 文件操作失败
- 检查文件路径权限
- 确认磁盘空间充足
- 查看服务器日志获取详细错误信息