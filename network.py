from PyQt5.QtCore import QThread, pyqtSignal
import json
import time
import socket
import datetime
import hashlib
import hmac


class SocketClient(QThread):
    """支持安全签名的Socket客户端"""
    status_updated = pyqtSignal(str)  # 用于发送状态消息
    message_received = pyqtSignal(dict)  # 用于发送接收到的消息
    connection_established = pyqtSignal()  # 连接成功信号
    connection_lost = pyqtSignal()  # 连接丢失信号


    def __init__(self, secret_key="personnel_management_system_key"):
        super().__init__()
        self.host = None
        self.port = None
        self.socket = None
        self.running = False
        self.buffer_size = 4096  # 增大缓冲区大小
        self.secret_key = secret_key.encode('utf-8')  # 初始化密钥并转为字节
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.reconnect_delay = 5  # 重连延迟(秒)

    def set_server(self, host, port):
        """设置服务器地址和端口"""
        self.host = host
        self.port = int(port)

    def send_secure_data(self, data):
        """发送带HMAC签名的数据"""
        if not self.socket or not self.running:
            self.status_updated.emit("未连接到服务器，无法发送安全数据")
            return

        try:
            # 提取命令和时间戳
            cmd = data.get("command", "")
            timestamp = data.get("timestamp", datetime.datetime.now().isoformat())

            # 生成签名
            data_to_sign = f"{cmd}|{timestamp}".encode('utf-8')
            signature = hmac.new(
                self.secret_key,
                data_to_sign,
                hashlib.sha256
            ).hexdigest()

            # 构建安全数据包
            secure_data = {
                **data,
                "signature": signature,
                "sign_type": "hmac-sha256",
                "client_type": "personnel_management_client"
            }

            # 发送数据
            json_data = json.dumps(secure_data).encode('utf-8')
            self.socket.sendall(len(json_data).to_bytes(4, byteorder='big'))
            self.socket.sendall(json_data)
            self.status_updated.emit(f"[安全] 发送命令: {cmd}")
        except Exception as e:
            self.status_updated.emit(f"发送安全命令失败: {str(e)}")
            self.handle_connection_lost()

    def run(self):
        """线程运行函数，处理Socket连接和数据接收"""
        self.running = True

        # 连接到服务器
        if not self.connect_to_server():
            # 连接失败，退出线程
            self.running = False
            return

        # 进入接收循环
        while self.running:
            if self.socket:
                try:
                    # 接收数据长度前缀
                    length_bytes = self.socket.recv(4)
                    if not length_bytes:
                        self.handle_connection_lost()
                        break

                    data_length = int.from_bytes(length_bytes, byteorder='big')

                    # 接收完整数据
                    received_data = b''
                    while len(received_data) < data_length:
                        chunk = self.socket.recv(min(self.buffer_size, data_length - len(received_data)))
                        if not chunk:
                            self.handle_connection_lost()
                            break
                        received_data += chunk

                    if received_data:
                        self.process_received_data(received_data)
                    else:
                        self.handle_connection_lost()
                        break

                except socket.timeout:
                    # 超时处理
                    self.status_updated.emit("接收数据超时")
                    continue
                except socket.error as e:
                    # 套接字错误
                    self.status_updated.emit(f"套接字错误: {str(e)}")
                    self.handle_connection_lost()
                    break
                except Exception as e:
                    # 其他错误
                    self.status_updated.emit(f"接收数据错误: {str(e)}")
                    self.handle_connection_lost()
                    break
            else:
                # 尝试重连
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    self.status_updated.emit(
                        f"尝试重连 ({self.reconnect_attempts + 1}/{self.max_reconnect_attempts})...")
                    if self.connect_to_server():
                        self.reconnect_attempts = 0
                    else:
                        self.reconnect_attempts += 1
                        time.sleep(self.reconnect_delay)  # 等待后再次尝试
                else:
                    self.status_updated.emit("重连尝试次数已达上限，停止重连")
                    self.running = False
                time.sleep(1)  # 避免CPU占用过高

    def connect_to_server(self):
        """连接到服务器，返回连接成功与否"""
        if not self.host or not self.port:
            self.status_updated.emit("请先设置服务器地址和端口")
            return False

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # 设置连接超时为10秒
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(None)  # 重置超时设置，使用阻塞模式
            self.status_updated.emit(f"成功连接到服务器 {self.host}:{self.port}")
            self.connection_established.emit()
            return True
        except Exception as e:
            self.status_updated.emit(f"连接服务器失败: {str(e)}")
            self.socket = None
            self.connection_lost.emit()
            return False

    def send_data(self, data):
        """发送数据到服务器"""
        if not self.socket or not self.running:
            self.status_updated.emit("未连接到服务器，无法发送数据")
            return

        try:
            # 将数据转换为JSON字符串
            json_data = json.dumps(data).encode('utf-8')
            # 发送数据长度和数据
            self.socket.sendall(len(json_data).to_bytes(4, byteorder='big'))
            self.socket.sendall(json_data)
            self.status_updated.emit(f"已发送数据: {data.get('type', '未知类型')}")
        except Exception as e:
            self.status_updated.emit(f"发送数据失败: {str(e)}")
            self.handle_connection_lost()

    def process_received_data(self, data):
        """处理接收到的数据，通过信号发送到主线程"""
        try:
            json_str = data.decode('utf-8')
            message = json.loads(json_str)

            # 发送原始消息到主线程处理
            self.message_received.emit(message)

        except json.JSONDecodeError as e:
            # 发送错误消息到主线程
            error_msg = {
                "type": "error",
                "error_type": "JSONDecodeError",
                "message": str(e),
                "raw_data": data[:100].decode('utf-8', errors='replace') + "..."
            }
            self.message_received.emit(error_msg)
        except Exception as e:
            error_msg = {
                "type": "error",
                "error_type": "ProcessingError",
                "message": str(e)
            }
            self.message_received.emit(error_msg)

    def handle_connection_lost(self):
        """处理连接丢失"""
        if self.running:  # 仅当线程仍在运行时发出信号
            self.status_updated.emit("与服务器的连接已丢失")
            self.connection_lost.emit()
        self.close_socket()

    def close_socket(self):
        """关闭Socket连接"""
        if self.socket:
            try:
                # 优雅关闭连接
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            except Exception as e:
                self.status_updated.emit(f"关闭socket时出错: {str(e)}")
            finally:
                self.socket = None

    def stop(self):
        """安全停止线程和连接"""
        self.running = False

        # 重置重连尝试
        self.reconnect_attempts = 0

        # 关闭socket
        self.close_socket()

        # 等待线程结束
        self.wait(2000)  # 等待最多2000秒
        if self.isRunning():
            self.terminate()  # 如果线程仍在运行，则强制终止
            self.wait()  # 确保线程已终止
            self.status_updated.emit("线程已强制终止")
        else:
            self.status_updated.emit("线程已安全停止")