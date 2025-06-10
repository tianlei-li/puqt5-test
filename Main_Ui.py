import datetime
import json
import os
import socket
import time
import weakref

import PyQt5.QtCore  # 导入整个 QtCore 模块
import pymysql
import sip
from PyQt5.QtCore import QDate
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont, QColor, QCursor
from PyQt5.QtGui import QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QFrame
from PyQt5.QtWidgets import QGridLayout, QDateEdit
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
                             QLabel, QLineEdit, QComboBox, QMessageBox, QAction, QGroupBox, QTextEdit)

import history
from db_connect import Database  # 假设已存在数据库连接类
from network import SocketClient


class MainWindow(QMainWindow):
    FIELD_MAPPING = [
        "employee_id",  # 第0列
        "employee_name",  # 第1列
        "account",  # 第2列
        "created_at",  # 第3列（日期类型）
        "marital_status",  # 第4列
        "education",  # 第5列
        "gender",  # 第6列
        "position_name"  # 第7列（可能为NULL）
    ] # 员工字段映射
    POSITION_FIELD_MAPPING = ["position_id", "position_name"]   # 职位映射
    def __init__(self, admin_type_id=1):
        super().__init__()
        self.admin_type_id = admin_type_id  # 管理员登录
        self.db = Database()  # 数据库连接
        self.init_ui()
        self.load_employee_data()  # 加载员工数据
        self.setup_menu()  # 设置菜单
        self.object_cleanup_timers = {}  # 维护清理定时器
        self.weak_refs = weakref.WeakValueDictionary()  # 全局弱引用存储
        self.socket_client = None  # 初始化 SocketClient 对象
        self.history_service = history.HistoryService(self.db)  # 初始化历史记录服务

    def init_ui(self):
        # 窗口基本设置
        self.setWindowIcon(QIcon("chimeng.png"))#设置窗口图标
        self.setWindowTitle("人事管理系统 - 主界面")
        self.resize(1735, 1050)
        self.setMinimumSize(1000, 600)

        # 中央部件和主布局
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        # 侧边栏导航
        self.setup_side_navigation(main_layout)

        # 中央内容区 - 初始显示员工列表
        self.employee_tab = self.create_employee_list_tab()
        self.current_tab = self.employee_tab
        main_layout.addWidget(self.current_tab, 3)  # 中央区域占3份，侧边栏占1份

        # 状态栏
        self.statusBar().showMessage(f"'管理员'登录 就绪", 3000)


    def setup_side_navigation(self, main_layout):
        """设置侧边栏导航"""
        side_nav = QWidget()
        side_nav.setMinimumWidth(200)
        side_nav.setStyleSheet("""
            background-color: #f0f5ff;
            border-right: 1px solid #d0d8e6;
        """)
        nav_layout = QVBoxLayout(side_nav)

        # 系统标题
        title_label = QLabel("人事管理系统")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #165DFF;
            padding: 15px;
            border-bottom: 1px solid #d0d8e6;
        """)
        nav_layout.addWidget(title_label)

        # 导航按钮
        self.nav_buttons = {
            "employee": self.create_nav_button("员工管理", "📋"),
            "position": self.create_nav_button("职位管理", "💼"),
            "history": self.create_nav_button("历史记录", "📜"),
            "admin": self.create_nav_button("系统管理", "⚙️"),
            "server": self.create_nav_button("服务器通信", "📡"),
            "reply": self.create_nav_button("回复箱", "💬")
        }

        for btn in self.nav_buttons.values():
            if btn:
                nav_layout.addWidget(btn)

        nav_layout.addStretch()  # 底部拉伸，使按钮居上
        main_layout.addWidget(side_nav, 1)  # 侧边栏占1份

    def create_nav_button(self, text, icon_char):
        """创建导航按钮"""
        btn = QPushButton(f"{icon_char}  {text}")
        btn.setMinimumHeight(50)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                text-align: left;
                padding-left: 20px;
                font-size: 14px;
                border: none;
                border-radius: 0;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #e0e8ff;
            }
            QPushButton:pressed {
                background-color: #d0d8e6;
            }
        """)
        btn.clicked.connect(lambda checked, t=text: self.switch_tab(t))
        return btn


    def setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")
        logout_action = QAction("退出登录", self)
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于系统", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def get_resource_path(self, relative_path):
        """获取资源文件的绝对路径"""
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def show_about(self):
        """显示美化后的关于对话框"""
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("关于人事管理系统")
        about_dialog.setFixedSize(450, 320)
        about_dialog.setStyleSheet("background-color: white;")
        about_dialog.setWindowFlags(
            about_dialog.windowFlags() & ~PyQt5.QtCore.Qt.WindowContextHelpButtonHint
        )

        layout = QVBoxLayout(about_dialog)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 图标
        icon_label = QLabel()
        icon_path = self.get_resource_path("chimeng.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
            icon_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon_label)

        # 标题
        title_label = QLabel("人事管理系统")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #165DFF;
            margin: 10px 0;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 版本信息
        version_label = QLabel("版本: 1.0.0")
        version_label.setStyleSheet("font-size: 14px; color: #666;")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # 系统说明
        desc_text = """
        <p style="text-align: center; margin: 10px 0; color: #333;">
            人事管理系统是一款专为企业打造的员工信息管理工具，<br>
            提供员工档案管理、职位设置、操作历史追踪等功能，<br>
            帮助企业高效管理人力资源。
        </p>
        """
        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # 版权信息
        copyright_label = QLabel("© 2025 人事管理系统 - 版权所有")
        copyright_label.setStyleSheet("font-size: 12px; color: #999; margin-top: 20px;")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)

        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.setMinimumSize(100, 35)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #165DFF;
                color: white;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0D47A1;
            }
        """)
        ok_btn.clicked.connect(about_dialog.accept)
        layout.addWidget(ok_btn, alignment=Qt.AlignCenter)

        about_dialog.exec_()

    def logout(self):
        """退出登录"""
        reply = QMessageBox.question(self, '确认', '确定要退出登录吗？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()

    def _populate_employee_table(self, employees):
        """通用方法：填充员工表格数据"""
        self.employee_table.setRowCount(len(employees))
        for row, emp in enumerate(employees):
            for col in range(8):
                field = self.FIELD_MAPPING[col]
                value = emp.get(field, "")
                if isinstance(value, (datetime.date, datetime.datetime)):
                    value = value.strftime('%Y-%m-%d')
                item_text = str(value) if value is not None else "未设置"
                self.employee_table.setItem(row, col, QTableWidgetItem(item_text))

    # 另一个功能的ui  分界符********************************
    def create_employee_list_tab(self):
        """创建员工列表选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 搜索栏
        search_bar = QHBoxLayout()
        search_bar.setContentsMargins(10, 10, 10, 10)

        # ---------- 新增搜索类型选择 ----------
        search_type_label = QLabel("搜索类型:")
        self.search_field_combo = QComboBox()
        self.search_field_combo.addItems(["员工ID", "姓名", "电话"])  # 可扩展更多字段

        self.emp_search = QLineEdit()
        self.emp_search.setPlaceholderText("输入搜索内容")
        self.emp_search.setMinimumWidth(200)
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search_employees)
        # --------------------------------------

        add_btn = QPushButton("添加员工")
        add_btn.clicked.connect(self.add_employee)
        edit_btn = QPushButton("修改员工")
        edit_btn.clicked.connect(self.edit_employee)
        del_btn = QPushButton("删除员工")
        del_btn.clicked.connect(self.delete_employee)

        # 组装搜索栏（注意顺序：类型选择 → 输入框 → 搜索按钮）
        search_bar.addWidget(search_type_label)
        search_bar.addWidget(self.search_field_combo)
        search_bar.addWidget(self.emp_search)
        search_bar.addWidget(search_btn)
        search_bar.addStretch()
        search_bar.addWidget(add_btn)
        search_bar.addWidget(edit_btn)
        search_bar.addWidget(del_btn)

        layout.addLayout(search_bar)

        # 员工表格
        self.employee_table = QTableWidget()
        self.employee_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 不可编辑
        self.employee_table.setSelectionBehavior(QTableWidget.SelectRows)  # 整行选择
        self.employee_table.setSelectionMode(QTableWidget.SingleSelection)  # 单选
        self.employee_table.setColumnCount(8)
        self.employee_table.setHorizontalHeaderLabels([
            "员工ID", "姓名", "电话", "入职日期", "婚姻状况", "学历", "性别", "职位"
        ])
        self.employee_table.horizontalHeader().setStretchLastSection(True)
        self.employee_table.doubleClicked.connect(self.edit_employee)  # 双击编辑

        layout.addWidget(self.employee_table)

        return tab
    # 另一个功能的ui  分界符********************************
    def load_employee_data(self):
        """加载员工基本信息到表格"""
        try:
            query = """
                SELECT e.employee_id, a.employee_name, a.account, a.created_at, 
                       e.marital_status, e.education, e.gender, p.position_name
                FROM employee_basic_info e
                LEFT JOIN employee_positions p ON e.position_id = p.position_id
                LEFT JOIN employee_accounts a ON e.employee_id = a.employee_id
                ORDER BY e.employee_id
            """

            employees = self.db.fetch_all(query)
            self._populate_employee_table(employees)


            self.statusBar().showMessage(f"已加载 {len(employees)} 条员工记录", 3000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载员工数据失败: {str(e)}")

    def search_employees(self):
        """搜索员工（优化版：支持选择搜索字段）"""
        keyword = self.emp_search.text().strip()
        if not keyword:
            self.load_employee_data()
            return

        # 1. 获取用户选择的搜索字段
        search_field = self.search_field_combo.currentText()

        # 2. 映射界面字段 → 数据库字段（确保表别名正确！）
        field_mapping = {
            "员工ID": "e.employee_id",  # e → employee_basic_info
            "姓名": "a.employee_name",  # a → employee_accounts
            "电话": "a.account"  # a → employee_accounts
        }
        db_field = field_mapping.get(search_field)
        if not db_field:
            QMessageBox.warning(self, "错误", "无效的搜索字段，请选择有效选项")
            return

        try:
            # 3. 构造动态查询
            query = f"""
                SELECT e.employee_id, a.employee_name, a.account, a.created_at, 
                       e.marital_status, e.education, e.gender, p.position_name
                FROM employee_basic_info e
                LEFT JOIN employee_positions p ON e.position_id = p.position_id
                LEFT JOIN employee_accounts a ON e.employee_id = a.employee_id
                WHERE {db_field} LIKE %s 
                ORDER BY e.employee_id
            """
            params = (f"%{keyword}%",)  # 模糊查询参数

            # 4. 执行查询并填充表格
            employees = self.db.fetch_all(query, params)
            self._populate_employee_table(employees)  # 复用统一填充方法

            self.statusBar().showMessage(f"搜索到 {len(employees)} 条记录", 3000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"搜索失败: {str(e)}")
    def add_employee(self):
        """添加员工（完整实现）"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加员工")
        dialog.setMinimumWidth(400)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        # 表单字段
        form_layout = QGridLayout()
        row = 0

        # 姓名
        form_layout.addWidget(QLabel("姓名:"), row, 0)
        name_input = QLineEdit()
        form_layout.addWidget(name_input, row, 1)
        row += 1

        # 电话
        form_layout.addWidget(QLabel("电话:"), row, 0)
        phone_input = QLineEdit()
        form_layout.addWidget(phone_input, row, 1)
        row += 1

        # 入职日期
        form_layout.addWidget(QLabel("入职日期:"), row, 0)
        hire_date_input = QDateEdit()
        hire_date_input.setDate(QDate.currentDate())
        hire_date_input.setCalendarPopup(True)
        form_layout.addWidget(hire_date_input, row, 1)
        row += 1

        # 婚姻状况
        form_layout.addWidget(QLabel("婚姻状况:"), row, 0)
        marital_combo = QComboBox()
        marital_combo.addItems(['单身', '已婚', '离异', '丧偶', '未录入'])
        form_layout.addWidget(marital_combo, row, 1)
        row += 1

        # 学历
        form_layout.addWidget(QLabel("学历:"), row, 0)
        edu_combo = QComboBox()
        edu_combo.addItems(['高中', '大专', '本科', '硕士', '博士','未录入'])
        form_layout.addWidget(edu_combo, row, 1)
        row += 1

        # 性别
        form_layout.addWidget(QLabel("性别:"), row, 0)
        gender_combo = QComboBox()
        gender_combo.addItems(['男', '女', '未录入'])
        form_layout.addWidget(gender_combo, row, 1)
        row += 1

        # 职位
        form_layout.addWidget(QLabel("职位:"), row, 0)
        position_combo = QComboBox()

        # 加载职位数据
        try:
            positions = self.db.fetch_all("SELECT position_id, position_name FROM employee_positions")
            for pos in positions:
                position_combo.addItem(pos['position_name'], pos['position_id'])
        except Exception as e:
            QMessageBox.critical(dialog, "错误", f"加载职位数据失败: {str(e)}")

        form_layout.addWidget(position_combo, row, 1)
        row += 1

        layout.addLayout(form_layout)

        # 按钮区域
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        # 保存逻辑
        def save_employee():
            # 数据验证
            if not name_input.text().strip():
                QMessageBox.warning(dialog, "警告", "姓名不能为空")
                return

            if not phone_input.text().strip():
                QMessageBox.warning(dialog, "警告", "电话不能为空")
                return

            # 检查电话唯一性
            try:
                check_query = "SELECT COUNT(*) AS count FROM employee_accounts WHERE account = %s"
                # 传递 1 个参数，匹配 1 个 %s
                result = self.db.fetch_one(check_query, (phone_input.text().strip(),))
                if result and result['count'] > 0:
                    QMessageBox.warning(dialog, "错误", "该电话号码已被使用")
                    return
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"验证电话失败: {str(e)}")
                return
            # 获取QDate对象
            hire_date = hire_date_input.date()
            # 转换为Python datetime并格式化为SQL字符串
            py_datetime = datetime.datetime(hire_date.year(), hire_date.month(), hire_date.day())
            sql_datetime_str = py_datetime.strftime('%Y-%m-%d %H:%M:%S')
            # 构建插入数据
            data = {
                'employee_name': name_input.text().strip(),
                'account': phone_input.text().strip(),
                'password': 'd5e1602460a42e0f6bfef74522606b93',  # 默认密码 pass123
                'created_at': sql_datetime_str,  # 使用正确的日期时间格式
                'marital_status': marital_combo.currentText(),
                'education': edu_combo.currentText(),
                'gender': gender_combo.currentText(),
                'position_id': position_combo.currentData() or None
            }
            try:
                # 1. 使用原始连接手动管理事务（绕过封装类的自动提交）
                conn = self.db.connection  # 获取原始 pymysql 连接
                conn.begin()  # 手动开启事务

                # 2. 插入员工账户表（使用原始游标）
                with conn.cursor() as cursor:
                    account_query = """
                        INSERT INTO employee_accounts 
                        (employee_name, account, password, created_at)
                        VALUES (%(employee_name)s, %(account)s, %(password)s, %(created_at)s)
                    """
                    cursor.execute(account_query, data)

                    # 3. 立即获取自增 ID（关键：使用同一游标）
                    employee_id = cursor.lastrowid  # 直接从游标获取
                    if employee_id == 0:
                        # 备选方案：执行 SELECT LAST_INSERT_ID()
                        cursor.execute("SELECT LAST_INSERT_ID() AS last_id")
                        result = cursor.fetchone()
                        employee_id = result['last_id']


                # 4. 更新/插入基本信息表（仍使用原始连接）
                with conn.cursor() as cursor:
                    info_query = """
                        UPDATE employee_basic_info 
                        SET marital_status = %(marital_status)s,
                            education = %(education)s,
                            gender = %(gender)s,
                            position_id = %(position_id)s
                        WHERE employee_id = %(employee_id)s
                    """
                    info_data = {**data, 'employee_id': employee_id}
                    cursor.execute(info_query, info_data)



                # 5. 手动提交事务（关键）
                conn.commit()
                # 记录员工创建历史
                self.history_service.record_change(
                    employee_id=employee_id,
                    change_type="employee_create",  # 对应change_type_dict中的type_name
                    old_info={},  # 新增无旧信息
                    new_info=data,
                    operator_id=self.admin_type_id,  # 从登录状态获取
                    client_ip=self.get_current_ip()  # 可选：获取客户端IP
                )
                QMessageBox.information(dialog, "成功", "员工添加成功")
                self.load_employee_data()  # 刷新数据
                dialog.accept()
            except pymysql.Error as e:
                QMessageBox.critical(dialog, "错误", f"添加失败: {str(e)}")

        save_btn.clicked.connect(save_employee)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec_()
    #上面为添加员工的ui
    # 下面为修改员工信息的ui
    def edit_employee(self):
        """修改员工（完善版）"""
        # 获取选中行
        selected_rows = self.employee_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要修改的员工")
            return

        row = selected_rows[0].row()
        emp_id = self.employee_table.item(row, 0).text()

        # 获取员工当前数据
        try:
            query = """
                SELECT e.employee_id, a.employee_name, a.account, a.created_at, 
                       e.marital_status, e.education, e.gender, p.position_name
                FROM employee_basic_info e
                LEFT JOIN employee_positions p ON e.position_id = p.position_id
                LEFT JOIN employee_accounts a ON e.employee_id = a.employee_id
                WHERE e.employee_id = %s
            """
            emp_data = self.db.fetch_one(query, (emp_id,))
            if not emp_data:
                QMessageBox.warning(self, "错误", "所选员工不存在")
                return
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取员工数据失败: {str(e)}")
            return

        # 创建编辑对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"修改员工 - {emp_data['employee_name']}")
        dialog.setMinimumWidth(400)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        # 创建表单字段
        form_layout = QGridLayout()

        # 姓名
        form_layout.addWidget(QLabel("姓名:"), 0, 0)
        name_input = QLineEdit(emp_data['employee_name'])
        form_layout.addWidget(name_input, 0, 1)

        # 电话
        form_layout.addWidget(QLabel("电话:"), 1, 0)
        phone_input = QLineEdit(emp_data['account'])
        form_layout.addWidget(phone_input, 1, 1)

        # 入职日期（直接构造QDate，避免fromPyDate）
        form_layout.addWidget(QLabel("入职日期:"), 2, 0)
        hire_date_input = QDateEdit()
        hire_date = emp_data['created_at']
        hire_date_input.setDate(QDate(hire_date.year, hire_date.month, hire_date.day))
        hire_date_input.setCalendarPopup(True)
        form_layout.addWidget(hire_date_input, 2, 1)

        # 婚姻状况
        form_layout.addWidget(QLabel("婚姻状况:"), 3, 0)
        marital_combo = QComboBox()
        marital_combo.addItems(['单身', '已婚', '离异', '丧偶', '未录入'])
        marital_combo.setCurrentText(emp_data['marital_status'])
        form_layout.addWidget(marital_combo, 3, 1)

        # 学历
        form_layout.addWidget(QLabel("学历:"), 4, 0)
        edu_combo = QComboBox()
        edu_combo.addItems(['高中', '大专', '本科', '硕士', '博士','未录入'])
        edu_combo.setCurrentText(emp_data['education'])
        form_layout.addWidget(edu_combo, 4, 1)

        # 性别
        form_layout.addWidget(QLabel("性别:"), 5, 0)
        gender_combo = QComboBox()
        gender_combo.addItems(['男', '女', '未录入'])
        gender_combo.setCurrentText(emp_data['gender'])
        form_layout.addWidget(gender_combo, 5, 1)

        # 职位（处理position_id为NULL的情况）
        form_layout.addWidget(QLabel("职位:"), 6, 0)
        position_combo = QComboBox()
        try:
            positions = self.db.fetch_all(
                "SELECT position_id, position_name FROM employee_positions ORDER BY position_id")
            current_pos_id = emp_data.get('position_id', None)  # 允许NULL
            current_pos_index = -1
            for i, pos in enumerate(positions):
                position_combo.addItem(pos['position_name'], pos['position_id'])
                if pos['position_id'] == current_pos_id:
                    current_pos_index = i
            if current_pos_index != -1:
                position_combo.setCurrentIndex(current_pos_index)
        except Exception as e:
            QMessageBox.critical(dialog, "错误", f"加载职位数据失败: {str(e)}")
            return

        layout.addLayout(form_layout)

        # 按钮区域
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        # 保存逻辑（修正JSON序列化）
        def update_employee():
            # 数据验证
            if not name_input.text().strip():
                QMessageBox.warning(dialog, "警告", "姓名不能为空")
                return

            if not phone_input.text().strip():
                QMessageBox.warning(dialog, "警告", "电话不能为空")
                return

            # 检查电话唯一性
            try:
                check_query = "SELECT COUNT(*) FROM employee_accounts WHERE account = %s AND employee_id != %s"
                count = self.db.fetch_one(check_query, (phone_input.text(), emp_id))['COUNT(*)']
                if count > 0:
                    QMessageBox.warning(dialog, "错误", "该电话号码已被使用")
                    return
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"电话验证失败: {str(e)}")
                return

            # 构建更新数据
            new_data = {
                'employee_id': emp_id,
                'employee_name': name_input.text(),
                'account': phone_input.text(),
                'marital_status': marital_combo.currentText(),
                'education': edu_combo.currentText(),
                'gender': gender_combo.currentText(),
                'position_id': position_combo.currentData()
            }

            # 旧数据转换为可序列化格式
            old_info = {
                'employee_id': emp_id,
                'employee_name': emp_data['employee_name'],
                'account': emp_data['account'],
                'marital_status': emp_data['marital_status'],
                'education': emp_data['education'],
                'gender': emp_data['gender'],
                'position_id': emp_data.get('position_id', None),
                'position_name': emp_data.get('position_name', '')
            }

            # 检查变更
            has_changes = any(new_data[key] != old_info[key] for key in new_data if key in old_info)
            if not has_changes:
                QMessageBox.information(dialog, "提示", "无数据变更")
                dialog.accept()
                return

            # 事务处理
            try:
                self.db.begin_transaction()

                # 更新员工表
                update_sql = """
                    UPDATE employee_basic_info 
                    SET marital_status=%s, education=%s, gender=%s, position_id=%s 
                    WHERE employee_id=%s
                """
                self.db.execute(update_sql, (
                    new_data['marital_status'], new_data['education'],
                    new_data['gender'], new_data['position_id'], new_data['employee_id']
                ))

                # 更新员工账户表（姓名和电话）
                account_sql = """
                    UPDATE employee_accounts 
                    SET employee_name=%s, account=%s 
                    WHERE employee_id=%s
                """
                self.db.execute(account_sql, (
                    new_data['employee_name'], new_data['account'], new_data['employee_id']
                ))

                self.db.commit()

                self.history_service.record_change(
                    employee_id=emp_id,
                    change_type="info_update",
                    old_info=old_info,
                    new_info=new_data,
                    operator_id=self.admin_type_id,
                    client_ip=self.get_current_ip()
                )
                QMessageBox.information(dialog, "成功", "员工信息更新成功")
                self.load_employee_data()
                dialog.accept()
            except pymysql.Error as e:
                self.db.rollback()
                if e.args[0] == 1452:
                    QMessageBox.critical(dialog, "错误", "职位不存在，操作失败")
                else:
                    QMessageBox.critical(dialog, "错误", f"数据库错误: {str(e)}")
            except Exception as e:
                self.db.rollback()
                QMessageBox.critical(dialog, "错误", f"未知错误: {str(e)}")

        save_btn.clicked.connect(update_employee)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec_()
###  上面为修改员工得函数
# 下面为删除员工得函数
    def delete_employee(self):
        """删除员工"""
        selected_rows = self.employee_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的员工")
            return

        # 修正：获取QModelIndex对应的行号
        row = selected_rows[0].row()  # 获取选中行的行号
        emp_id = self.employee_table.item(row, 0).text()
        emp_name = self.employee_table.item(row, 1).text()

        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除员工 {emp_name} (ID: {emp_id}) 吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                # 获取删除前的员工信息
                query = """
                    SELECT e.employee_id, a.employee_name, a.account, a.created_at, 
                           e.marital_status, e.education, e.gender, p.position_name
                    FROM employee_basic_info e
                    LEFT JOIN employee_positions p ON e.position_id = p.position_id
                    LEFT JOIN employee_accounts a ON e.employee_id = a.employee_id
                    WHERE e.employee_id = %s
                """
                emp_data = self.db.fetch_one(query, (emp_id,))

                query = "DELETE FROM employee_basic_info WHERE employee_id = %s"
                self.db.execute(query, (emp_id,))

                self.history_service.record_change(
                    employee_id=emp_id,
                    change_type="employee_delete",
                    old_info=emp_data,
                    new_info={},  # 删除后无新信息
                    operator_id=self.admin_type_id,
                    client_ip=self.get_current_ip()
                )
                self.load_employee_data()  # 重新加载数据
                self.statusBar().showMessage(f"已删除员工 {emp_name}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
    # 另一个功能的ui  分界符********************************
    def create_position_management_tab(self):
        """创建职位管理选项卡（重构版）"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # 顶部操作栏
        top_bar = QHBoxLayout()

        # 搜索框
        search_frame = QWidget()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.addWidget(QLabel("职位名称:"))
        self.pos_search = QLineEdit()
        self.pos_search.setPlaceholderText("输入职位名称搜索")
        search_layout.addWidget(self.pos_search)
        search_btn = QPushButton("搜索")
        search_layout.addWidget(search_btn)
        top_bar.addWidget(search_frame)

        # 操作按钮
        btn_frame = QWidget()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        add_btn = QPushButton("添加职位")
        edit_btn = QPushButton("修改职位")
        delete_btn = QPushButton("删除职位")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        top_bar.addWidget(btn_frame)
        top_bar.addStretch()  # 按钮靠右排列

        layout.addLayout(top_bar)

        # 职位表格
        self.position_table = QTableWidget()
        self.position_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.position_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.position_table.setSelectionMode(QTableWidget.SingleSelection)
        self.position_table.setColumnCount(2)
        self.position_table.setHorizontalHeaderLabels(["职位ID", "职位名称"])
        self.position_table.horizontalHeader().setStretchLastSection(True)
        self.position_table.verticalHeader().setVisible(False)  # 隐藏行号
        self.position_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #d0d8e6;
                border-radius: 4px;
                background-color: white;
            }
            QTableWidget::header {
                background-color: #f0f5ff;
                border-bottom: 1px solid #d0d8e6;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)

        layout.addWidget(self.position_table)

        # 状态提示
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 12px; margin-top: 5px;")
        layout.addWidget(self.status_label)

        # 加载数据
        self.load_position_data()

        # 事件连接
        search_btn.clicked.connect(self.search_positions)
        add_btn.clicked.connect(self.show_add_position_dialog)
        edit_btn.clicked.connect(self.show_edit_position_dialog)
        delete_btn.clicked.connect(self.delete_position)
        self.position_table.doubleClicked.connect(self.show_edit_position_dialog)

        return tab

    def load_position_data(self):
        """加载职位数据（修复版）"""
        try:
            query = "SELECT position_id, position_name FROM employee_positions ORDER BY position_id"
            positions = self.db.fetch_all(query)

            self.position_table.setRowCount(len(positions))
            for row, pos in enumerate(positions):
                for col in range(2):
                    field = self.POSITION_FIELD_MAPPING[col]  # 按列取字段名
                    value = pos.get(field, "")  # 安全获取值（避免键不存在）

                    # 处理空值（如数据库中为NULL）
                    item_text = str(value) if value is not None else "未设置"

                    item = QTableWidgetItem(item_text)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.position_table.setItem(row, col, item)

            self.status_label.setText(f"共加载 {len(positions)} 个职位")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载职位数据失败: {str(e)}")
            self.status_label.setText("数据加载失败")

    def search_positions(self):
        """搜索职位（修复版）"""
        keyword = self.pos_search.text().strip()
        if not keyword:
            self.load_position_data()
            return

        try:
            query = "SELECT position_id, position_name FROM employee_positions WHERE position_name LIKE %s ORDER BY position_id"
            positions = self.db.fetch_all(query, (f"%{keyword}%",))

            self.position_table.setRowCount(len(positions))
            for row, pos in enumerate(positions):
                for col in range(2):
                    field = self.POSITION_FIELD_MAPPING[col]
                    value = pos.get(field, "")
                    item_text = str(value) if value is not None else "未设置"

                    item = QTableWidgetItem(item_text)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.position_table.setItem(row, col, item)

            self.status_label.setText(f"搜索到 {len(positions)} 个职位")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"搜索职位失败: {str(e)}")
            self.status_label.setText("搜索失败")
    def show_add_position_dialog(self):
        """显示添加职位对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加职位")
        dialog.setFixedSize(300, 150)
        layout = QVBoxLayout(dialog)

        # 输入框
        name_label = QLabel("职位名称:")
        name_input = QLineEdit()
        name_input.setPlaceholderText("如：软件工程师")

        # 按钮
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addWidget(name_label)
        layout.addWidget(name_input)
        layout.addLayout(btn_layout)

        def handle_ok():
            position_name = name_input.text().strip()
            if not position_name:
                QMessageBox.warning(dialog, "警告", "请输入职位名称")
                return

            try:
                with self.db.connection.cursor() as cursor:
                    # 执行插入并获取自增ID
                    query = "INSERT INTO employee_positions (position_name) VALUES (%s)"
                    cursor.execute(query, (position_name,))
                    position_id = cursor.lastrowid
                    self.db.connection.commit()

                # 记录职位创建历史
                self.history_service.record_position_create(
                    position_id=position_id,
                    position_name=position_name,
                    operator_id=self.admin_type_id,
                    client_ip=self.get_current_ip()
                )

                self.load_position_data()
                dialog.accept()
                self.status_label.setText(f"已添加职位: {position_name}")
            except pymysql.Error as e:
                if e.args[0] == 1062:
                    QMessageBox.warning(dialog, "错误", "该职位名称已存在")
                else:
                    QMessageBox.critical(dialog, "错误", f"添加失败: {e}")

        ok_btn.clicked.connect(handle_ok)
        cancel_btn.clicked.connect(dialog.reject)
        name_input.returnPressed.connect(handle_ok)

        dialog.exec_()

    def show_edit_position_dialog(self):
        """显示修改职位对话框"""
        # 修正：使用正确的表格
        selected_rows = self.position_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要修改的职位")
            return

        row = selected_rows[0].row()
        # 安全检查：确保单元格有数据
        pos_id_item = self.position_table.item(row, 0)
        pos_name_item = self.position_table.item(row, 1)

        if not pos_id_item or not pos_name_item:
            QMessageBox.warning(self, "错误", "所选职位数据不完整")
            return

        pos_id = pos_id_item.text()
        current_name = pos_name_item.text()

        dialog = QDialog(self)
        dialog.setWindowTitle("修改职位")
        dialog.setFixedSize(300, 150)
        layout = QVBoxLayout(dialog)

        name_label = QLabel("职位名称:")
        name_input = QLineEdit(current_name)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addWidget(name_label)
        layout.addWidget(name_input)
        layout.addLayout(btn_layout)

        def handle_ok():
            new_name = name_input.text().strip()
            if not new_name:
                QMessageBox.warning(dialog, "警告", "请输入职位名称")
                return

            if new_name == current_name:
                dialog.accept()
                return

            try:
                # 获取旧职位名称
                old_name = pos_name_item.text()

                # 执行更新
                query = "UPDATE employee_positions SET position_name = %s WHERE position_id = %s"
                self.db.execute(query, (new_name, pos_id))

                # 记录职位更新历史
                self.history_service.record_position_update(
                    position_id=int(pos_id),
                    old_name=old_name,
                    new_name=new_name,
                    operator_id=self.admin_type_id,
                    client_ip=self.get_current_ip()
                )

                self.load_position_data()
                dialog.accept()
                self.status_label.setText(f"已修改职位ID {pos_id} 为: {new_name}")
            except pymysql.Error as e:
                if e.args[0] == 1062:
                    QMessageBox.warning(dialog, "错误", "该职位名称已存在")
                else:
                    QMessageBox.critical(dialog, "错误", f"修改失败: {e}")

        ok_btn.clicked.connect(handle_ok)
        cancel_btn.clicked.connect(dialog.reject)
        name_input.returnPressed.connect(handle_ok)

        dialog.exec_()

    def delete_position(self):
        """删除职位"""
        # 修正：使用正确的表格
        selected_rows = self.position_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的职位")
            return

        row = selected_rows[0].row()
        # 安全检查
        pos_id_item = self.position_table.item(row, 0)
        pos_name_item = self.position_table.item(row, 1)

        if not pos_id_item or not pos_name_item:
            QMessageBox.warning(self, "错误", "所选职位数据不完整")
            return

        pos_id = pos_id_item.text()
        pos_name = pos_name_item.text()

        # 检查职位是否被使用
        try:
            check_query = "SELECT COUNT(*) as count FROM employee_basic_info WHERE position_id = %s"
            result = self.db.fetch_one(check_query, (pos_id,))
            if result and result['count'] > 0:
                QMessageBox.warning(self, "错误", f"职位 '{pos_name}' 正在被使用，无法删除")
                return

            reply = QMessageBox.question(self, "确认删除",
                                         f"确定要删除职位 '{pos_name}' (ID: {pos_id}) 吗？",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                query = "DELETE FROM employee_positions WHERE position_id = %s"
                self.db.execute(query, (pos_id,))
                self.history_service.record_position_delete(
                    position_id=int(pos_id),
                    position_name=pos_name,
                    operator_id=self.admin_type_id,
                    client_ip=self.get_current_ip()
                )

                self.load_position_data()
                self.status_label.setText(f"已删除职位: {pos_name}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除失败: {e}")
            self.status_label.setText("删除操作失败")





    # 另一个功能模块 分节符****************************************************************
    def create_history_management_tab(self):
        """创建历史记录管理选项卡（增强交互版）"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 标题栏
        title_label = QLabel("历史记录管理")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #333; padding: 8px 0; text-align: center;")
        layout.addWidget(title_label)

        # 筛选栏（紧凑设计）
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "border: 1px solid #e0e0e0; border-radius: 6px; background-color: #f9f9f9; padding: 10px;")
        filter_layout = QGridLayout(filter_frame)
        filter_layout.setContentsMargins(8, 8, 8, 8)
        filter_layout.setSpacing(8)
        filter_layout.setColumnStretch(0, 1)
        filter_layout.setColumnStretch(1, 2)  # 给员工筛选更多空间
        filter_layout.setColumnStretch(2, 1)
        filter_layout.setColumnStretch(3, 2)  # 给日期范围更多空间

        # 员工筛选（简化）
        emp_label = QLabel("员工筛选:")
        emp_label.setStyleSheet("font-weight: bold;")
        filter_layout.addWidget(emp_label, 0, 0)

        self.history_emp_id = QLineEdit()
        self.history_emp_id.setPlaceholderText("输入员工ID或姓名")
        self.history_emp_id.setClearButtonEnabled(True)
        # 添加回车键触发搜索
        self.history_emp_id.returnPressed.connect(self.search_history)
        filter_layout.addWidget(self.history_emp_id, 0, 1, 1, 2)  # 跨两列

        # 变更类型（简化）
        type_label = QLabel("变更类型:")
        type_label.setStyleSheet("font-weight: bold;")
        filter_layout.addWidget(type_label, 0, 3)

        self.history_type = QComboBox()
        self.history_type.setMinimumWidth(120)

        # 加载变更类型（修复数据绑定）
        try:
            # 获取type_id、type_name、description三个字段
            types = self.db.fetch_all("""
                SELECT type_id, type_name, description 
                FROM change_type_dict 
                WHERE is_active = 1
            """)
            self.history_type.addItem("所有类型", None)
            for t in types:
                # 显示友好的description，存储type_name作为筛选依据
                self.history_type.addItem(t['description'], t['type_name'])
        except Exception as e:
            # 错误处理时使用带type_name的模拟数据
            self.history_type.addItem("所有类型", None)
            self.history_type.addItem("员工信息更新", "info_update")
            self.history_type.addItem("密码更新", "password_update")
            self.history_type.addItem("职位变更", "position_change")
            self.history_type.addItem("权限调整", "permission_update")

        filter_layout.addWidget(self.history_type, 0, 4)

        # 日期范围（优化布局）
        date_label = QLabel("日期范围:")
        date_label.setStyleSheet("font-weight: bold;")
        filter_layout.addWidget(date_label, 1, 0)

        date_layout = QHBoxLayout()
        date_layout.setSpacing(4)

        # 从日期
        from_label = QLabel("从:")
        from_label.setStyleSheet("min-width: 5px;")
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setFixedWidth(180)  # 较小宽度

        # 到日期
        to_label = QLabel("到:")
        to_label.setStyleSheet("min-width: 5px;")
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setFixedWidth(180)  # 较小宽度

        date_layout.addWidget(from_label)
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(to_label)
        date_layout.addWidget(self.end_date)

        # 日期范围占两列，给后面按钮留空间
        filter_layout.addLayout(date_layout, 1, 1, 1, 2)

        # 操作按钮（紧凑排列） - 添加悬停和点击效果
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        search_btn = QPushButton("搜索")
        export_btn = QPushButton("导出")
        refresh_btn = QPushButton("刷新")
        clear_btn = QPushButton("清空")

        # 增强按钮样式 - 添加悬停和点击效果
        button_style = """
            QPushButton {
                padding: 7px 14px; 
                border-radius: 4px; 
                font-size: 13px;
                min-width: 70px;
                border: none;
                transition: all 0.2s;
            }
            QPushButton:hover {
                transform: translateY(-1px);
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            QPushButton:pressed {
                transform: translateY(1px);
                box-shadow: none;
            }
        """
        search_btn.setStyleSheet(button_style + """
            background-color: #4a86e8; 
            color: white;
            QPushButton:hover { background-color: #3a76d8; }
            QPushButton:pressed { background-color: #2a66c8; }
        """)
        export_btn.setStyleSheet(button_style + """
            background-color: #34a853; 
            color: white;
            QPushButton:hover { background-color: #2e984b; }
            QPushButton:pressed { background-color: #288843; }
        """)
        refresh_btn.setStyleSheet(button_style + """
            background-color: #f9ab00; 
            color: white;
            QPushButton:hover { background-color: #e99b00; }
            QPushButton:pressed { background-color: #d98b00; }
        """)
        clear_btn.setStyleSheet(button_style + """
            background-color: #ea4335; 
            color: white;
            QPushButton:hover { background-color: #da3325; }
            QPushButton:pressed { background-color: #ca2315; }
        """)

        # 添加按钮图标增强视觉效果
        search_btn.setIcon(QIcon(":/icons/search.png"))
        export_btn.setIcon(QIcon(":/icons/export.png"))
        refresh_btn.setIcon(QIcon(":/icons/refresh.png"))
        clear_btn.setIcon(QIcon(":/icons/clear.png"))

        # 设置按钮光标形状
        for btn in [search_btn, export_btn, refresh_btn, clear_btn]:
            btn.setCursor(QCursor(Qt.PointingHandCursor))

        btn_layout.addWidget(search_btn)
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(clear_btn)

        # 按钮放在日期范围右侧
        filter_layout.addLayout(btn_layout, 1, 3, 1, 2)

        layout.addWidget(filter_frame)

        # 历史记录表格
        table_frame = QFrame()
        table_frame.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 6px;")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)

        # 表格上方状态栏
        status_bar = QFrame()
        status_bar.setStyleSheet("background-color: #f5f5f5; border-bottom: 1px solid #e0e0e0;")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(10, 5, 10, 5)

        self.history_status = QLabel("共0条记录")
        self.history_status.setStyleSheet("color: #666; font-size: 12px;")

        status_layout.addWidget(self.history_status)
        status_layout.addStretch()

        table_layout.addWidget(status_bar)

        # 历史记录表格 - 增强交互效果
        self.history_table = QTableWidget()
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SingleSelection)
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "记录ID", "员工信息", "变更时间", "变更类型", "操作人", "旧信息摘要", "新信息摘要"
        ])

        # 增强表格样式 - 添加悬停和点击效果
        self.history_table.setStyleSheet("""
            QTableWidget {
                border: none; 
                gridline-color: #eee; 
                font-size: 13px; 
                selection-background-color: #d1e8ff;
                selection-color: #000;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #d1e8ff;
                color: #000;
                border: none;
            }
            QTableWidget::item:hover {
                background-color: #f0f7ff;
            }
        """)

        # 设置交替行颜色
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setStyleSheet(self.history_table.styleSheet() + """
            QTableWidget {
                alternate-background-color: #f9f9f9;
            }
        """)

        header_style = """
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #e0e0e0;
                font-weight: bold;
                color: #555;
            }
            QHeaderView::section:hover {
                background-color: #eaeaea;
            }
        """
        self.history_table.horizontalHeader().setStyleSheet(header_style)
        self.history_table.verticalHeader().setStyleSheet(header_style)
        self.history_table.verticalHeader().setDefaultSectionSize(36)  # 行高

        # 优化列宽策略 - 重点调整摘要列宽度
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)  # ID
        self.history_table.setColumnWidth(0, 80)  # 固定宽度

        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)  # 员工信息
        self.history_table.setColumnWidth(1, 150)  # 固定宽度

        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)  # 变更时间
        self.history_table.setColumnWidth(2, 160)  # 固定宽度

        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)  # 变更类型
        self.history_table.setColumnWidth(3, 120)  # 固定宽度

        self.history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)  # 操作人
        self.history_table.setColumnWidth(4, 120)  # 固定宽度

        # 摘要列使用拉伸模式
        self.history_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # 旧信息摘要
        self.history_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)  # 新信息摘要

        # 设置最小列宽
        self.history_table.horizontalHeader().setMinimumSectionSize(80)

        # 启用排序
        self.history_table.setSortingEnabled(True)

        # 设置表格光标形状
        self.history_table.setCursor(QCursor(Qt.PointingHandCursor))

        table_layout.addWidget(self.history_table)

        # 分页控件（底部居中）- 增强交互效果
        page_frame = QFrame()
        page_frame.setStyleSheet("border-top: 1px solid #e0e0e0; padding: 8px;")
        page_layout = QHBoxLayout(page_frame)
        page_layout.setContentsMargins(10, 5, 10, 5)

        self.prev_page = QPushButton("◀ 上一页")
        self.next_page = QPushButton("下一页 ▶")
        self.page_label = QLabel("第 1 页 / 共 1 页")
        self.page_combo = QComboBox()
        self.page_combo.setFixedWidth(70)

        # 分页按钮样式增强
        page_btn_style = """
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
                transition: all 0.2s;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #ccc;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
            QPushButton:disabled {
                color: #ccc;
                background-color: #f9f9f9;
            }
        """
        self.prev_page.setStyleSheet(page_btn_style)
        self.next_page.setStyleSheet(page_btn_style)
        self.prev_page.setEnabled(False)
        self.next_page.setEnabled(False)

        # 设置分页按钮光标
        self.prev_page.setCursor(QCursor(Qt.PointingHandCursor))
        self.next_page.setCursor(QCursor(Qt.PointingHandCursor))

        page_layout.addStretch(1)
        page_layout.addWidget(self.prev_page)
        page_layout.addWidget(self.page_label)
        page_layout.addWidget(self.next_page)
        page_layout.addWidget(QLabel("跳转到:"))
        page_layout.addWidget(self.page_combo)
        page_layout.addStretch(1)

        table_layout.addWidget(page_frame)
        layout.addWidget(table_frame, 1)  # 表格区域占据更多空间

        # 事件连接
        search_btn.clicked.connect(self.search_history)
        export_btn.clicked.connect(self.export_history)
        refresh_btn.clicked.connect(self.load_history_data)
        clear_btn.clicked.connect(self.clear_filters)
        self.history_table.doubleClicked.connect(self.show_history_detail)
        self.prev_page.clicked.connect(self.prev_page_func)
        self.next_page.clicked.connect(self.next_page_func)
        self.page_combo.currentIndexChanged.connect(self.goto_page)

        # 初始化分页
        self.current_page = 1
        self.total_pages = 1
        self.items_per_page = 50
        return tab

    def load_history_data(self, page=1):
        """加载历史记录（修复数据显示、记录数矛盾）"""
        try:
            offset = (page - 1) * self.items_per_page
            base_subquery = """
                SELECT h.history_id, h.employee_id, a.employee_name, h.change_date, 
                       t.type_name AS change_type, admin.admin_account AS operator,
                       h.old_info, h.new_info, h.related_table
                FROM history_info h
                JOIN change_type_dict t ON h.type_id = t.type_id
                LEFT JOIN employee_accounts a ON h.employee_id = a.employee_id
                LEFT JOIN admin_accounts admin ON h.operator_id = admin.admin_account_id
            """
            where_clause = " WHERE 1=1 "
            params = []

            # 员工筛选
            emp_id = self.history_emp_id.text().strip()
            if emp_id:
                where_clause += " AND (subquery.employee_id = %s OR subquery.employee_name LIKE %s) "
                params.extend([emp_id, f"%{emp_id}%"])

            # 变更类型筛选（修复：匹配数据库`type_name`）
            change_type = self.history_type.currentData()  # 存储type_name
            if change_type is not None and change_type != "所有类型":
                where_clause += " AND subquery.change_type = %s "
                params.append(change_type)

            # 日期筛选
            start_date = self.start_date.date().toString("yyyy-MM-dd")
            end_date = self.end_date.date().toString("yyyy-MM-dd")
            where_clause += " AND subquery.change_date BETWEEN %s AND %s "
            params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])

            # 总记录数（修复列引用）
            count_query = f"SELECT COUNT(*) as total FROM ({base_subquery}) AS subquery {where_clause}"
            total_result = self.db.fetch_one(count_query, params)
            total = total_result["total"] if total_result else 0
            self.total_pages = (total + self.items_per_page - 1) // self.items_per_page
            self.current_page = page

            # 分页查询（修复列引用）
            query = f"""
                SELECT * FROM ({base_subquery}) AS subquery 
                {where_clause} 
                ORDER BY subquery.history_id DESC 
                LIMIT %s OFFSET %s
            """
            params.extend([self.items_per_page, offset])
            history = self.db.fetch_all(query, params) or []

            # 填充表格（存储原始JSON到UserRole）
            self.history_table.setRowCount(len(history))
            for row, item in enumerate(history):
                # 字段格式化
                employee_display = f"{item['employee_id']} - {item.get('employee_name', '')}" if item.get(
                    'employee_name') else str(item['employee_id'])
                change_date = item["change_date"].strftime("%Y-%m-%d %H:%M:%S") if item.get("change_date") else ""
                operator = item.get("operator", "系统")
                change_type = item["change_type"]

                # 新旧信息：显示摘要 + 存储原始JSON
                old_info_raw = item.get("old_info", "{}")
                new_info_raw = item.get("new_info", "{}")
                old_info_display = self._format_history_info(old_info_raw)
                new_info_display = self._format_history_info(new_info_raw)

                # 记录ID（居右）
                id_item = QTableWidgetItem(str(item["history_id"]))
                id_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.history_table.setItem(row, 0, id_item)

                # 员工信息（居左）
                emp_item = QTableWidgetItem(employee_display)
                emp_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.history_table.setItem(row, 1, emp_item)

                # 变更时间（居中）
                time_item = QTableWidgetItem(change_date)
                time_item.setTextAlignment(Qt.AlignCenter)
                self.history_table.setItem(row, 2, time_item)

                # 变更类型（居中）
                type_item = QTableWidgetItem(change_type)
                type_item.setTextAlignment(Qt.AlignCenter)
                self.history_table.setItem(row, 3, type_item)

                # 操作人（居中）
                op_item = QTableWidgetItem(operator)
                op_item.setTextAlignment(Qt.AlignCenter)
                self.history_table.setItem(row, 4, op_item)

                # 旧信息（存储原始数据）
                old_item = QTableWidgetItem(old_info_display)
                old_item.setData(Qt.UserRole, old_info_raw)
                self.history_table.setItem(row, 5, old_item)

                # 新信息（存储原始数据）
                new_item = QTableWidgetItem(new_info_display)
                new_item.setData(Qt.UserRole, new_info_raw)
                self.history_table.setItem(row, 6, new_item)

            # 更新状态
            self.update_pagination()
            self.history_status.setText(f"共 {total} 条记录，当前显示 {len(history)} 条")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载失败: {str(e)}")
            self.history_status.setText("数据加载失败")


    def show_history_detail(self, index):
        """显示详情（修复数据为空）"""
        row = index.row()
        if row < 0:
            return

        # 读取原始JSON（从UserRole）
        old_info_raw = self.history_table.item(row, 5).data(Qt.UserRole)
        new_info_raw = self.history_table.item(row, 6).data(Qt.UserRole)

        # 解析JSON
        try:
            old_json = json.loads(old_info_raw) if old_info_raw else {}
            new_json = json.loads(new_info_raw) if new_info_raw else {}
        except json.JSONDecodeError as e:
            old_json = {}
            new_json = {}
            QMessageBox.warning(self, "解析错误", f"数据错误: {str(e)}")

        # 提取其他字段
        history_id = self.history_table.item(row, 0).text()
        employee = self.history_table.item(row, 1).text()
        change_type = self.history_table.item(row, 3).text()
        operator = self.history_table.item(row, 4).text()
        change_time = self.history_table.item(row, 2).text()

        # 构建对话框
        detail_dialog = QDialog(self)
        detail_dialog.setWindowTitle(f"详情 - ID: {history_id}")
        detail_dialog.setMinimumSize(700, 500)
        detail_layout = QVBoxLayout(detail_dialog)

        # 基本信息
        basic_info = QGroupBox("基本信息")
        basic_layout = QGridLayout(basic_info)
        basic_layout.addWidget(QLabel("员工:"), 0, 0)
        basic_layout.addWidget(QLabel(employee), 0, 1)
        basic_layout.addWidget(QLabel("类型:"), 1, 0)
        basic_layout.addWidget(QLabel(change_type), 1, 1)
        basic_layout.addWidget(QLabel("操作人:"), 2, 0)
        basic_layout.addWidget(QLabel(operator), 2, 1)
        basic_layout.addWidget(QLabel("时间:"), 3, 0)
        basic_layout.addWidget(QLabel(change_time), 3, 1)
        detail_layout.addWidget(basic_info)

        # 变更内容
        change_info = QGroupBox("变更内容")
        change_layout = QHBoxLayout(change_info)

        # 旧信息
        old_group = QGroupBox("旧信息")
        old_text = QTextEdit()
        old_text.setReadOnly(True)
        old_text.setPlainText(json.dumps(old_json, ensure_ascii=False, indent=2) or "无")
        old_group.setLayout(QVBoxLayout())
        old_group.layout().addWidget(old_text)

        # 新信息
        new_group = QGroupBox("新信息")
        new_text = QTextEdit()
        new_text.setReadOnly(True)
        new_text.setPlainText(json.dumps(new_json, ensure_ascii=False, indent=2) or "无")
        new_group.setLayout(QVBoxLayout())
        new_group.layout().addWidget(new_text)

        change_layout.addWidget(old_group, 1)
        change_layout.addWidget(new_group, 1)
        detail_layout.addWidget(change_info)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(detail_dialog.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        detail_layout.addLayout(btn_layout)

        detail_dialog.exec_()

    def update_pagination(self):
        """更新分页控件状态（修复递归循环）"""
        # 临时断开信号，避免 setCurrentIndex 触发递归
        self.page_combo.blockSignals(True)

        self.total_pages = max(1, self.total_pages)  # 确保至少1页
        self.page_label.setText(f"第 {self.current_page} 页 / 共 {self.total_pages} 页")
        self.page_combo.clear()
        for i in range(1, self.total_pages + 1):
            self.page_combo.addItem(str(i))
        self.page_combo.setCurrentIndex(self.current_page - 1)

        # 恢复信号连接
        self.page_combo.blockSignals(False)

        self.prev_page.setEnabled(self.current_page > 1)
        self.next_page.setEnabled(self.current_page < self.total_pages)

    def search_history(self):
        """搜索历史记录（支持分页）"""
        self.load_history_data(page=1)

    def prev_page_func(self):
        """上一页"""
        if self.current_page > 1:
            self.load_history_data(self.current_page - 1)

    def next_page_func(self):
        """下一页"""
        if self.current_page < self.total_pages:
            self.load_history_data(self.current_page + 1)

    def goto_page(self, index):
        """跳转到指定页"""
        page = index + 1
        self.load_history_data(page)

    def clear_filters(self):
        """清空筛选条件"""
        self.history_emp_id.clear()
        self.history_type.setCurrentIndex(0)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.end_date.setDate(QDate.currentDate())
        self.load_history_data(page=1)

    def _format_history_info(self, info):
        """格式化历史记录中的JSON数据，提取关键信息（优化版）"""
        if not info:
            return "无"

        # 处理字符串形式的JSON
        if isinstance(info, str):
            try:
                info = json.loads(info)
            except json.JSONDecodeError:
                return f"[JSON解析错误: {info[:30]}...]"

        # 根据变更类型提取关键信息
        if 'employee_name' in info and 'account' in info:  # 员工账户信息变更
            return f"姓名: {info.get('employee_name', '')}, 电话: {info.get('account', '')}"
        elif 'marital_status' in info and 'education' in info:  # 基本信息变更
            return f"婚姻: {info.get('marital_status', '')}, 学历: {info.get('education', '')}, 性别: {info.get('gender', '')}"
        elif 'position_id' in info:  # 职位变更
            return f"职位ID: {info.get('position_id', '')}"
        elif 'password' in info:  # 密码变更
            return "密码已修改"
        elif 'position_name' in info:  # 职位名称变更
            return f"职位名称: {info.get('position_name', '')}"
        elif 'employee_id' in info and 'position_name' in info:  # 职位删除
            return f"删除职位: {info.get('position_name', '')} (ID: {info.get('employee_id', '')})"

        # 通用格式（截断长内容）
        return json.dumps(info, ensure_ascii=False)[:50] + "..." if len(str(info)) > 50 else str(info)

    def export_history(self):
        """导出历史记录为CSV"""
        from datetime import datetime
        import csv
        from PyQt5.QtWidgets import QFileDialog

        # 获取当前筛选条件下的数据
        self.search_history()  # 确保加载最新数据

        # 生成文件名
        filename = f"历史记录导出_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出历史记录", filename, "CSV文件 (*.csv);;所有文件 (*)"
        )
        if not file_path:
            return

        # 提取表格数据
        data = []
        for row in range(self.history_table.rowCount()):
            row_data = []
            for col in range(self.history_table.columnCount()):
                item = self.history_table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        # 写入CSV
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 写入表头
                header = [self.history_table.horizontalHeaderItem(col).text() for col in
                          range(self.history_table.columnCount())]
                writer.writerow(header)
                # 写入数据
                writer.writerows(data)

            QMessageBox.information(self, "成功", f"历史记录已成功导出到\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    # 分界符 ***************************************************************
    def create_system_management_tab(self):
        """创建系统管理标签页（管理员账户管理）"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(20)

        # 当前管理员信息卡片
        admin_info_card = QGroupBox("当前管理员信息")
        info_layout = QGridLayout(admin_info_card)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setVerticalSpacing(15)

        # 获取当前管理员数据
        admin_data = self.get_current_admin_info()
        admin_name = admin_data.get('admin_account', '未获取到账号')
        admin_ip = "127.0.0.1"  # 实际应从登录日志获取IP
        welcome_text = f"欢迎你，管理员 {admin_name}"

        # 显示欢迎信息（大字体居中）
        welcome_label = QLabel(welcome_text)
        welcome_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #165DFF;
            margin-bottom: 15px;
        """)
        welcome_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(welcome_label, 0, 0, 1, 2)  # 跨2列

        # 账号信息
        info_layout.addWidget(QLabel("账号:"), 1, 0)
        info_layout.addWidget(QLabel(admin_name), 1, 1)

        # IP信息
        info_layout.addWidget(QLabel("登录IP:"), 2, 0)
        info_layout.addWidget(QLabel(admin_ip), 2, 1)

        # 最后登录时间（模拟数据）
        login_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        info_layout.addWidget(QLabel("最后登录:"), 3, 0)
        info_layout.addWidget(QLabel(login_time), 3, 1)

        layout.addWidget(admin_info_card)

        # 功能操作区
        function_area = QGroupBox("账户管理")
        function_layout = QVBoxLayout(function_area)
        function_layout.setContentsMargins(20, 10, 20, 20)
        function_layout.setSpacing(15)

        # 账号密码修改按钮
        modify_frame = QHBoxLayout()
        modify_account_btn = QPushButton("修改账号")
        modify_password_btn = QPushButton("修改密码")
        modify_account_btn.setMinimumSize(150, 40)
        modify_password_btn.setMinimumSize(150, 40)
        modify_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f5ff;
                color: #165DFF;
                border: 1px solid #165DFF;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e0e8ff;
            }
            QPushButton:pressed {
                background-color: #d0d8e6;
            }
        """)
        modify_password_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f5ff;
                color: #165DFF;
                border: 1px solid #165DFF;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e0e8ff;
            }
            QPushButton:pressed {
                background-color: #d0d8e6;
            }
        """)
        modify_frame.addWidget(modify_account_btn)
        modify_frame.addWidget(modify_password_btn)
        function_layout.addLayout(modify_frame)

        # 功能待续提示
        future_features = QLabel("""
            <p style="color: #999; margin-top: 20px; text-align: center;">
                <span style="color: #165DFF;">后续功能待续：</span>角色权限管理、登录日志查看、系统参数配置
            </p>
        """)
        future_features.setWordWrap(True)
        function_layout.addWidget(future_features)

        layout.addWidget(function_area)

        # 事件连接
        modify_account_btn.clicked.connect(self.show_modify_account_dialog)
        modify_password_btn.clicked.connect(self.show_modify_password_dialog)

        return tab

    def get_current_admin_info(self):
        """获取当前登录管理员信息（从数据库获取）"""
        try:
            # 实际应用中应从登录状态获取当前管理员ID，此处用固定值示例
            query = "SELECT admin_account FROM admin_accounts WHERE admin_account_id = %s"
            result = self.db.fetch_one(query, (self.admin_type_id))
            return result or {}
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取管理员信息失败: {str(e)}")
            return {"admin_account": "系统错误"}

    def show_modify_account_dialog(self):
        """修改管理员账号对话框"""
        current_info = self.get_current_admin_info()
        if not current_info:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("修改管理员账号")
        dialog.setFixedSize(350, 180)
        dialog.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)

        # 账号输入
        account_label = QLabel("新账号:")
        account_input = QLineEdit(current_info['admin_account'])
        account_input.setPlaceholderText("请输入新账号（5-20位字符）")

        # 验证提示
        tip_label = QLabel("账号只能包含字母、数字和下划线，长度5-20位")
        tip_label.setStyleSheet("color: #999; font-size: 12px;")

        # 按钮
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #165DFF;
                color: white;
                border-radius: 5px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #0D47A1;
            }
        """)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f5ff;
                color: #666;
                border: 1px solid #d0d8e6;
                border-radius: 5px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #e8f0ff;
            }
        """)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addWidget(account_label)
        layout.addWidget(account_input)
        layout.addWidget(tip_label)
        layout.addLayout(btn_layout)

        def handle_ok():
            new_account = account_input.text().strip()
            if not new_account:
                QMessageBox.warning(dialog, "警告", "账号不能为空")
                return
            if len(new_account) < 5 or len(new_account) > 20:
                QMessageBox.warning(dialog, "警告", "账号长度需在5-20位之间")
                return
            if not new_account.isalnum() and '_' not in new_account:
                QMessageBox.warning(dialog, "警告", "账号只能包含字母、数字和下划线")
                return

            # 检查账号唯一性
            try:
                check_query = "SELECT COUNT(*) FROM admin_accounts WHERE admin_account = %s AND admin_account_id != %s"
                admin_id = 1  # 实际应从登录状态获取
                count = self.db.fetch_one(check_query, (new_account, admin_id))['COUNT(*)']
                if count > 0:
                    QMessageBox.warning(dialog, "错误", "该账号已被使用")
                    return
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"验证账号失败: {str(e)}")
                return

            # 执行修改
            try:
                query = "UPDATE admin_accounts SET admin_account = %s WHERE admin_account_id = %s"
                self.db.execute(query, (new_account, admin_id))
                QMessageBox.information(dialog, "成功", "账号修改成功，请重新登录生效")
                dialog.accept()
            except pymysql.Error as e:
                QMessageBox.critical(dialog, "错误", f"修改失败: {str(e)}")

        ok_btn.clicked.connect(handle_ok)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec_()

    def show_modify_password_dialog(self):
        """修改管理员密码对话框（UI优化版）"""
        dialog = QDialog(self)
        dialog.setWindowTitle("修改管理员密码")
        dialog.setFixedSize(450, 300)  # 更大的尺寸
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                font-family: "Microsoft YaHei";
                font-size: 14px;
            }
            QLabel {
                margin-top: 8px;
            }
            QLineEdit {
                height: 35px;  # 更高的输入框
                border: 1px solid #d0d8e6;
                border-radius: 4px;
                padding: 0 10px;
            }
            QPushButton {
                padding: 10px 30px;  # 更大的按钮
                margin: 10px 0;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # 旧密码输入
        old_pass_layout = QHBoxLayout()
        old_pass_layout.addWidget(QLabel("当前密码:"), 1)
        old_pass_input = QLineEdit()
        old_pass_input.setEchoMode(QLineEdit.Password)
        old_pass_input.setMinimumWidth(200)
        old_pass_layout.addWidget(old_pass_input, 2)
        layout.addLayout(old_pass_layout)

        # 新密码输入
        new_pass_layout = QHBoxLayout()
        new_pass_layout.addWidget(QLabel("新密码:"), 1)
        new_pass_input = QLineEdit()
        new_pass_input.setEchoMode(QLineEdit.Password)
        new_pass_input.setMinimumWidth(200)
        new_pass_input.setPlaceholderText("6-20位，包含字母和数字")
        new_pass_layout.addWidget(new_pass_input, 2)
        layout.addLayout(new_pass_layout)

        # 确认密码输入
        confirm_pass_layout = QHBoxLayout()
        confirm_pass_layout.addWidget(QLabel("确认新密码:"), 1)
        confirm_pass_input = QLineEdit()
        confirm_pass_input.setEchoMode(QLineEdit.Password)
        confirm_pass_input.setMinimumWidth(200)
        confirm_pass_layout.addWidget(confirm_pass_input, 2)
        layout.addLayout(confirm_pass_layout)

        # 提示信息
        tip_label = QLabel("密码要求：6-20位，必须包含字母和数字")
        tip_label.setStyleSheet("color: #999; font-size: 12px; margin-top: -10px;")
        layout.addWidget(tip_label)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()  # 按钮居中
        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet("""
            background-color: #165DFF;
            color: white;
            border-radius: 5px;
        """)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            background-color: #f5f5f5;
            color: #666;
            border: 1px solid #d0d8e6;
            border-radius: 5px;
        """)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 验证逻辑
        def handle_ok():
            old_password = old_pass_input.text().strip()
            new_password = new_pass_input.text().strip()
            confirm_password = confirm_pass_input.text().strip()

            if not old_password or not new_password or not confirm_password:
                QMessageBox.warning(dialog, "警告", "密码不能为空")
                return

            if len(new_password) < 6 or len(new_password) > 20:
                QMessageBox.warning(dialog, "警告", "密码长度需在6-20位之间")
                return

            if not any(c.isalpha() for c in new_password) or not any(c.isdigit() for c in new_password):
                QMessageBox.warning(dialog, "警告", "密码需包含字母和数字")
                return

            if new_password != confirm_password:
                QMessageBox.warning(dialog, "警告", "两次输入的密码不一致")
                return

            # 验证旧密码
            try:
                admin_id = 1  # 实际应从登录状态获取
                query = "SELECT admin_password FROM admin_accounts WHERE admin_account_id = %s"
                result = self.db.fetch_one(query, (admin_id,))
                if not result or result['admin_password'] != old_password:
                    QMessageBox.warning(dialog, "错误", "当前密码输入错误")
                    return
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"验证密码失败: {str(e)}")
                return

            # 执行修改
            try:
                query = "UPDATE admin_accounts SET admin_password = %s WHERE admin_account_id = %s"
                self.db.execute(query, (new_password, admin_id))
                QMessageBox.information(dialog, "成功", "密码修改成功，请重新登录生效")
                dialog.accept()
            except pymysql.Error as e:
                QMessageBox.critical(dialog, "错误", f"修改失败: {str(e)}")

        ok_btn.clicked.connect(handle_ok)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec_()

    #分界符 *****************************************************************
    def create_server_communication_tab(self):
        """创建服务器通信选项卡（完整实现）"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 服务器连接设置
        connection_group = QGroupBox("服务器连接")
        connection_layout = QHBoxLayout(connection_group)

        host_label = QLabel("服务器地址:")
        self.server_host = QLineEdit("127.0.0.1")
        port_label = QLabel("端口:")
        self.server_port = QLineEdit("5555")
        self.connect_btn = QPushButton("连接服务器")
        self.disconnect_btn = QPushButton("断开连接")
        self.disconnect_btn.setEnabled(False)

        connection_layout.addWidget(host_label)
        connection_layout.addWidget(self.server_host)
        connection_layout.addWidget(port_label)
        connection_layout.addWidget(self.server_port)
        connection_layout.addWidget(self.connect_btn)
        connection_layout.addWidget(self.disconnect_btn)
        connection_layout.addStretch()

        # 状态显示
        self.status_label = QLabel("服务器状态: 未连接")
        self.status_label.setStyleSheet("font-size: 14px; color: #FF5722; font-weight: bold;")
        connection_layout.addWidget(self.status_label)

        layout.addWidget(connection_group)

        # IP发送区域
        ip_group = QGroupBox("发送IP信息")
        ip_layout = QVBoxLayout(ip_group)

        ip_info_label = QLabel("当前IP地址:")
        self.ip_display = QLabel("获取中...")
        self.get_ip_btn = QPushButton("获取当前IP")
        self.send_ip_btn = QPushButton("发送IP到服务器")
        self.send_ip_btn.setEnabled(False)

        ip_layout.addWidget(ip_info_label)
        ip_layout.addWidget(self.ip_display)
        ip_layout.addWidget(self.get_ip_btn)
        ip_layout.addWidget(self.send_ip_btn)

        layout.addWidget(ip_group)

        # 命令发送区域
        cmd_group = QGroupBox("发送命令")
        cmd_layout = QVBoxLayout(cmd_group)

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("输入命令...")
        send_cmd_btn = QPushButton("发送命令")

        cmd_layout.addWidget(self.cmd_input)
        cmd_layout.addWidget(send_cmd_btn)

        layout.addWidget(cmd_group)

        # 日志显示
        log_group = QGroupBox("通信日志")
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("border: 1px solid #ccc; padding: 10px;")
        log_group.setLayout(QVBoxLayout())
        log_group.layout().addWidget(self.log_display)

        layout.addWidget(log_group)

        # 连接信号
        self.connect_btn.clicked.connect(self.connect_to_server)
        self.disconnect_btn.clicked.connect(self.disconnect_from_server)
        self.get_ip_btn.clicked.connect(self.get_server_ip)
        self.send_ip_btn.clicked.connect(self.send_ip_to_server)
        self.cmd_input.returnPressed.connect(lambda: send_cmd_btn.click())
        send_cmd_btn.clicked.connect(self.send_command)

        return tab

    def connect_to_server(self):
        """连接到服务器"""
        host = self.server_host.text().strip()
        port = self.server_port.text().strip()

        if not host or not port:
            QMessageBox.warning(self, "警告", "请输入服务器地址和端口")
            return

        try:
            self.socket_client = SocketClient()
            self.socket_client.set_server(host, port)
            self.socket_client.status_updated.connect(self.update_log)
            self.socket_client.message_received.connect(self.process_server_message)  # 关键修改：连接到新的处理方法
            self.socket_client.connection_established.connect(self.on_connected)
            self.socket_client.connection_lost.connect(self.on_disconnected)

            self.socket_client.start()
            self.log_display.append(f"正在连接到服务器 {host}:{port}...")
        except Exception as e:
            self.update_log(f"连接服务器失败: {str(e)}")

    def process_server_message(self, message):
        """处理服务器返回的消息（包括命令执行结果）"""
        try:
            # 确保message是字典类型
            if not isinstance(message, dict):
                self.update_log(f"错误: 接收到非字典类型消息: {type(message)}")
                return

            # 处理命令响应
            if message.get("type") == "command_response":
                status = message.get("status", "unknown")
                command = message.get("command", "unknown")
                output = message.get("output", "")
                error = message.get("error", "")

                result = f"命令执行结果: {command}\n状态: {status}\n输出:\n{output}\n错误:\n{error}"
                self.update_log(result)

            # 处理普通消息
            elif message.get("type") in ["response", "heartbeat_ack", "ip"]:
                self.update_log(f"收到服务器消息: {message}")

            # 处理错误消息
            elif message.get("type") == "error":
                error_type = message.get("error_type", "未知错误")
                error_msg = message.get("message", "无错误详情")
                self.update_log(f"错误 ({error_type}): {error_msg}")

        except Exception as e:
            self.update_log(f"处理服务器消息失败: {str(e)}")
    def disconnect_from_server(self):
        """断开与服务器的连接"""
        if self.socket_client and self.socket_client.isRunning():
            self.socket_client.stop()
            self.socket_client = None
            self.on_disconnected()

    def get_current_ip(self):
        """获取当前IP地址（稳定版）"""
        return '127.0.0.1'
    def get_server_ip(self):
        """获取服务器IP地址（稳定版）"""
        try:
            # 优先使用公网IP服务
            urls = ["https://api.ipify.org", "https://icanhazip.com"]
            for url in urls:
                try:
                    manager = QNetworkAccessManager()
                    request = QNetworkRequest(PyQt5.QUrl(url))
                    request.setHeader(QNetworkRequest.UserAgentHeader, "Mozilla/5.0")
                    loop = PyQt5.QEventLoop()
                    reply = manager.get(request)
                    reply.finished.connect(loop.quit)
                    loop.exec_()
                    if reply.error() == QNetworkReply.NoError:
                        ip = reply.readAll().data().decode().strip()
                        self.ip_display.setText(ip)
                        self.update_log(f"获取到IP: {ip}")
                        return
                except:
                    continue

            # 备用：本地IP（确保正确实现）
            ip = self.get_local_ip()
            self.ip_display.setText(ip)
            self.update_log(f"公网IP获取失败，使用内网IP: {ip}")
        except Exception as e:
            ip = self.get_local_ip()
            self.ip_display.setText(ip)
            self.update_log(f"IP获取失败: {str(e)}，使用内网IP: {ip}")

    def get_local_ip(self):
        """获取本地IP（防异常版）"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "127.0.0.1"

    def send_ip_to_server(self):
        """发送IP到服务器"""
        ip = self.ip_display.text()
        if not ip or ip == "获取中...":
            QMessageBox.warning(self, "警告", "请先获取IP地址")
            return

        if not self.socket_client or not self.socket_client.isRunning():
            QMessageBox.warning(self, "警告", "请先连接到服务器")
            return

        data = {"type": "ip", "ip": ip, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        self.socket_client.send_data(data)

    def send_command(self):
        """发送带签名的安全命令到服务器"""
        cmd = self.cmd_input.text().strip()
        if not cmd:
            QMessageBox.warning(self, "警告", "请输入命令")
            return

        if not self.socket_client or not self.socket_client.isRunning():
            QMessageBox.warning(self, "警告", "请先连接到服务器")
            return

        # 构建命令数据
        data = {
            "type": "command",
            "command": cmd,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "client_id": "your_client_identifier"  # 客户端标识
        }

        # 发送安全数据（包含签名）
        self.socket_client.send_secure_data(data)
        self.cmd_input.clear()
        self.update_log(f"发送安全命令: {cmd}")

    def on_connected(self):
        """连接建立后的处理"""
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.send_ip_btn.setEnabled(True)
        self.status_label.setText("服务器状态: 已连接")
        self.status_label.setStyleSheet("font-size: 14px; color: #4CAF50; font-weight: bold;")
        self.update_log("服务器连接已建立")

    def on_disconnected(self):
        """连接断开后的处理"""
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.send_ip_btn.setEnabled(False)
        self.status_label.setText("服务器状态: 未连接")
        self.status_label.setStyleSheet("font-size: 14px; color: #FF5722; font-weight: bold;")
        self.update_log("服务器连接已断开")

    def update_log(self, message):
        """更新日志显示（增强格式）"""
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")

        # 区分不同类型的日志
        if message.startswith("[安全]"):
            # 安全命令日志（蓝色）
            self.log_display.append(f"{timestamp}<span style='color:#165DFF;'>{message}</span>")
        elif message.startswith("错误"):
            # 错误日志（红色）
            self.log_display.append(f"{timestamp}<span style='color:#FF5722;'>{message}</span>")
        elif "命令执行结果" in message:
            # 命令结果（绿色）
            self.log_display.append(f"{timestamp}<span style='color:#4CAF50;'>{message}</span>")
        else:
            # 普通日志
            self.log_display.append(f"{timestamp}{message}")

        # 滚动到底部
        self.log_display.ensureCursorVisible()


    # 分界符*********************************************
    def create_suggestion_management_tab(self):
        """创建意见箱管理标签页（管理员专用，支持回复功能）"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 标题栏
        title_label = QLabel("意见箱管理")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #333; padding: 8px 0; text-align: center;"
        )
        layout.addWidget(title_label)

        # 筛选栏
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "border: 1px solid #e0e0e0; border-radius: 6px; background-color: #f9f9f9; padding: 10px;"
        )
        filter_layout = QGridLayout(filter_frame)
        filter_layout.setContentsMargins(8, 8, 8, 8)
        filter_layout.setSpacing(8)

        # 员工筛选
        emp_label = QLabel("员工筛选:")
        emp_label.setStyleSheet("font-weight: bold;")
        filter_layout.addWidget(emp_label, 0, 0)

        self.suggest_emp_id = QLineEdit()
        self.suggest_emp_id.setPlaceholderText("输入员工ID或姓名")
        filter_layout.addWidget(self.suggest_emp_id, 0, 1)

        # 状态筛选
        status_label = QLabel("状态:")
        status_label.setStyleSheet("font-weight: bold;")
        filter_layout.addWidget(status_label, 0, 2)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["全部", "未处理", "已处理"])
        filter_layout.addWidget(self.status_combo, 0, 3)

        # 日期范围
        date_label = QLabel("日期范围:")
        date_label.setStyleSheet("font-weight: bold;")
        filter_layout.addWidget(date_label, 1, 0)

        self.suggest_start_date = QDateEdit()
        self.suggest_start_date.setDate(QDate.currentDate().addMonths(-1))
        self.suggest_start_date.setCalendarPopup(True)
        self.suggest_start_date.setDisplayFormat("yyyy-MM-dd")

        self.suggest_end_date = QDateEdit()
        self.suggest_end_date.setDate(QDate.currentDate())
        self.suggest_end_date.setCalendarPopup(True)
        self.suggest_end_date.setDisplayFormat("yyyy-MM-dd")

        filter_layout.addWidget(self.suggest_start_date, 1, 1)
        filter_layout.addWidget(QLabel("到"), 1, 2)
        filter_layout.addWidget(self.suggest_end_date, 1, 3)

        # 搜索按钮
        search_btn = QPushButton("搜索")
        refresh_btn = QPushButton("刷新")
        filter_layout.addWidget(search_btn, 0, 4, 2, 1)  # 跨两行
        filter_layout.addWidget(refresh_btn, 1, 4)

        layout.addWidget(filter_frame)

        # 意见表格
        table_frame = QFrame()
        table_frame.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 6px;")
        table_layout = QVBoxLayout(table_frame)

        self.suggestion_table = QTableWidget()
        self.suggestion_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.suggestion_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.suggestion_table.setColumnCount(7)
        self.suggestion_table.setHorizontalHeaderLabels([
            "ID", "员工", "类型", "内容", "提交时间", "状态", "操作"
        ])
        self.suggestion_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.suggestion_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.suggestion_table.setStyleSheet("""
            QTableWidget {
                border: none; 
                gridline-color: #eee; 
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #d1e8ff;
                color: #000;
            }
        """)

        table_layout.addWidget(self.suggestion_table)
        layout.addWidget(table_frame)

        # 事件连接
        search_btn.clicked.connect(self.search_suggestions)
        refresh_btn.clicked.connect(self.load_suggestion_data)
        self.suggestion_table.cellDoubleClicked.connect(self.show_reply_dialog)

        # 初始化数据
        self.load_suggestion_data()
        return tab

    def load_suggestion_data(self):
        """加载意见数据（管理员视图）"""
        try:
            query = """
                SELECT s.suggestion_id, 
                       CONCAT(a.employee_id, ' - ', a.employee_name) AS employee,
                       s.suggestion_type, s.suggestion_content,
                       s.submit_time, s.status, s.employee_id
                FROM suggestion_box s
                LEFT JOIN employee_accounts a ON s.employee_id = a.employee_id
                ORDER BY s.submit_time DESC
            """
            suggestions = self.db.fetch_all(query)

            self.suggestion_table.setRowCount(len(suggestions))
            for row, sugg in enumerate(suggestions):
                self.suggestion_table.setItem(row, 0, QTableWidgetItem(str(sugg['suggestion_id'])))
                self.suggestion_table.setItem(row, 1, QTableWidgetItem(sugg['employee']))
                self.suggestion_table.setItem(row, 2, QTableWidgetItem(sugg['suggestion_type']))
                self.suggestion_table.setItem(row, 3, QTableWidgetItem(sugg['suggestion_content']))
                self.suggestion_table.setItem(row, 4, QTableWidgetItem(str(sugg['submit_time'])))

                # 状态显示
                status_text = "未处理" if sugg['status'] == 0 else "已处理"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(QColor("red" if sugg['status'] == 0 else "green"))
                self.suggestion_table.setItem(row, 5, status_item)

                # 操作按钮
                reply_btn = QPushButton("回复")
                reply_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #165DFF;
                        color: white;
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #0D47A1;
                    }
                """)
                reply_btn.clicked.connect(lambda checked, id=sugg['suggestion_id']: self.show_reply_dialog(id))
                self.suggestion_table.setCellWidget(row, 6, reply_btn)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载意见数据失败: {str(e)}")

    def search_suggestions(self):
        """搜索意见"""
        emp_key = self.suggest_emp_id.text().strip()
        status = self.status_combo.currentIndex()
        start_date = self.suggest_start_date.date().toString("yyyy-MM-dd")
        end_date = self.suggest_end_date.date().toString("yyyy-MM-dd")

        query = """
            SELECT s.suggestion_id, 
                   CONCAT(a.employee_id, ' - ', a.employee_name) AS employee,
                   s.suggestion_type, s.suggestion_content,
                   s.submit_time, s.status, s.employee_id
            FROM suggestion_box s
            LEFT JOIN employee_accounts a ON s.employee_id = a.employee_id
        """
        where_clause = " WHERE 1=1 "
        params = []

        if emp_key:
            where_clause += " AND (a.employee_id = %s OR a.employee_name LIKE %s) "
            params.extend([emp_key, f"%{emp_key}%"])

        if status == 1:  # 未处理
            where_clause += " AND s.status = 0 "
        elif status == 2:  # 已处理
            where_clause += " AND s.status = 1 "

        where_clause += " AND s.submit_time BETWEEN %s AND %s "
        params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])

        query += where_clause + " ORDER BY s.submit_time DESC"

        try:
            suggestions = self.db.fetch_all(query, params)
            self.suggestion_table.setRowCount(len(suggestions))
            for row, sugg in enumerate(suggestions):
                self.suggestion_table.setItem(row, 0, QTableWidgetItem(str(sugg['suggestion_id'])))
                self.suggestion_table.setItem(row, 1, QTableWidgetItem(sugg['employee']))
                self.suggestion_table.setItem(row, 2, QTableWidgetItem(sugg['suggestion_type']))
                self.suggestion_table.setItem(row, 3, QTableWidgetItem(sugg['suggestion_content']))
                self.suggestion_table.setItem(row, 4, QTableWidgetItem(str(sugg['submit_time'])))

                status_text = "未处理" if sugg['status'] == 0 else "已处理"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(QColor("red" if sugg['status'] == 0 else "green"))
                self.suggestion_table.setItem(row, 5, status_item)

                reply_btn = QPushButton("回复")
                reply_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #165DFF;
                        color: white;
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #0D47A1;
                    }
                """)
                reply_btn.clicked.connect(lambda checked, id=sugg['suggestion_id']: self.show_reply_dialog(id))
                self.suggestion_table.setCellWidget(row, 6, reply_btn)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"搜索意见失败: {str(e)}")

    def show_reply_dialog(self, suggestion_id=None):
        """显示回复对话框"""
        # 如果未指定ID，检查选中行
        if suggestion_id is None:
            selected_rows = self.suggestion_table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "提示", "请先选择一条意见")
                return

            row = selected_rows[0].row()
            suggestion_id = self.suggestion_table.item(row, 0).text()

        # 获取意见详情
        try:
            query = """
                SELECT s.suggestion_id, s.employee_id, a.employee_name, 
                       s.suggestion_type, s.suggestion_content, s.submit_time,
                       r.reply_content, r.reply_time, r.reply_admin_id, a2.employee_name AS admin_name
                FROM suggestion_box s
                LEFT JOIN employee_accounts a ON s.employee_id = a.employee_id
                LEFT JOIN suggestion_replies r ON s.suggestion_id = r.suggestion_id
                LEFT JOIN employee_accounts a2 ON r.reply_admin_id = a2.employee_id
                WHERE s.suggestion_id = %s
            """
            suggestion = self.db.fetch_one(query, (suggestion_id,))
            if not suggestion:
                QMessageBox.warning(self, "错误", "意见不存在")
                return
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取意见详情失败: {str(e)}")
            return

        # 创建回复对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"回复意见 - ID: {suggestion_id}")
        dialog.setMinimumSize(600, 500)
        layout = QVBoxLayout(dialog)

        # 意见详情
        detail_group = QGroupBox("意见详情")
        detail_layout = QGridLayout(detail_group)
        detail_layout.addWidget(QLabel("员工:"), 0, 0)
        detail_layout.addWidget(QLabel(f"{suggestion['employee_id']} - {suggestion['employee_name']}"), 0, 1)
        detail_layout.addWidget(QLabel("类型:"), 1, 0)
        detail_layout.addWidget(QLabel(suggestion['suggestion_type']), 1, 1)
        detail_layout.addWidget(QLabel("提交时间:"), 2, 0)
        detail_layout.addWidget(QLabel(str(suggestion['submit_time'])), 2, 1)
        detail_layout.addWidget(QLabel("内容:"), 3, 0, 1, 2)
        content_label = QTextEdit(suggestion['suggestion_content'])
        content_label.setReadOnly(True)
        detail_layout.addWidget(content_label, 4, 0, 1, 2)
        layout.addWidget(detail_group)

        # 回复区域
        reply_group = QGroupBox("回复内容")
        reply_layout = QVBoxLayout(reply_group)
        self.reply_content = QTextEdit()
        self.reply_content.setPlaceholderText("请输入回复内容...")
        reply_layout.addWidget(self.reply_content)
        layout.addWidget(reply_group)

        # 已有回复
        if suggestion['reply_content']:
            existing_reply = QGroupBox("已有回复")
            existing_layout = QVBoxLayout(existing_reply)
            reply_text = QTextEdit(suggestion['reply_content'])
            reply_text.setReadOnly(True)
            reply_text.setStyleSheet("background-color: #f5f5f5; border: 1px solid #e0e0e0;")
            reply_info = QLabel(
                f"回复人: {suggestion['admin_name'] or '系统'} | 回复时间: {suggestion['reply_time'] or '无'}")
            reply_info.setStyleSheet("font-size: 12px; color: #666;")
            existing_layout.addWidget(reply_info)
            existing_layout.addWidget(reply_text)
            layout.addWidget(existing_reply)

        # 按钮区域
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存回复")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        # 保存回复
        def save_reply():
            content = self.reply_content.toPlainText().strip()
            if not content:
                QMessageBox.warning(dialog, "警告", "回复内容不能为空")
                return

            try:
                # 检查是否已有回复，有则更新，无则插入
                if suggestion['reply_content']:
                    query = """
                        UPDATE suggestion_replies 
                        SET reply_content = %s, reply_time = NOW() 
                        WHERE suggestion_id = %s
                    """
                    self.db.execute(query, (content, suggestion_id))
                else:
                    query = """
                        INSERT INTO suggestion_replies 
                        (suggestion_id, reply_admin_id, reply_content)
                        VALUES (%s, %s, %s)
                    """
                    # 假设当前管理员ID为1，实际应从登录状态获取
                    self.db.execute(query, (suggestion_id, 1, content))

                # 更新意见状态为已处理
                self.db.execute("UPDATE suggestion_box SET status = 1 WHERE suggestion_id = %s", (suggestion_id,))
                QMessageBox.information(dialog, "成功", "回复保存成功")
                dialog.accept()
                self.load_suggestion_data()  # 刷新数据
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"保存回复失败: {str(e)}")

        save_btn.clicked.connect(save_reply)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec_()

    def switch_tab(self, tab_name):
        """
        安全切换标签页（2025年6月更新版）
        功能：支持重复点击刷新，解决C++对象删除问题
        """
        try:
            # 状态记录
            prev_tab_name = getattr(self, 'current_tab_name', None)
            is_same_tab = (prev_tab_name == tab_name)

            # 获取主布局
            main_layout = self.centralWidget().layout()

            # 相同标签页处理（刷新而非重建）
            if is_same_tab:
                self.refresh_current_tab()
                return

            # 安全移除旧部件
            while main_layout.count() > 1:
                item = main_layout.takeAt(1)
                if item.widget():
                    item.widget().deleteLater()
                del item
            # 创建新标签页（带异常捕获）
            try:
                if tab_name == "员工管理":
                    new_tab = self.create_employee_list_tab()
                    self.load_employee_data()
                elif tab_name == "职位管理":
                    new_tab = self.create_position_management_tab()
                    self.load_position_data()
                elif tab_name == "历史记录":
                    new_tab = self.create_history_management_tab()
                    self.load_history_data()
                elif tab_name == "系统管理" :
                    new_tab = self.create_system_management_tab()
                    # self.load_system_data()
                elif tab_name == "服务器通信":
                    new_tab = self.create_server_communication_tab()
                    # self.load_server_data()
                elif tab_name == "回复箱":
                    new_tab = self.create_suggestion_management_tab()
                    self.load_suggestion_data()
                else:
                    raise ValueError(f"未知标签页: {tab_name}")
            except Exception as e:
                raise RuntimeError(f"创建{tab_name}标签页失败: {str(e)}")

            # 更新当前标签页引用
            self.current_tab = new_tab
            self.current_tab_name = tab_name
            main_layout.addWidget(new_tab, 3)

        except Exception as e:
            error_msg = f"标签页切换错误({datetime.datetime.now().strftime('%H:%M:%S')}):  {str(e)}"
            print(error_msg)  # 日志记录
            QMessageBox.critical(self, "系统错误",
                                 f"操作失败，请重试\n错误详情：{error_msg.split(':')[-1]}")

        finally:
            QApplication.processEvents()  # 强制处理事件队列

    def refresh_current_tab(self):
        """安全刷新当前标签页数据"""
        if not hasattr(self, 'current_tab_name'):
            return

        try:
            # 对象存活检查
            if not self.current_tab or not sip.isdeleted(self.current_tab):
                if self.current_tab_name == "员工管理":
                    self.employee_table = getattr(self, 'employee_table', None)
                    if self.employee_table and not sip.isdeleted(self.employee_table):
                        self.load_employee_data()
                    else:
                        self.rebuild_employee_table()
                elif self.current_tab_name == "职位管理":
                    self.position_table = getattr(self, 'position_table', None)
                    if self.position_table and not sip.isdeleted(self.position_table):
                        self.load_position_data()
                    else:
                        self.rebuild_position_table()
                elif self.current_tab_name == "历史记录":
                    self.history_table = getattr(self, 'history_table', None)
                    if self.history_table and not sip.isdeleted(self.history_table):
                        self.load_history_data()
                    else:
                        self.rebuild_history_table()
                # elif self.current_tab_name == "系统管理":
                #     self.system_table = getattr(self, 'system_table', None)
                #     if self.system_table and not sip.isdeleted(self.system_table):
                #         self.load_system_data()
                #     else:
                #         self.rebuild_system_table()
                # elif self.current_tab_name == "服务器通信":
                #     self.server_table = getattr(self, 'server_table', None)
                #     if self.server_table and not sip.isdeleted(self.server_table):
                #         self.load_server_data()
                #     else:
                #         self.rebuild_server_table()
        except Exception as e:
            QMessageBox.warning(self, "刷新警告",
                                f"数据刷新失败，正在尝试恢复...\n{str(e)}")
            self.switch_tab(self.current_tab_name)  # 自动重建

    def rebuild_employee_table(self):
        """完全重建员工表格（应急恢复）"""
        try:
            # 清理旧资源
            if hasattr(self, 'employee_table'):
                try:
                    self.employee_table.deleteLater()
                except RuntimeError:
                    pass

                    # 新建表格
            self.employee_table = QTableWidget()
            self.employee_table.setObjectName(f"employeeTable_{int(time.time())}")

            # 重新初始化
            self.employee_table.setColumnCount(8)
            self.employee_table.setHorizontalHeaderLabels([
                "员工ID", "姓名", "电话", "入职日期",
                "婚姻状况", "学历", "性别", "职位"
            ])
            # 其他初始化配置...

            # 弱引用信号连接
            weakref.WeakMethod(self.edit_employee)  # 示例连接
            return True

        except Exception as e:
            QMessageBox.critical(self, "紧急错误",
                                 f"系统无法自动恢复，请重启应用\n错误代码: EMP_TABLE_RECREATE_FAIL")
            return False



    def rebuild_history_table(self):
        """完全重建历史记录表格（应急恢复）"""
        try:
            # 清理旧资源
            if hasattr(self, 'history_table'):
                try:
                    self.history_table.deleteLater()
                except RuntimeError:
                    pass

            # 新建表格并设置唯一对象名（便于调试）
            self.history_table = QTableWidget()
            self.history_table.setObjectName(f"historyTable_{int(time.time())}")

            # 重新初始化表格配置
            self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
            self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.history_table.setColumnCount(6)
            self.history_table.setHorizontalHeaderLabels([
                "记录ID", "员工ID", "变更时间", "变更类型", "旧信息", "新信息"
            ])
            self.history_table.horizontalHeader().setStretchLastSection(True)
            self.history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
            self.history_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)

            # 弱引用信号连接（避免内存泄漏）
            search_btn = getattr(self, 'history_search_btn', None)
            if search_btn:
                search_btn.clicked.disconnect()
                search_btn.clicked.connect(self.search_history)

            # 返回重建状态
            return True

        except Exception as e:
            QMessageBox.critical(self, "紧急错误",
                                 f"历史记录表格重建失败，请重启应用\n错误详情: {str(e)}")
            return False

    def rebuild_position_table(self):
        """完全重建职位管理表格（应急恢复）"""
        try:
            # 清理旧资源
            if hasattr(self, 'position_table'):
                try:
                    self.position_table.deleteLater()
                except RuntimeError:
                    pass

            # 新建表格并设置唯一对象名
            self.position_table = QTableWidget()
            self.position_table.setObjectName(f"positionTable_{int(time.time())}")

            # 重新初始化表格配置
            self.position_table.setEditTriggers(QTableWidget.NoEditTriggers)
            self.position_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.position_table.setSelectionMode(QTableWidget.SingleSelection)
            self.position_table.setColumnCount(2)
            self.position_table.setHorizontalHeaderLabels(["职位ID", "职位名称"])
            self.position_table.horizontalHeader().setStretchLastSection(True)
            self.position_table.verticalHeader().setVisible(False)  # 隐藏行号

            # 恢复表格样式
            self.position_table.setStyleSheet("""
                QTableWidget {
                    border: 1px solid #d0d8e6;
                    border-radius: 4px;
                    background-color: white;
                }
                QTableWidget::header {
                    background-color: #f0f5ff;
                    border-bottom: 1px solid #d0d8e6;
                }
                QTableWidget::item {
                    padding: 5px;
                }
            """)

            # 信号连接恢复
            search_btn = getattr(self, 'pos_search', None)
            if search_btn:
                search_btn.clicked.disconnect()
                search_btn.clicked.connect(self.search_positions)

            add_btn = getattr(self, 'pos_add_btn', None)
            if add_btn:
                add_btn.clicked.disconnect()
                add_btn.clicked.connect(self.show_add_position_dialog)

            # 加载数据
            self.load_position_data()
            return True

        except Exception as e:
            QMessageBox.critical(self, "紧急错误",
                                 f"职位表格重建失败，请重启应用\n错误详情: {str(e)}")
            return False

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))

    # 显示登录窗口
    # login_dialog = LoginDialog()
    # if login_dialog.exec_() == QDialog.Accepted:
        # 登录成功后显示主窗口
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
    # else:
    #     sys.exit(0)