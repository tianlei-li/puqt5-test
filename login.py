from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QSettings, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import (QDialog, QLabel, QLineEdit, QPushButton,QCheckBox, QMessageBox, QProgressDialog)
from PyQt5.QtGui import QIcon, QPixmap
from shixun.Main_Ui import MainWindow
from db_connect import Database
import hashlib
import os
from User_functions import UserMainWindow
main_window = None
class LoginDialog(QDialog):

    login_success_signal = QtCore.pyqtSignal(bool, int)  # 布尔值（是否管理员）和用户ID
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        self.settings = QSettings('HRM_Login', 'Settings')
        self.init_ui()
        self.load_settings()
        self.connect_signals()

    def init_ui(self):
        # 窗口基本设置
        self.setObjectName("LoginDialog")
        self.resize(800, 500)
        self.setFixedSize(800, 500)
        self.setWindowTitle("人事管理系统登录")

        # 设置应用图标（使用相对路径）
        icon_path = self.get_resource_path("chimeng.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"图标文件不存在: {icon_path}")
        # 背景设置 - 修改为渐变背景
        self.background = QLabel(self)
        self.background.setGeometry(QtCore.QRect(0, 0, 800, 500))
        # 使用从深蓝到浅蓝的渐变背景
        self.background.setStyleSheet("""
            background: qlineargradient(
                spread:pad, 
                x1:0, y1:0, 
                x2:1, y2:1, 
                stop:0 #0c2461, 
                stop:0.5 #1e3799, 
                stop:1 #4a69bd
            );
            border-radius: 10px;
        """)

        # 添加装饰性元素
        self.decorative_circle = QLabel(self)
        self.decorative_circle.setGeometry(100, 100, 200, 200)
        self.decorative_circle.setStyleSheet("""
            background: radial-gradient(
                circle, 
                rgba(255,255,255,0.1) 0%,
                rgba(255,255,255,0) 70%
            );
            border-radius: 100px;
        """)

        self.decorative_circle2 = QLabel(self)
        self.decorative_circle2.setGeometry(550, 300, 150, 150)
        self.decorative_circle2.setStyleSheet("""
            background: radial-gradient(
                circle, 
                rgba(255,255,255,0.1) 0%,
                rgba(255,255,255,0) 70%
            );
            border-radius: 75px;
        """)

        # 头像设置（使用相对路径）
        self.avatar = QLabel(self)
        self.avatar.setGeometry(QtCore.QRect(350, 50, 100, 100))
        avatar_path = self.get_resource_path(r"OIP-C.jpg")#头像路径
        if os.path.exists(avatar_path):
            self.avatar.setPixmap(QPixmap(avatar_path))
        else:
            # 使用纯色圆形代替头像
            self.avatar.setStyleSheet("""
                background: qradialgradient(
                    cx:0.5, cy:0.5, 
                    radius: 0.5,
                    fx:0.5, fy:0.5,
                    stop:0 #ffffff, 
                    stop:1 #3498db
                );
                border-radius: 50px;
            """)
        self.avatar.setScaledContents(True)
        self.avatar.setStyleSheet(self.avatar.styleSheet() + """
            border-radius: 50px; 
            border: 2px solid #ffffff;
        """)

        # 居中布局
        center_x = 400 - 150
        center_y = 250 - 50

        # 账号类型标签
        self.account_type = QLabel(self)
        self.account_type.setText("用户登录")
        self.account_type.setGeometry(QtCore.QRect(center_x, center_y - 30, 300, 30))  # 增加高度
        self.account_type.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold;
            color: #ffffff;
            background-color: rgba(0,0,0,0.2);
            border-radius: 5px;
            padding: 5px;
        """)
        self.account_type.setAlignment(QtCore.Qt.AlignCenter)

        # 用户名输入框
        self.username = QLineEdit(self)
        self.username.setGeometry(QtCore.QRect(center_x, center_y, 300, 40))  # 增加高度
        self.username.setPlaceholderText("员工账号/管理员账号")
        self.username.setStyleSheet("""
            padding: 10px; 
            border-radius: 5px; 
            border: 1px solid #ddd;
            background-color: rgba(255,255,255,0.9);
            font-size: 14px;
        """)

        # 密码输入框
        self.password = QLineEdit(self)
        self.password.setGeometry(QtCore.QRect(center_x, center_y + 50, 300, 40))  # 增加高度
        self.password.setPlaceholderText("密码")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setStyleSheet("""
            padding: 10px; 
            border-radius: 5px; 
            border: 1px solid #ddd;
            background-color: rgba(255,255,255,0.9);
            font-size: 14px;
        """)

        # 显示/隐藏密码按钮
        self.show_pwd_btn = QPushButton(self)
        self.show_pwd_btn.setGeometry(QtCore.QRect(center_x + 260, center_y + 50, 40, 40))  # 调整位置和大小
        self.show_pwd_btn.setText("👁")
        self.show_pwd_btn.setStyleSheet("""
            border: none; 
            background-color: rgba(255,255,255,0.5);
            border-radius: 3px;
            font-size: 16px;
        """)

        # 记住密码
        self.remember = QCheckBox(self)
        self.remember.setGeometry(QtCore.QRect(center_x, center_y + 100, 100, 25))  # 增加高度
        self.remember.setText("记住密码")
        self.remember.setStyleSheet("""
            color: #ffffff;
            font-size: 13px;
        """)

        # 自动登录
        self.auto_login = QCheckBox(self)
        self.auto_login.setGeometry(QtCore.QRect(center_x + 180, center_y + 100, 100, 25))  # 增加高度
        self.auto_login.setText("自动登录")
        self.auto_login.setStyleSheet("""
            color: #ffffff;
            font-size: 13px;
        """)

        # 登录按钮
        self.login_btn = QPushButton(self)
        self.login_btn.setGeometry(QtCore.QRect(center_x, center_y + 135, 300, 45))  # 增加高度
        self.login_btn.setText("登 录")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c6ea4;
            }
        """)

        # 注册按钮
        self.register_btn = QPushButton(self)
        self.register_btn.setGeometry(QtCore.QRect(center_x, center_y + 190, 140, 35))  # 调整位置和大小
        self.register_btn.setText("员工注册")
        self.register_btn.setStyleSheet("""
            QPushButton {
                color: #ffffff;
                background-color: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.2);
            }
        """)

        # 管理员登录切换按钮
        self.admin_login = QPushButton(self)
        self.admin_login.setGeometry(QtCore.QRect(center_x + 160, center_y + 190, 140, 35))  # 调整位置和大小
        self.admin_login.setText("管理员登录")
        self.admin_login.setStyleSheet("""
            QPushButton {
                color: #f1c40f;
                background-color: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.2);
            }
        """)

    def get_resource_path(self, filename):
        """获取资源文件的绝对路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, filename)

    def connect_signals(self):
        self.login_btn.clicked.connect(self.handle_login)
        self.register_btn.clicked.connect(self.show_register_dialog)
        self.admin_login.clicked.connect(self.switch_to_admin_login)
        self.show_pwd_btn.clicked.connect(self.toggle_password_visibility)
        self.username.returnPressed.connect(self.handle_login)
        self.password.returnPressed.connect(self.handle_login)

    def load_settings(self):
        username = self.settings.value('username', '', type=str)
        password = self.settings.value('password', '', type=str)
        remember = self.settings.value('remember', False, type=bool)
        auto_login = self.settings.value('auto_login', False, type=bool)
        is_admin = self.settings.value('is_admin', False, type=bool)

        self.username.setText(username)
        if remember or auto_login:
            self.password.setText(password)
            self.remember.setChecked(remember)
            self.auto_login.setChecked(auto_login)
            if is_admin:
                self.account_type.setText("管理员登录")
            else:
                self.account_type.setText("用户登录")
            if auto_login and password:
                self.handle_login()

    def handle_login(self):
        username = self.username.text().strip()
        password = self.password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, '警告', '请输入账号和密码！')
            return

        md5 = hashlib.md5()
        md5.update(password.encode('utf-8'))
        encrypted_pwd = md5.hexdigest()

        # 判断登录类型
        is_admin = self.account_type.text() == "管理员登录"
        table_name = "admin_accounts" if is_admin else "employee_accounts"
        id_field = "admin_account_id" if is_admin else "employee_id"  # 修正员工表使用employee_id
        account_field = "admin_account" if is_admin else "account"
        pwd_field = "admin_password" if is_admin else "password"

        # 创建登录进度对话框
        self.progress = QProgressDialog('正在验证身份...', '取消', 0, 100, self)
        self.progress.setWindowTitle('登录中')
        self.progress.setWindowModality(QtCore.Qt.ApplicationModal)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)
        self.progress.canceled.connect(self.cancel_login)

        # 启动进度动画
        self.animation = QPropertyAnimation(self.progress, b"value")
        self.animation.setDuration(1500)
        self.animation.setStartValue(0)
        self.animation.setEndValue(100)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        # 数据库验证
        db = Database()
        try:
            query = f"SELECT {id_field} FROM {table_name} WHERE {account_field} = %s AND {pwd_field} = %s"
            user = db.fetch_one(query, (username, encrypted_pwd))

            if user:
                user_id = user[id_field]  # 从查询结果中提取用户ID
                self.settings.setValue('username', username if self.remember.isChecked() else '')
                self.settings.setValue('password', password if self.remember.isChecked() else '')
                self.settings.setValue('remember', self.remember.isChecked())
                self.settings.setValue('auto_login', self.auto_login.isChecked())
                self.settings.setValue('is_admin', is_admin)

                self.progress.show()
                self.animation.start()
                # 连接动画完成信号到登录成功方法，并传递user_id
                self.animation.finished.connect(lambda: self.login_success(is_admin, db, user_id))
            else:
                QMessageBox.warning(self, '登录失败', '账号或密码错误，请重新输入')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'数据验证失败: {str(e)}')
            if hasattr(self, 'progress'):
                self.progress.close()
            db.close()

    def login_success(self, is_admin, db, user_id):
        """处理登录成功逻辑，接收user_id参数"""
        try:
            if hasattr(self, 'progress'):
                self.progress.close()

            # 关闭数据库连接
            db.close()

            # 关闭登录窗口并发射信号，传递is_admin和user_id
            self.accept()
            self.login_success_signal.emit(is_admin, user_id)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'登录过程出错: {str(e)}')

    def cancel_login(self):
        """处理登录取消"""
        try:
            if hasattr(self, 'animation') and self.animation.state() == QPropertyAnimation.Running:
                self.animation.stop()
            if hasattr(self, 'progress'):
                self.progress.close()
        except Exception as e:
            print(f"取消登录时出错: {str(e)}")

    def show_register_dialog(self):
        try:
            from register import RegisterDialog
            register_dialog = RegisterDialog()
            register_dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, '错误', f'无法打开注册界面: {str(e)}')

    def switch_to_admin_login(self):
        current_text = self.account_type.text()
        if current_text == "用户登录":
            self.account_type.setText("管理员登录")
            self.admin_login.setText("用户登录")
        else:
            self.account_type.setText("用户登录")
            self.admin_login.setText("管理员登录")

    def toggle_password_visibility(self):
        current_mode = self.password.echoMode()
        if current_mode == QLineEdit.Password:
            self.password.setEchoMode(QLineEdit.Normal)
            self.show_pwd_btn.setText("👁️")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.show_pwd_btn.setText("👁")

    def closeEvent(self, event):
        """窗口关闭时释放资源"""
        if hasattr(self, 'animation') and self.animation.state() == QPropertyAnimation.Running:
            self.animation.stop()
        if hasattr(self, 'progress'):
            self.progress.close()
        event.accept()
def show_main_window(is_admin, user_id):
    """根据登录类型显示不同主窗口（新增user_id参数）"""
    global main_window

    # 关闭现有窗口
    if main_window:
        main_window.close()

    try:
        if is_admin:
            main_window = MainWindow(user_id)
        else:
            main_window = UserMainWindow(user_id)

        main_window.show()
        print(f"主窗口已显示 - 类型: {'管理员' if is_admin else '用户'}, ID: {user_id}")

    except Exception as e:
        print(f"创建主窗口失败: {e}")
        QMessageBox.critical(None, "错误", f"创建主窗口失败: {str(e)}")
# 调试所用
if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    font = QtGui.QFont("Microsoft YaHei", 9)
    app.setFont(font)

    login_window = LoginDialog()




    login_window.login_success_signal.connect(show_main_window)

    login_window.show()
    sys.exit(app.exec_())

