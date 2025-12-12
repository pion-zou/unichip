# test_db.py
import os
from sqlalchemy import create_engine, text

# 使用你的 Neon 连接字符串
database_url = "postgresql://neondb_owner:npg_JL27TAjqkmDS@ep-winter-paper-a4rhg7f2-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

print(f"测试连接: {database_url[:60]}...")

try:
    # 尝试使用 pg8000 驱动
    engine = create_engine(database_url.replace('postgresql://', 'postgresql+pg8000://'))

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"连接成功! 结果: {result.scalar()}")

        # 测试查询版本
        result = conn.execute(text("SELECT version()"))
        print(f"数据库版本: {result.scalar()}")

except Exception as e:
    print(f"连接失败: {e}")

    # 尝试不使用 SSL
    print("\n尝试不使用 SSL...")
    try:
        no_ssl_url = database_url.replace('?sslmode=require', '')
        engine = create_engine(no_ssl_url.replace('postgresql://', 'postgresql+pg8000://'))

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"连接成功! 结果: {result.scalar()}")
    except Exception as e2:
        print(f"无SSL连接也失败: {e2}")