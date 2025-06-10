import threading
import socket
import json
import time
import hmac
import hashlib
import subprocess
from datetime import datetime
import platform


def verify_hmac_signature(data, signature, secret_key):
    """验证HMAC签名"""
    cmd = data.get("command", "")
    timestamp = data.get("timestamp", "")
    data_to_sign = f"{cmd}|{timestamp}".encode('utf-8')
    expected_signature = hmac.new(
        secret_key.encode('utf-8'),
        data_to_sign,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


def execute_command(command):
    """安全执行命令并返回结果"""
    try:
        # 命令白名单（仅允许执行安全命令）
        safe_commands = ["ls", "dir", "echo", "date", "time", "whoami", "ping", "ps", "top", "df"]

        # 检查命令是否在白名单中（简化实现，实际应更严格）
        cmd_parts = command.split()
        if not cmd_parts:
            return {"status": "error", "message": "空命令"}

        cmd = cmd_parts[0].lower()
        if cmd not in safe_commands:
            return {"status": "error", "message": "禁止执行该命令"}

        # 根据操作系统选择合适的命令执行方式
        if platform.system() == "Windows":
            if cmd == "ls":
                cmd = "dir"  # Windows中ls等价于dir
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10  # 命令执行超时
            )
        else:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

        # 构建执行结果
        if result.returncode == 0:
            return {
                "status": "success",
                "message": "命令执行成功",
                "output": result.stdout,
                "error": result.stderr
            }
        else:
            return {
                "status": "error",
                "message": f"命令执行失败 (返回码: {result.returncode})",
                "output": result.stdout,
                "error": result.stderr
            }

    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "命令执行超时"}
    except Exception as e:
        return {"status": "error", "message": f"执行错误: {str(e)}"}


def handle_client(client_socket, client_address, secret_key="personnel_management_system_key"):
    """处理客户端连接"""
    print(f"新客户端连接: {client_address}")
    try:
        while True:
            # 接收数据长度前缀
            length_bytes = client_socket.recv(4)
            if not length_bytes:
                break

            data_length = int.from_bytes(length_bytes, byteorder='big')

            # 接收完整数据
            received_data = b''
            while len(received_data) < data_length:
                chunk = client_socket.recv(min(1024, data_length - len(received_data)))
                if not chunk:
                    break
                received_data += chunk

            if not received_data:
                break

            try:
                message = received_data.decode('utf-8')
                message_obj = json.loads(message)

                # 处理心跳包
                if message_obj.get("type") == "heartbeat":
                    response = {"type": "heartbeat_ack", "timestamp": time.time()}
                    json_response = json.dumps(response).encode('utf-8')
                    client_socket.sendall(len(json_response).to_bytes(4, byteorder='big'))
                    client_socket.sendall(json_response)
                    continue

                # 验证安全签名
                if "signature" in message_obj:
                    signature = message_obj.pop("signature")
                    sign_type = message_obj.get("sign_type", "")

                    if sign_type == "hmac-sha256":
                        is_valid = verify_hmac_signature(
                            message_obj,
                            signature,
                            secret_key
                        )

                        if not is_valid:
                            print(f"[警告] 无效签名: {message_obj}")
                            response = {
                                "type": "error",
                                "code": 401,
                                "message": "签名验证失败"
                            }
                            json_response = json.dumps(response).encode('utf-8')
                            client_socket.sendall(len(json_response).to_bytes(4, byteorder='big'))
                            client_socket.sendall(json_response)
                            continue
                    else:
                        print(f"[警告] 不支持的签名类型: {sign_type}")

                print(f"收到命令: {message_obj.get('command', '未知命令')}")

                # 执行命令（仅处理command类型消息）
                if message_obj.get("type") == "command":
                    cmd = message_obj.get("command", "")
                    if cmd:
                        # 执行命令并获取结果
                        cmd_result = execute_command(cmd)

                        # 构建响应
                        response_data = {
                            "type": "command_response",
                            "command": cmd,
                            "timestamp": datetime.now().isoformat(),
                            "status": cmd_result["status"],
                            "message": cmd_result["message"],
                            "output": cmd_result.get("output", ""),
                            "error": cmd_result.get("error", "")
                        }
                    else:
                        response_data = {
                            "type": "error",
                            "message": "命令为空"
                        }
                else:
                    response_data = {
                        "type": "response",
                        "received": message_obj,
                        "timestamp": datetime.now().isoformat(),
                        "status": "success"
                    }

                # 发送响应
                json_response = json.dumps(response_data).encode('utf-8')
                client_socket.sendall(len(json_response).to_bytes(4, byteorder='big'))
                client_socket.sendall(json_response)

            except json.JSONDecodeError:
                print(f"收到非JSON数据: {received_data.decode('utf-8', errors='ignore')}")
                response_data = {
                    "type": "legacy_response",
                    "raw_message": received_data.decode('utf-8', errors='ignore'),
                    "timestamp": time.time()
                }
                json_response = json.dumps(response_data).encode('utf-8')
                client_socket.sendall(len(json_response).to_bytes(4, byteorder='big'))
                client_socket.sendall(json_response)

    except Exception as e:
        print(f"客户端处理错误: {e}")
    finally:
        client_socket.close()
        print(f"客户端断开: {client_address}")


def start_server(host='0.0.0.0', port=5555, secret_key="personnel_management_system_key"):
    """启动服务器"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    print(f"服务器启动，监听 {host}:{port}")

    try:
        while True:
            client_socket, client_address = server.accept()
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address, secret_key),
                daemon=True
            )
            client_thread.start()
    except KeyboardInterrupt:
        print("服务器停止")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()