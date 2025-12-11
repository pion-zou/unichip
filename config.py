import os
from dotenv import load_dotenv

load_dotenv()

# 获取项目根目录的绝对路径
basedir = os.path.abspath(os.path.dirname(__file__))

# 确保数据库目录存在
db_dir = os.path.join(basedir, 'database')
os.makedirs(db_dir, exist_ok=True)

# 构建正确的SQLite数据库路径 (Windows需要特殊处理)
db_path = os.path.join(db_dir, 'chips.db')
# 将Windows反斜杠替换为正斜杠，SQLite URI需要这种格式
db_uri = 'sqlite:///' + db_path.replace('\\', '/')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or db_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = 'smtp.qiye.aliyun.com'  # 替换为您的SMTP服务器
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = ' postmaster@unichip.hk'  # 替换为您的邮箱
    MAIL_PASSWORD = 'unichip@233'  # 替换为您的邮箱密码
