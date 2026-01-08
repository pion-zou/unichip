import os
from dotenv import load_dotenv
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

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
            print(f"原始数据库URL: {database_url[:50]}...")

            # 解析 URL 以处理参数
            parsed = urlparse(database_url)

            # 解析查询参数
            query_params = parse_qs(parsed.query)

            # 移除 sslmode 参数，因为 pg8000 不接受它
            if 'sslmode' in query_params:
                print(f"移除 sslmode 参数: {query_params.get('sslmode', [''])[0]}")
                del query_params['sslmode']

            # 重建查询字符串
            new_query = urlencode(query_params, doseq=True)

            # 重建 URL，确保使用 pg8000 驱动
            if parsed.scheme == 'postgresql':
                scheme = 'postgresql+pg8000'
            elif parsed.scheme == 'postgres':
                scheme = 'postgresql+pg8000'
            else:
                scheme = parsed.scheme

            # 重建 URL
            database_url = urlunparse((
                scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))

            SQLALCHEMY_DATABASE_URI = database_url

            # 设置引擎选项
            # pg8000 默认会使用 SSL（如果服务器要求），我们不需要传递 ssl 参数
            SQLALCHEMY_ENGINE_OPTIONS = {
                'pool_recycle': 300,
                'pool_pre_ping': True,
                'connect_args': {
                    'timeout': 10,
                }
            }

            print(f"配置: 使用 PostgreSQL (Neon) 数据库")
            print(f"最终数据库URL: {database_url[:80]}...")
        else:
            # 如果没有提供数据库连接字符串，使用一个安全的默认值或抛出错误
            SQLALCHEMY_DATABASE_URI = None
            SQLALCHEMY_ENGINE_OPTIONS = {}
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

        # SQLite 不需要特殊引擎选项
        SQLALCHEMY_ENGINE_OPTIONS = {}
        print(f"配置: 使用本地 SQLite 数据库 ({db_path})")

    # SQLAlchemy 配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ====== 国际化配置 ======
    # Babel 配置
    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_SUPPORTED_LOCALES = ['zh', 'en', 'fr', 'ja', 'ru']
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(basedir, 'translations')  # 翻译文件目录

    # ====== 阿里云邮件推送 (DirectMail) 配置 ======
    # 请确保以下敏感信息通过环境变量设置，不要硬编码！
    ALIYUN_ACCESS_KEY_ID = os.environ.get('ALIYUN_ACCESS_KEY_ID')
    ALIYUN_ACCESS_KEY_SECRET = os.environ.get('ALIYUN_ACCESS_KEY_SECRET')
    # 地域ID，邮件推送服务通常为 `cn-hangzhou`
    ALIYUN_REGION_ID = 'cn-hangzhou'
    # 控制台中配置的**发信地址**，例如：no-reply@mail.unichip.hk
    ALIYUN_ACCOUNT_NAME = os.environ.get('ALIYUN_ACCOUNT_NAME', 'no-reply@mail.unichip.hk')
    # 发信人昵称（可选）
    ALIYUN_FROM_ALIAS = os.environ.get('ALIYUN_FROM_ALIAS', 'Unichip客户系统')
    # 邮件标签（可选，用于分类统计）
    ALIYUN_TAG_NAME = 'website_contact'
