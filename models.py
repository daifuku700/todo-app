# models.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# 例）"mssql+pyodbc://username:password@your-sql-server.database.windows.net:1433/yourdb?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30"
AZURE_SQL_CONNECTION_STRING = os.getenv("AZURE_SQL_CONNECTION_STRING")

if not AZURE_SQL_CONNECTION_STRING:
    raise RuntimeError("環境変数 AZURE_SQL_CONNECTION_STRING を設定してください。")

engine = create_engine(AZURE_SQL_CONNECTION_STRING, pool_pre_ping=True, future=True)


class Todo(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_oid = Column(String(64), index=True, nullable=False)  # Entra ID のユーザー OID
    title = Column(String(255), nullable=False)
    is_done = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False)
