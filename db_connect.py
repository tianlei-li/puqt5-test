import pymysql
from pymysql.cursors import DictCursor


class Database:
    def __init__(self):
        """初始化数据库连接，包含连接异常处理"""
        self.connection = None
        self.connect_success = False

        try:
            self.connection = pymysql.connect(
                host='localhost',  # 或你的数据库主机地址
                user='root',
                password='208271',
                database='works',
                charset='utf8mb4',
                cursorclass=DictCursor
            )
            self.connect_success = True
        except pymysql.Error as e:
            print(f"数据库连接失败: {e}")

    def execute(self, query, args=None):
        """执行更新操作（INSERT/UPDATE/DELETE），返回操作是否成功"""
        if not self.connect_success or not self.connection:
            print("数据库未连接，无法执行操作")
            return False

        try:
            with self.connection.cursor() as cursor:
                affected_rows = cursor.execute(query, args)
                self.connection.commit()
                return affected_rows > 0  # 返回受影响的行数是否大于0
        except pymysql.Error as e:
            self.connection.rollback()  # 操作失败时回滚事务
            print(f"执行SQL失败: {e}, SQL: {query}, 参数: {args}")
            return False

    def fetch_one(self, query, args=None):
        """查询单条记录，返回None或字典"""
        if not self.connect_success or not self.connection:
            return None

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, args)
                return cursor.fetchone()
        except pymysql.Error as e:
            print(f"查询失败: {e}, SQL: {query}, 参数: {args}")
            return None

    def fetch_all(self, query, args=None):
        """查询多条记录，返回空列表或列表"""
        if not self.connect_success or not self.connection:
            return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, args)
                return cursor.fetchall()
        except pymysql.Error as e:
            print(f"查询失败: {e}, SQL: {query}, 参数: {args}")
            return []

    def begin_transaction(self):
        self.connection.begin()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        """关闭数据库连接，包含异常处理"""
        if self.connection:
            try:
                self.connection.close()
                self.connect_success = False
            except pymysql.Error as e:
                print(f"关闭连接失败: {e}")

    def get_lastrowid(self):
        """获取最后插入行的自增ID"""
        if not self.connect_success or not self.connection:
            print("数据库未连接，无法获取最后插入ID")
            return None

        try:
            # PyMySQL中正确的获取方式是通过connection.insert_id()
            return self.connection.insert_id()
        except pymysql.Error as e:
            print(f"获取最后插入ID失败: {e}")
            return None