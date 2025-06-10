-- 注意这里只做关键表结构展示,不做sql语句的插入,因为数据库脚本可以直接创建了
-- 注意这里只做关键表结构展示,不做sql语句的插入,因为数据库脚本可以直接创建了
-- 注意这里只做关键表结构展示,不做sql语句的插入,因为数据库脚本可以直接创建了
DELIMITER $$
-- 员工注册时自动创建基本信息记录
CREATE TRIGGER after_employee_accounts_insert
AFTER INSERT ON employee_accounts
FOR EACH ROW
BEGIN
    INSERT INTO employee_basic_info (employee_id)
    VALUES (employee_accounts.employee_id);
END$$

-- 员工表删除时同步删除信息表
CREATE TRIGGER delete_employee_accounts
AFTER DELETE ON employee_basic_info
FOR EACH ROW
BEGIN
    DELETE FROM employee_accounts
    WHERE employee_id = OLD.employee_id;
END$$
DELIMITER ;



