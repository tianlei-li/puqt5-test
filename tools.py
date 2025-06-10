
from PyQt5.QtCore import QDate
from datetime import datetime
import datetime
def to_qdate(date_obj):
    """将Python日期对象转换为QDate对象"""
    if isinstance(date_obj, datetime.date):
        return QDate(date_obj.year, date_obj.month, date_obj.day)
    elif isinstance(date_obj, str):
        # 尝试解析常见的日期格式
        for fmt in ('yyyy-MM-dd', 'yyyy/MM/dd', 'MM/dd/yyyy'):
            qdate = QDate.fromString(date_obj, fmt)
            if qdate.isValid():
                return qdate
        raise ValueError(f"无法解析日期: {date_obj}")
    raise TypeError(f"不支持的日期类型: {type(date_obj)}")