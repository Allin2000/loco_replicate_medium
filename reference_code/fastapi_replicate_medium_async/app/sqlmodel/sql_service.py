# from typing import AsyncGenerator

# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.orm import sessionmaker


# from app.core.config import get_app_settings



# settings = get_app_settings()

# url=settings.sql_db_uri

# print(url)



# # 配置数据库连接 URL
# SQLALCHEMY_DATABASE_URI = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

# # 创建异步 SQLAlchemy 引擎
# engine = create_async_engine(
#     SQLALCHEMY_DATABASE_URI,
#     echo=True,  # 是否显示 SQL 查询
# )

# # 创建异步会话类
# SessionLocal = sessionmaker(
#     bind=engine,
#     class_=AsyncSession,
#     expire_on_commit=False,  # 控制会话是否在提交时清除对象的状态
# )

# # 创建一个 DatabaseService 类，用于管理数据库会话
# class DatabaseService:
#     def __init__(self, db_session: sessionmaker = SessionLocal):
#         """构造函数注入数据库会话工厂"""
#         self.db_session = db_session

#     async def get_db(self) -> AsyncGenerator[AsyncSession, None]:
#         """生成异步数据库会话"""
#         async with self.db_session() as db:
#             yield db

#     def get_session(self) -> sessionmaker:
#         """返回数据库会话工厂"""
#         return self.db_session
    


# # 配置数据库连接 URL
# SQLALCHEMY_DATABASE_URI = "postgres://myuser:mypassword@localhost:5432/fastapi-median-db"

# # 创建 SQLAlchemy 引擎
# engine = create_engine(
#     SQLALCHEMY_DATABASE_URI,
# )

# # 创建会话类
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# # 创建一个 DatabaseService 类，用于管理数据库会话
# class DatabaseService:
#     def __init__(self, db_session: sessionmaker = SessionLocal):
#         """构造函数注入数据库会话工厂"""
#         self.db_session = db_session

#     def get_db(self) -> Generator[Session, None, None]:
#         """生成数据库会话"""
#         db = self.db_session()
#         try:
#             yield db
#         finally:
#             db.close()

#     def get_session(self) -> sessionmaker:
#         """返回数据库会话工厂"""
#         return self.db_session

# database_service = DatabaseService()

# class Service_SQL:
#     @staticmethod
#     def get_db() -> Generator[Session, None, None]:
#         """生成数据库会话"""
#         db = SessionLocal()
#         try:
#             yield db
#         finally:
#             db.close()

#     @staticmethod
#     def get_session() -> sessionmaker:
#         """返回数据库会话工厂"""
#         return SessionLocal