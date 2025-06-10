import json
import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QLineEdit, QMessageBox, QTextEdit, QFormLayout,
                             QComboBox, QTabWidget, QHeaderView)

from db_connect import Database


class UserMainWindow(QMainWindow):
    def __init__(self, user_id=1):
        super().__init__()
        try:
            self.user_id = user_id
            self.db = Database()
            self.init_ui()

            # 先显示窗口，再处理可能耗时的操作
            self.show()

            # 加载用户信息
            user_info = self.load_user_info()
            if user_info:
                self.show_user_info()
            else:
                # 显示空状态界面
                print("显示用户界面错误")

        except Exception as e:
            print(f"用户主窗口初始化异常: {e}")
            QMessageBox.critical(self, "初始化错误", f"用户界面初始化失败:\n{str(e)}")

    def init_ui(self):
        # 窗口基本设置
        self.setWindowTitle("人事管理系统 - 用户界面")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 600)

        # 中央部件和主布局
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        # 顶部导航栏
        nav_bar = QHBoxLayout()
        info_btn = QPushButton("个人信息")
        info_btn.clicked.connect(self.show_user_info)
        modify_btn = QPushButton("修改信息")
        modify_btn.clicked.connect(self.modify_user_info)
        suggestion_btn = QPushButton("意见箱")
        suggestion_btn.clicked.connect(self.show_suggestion_box)
        notice_btn = QPushButton("官方通知")
        notice_btn.clicked.connect(self.show_notifications)

        nav_bar.addWidget(info_btn)
        nav_bar.addWidget(modify_btn)
        nav_bar.addWidget(suggestion_btn)
        nav_bar.addWidget(notice_btn)
        main_layout.addLayout(nav_bar)

        # 内容显示区域
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        main_layout.addWidget(self.content_widget)

        # 状态栏
        self.statusBar().showMessage("用户登录 | 就绪", 3000)


    def load_user_info(self):
        """加载用户完整信息（关联账户表和基本信息表）"""
        query = """
            SELECT 
                a.employee_id, 
                a.account AS phone, 
                a.employee_name, 
                b.gender, 
                b.education, 
                b.marital_status,
                p.position_name,
                b.position_id
            FROM employee_accounts a
            LEFT JOIN employee_basic_info b ON a.employee_id = b.employee_id
            LEFT JOIN employee_positions p ON b.position_id = p.position_id
            WHERE a.employee_id = %s
        """
        user_info = self.db.fetch_one(query, (self.user_id,))
        return user_info

    def show_user_info(self):
        """显示用户信息"""
        self.clear_content_layout()  # 替换原循环

        user_info = self.load_user_info()
        if user_info:
            # 创建标签页展示不同类别的信息
            tab_widget = QTabWidget()

            # 基本信息标签页
            basic_info_widget = QWidget()
            basic_info_layout = QFormLayout(basic_info_widget)

            # 显示用户信息（格式化ENUM值）
            basic_info_layout.addRow("员工ID", QLabel(str(user_info['employee_id'])))
            basic_info_layout.addRow("姓名", QLabel(user_info['employee_name']))
            basic_info_layout.addRow("手机号", QLabel(user_info['phone']))
            basic_info_layout.addRow("性别", QLabel(user_info['gender']))
            basic_info_layout.addRow("学历", QLabel(user_info['education']))
            basic_info_layout.addRow("婚姻状况", QLabel(user_info['marital_status']))
            basic_info_layout.addRow("职位", QLabel(user_info['position_name'] or "未设置"))

            tab_widget.addTab(basic_info_widget, "基本信息")

            # 添加其他可能的标签页（如历史记录等）
            # tab_widget.addTab(other_widget, "其他信息")

            self.content_layout.addWidget(tab_widget)

    def modify_user_info(self):
        """修改用户信息（仅允许修改姓名和手机号）"""
        self.clear_content_layout()  # 替换原循环

        user_info = self.load_user_info()
        if user_info:
            form_layout = QFormLayout()

            # 可修改字段：姓名和手机号
            name_edit = QLineEdit()
            name_edit.setText(user_info['employee_name'])
            form_layout.addRow("姓名", name_edit)

            phone_edit = QLineEdit()
            phone_edit.setText(user_info['phone'])
            form_layout.addRow("手机号", phone_edit)

            # 提交按钮
            save_btn = QPushButton("保存修改")
            save_btn.clicked.connect(lambda: self.save_modified_info(
                name_edit.text(), phone_edit.text()
            ))
            form_layout.addRow(save_btn)

            # 提示信息
            notice_label = QLabel("提示：如需修改性别、年龄、岗位等内部信息，请通过意见箱提交申请。")
            notice_label.setStyleSheet("color: #666; font-size: 12px;")
            form_layout.addRow(notice_label)

            self.content_layout.addLayout(form_layout)

    def save_modified_info(self, name, phone):
        """保存修改后的用户信息"""
        # 检查手机号格式（简化示例，实际应使用正则表达式）
        if not phone.isdigit() or len(phone) != 11:
            QMessageBox.warning(self, "格式错误", "手机号必须为11位数字！")
            return

        # 开启数据库事务
        self.db.begin_transaction()

        try:
            # 更新账户表
            query = "UPDATE employee_accounts SET employee_name = %s, account = %s WHERE employee_id = %s"
            result = self.db.execute(query, (name, phone, self.user_id))

            if result:
                # 记录修改历史
                self.record_modification_history("account_update", {
                    "old_info": {"employee_name": self.load_user_info()['employee_name'],
                                 "phone": self.load_user_info()['phone']},
                    "new_info": {"employee_name": name, "phone": phone}
                })

                self.db.commit()
                QMessageBox.information(self, "成功", "个人信息修改成功！")
                self.show_user_info()
            else:
                self.db.rollback()
                QMessageBox.warning(self, "失败", "个人信息修改失败！")
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "错误", f"发生异常: {str(e)}")

    def record_modification_history(self, change_type, data):
        """记录修改历史到history_info表（修正JSON格式）"""
        # 校验type_name是否存在
        check_query = "SELECT type_id FROM change_type_dict WHERE type_name = %s"
        type_id = self.db.fetch_one(check_query, (change_type,))

        if not type_id:
            QMessageBox.critical(self, "错误", f"变更类型 '{change_type}' 不存在，请联系管理员！")
            return False

        try:
            # 核心修复：使用json.dumps生成合法JSON（双引号包裹）
            old_json = json.dumps(data['old_info'], ensure_ascii=False)
            new_json = json.dumps(data['new_info'], ensure_ascii=False)

            query = """
                INSERT INTO history_info 
                (employee_id, operator_id, type_id, old_info, new_info, related_table)
                VALUES (%s, NULL, %s, %s, %s, 'employee_accounts')
            """
            return self.db.execute(query, (
                self.user_id,
                type_id['type_id'],
                old_json,
                new_json
            ))
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "JSON错误", f"JSON序列化失败: {str(e)}")
            return False
    def show_suggestion_box(self):
        """显示意见箱"""
        self.clear_content_layout()  # 替换原循环

        # 创建标签页：提交意见和查看历史
        tab_widget = QTabWidget()

        # 提交意见标签页
        submit_widget = QWidget()
        submit_layout = QVBoxLayout(submit_widget)

        suggestion_type = QComboBox()
        suggestion_type.addItems(["信息修改申请", "岗位调整申请", "福利建议", "其他"])

        suggestion_content = QTextEdit()
        suggestion_content.setPlaceholderText("请详细描述您的意见或申请...")

        submit_btn = QPushButton("提交")
        submit_btn.clicked.connect(lambda: self.submit_suggestion(
            suggestion_type.currentText(), suggestion_content.toPlainText()
        ))

        submit_layout.addWidget(QLabel("意见类型:"))
        submit_layout.addWidget(suggestion_type)
        submit_layout.addWidget(QLabel("意见内容:"))
        submit_layout.addWidget(suggestion_content)
        submit_layout.addWidget(submit_btn)

        # 历史记录标签页
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)

        # 查询意见历史
        query = """
            SELECT 
                s.suggestion_id,
                s.suggestion_type,
                s.suggestion_content,
                s.submit_time,
                s.status,
                r.reply_content,
                r.reply_time,
                a.admin_account AS reply_by
            FROM suggestion_box s
            LEFT JOIN suggestion_replies r ON s.suggestion_id = r.suggestion_id
            LEFT JOIN admin_accounts a ON r.reply_admin_id = a.admin_account_id
            WHERE s.employee_id = %s
            ORDER BY s.submit_time DESC
        """
        suggestions = self.db.fetch_all(query, (self.user_id,))

        if suggestions:
            table = QTableWidget()
            table.setColumnCount(7)
            table.setRowCount(len(suggestions))
            table.setHorizontalHeaderLabels(["ID", "类型", "内容", "提交时间", "状态", "回复内容", "回复时间"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 内容列自适应

            for row, suggestion in enumerate(suggestions):
                table.setItem(row, 0, QTableWidgetItem(str(suggestion['suggestion_id'])))
                table.setItem(row, 1, QTableWidgetItem(suggestion['suggestion_type']))
                table.setItem(row, 2, QTableWidgetItem(suggestion['suggestion_content']))
                table.setItem(row, 3, QTableWidgetItem(str(suggestion['submit_time'])))

                # 状态显示
                status = "已提交"
                if suggestion['status'] == 1:
                    status = "已处理"
                table.setItem(row, 4, QTableWidgetItem(status))

                # 回复内容
                table.setItem(row, 5, QTableWidgetItem(suggestion['reply_content'] or "等待回复"))
                table.setItem(row, 6, QTableWidgetItem(str(suggestion['reply_time'] or "")))

            history_layout.addWidget(table)
        else:
            history_layout.addWidget(QLabel("暂无提交记录"))

        # 添加标签页
        tab_widget.addTab(submit_widget, "提交意见")
        tab_widget.addTab(history_widget, "历史记录")

        self.content_layout.addWidget(tab_widget)

    def submit_suggestion(self, suggestion_type, content):
        """提交意见"""
        if not content:
            QMessageBox.warning(self, "提示", "请输入意见内容！")
            return

        query = """
            INSERT INTO suggestion_box 
            (employee_id, suggestion_type, suggestion_content, submit_time, status)
            VALUES (%s, %s, %s, NOW(), 0)
        """
        result = self.db.execute(query, (self.user_id, suggestion_type, content))
        if result:
            QMessageBox.information(self, "成功", "意见提交成功！")
            self.show_suggestion_box()  # 刷新页面
        else:
            QMessageBox.warning(self, "失败", "意见提交失败！")

    def show_notifications(self):
        """显示官方通知"""
        self.clear_content_layout()  # 替换原循环

        # 创建标签页：系统通知和岗位变动
        tab_widget = QTabWidget()

        # 系统通知标签页
        system_notice_widget = QWidget()
        system_notice_layout = QVBoxLayout(system_notice_widget)

        # 查询系统通知
        query = """
            SELECT * FROM system_notifications 
            WHERE target_employee_id = %s OR target_type = 'all'
            ORDER BY publish_time DESC
        """
        system_notices = self.db.fetch_all(query, (self.user_id,))

        if system_notices:
            table = QTableWidget()
            table.setColumnCount(5)
            table.setRowCount(len(system_notices))
            table.setHorizontalHeaderLabels(["标题", "内容", "发布时间", "发布者", "类型"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

            for row, notice in enumerate(system_notices):
                table.setItem(row, 0, QTableWidgetItem(notice['title']))
                table.setItem(row, 1, QTableWidgetItem(notice['content']))
                table.setItem(row, 2, QTableWidgetItem(str(notice['publish_time'])))
                table.setItem(row, 3, QTableWidgetItem(notice['publisher']))

                # 类型显示
                target_type = "个人通知"
                if notice['target_type'] == 'all':
                    target_type = "全体通知"
                elif notice['target_type'] == 'department':
                    target_type = "部门通知"
                table.setItem(row, 4, QTableWidgetItem(target_type))

            system_notice_layout.addWidget(table)
        else:
            system_notice_layout.addWidget(QLabel("暂无系统通知"))

        # 岗位变动标签页
        position_change_widget = QWidget()
        position_change_layout = QVBoxLayout(position_change_widget)

        # 查询岗位变动历史
        query = """
            SELECT 
                h.history_id,
                h.change_date,
                h.old_info,
                h.new_info,
                a.admin_account AS operator
            FROM history_info h
            JOIN admin_accounts a ON h.operator_id = a.admin_account_id
            WHERE h.employee_id = %s 
            AND h.type_id = (SELECT type_id FROM change_type_dict WHERE type_name = 'position_update')
            ORDER BY h.change_date DESC
        """
        position_changes = self.db.fetch_all(query, (self.user_id,))

        if position_changes:
            table = QTableWidget()
            table.setColumnCount(5)
            table.setRowCount(len(position_changes))
            table.setHorizontalHeaderLabels(["变更ID", "变更时间", "原岗位", "新岗位", "操作人"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

            for row, change in enumerate(position_changes):
                table.setItem(row, 0, QTableWidgetItem(str(change['history_id'])))
                table.setItem(row, 1, QTableWidgetItem(str(change['change_date'])))

                # 解析JSON获取岗位名称
                old_info = eval(change['old_info'])
                new_info = eval(change['new_info'])

                old_position = old_info.get('position_name', '未知')
                new_position = new_info.get('position_name', '未知')

                table.setItem(row, 2, QTableWidgetItem(old_position))
                table.setItem(row, 3, QTableWidgetItem(new_position))
                table.setItem(row, 4, QTableWidgetItem(change['operator']))

            position_change_layout.addWidget(table)
        else:
            position_change_layout.addWidget(QLabel("暂无岗位变动记录"))

        # 添加标签页
        tab_widget.addTab(system_notice_widget, "系统通知")
        tab_widget.addTab(position_change_widget, "岗位变动")

        self.content_layout.addWidget(tab_widget)

    def clear_content_layout(self):
        """递归清空布局（支持嵌套布局）"""
        for i in reversed(range(self.content_layout.count())):
            layout_item = self.content_layout.itemAt(i)
            if layout_item is not None:
                widget = layout_item.widget()
                if widget is not None:
                    widget.setParent(None)
                else:
                    # 如果是子布局，递归清空
                    sub_layout = layout_item.layout()
                    if sub_layout is not None:
                        for j in reversed(range(sub_layout.count())):
                            sub_item = sub_layout.itemAt(j)
                            if sub_item is not None:
                                sub_widget = sub_item.widget()
                                if sub_widget is not None:
                                    sub_widget.setParent(None)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 创建并显示用户界面
    user_window = UserMainWindow()
    user_window.show()

    sys.exit(app.exec_())