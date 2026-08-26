"""应用配置：从环境变量读取，兼容本地与容器部署。"""
from __future__ import annotations

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "电商风险控制系统"
    app_env: str = os.getenv("APP_ENV", "dev")

    # MySQL 连接，默认本地 root/root（本地与 docker-compose 均可覆盖）
    mysql_host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "root")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "risk_control")

    # 评分阈值（按等级划分 boundary）
    low_threshold: int = 40
    high_threshold: int = 70

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )


settings = Settings()
