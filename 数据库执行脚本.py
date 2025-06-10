import mysql.connector
from mysql.connector import Error

# 数据库连接配置
config = {
    'host': 'localhost',
    'user': 'root',  # 请替换为你的 MySQL 用户名
    'password': 'password',  # 请替换为你的 MySQL 密码
    'raise_on_warnings': True
}

# SQL 语句集合（修正了触发器部分）
SQL_STATEMENTS = [
    # 创建数据库
    "CREATE DATABASE IF NOT EXISTS works DEFAULT CHARACTER SET utf8mb4",

    # 使用指定数据库
    "USE works",

    # 创建员工账户表
    """CREATE TABLE IF NOT EXISTS employee_accounts (
        employee_id INT AUTO_INCREMENT PRIMARY KEY,
        account VARCHAR(20) NOT NULL UNIQUE,
        employee_name VARCHAR(50) NOT NULL,
        password VARCHAR(32) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 创建管理员账户表
    """CREATE TABLE IF NOT EXISTS admin_accounts (
        admin_account_id INT AUTO_INCREMENT PRIMARY KEY,
        admin_account VARCHAR(50) NOT NULL UNIQUE,
        admin_password VARCHAR(32) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 创建职位表
    """CREATE TABLE IF NOT EXISTS employee_positions (
        position_id INT AUTO_INCREMENT PRIMARY KEY,
        position_name VARCHAR(50) NOT NULL UNIQUE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 创建员工基本信息表
    """CREATE TABLE IF NOT EXISTS employee_basic_info (
        employee_id INT PRIMARY KEY,
        marital_status ENUM('单身', '已婚', '离异', '丧偶', '未录入') DEFAULT '未录入',
        education ENUM('高中', '大专', '本科', '硕士', '博士', '未录入') DEFAULT '未录入',
        gender ENUM('男', '女', '未录入') DEFAULT '未录入',
        position_id INT,
        FOREIGN KEY (position_id) REFERENCES employee_positions(position_id),
        FOREIGN KEY (employee_id) REFERENCES employee_accounts(employee_id) ON UPDATE CASCADE ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 创建变更类型字典表
    """CREATE TABLE IF NOT EXISTS `change_type_dict` (
        `type_id` int NOT NULL AUTO_INCREMENT,
        `type_name` varchar(50) NOT NULL COMMENT '变更类型名称（如info_update）',
        `description` varchar(200) DEFAULT NULL COMMENT '类型描述（如“员工信息更新”）',
        `category` varchar(30) DEFAULT NULL COMMENT '变更分类（员工/职位/系统等）',
        `is_active` tinyint DEFAULT 1 COMMENT '是否启用',
        PRIMARY KEY (`type_id`),
        UNIQUE KEY `type_name` (`type_name`)
    ) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""",

    # 创建历史信息主表
    """CREATE TABLE IF NOT EXISTS `history_info` (
        `history_id` int NOT NULL AUTO_INCREMENT,
        `employee_id` int DEFAULT NULL COMMENT '关联的员工ID（职位变更时可为空）',
        `operator_id` int DEFAULT NULL COMMENT '关联管理员（操作人）',
        `client_ip` varchar(50) DEFAULT NULL COMMENT '操作端IP（审计用）',
        `change_date` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '变更时间（改用DATETIME避免时区问题）',
        `type_id` int NOT NULL COMMENT '关联变更类型字典',
        `old_info` json DEFAULT NULL COMMENT '旧数据（结构化存储）',
        `new_info` json DEFAULT NULL COMMENT '新数据（结构化存储）',
        `related_table` varchar(50) DEFAULT NULL COMMENT '关联的表（employee/position等）',
        PRIMARY KEY (`history_id`),
        KEY `employee_id` (`employee_id`),
        KEY `operator_id` (`operator_id`),
        KEY `type_id` (`type_id`),
        CONSTRAINT `history_info_ibfk_1` FOREIGN KEY (`employee_id`) REFERENCES `employee_accounts` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT `history_info_ibfk_2` FOREIGN KEY (`operator_id`) REFERENCES `admin_accounts` (`admin_account_id`) ON DELETE SET NULL,
        CONSTRAINT `history_info_ibfk_3` FOREIGN KEY (`type_id`) REFERENCES `change_type_dict` (`type_id`)
    ) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci""",

    # 创建意见箱表
    """CREATE TABLE IF NOT EXISTS suggestion_box (
        suggestion_id INT AUTO_INCREMENT PRIMARY KEY,
        employee_id INT NOT NULL,
        suggestion_type VARCHAR(50) NOT NULL,
        suggestion_content TEXT NOT NULL,
        submit_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TINYINT DEFAULT 0 COMMENT '0:未处理, 1:已处理',
        FOREIGN KEY (employee_id) REFERENCES employee_accounts(employee_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 创建意见回复表
    """CREATE TABLE IF NOT EXISTS suggestion_replies (
        reply_id INT AUTO_INCREMENT PRIMARY KEY,
        suggestion_id INT NOT NULL,
        reply_admin_id INT NOT NULL,
        reply_content TEXT NOT NULL,
        reply_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (suggestion_id) REFERENCES suggestion_box(suggestion_id),
        FOREIGN KEY (reply_admin_id) REFERENCES admin_accounts(admin_account_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 创建系统通知表
    """CREATE TABLE IF NOT EXISTS system_notifications (
        notification_id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(100) NOT NULL,
        content TEXT NOT NULL,
        publish_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        publisher VARCHAR(50) NOT NULL,
        target_type ENUM('all', 'department', 'individual') DEFAULT 'all',
        target_employee_id INT DEFAULT NULL,
        target_department_id INT DEFAULT NULL,
        FOREIGN KEY (target_employee_id) REFERENCES employee_accounts(employee_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    # 创建触发器（移除了DELIMITER）
    """CREATE TRIGGER IF NOT EXISTS after_employee_accounts_insert
    AFTER INSERT ON employee_accounts
    FOR EACH ROW
    BEGIN
        INSERT INTO employee_basic_info (employee_id)
        VALUES (NEW.employee_id);
    END""",

    """CREATE TRIGGER IF NOT EXISTS delete_employee_accounts
    AFTER DELETE ON employee_accounts
    FOR EACH ROW
    BEGIN
        DELETE FROM employee_basic_info
        WHERE employee_id = OLD.employee_id;
    END"""
]


def execute_sql_scripts():
    """执行SQL脚本创建数据库和表结构"""
    try:
        # 连接到MySQL服务器
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()

        print("成功连接到MySQL服务器")

        # 依次执行SQL语句
        for sql in SQL_STATEMENTS:
            try:
                print(f"执行: {sql[:50]}...")
                cursor.execute(sql)
                connection.commit()
                print("→ 成功")
            except Error as e:
                print(f"→ 错误: {e}")

        print("所有SQL语句执行完毕！")

    except Error as e:
        print(f"数据库连接错误: {e}")
    finally:
        # 关闭数据库连接
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("数据库连接已关闭")


if __name__ == "__main__":
    execute_sql_scripts()