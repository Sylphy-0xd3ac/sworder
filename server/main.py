import os
import sys
import json
import socket
import threading
import time
import subprocess
import pty
import select
import ssl
import base64
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from io import BytesIO
import shutil
import struct

class WebSocketServer:
    """WebSocket服务器实现，支持WS和WSS，无第三方依赖"""
    
    MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    OPCODE_CONTINUATION = 0x0
    OPCODE_TEXT = 0x1
    OPCODE_BINARY = 0x2
    OPCODE_CLOSE = 0x8
    OPCODE_PING = 0x9
    OPCODE_PONG = 0xa
    
    def __init__(self, host='localhost', port=8765, token=None, cert_file=None, key_file=None):
        self.host = host
        self.port = port
        self.token = token
        self.cert_file = cert_file
        self.key_file = key_file
        self.clients = {}
        self.shells = {}
        self.running = False
        self.server_thread = None
        
    def start(self):
        """启动WebSocket服务器"""
        self.running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        
    def stop(self):
        """停止WebSocket服务器"""
        self.running = False
        for shell in self.shells.values():
            try:
                shell.terminate()
            except:
                pass
        self.shells.clear()
        
    def _run_server(self):
        """运行服务器主循环"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            
            if self.cert_file and self.key_file:
                try:
                    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                    context.load_cert_chain(certfile=self.cert_file, keyfile=self.key_file)
                    server_socket = context.wrap_socket(server_socket, server_side=True)
                    print(f"WSS服务器启动在 {self.host}:{self.port}")
                except Exception as e:
                    print(f"WSS启动失败，使用WS: {e}")
                    print(f"WS服务器启动在 {self.host}:{self.port}")
            else:
                print(f"WS服务器启动在 {self.host}:{self.port}")
                
            while self.running:
                try:
                    client_socket, address = server_socket.accept()
                    client_thread = threading.Thread(target=self._handle_client, args=(client_socket, address), daemon=True)
                    client_thread.start()
                except:
                    break
                    
        except Exception as e:
            print(f"服务器启动失败: {e}")
        finally:
            server_socket.close()
            
    def _handle_client(self, client_socket, address):
        """处理客户端连接"""
        try:
            # WebSocket握手
            if not self._websocket_handshake(client_socket):
                client_socket.close()
                return
                
            client_id = f"{address[0]}:{address[1]}:{time.time()}"
            self.clients[client_id] = client_socket
            
            # 处理WebSocket消息
            while self.running:
                try:
                    message = self._receive_websocket_message(client_socket)
                    if message is None:
                        break
                        
                    data = json.loads(message)
                    self._handle_message(client_id, data)
                    
                except Exception as e:
                    print(f"处理消息错误: {e}")
                    break
                    
        except Exception as e:
            print(f"客户端处理错误: {e}")
        finally:
            self._cleanup_client(client_id)
            
    def _websocket_handshake(self, client_socket):
        """WebSocket握手"""
        try:
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                return False
                
            lines = data.split('\r\n')
            if len(lines) < 7 or 'Upgrade: websocket' not in data:
                return False
                
            # 提取WebSocket-Key
            ws_key = None
            for line in lines:
                if line.startswith('Sec-WebSocket-Key:'):
                    ws_key = line.split(': ')[1]
                    break
                    
            if not ws_key:
                return False
                
            # 计算accept key
            accept = base64.b64encode(
                hashlib.sha1((ws_key + self.MAGIC_STRING).encode()).digest()
            ).decode()
            
            # 发送握手响应
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n"
                "\r\n"
            )
            client_socket.send(response.encode())
            return True
            
        except Exception as e:
            print(f"握手失败: {e}")
            return False
            
    def _receive_websocket_message(self, client_socket):
        """接收WebSocket消息"""
        try:
            header = client_socket.recv(2)
            if len(header) < 2:
                return None
                
            b1, b2 = header
            fin = b1 & 0x80
            opcode = b1 & 0x0f
            masked = b2 & 0x80
            payload_length = b2 & 0x7f
            
            # 读取扩展长度
            if payload_length == 126:
                data = client_socket.recv(2)
                payload_length = struct.unpack('>H', data)[0]
            elif payload_length == 127:
                data = client_socket.recv(8)
                payload_length = struct.unpack('>Q', data)[0]
                
            # 读取掩码
            if masked:
                mask = client_socket.recv(4)
            else:
                mask = None
                
            # 读取载荷
            payload = b''
            while len(payload) < payload_length:
                data = client_socket.recv(payload_length - len(payload))
                if not data:
                    return None
                payload += data
                
            # 解掩码
            if mask:
                payload = bytes([payload[i] ^ mask[i % 4] for i in range(len(payload))])
                
            # 处理控制帧
            if opcode == self.OPCODE_CLOSE:
                return None
            elif opcode == self.OPCODE_PING:
                self._send_websocket_frame(client_socket, self.OPCODE_PONG, payload)
                return None
                
            return payload.decode('utf-8')
            
        except Exception as e:
            print(f"接收消息错误: {e}")
            return None
            
    def _send_websocket_frame(self, client_socket, opcode, data):
        """发送WebSocket帧"""
        try:
            payload = data.encode() if isinstance(data, str) else data
            payload_length = len(payload)
            
            # 构建帧头
            frame = bytearray()
            frame.append(0x80 | opcode)  # FIN=1, opcode
            
            if payload_length < 126:
                frame.append(payload_length)
            elif payload_length < 65536:
                frame.append(126)
                frame.extend(struct.pack('>H', payload_length))
            else:
                frame.append(127)
                frame.extend(struct.pack('>Q', payload_length))
                
            frame.extend(payload)
            client_socket.send(frame)
            
        except Exception as e:
            print(f"发送帧错误: {e}")
            
    def _handle_message(self, client_id, data):
        """处理接收到的消息"""
        msg_type = data.get('type')
        
        if msg_type == 'auth':
            self._handle_auth(client_id, data)
        elif msg_type == 'shell':
            self._handle_shell(client_id, data)
        elif msg_type == 'file_upload':
            self._handle_file_upload(client_id, data)
        elif msg_type == 'file_download':
            self._handle_file_download(client_id, data)
            
    def _handle_auth(self, client_id, data):
        """处理认证"""
        token = data.get('token')
        if token == self.token:
            response = {'type': 'auth_response', 'success': True}
        else:
            response = {'type': 'auth_response', 'success': False, 'message': 'Token无效'}
        
        self._send_to_client(client_id, response)
        
    def _handle_shell(self, client_id, data):
        """处理shell命令"""
        action = data.get('action')
        
        if action == 'start':
            self._start_shell(client_id)
        elif action == 'input':
            self._shell_input(client_id, data.get('data', ''))
        elif action == 'resize':
            self._shell_resize(client_id, data.get('rows', 24), data.get('cols', 80))
        elif action == 'stop':
            self._stop_shell(client_id)
            
    def _start_shell(self, client_id):
        """启动shell"""
        if client_id in self.shells:
            self._stop_shell(client_id)
            
        try:
            # 创建伪终端
            master_fd, slave_fd = pty.openpty()
            process = subprocess.Popen(
                ['/bin/bash'],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                text=True,
                bufsize=0,
                preexec_fn=os.setsid
            )
            os.close(slave_fd)
            
            self.shells[client_id] = {
                'process': process,
                'master_fd': master_fd
            }
            
            # 启动输出读取线程
            output_thread = threading.Thread(
                target=self._read_shell_output,
                args=(client_id, master_fd),
                daemon=True
            )
            output_thread.start()
            
            self._send_to_client(client_id, {'type': 'shell_started'})
            
        except Exception as e:
            self._send_to_client(client_id, {'type': 'shell_error', 'message': str(e)})
            
    def _read_shell_output(self, client_id, master_fd):
        """读取shell输出"""
        while client_id in self.shells and self.running:
            try:
                ready, _, _ = select.select([master_fd], [], [], 0.1)
                if ready:
                    data = os.read(master_fd, 4096)
                    if data:
                        self._send_to_client(client_id, {
                            'type': 'shell_output',
                            'data': base64.b64encode(data).decode()
                        })
                    else:
                        break
            except:
                break
                
        self._stop_shell(client_id)
        
    def _shell_input(self, client_id, data):
        """向shell发送输入"""
        if client_id in self.shells:
            try:
                master_fd = self.shells[client_id]['master_fd']
                os.write(master_fd, data.encode())
            except Exception as e:
                print(f"shell输入错误: {e}")
                
    def _shell_resize(self, client_id, rows, cols):
        """调整shell终端大小"""
        if client_id in self.shells:
            try:
                master_fd = self.shells[client_id]['master_fd']
                # 这里应该设置窗口大小，但标准库没有直接支持
                # 可以通过ioctl实现，但为了简化暂时跳过
            except Exception as e:
                print(f"shell resize错误: {e}")
                
    def _stop_shell(self, client_id):
        """停止shell"""
        if client_id in self.shells:
            try:
                shell = self.shells[client_id]
                shell['process'].terminate()
                os.close(shell['master_fd'])
            except:
                pass
            del self.shells[client_id]
            self._send_to_client(client_id, {'type': 'shell_stopped'})
            
    def _handle_file_upload(self, client_id, data):
        """处理文件上传"""
        try:
            file_data = base64.b64decode(data.get('content', ''))
            file_path = data.get('path', '')
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
                
            self._send_to_client(client_id, {
                'type': 'file_upload_response',
                'success': True,
                'message': f'文件已上传到 {file_path}'
            })
        except Exception as e:
            self._send_to_client(client_id, {
                'type': 'file_upload_response',
                'success': False,
                'message': str(e)
            })
            
    def _handle_file_download(self, client_id, data):
        """处理文件下载"""
        try:
            file_path = data.get('path', '')
            with open(file_path, 'rb') as f:
                file_data = f.read()
                
            self._send_to_client(client_id, {
                'type': 'file_download_response',
                'success': True,
                'content': base64.b64encode(file_data).decode(),
                'filename': os.path.basename(file_path)
            })
        except Exception as e:
            self._send_to_client(client_id, {
                'type': 'file_download_response',
                'success': False,
                'message': str(e)
            })
            
    def _send_to_client(self, client_id, data):
        """发送消息到客户端"""
        if client_id in self.clients:
            try:
                message = json.dumps(data)
                self._send_websocket_frame(self.clients[client_id], self.OPCODE_TEXT, message)
            except Exception as e:
                print(f"发送消息错误: {e}")
                self._cleanup_client(client_id)
                
    def _cleanup_client(self, client_id):
        """清理客户端连接"""
        if client_id in self.clients:
            try:
                self.clients[client_id].close()
            except:
                pass
            del self.clients[client_id]
            
        if client_id in self.shells:
            self._stop_shell(client_id)

def load_env():
    """加载环境变量"""
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# 全局服务器实例
_server_instance = None

def start_server(host=None, port=None, token=None, cert_file=None, key_file=None):
    """启动WebSocket服务器（后台运行）"""
    global _server_instance
    
    if _server_instance is not None:
        return _server_instance
        
    load_env()
    
    host = host or os.environ.get('WS_HOST', 'localhost')
    port = port or int(os.environ.get('WS_PORT', 8765))
    token = token or os.environ.get('WS_TOKEN', 'default-token')
    cert_file = cert_file or os.environ.get('CERT_FILE')
    key_file = key_file or os.environ.get('KEY_FILE')
    
    _server_instance = WebSocketServer(host, port, token, cert_file, key_file)
    _server_instance.start()
    
    return _server_instance

def stop_server():
    """停止WebSocket服务器"""
    global _server_instance
    if _server_instance:
        _server_instance.stop()
        _server_instance = None

def main():
    """主函数，用于直接运行服务器"""
    load_env()
    
    host = os.environ.get('WS_HOST', 'localhost')
    port = int(os.environ.get('WS_PORT', 8765))
    token = os.environ.get('WS_TOKEN', 'default-token')
    cert_file = os.environ.get('CERT_FILE')
    key_file = os.environ.get('KEY_FILE')
    
    server = WebSocketServer(host, port, token, cert_file, key_file)
    server.start()
    
    try:
        print(f"服务器运行中，按Ctrl+C停止...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        server.stop()
        print("服务器已停止")

if __name__ == '__main__':
    main()