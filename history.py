import json
import logging
import datetime
class HistoryService:
    def __init__(self, db):
        self.db = db
    def record_change(self, employee_id, change_type, old_info, new_info, operator_id=None, client_ip=None):
        """记录员工变更历史"""
        try:
            # 将变更类型映射为数据库中的type_id（从字典表查询）
            type_id = self._get_type_id(change_type)
            if not type_id:
                raise ValueError(f"未知变更类型: {change_type}")

            # 构造历史记录数据
            data = {
                "employee_id": employee_id,
                "operator_id": operator_id,
                "client_ip": client_ip,
                "change_date": datetime.datetime.now(),
                "type_id": type_id,
                "old_info": json.dumps(old_info, ensure_ascii=False),
                "new_info": json.dumps(new_info, ensure_ascii=False)
            }

            # 写入历史表（使用事务确保原子性）
            with self.db.connection.cursor() as cursor:
                query = """
                    INSERT INTO history_info 
                    (employee_id, operator_id, client_ip, change_date, type_id, old_info, new_info)
                    VALUES (%(employee_id)s, %(operator_id)s, %(client_ip)s, %(change_date)s, %(type_id)s, %(old_info)s, %(new_info)s)
                """
                cursor.execute(query, data)

            self.db.connection.commit()
            return True
        except Exception as e:
            self.db.connection.rollback()
            logging.error(f"记录历史失败: {str(e)}", exc_info=True)
            return False

    def _get_type_id(self, change_type):
        """根据变更类型名称获取type_id"""
        with self.db.connection.cursor() as cursor:
            query = "SELECT type_id FROM change_type_dict WHERE type_name = %s"
            cursor.execute(query, (change_type,))
            result = cursor.fetchone()
            return result["type_id"] if result else None
    def record_position_create(self, position_id, position_name, operator_id=None, client_ip=None):
        """记录职位创建（无员工关联，employee_id=None）"""
        return self.record_change(
            employee_id=None,  # 职位新增时，无关联员工
            change_type="position_create",
            old_info={},
            new_info={"position_id": position_id, "position_name": position_name},
            operator_id=operator_id,
            client_ip=client_ip
        )
    def record_position_update(self, position_id, old_name, new_name, operator_id=None, client_ip=None):
        return self.record_change(
            employee_id=None,
            change_type="position_update",
            old_info={"position_id": position_id, "position_name": old_name},
            new_info={"position_id": position_id, "position_name": new_name},
            operator_id=operator_id,
            client_ip=client_ip
        )
    def record_position_delete(self, position_id, position_name, operator_id=None, client_ip=None):
        return self.record_change(
            employee_id=None,
            change_type="position_delete",
            old_info={"position_id": position_id, "position_name": position_name},
            new_info={},
            operator_id=operator_id,
            client_ip=client_ip
        )