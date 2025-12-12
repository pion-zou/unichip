import os
from dotenv import load_dotenv

load_dotenv()

# 获取项目根目录的绝对路径
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # 密钥配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    # 数据库配置
    # 检查是否在 Vercel 环境或有 Neon 连接字符串
    is_vercel = os.environ.get('VERCEL_ENV') == 'production'
    has_neon_url = os.environ.get('DATABASE_URL') is not None

    if is_vercel or has_neon_url:
        # Vercel 环境或有 Neon 连接字符串：使用 PostgreSQL (Neon)
        # 优先使用 DATABASE_URL，如果没有则使用 POSTGRES_URL
        database_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')

        if database_url:
            # 确保使用 pg8000 驱动
            if database_url.startswith('postgresql://'):
                database_url = database_url.replace('postgresql://', 'postgresql+pg8000://', 1)
            elif database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql+pg8000://', 1)

            # 添加客户端编码参数（推荐）
            if '?' not in database_url:
                database_url += '?client_encoding=utf8'
            else:
                database_url += '&client_encoding=utf8'

            SQLALCHEMY_DATABASE_URI = database_url
            print(f"配置: 使用 PostgreSQL (Neon) 数据库")
        else:
            # 如果没有提供数据库连接字符串，使用一个安全的默认值或抛出错误
            SQLALCHEMY_DATABASE_URI = None
            print("警告: Vercel 环境下未找到数据库连接字符串")
    else:
        # 本地开发环境：使用 SQLite
        # 确保 instance 目录存在
        db_dir = os.path.join(basedir, 'instance')
        os.makedirs(db_dir, exist_ok=True)

        # 构建 SQLite 数据库路径
        db_path = os.path.join(db_dir, 'local.db')
        # 将 Windows 反斜杠替换为正斜杠，SQLite URI 需要这种格式
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path.replace('\\', '/')
        print(f"配置: 使用本地 SQLite 数据库 ({db_path})")

    # SQLAlchemy 配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 邮件配置
    MAIL_SERVER = 'smtp.qiye.aliyun.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'postmaster@unichip.hk'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'unichip@233'
    MAIL_DEFAULT_SENDER = MAIL_USERNAME