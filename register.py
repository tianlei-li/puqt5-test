import hashlib
import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox, QHBoxLayout, QVBoxLayout, QGridLayout

from db_connect import Database


class RegisterDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("chimeng.png"))#设置窗口图标
        self.setWindowTitle("注册")
        self.setFixedSize(450, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fa;
            }
            QLabel {
                color: #333;
                font-size: 14px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #409eff;
            }
            QPushButton {
                background-color: #409eff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
            QComboBox {
                padding: 6px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                font-size: 14px;
            }
        """)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(15)

        # 标题
        title_label = QtWidgets.QLabel("新用户注册")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #303133;
            padding-bottom: 10px;
        """)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 表单布局
        form_layout = QGridLayout()
        form_layout.setVerticalSpacing(15)
        form_layout.setHorizontalSpacing(10)

        # 注册类型
        form_layout.addWidget(QtWidgets.QLabel("注册类型:"), 0, 0)
        self.register_type = QtWidgets.QComboBox()
        self.register_type.addItems(["员工注册", "管理员注册"])
        form_layout.addWidget(self.register_type, 0, 1, 1, 2)

        # 账号
        form_layout.addWidget(QtWidgets.QLabel("手机号:"), 1, 0)
        self.username = QtWidgets.QLineEdit()
        self.username.setPlaceholderText("输入你的手机号")
        form_layout.addWidget(self.username, 1, 1, 1, 2)

        # 员工姓名（仅员工注册显示）
        self.name_label = QtWidgets.QLabel("员工姓名:")
        form_layout.addWidget(self.name_label, 2, 0)
        self.employee_name = QtWidgets.QLineEdit()
        self.employee_name.setPlaceholderText("请输入真实姓名")
        form_layout.addWidget(self.employee_name, 2, 1, 1, 2)

        # 密码
        form_layout.addWidget(QtWidgets.QLabel("密码:"), 3, 0)

        # 密码输入框和按钮容器
        password_container = QtWidgets.QWidget()
        password_layout = QHBoxLayout(password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(0)

        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText("设置登录密码")
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        password_layout.addWidget(self.password)

        self.show_pwd_btn1 = QtWidgets.QPushButton()
        self.show_pwd_btn1.setFixedSize(30, 30)
        self.show_pwd_btn1.setIcon(QIcon(self.get_resource_path("eye_closed.png")))
        self.show_pwd_btn1.setStyleSheet("border: none; background: transparent;")
        self.show_pwd_btn1.setCursor(QtCore.Qt.PointingHandCursor)
        password_layout.addWidget(self.show_pwd_btn1)

        form_layout.addWidget(password_container, 3, 1, 1, 2)

        # 确认密码
        form_layout.addWidget(QtWidgets.QLabel("确认密码:"), 4, 0)

        # 确认密码输入框和按钮容器
        confirm_container = QtWidgets.QWidget()
        confirm_layout = QHBoxLayout(confirm_container)
        confirm_layout.setContentsMargins(0, 0, 0, 0)
        confirm_layout.setSpacing(0)

        self.confirm_password = QtWidgets.QLineEdit()
        self.confirm_password.setPlaceholderText("再次输入密码")
        self.confirm_password.setEchoMode(QtWidgets.QLineEdit.Password)
        confirm_layout.addWidget(self.confirm_password)

        self.show_pwd_btn2 = QtWidgets.QPushButton()
        self.show_pwd_btn2.setFixedSize(30, 30)
        self.show_pwd_btn2.setIcon(QIcon(self.get_resource_path("eye_closed.png")))
        self.show_pwd_btn2.setStyleSheet("border: none; background: transparent;")
        self.show_pwd_btn2.setCursor(QtCore.Qt.PointingHandCursor)
        confirm_layout.addWidget(self.show_pwd_btn2)

        form_layout.addWidget(confirm_container, 4, 1, 1, 2)

        # 管理员凭证（仅管理员注册显示）
        self.credential_label = QtWidgets.QLabel("管理员凭证:")
        form_layout.addWidget(self.credential_label, 5, 0)
        self.admin_credential = QtWidgets.QLineEdit()
        self.admin_credential.setPlaceholderText("请输入管理员凭证")
        form_layout.addWidget(self.admin_credential, 5, 1, 1, 2)
        self.credential_label.setVisible(False)
        self.admin_credential.setVisible(False)

        main_layout.addLayout(form_layout)

        # 注册按钮
        self.register_btn = QtWidgets.QPushButton("注册账号")
        self.register_btn.setStyleSheet("""
            QPushButton {
                background-color: #67c23a;
                font-size: 16px;
                padding: 10px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #85ce61;
            }
            QPushButton:pressed {
                background-color: #5daf34;
            }
        """)
        self.register_btn.setCursor(QtCore.Qt.PointingHandCursor)
        main_layout.addWidget(self.register_btn)

        self.setLayout(main_layout)

        # 连接信号
        self.register_btn.clicked.connect(self.handle_register)
        self.register_type.currentIndexChanged.connect(self.toggle_fields)
        self.show_pwd_btn1.clicked.connect(lambda: self.toggle_password_visibility(self.password, self.show_pwd_btn1))
        self.show_pwd_btn2.clicked.connect(
            lambda: self.toggle_password_visibility(self.confirm_password, self.show_pwd_btn2))

        # 初始字段状态
        self.toggle_fields(0)

    def get_resource_path(self, filename):
        """获取资源文件的绝对路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        resource_dir = os.path.join(current_dir, "assets")

        # 如果资源目录不存在，创建它
        if not os.path.exists(resource_dir):
            os.makedirs(resource_dir)

        # 创建默认的眼睛图标（如果没有的话）
        icon_path = os.path.join(resource_dir, filename)
        if not os.path.exists(icon_path):
            # 这里可以添加创建默认图标的代码
            # 实际应用中应该提供真实的图标文件
            pass

        return icon_path

    def toggle_fields(self, index):
        """根据注册类型切换字段显示"""
        is_employee = index == 0  # 员工注册

        # 员工姓名字段
        self.name_label.setVisible(is_employee)
        self.employee_name.setVisible(is_employee)

        # 管理员凭证字段
        self.credential_label.setVisible(not is_employee)
        self.admin_credential.setVisible(not is_employee)

        # 调整提示文本
        if is_employee:
            self.username.setPlaceholderText("输入你的手机号")
        else:
            self.username.setPlaceholderText("管理员账号")

    def toggle_password_visibility(self, password_field, button):
        """切换密码显示/隐藏"""
        if password_field.echoMode() == QtWidgets.QLineEdit.Password:
            password_field.setEchoMode(QtWidgets.QLineEdit.Normal)
            button.setIcon(QIcon(self.get_resource_path("eye_open.png")))
        else:
            password_field.setEchoMode(QtWidgets.QLineEdit.Password)
            button.setIcon(QIcon(self.get_resource_path("eye_closed.png")))

    def handle_register(self):
        username = self.username.text().strip()
        password = self.password.text().strip()
        confirm_password = self.confirm_password.text().strip()
        register_type = self.register_type.currentText()
        employee_name = self.employee_name.text().strip()

        # 验证手机号格式（简单验证）
        if register_type == "员工注册" and (not username.isdigit() or len(username) != 11):
            QMessageBox.warning(self, '警告', '请输入有效的11位手机号码！')
            return

        if not username:
            QMessageBox.warning(self, '警告', '请输入账号！')
            return

        if not password:
            QMessageBox.warning(self, '警告', '请输入密码！')
            return

        if password != confirm_password:
            QMessageBox.warning(self, '警告', '两次输入的密码不一致！')
            return

        # 员工注册需要姓名
        if register_type == "员工注册" and not employee_name:
            QMessageBox.warning(self, '警告', '请输入员工姓名！')
            return

        # 密码长度要求
        if len(password) < 6:
            QMessageBox.warning(self, '警告', '密码长度不能少于6位！')
            return

        md5 = hashlib.md5()
        md5.update(password.encode('utf-8'))
        encrypted_pwd = md5.hexdigest()

        db = Database()
        try:
            if register_type == "员工注册":
                # 检查手机号是否已注册
                if db.fetch_one("SELECT employee_id FROM employee_accounts WHERE account = %s", (username,)):
                    QMessageBox.warning(self, '警告', '该手机号已注册！')
                    return

                query = "INSERT INTO employee_accounts (account, password, employee_name) VALUES (%s, %s, %s)"
                db.execute(query, (username, encrypted_pwd, employee_name))
                QMessageBox.information(self, '成功', '员工注册成功！')
            else:  # 管理员注册
                # 检查账号是否已存在
                if db.fetch_one("SELECT admin_account_id FROM admin_accounts WHERE admin_account = %s", (username,)):
                    QMessageBox.warning(self, '警告', '该管理员账号已存在！')
                    return

                credential = self.admin_credential.text().strip()
                if not credential:
                    QMessageBox.warning(self, '警告', '请输入管理员凭证！')
                    return

                # 这里可以添加对凭证的验证逻辑
                if credential == "chi_meng":  # 后期会由服务器存储凭证，由服务器进行验证
                    query = "INSERT INTO admin_accounts (admin_account, admin_password) VALUES (%s, %s)"
                    db.execute(query, (username, encrypted_pwd))
                    QMessageBox.information(self, '成功', '管理员注册成功！')
                else:
                    QMessageBox.warning(self, '警告', '管理员凭证错误！')
                    return
        except Exception as e:
            QMessageBox.critical(self, '错误', f'注册失败: {str(e)}')
        finally:
            db.close()

        self.close()