-- 注意这里只做关键表结构展示,不做sql语句的插入,因为数据库脚本可以直接创建了
-- 注意这里只做关键表结构展示,不做sql语句的插入,因为数据库脚本可以直接创建了
-- 注意这里只做关键表结构展示,不做sql语句的插入,因为数据库脚本可以直接创建了
-- 创建员工账户表
CREATE TABLE employee_accounts (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    account VARCHAR(20) NOT NULL UNIQUE, -- 以手机号进行注册
    employee_name VARCHAR(50) NOT NULL,
    password VARCHAR(32) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建管理员账户表
CREATE TABLE admin_accounts (
    admin_account_id INT AUTO_INCREMENT PRIMARY KEY,
    admin_account VARCHAR(50) NOT NULL UNIQUE,
    admin_password VARCHAR(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- 创建职位表
CREATE TABLE employee_positions (
    position_id INT AUTO_INCREMENT PRIMARY KEY,
    position_name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建员工基本信息表
CREATE TABLE employee_basic_info (
    employee_id INT  PRIMARY KEY,
    marital_status ENUM('单身', '已婚', '离异', '丧偶', '未录入') DEFAULT '未录入',
    education ENUM('高中', '大专', '本科', '硕士', '博士','未录入') DEFAULT '未录入',
    gender ENUM('男', '女', '未录入') DEFAULT '未录入',
    position_id INT,
    -- 关联员工职位表，外键保持
    FOREIGN KEY (position_id) REFERENCES employee_positions(position_id),
    -- 这里原外键关联可能有问题，假设是关联员工账户表的 phone 字段，按此修正，若实际不是，需调整
    FOREIGN KEY (employee_id) REFERENCES employee_accounts(employee_id) ON UPDATE CASCADE ON DELETE CASCADE -- 同步更新和删除 不依靠触发器
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- 创建员工职位表


-- 1. 变更类型字典表（解耦类型，支持动态扩展）
CREATE TABLE `change_type_dict` (
  `type_id` int NOT NULL AUTO_INCREMENT,
  `type_name` varchar(50) NOT NULL COMMENT '变更类型名称（如info_update）',
  `description` varchar(200) DEFAULT NULL COMMENT '类型描述（如“员工信息更新”）',
  `category` varchar(30) DEFAULT NULL COMMENT '变更分类（员工/职位/系统等）',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否启用',
  PRIMARY KEY (`type_id`),
  UNIQUE KEY `type_name` (`type_name`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 2. 历史信息主表（核心重构）
CREATE TABLE `history_info` (
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
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 意见箱表
CREATE TABLE suggestion_box (
    suggestion_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    suggestion_type VARCHAR(50) NOT NULL,
    suggestion_content TEXT NOT NULL,
    submit_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TINYINT DEFAULT 0 COMMENT '0:未处理, 1:已处理',
    FOREIGN KEY (employee_id) REFERENCES employee_accounts(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 意见回复表
CREATE TABLE suggestion_replies (
    reply_id INT AUTO_INCREMENT PRIMARY KEY,
    suggestion_id INT NOT NULL,
    reply_admin_id INT NOT NULL,
    reply_content TEXT NOT NULL,
    reply_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (suggestion_id) REFERENCES suggestion_box(suggestion_id),
    FOREIGN KEY (reply_admin_id) REFERENCES admin_accounts(admin_account_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 系统通知表
CREATE TABLE system_notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    publish_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    publisher VARCHAR(50) NOT NULL,
    target_type ENUM('all', 'department', 'individual') DEFAULT 'all',
    target_employee_id INT DEFAULT NULL,
    target_department_id INT DEFAULT NULL,
    FOREIGN KEY (target_employee_id) REFERENCES employee_accounts(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;