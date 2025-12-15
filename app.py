import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, CSRFError
from wtforms import StringField, IntegerField, TextAreaField, PasswordField, EmailField, FloatField
from wtforms.validators import DataRequired, Email, NumberRange

# 在 app.py 的配置部分简化处理

app = Flask(__name__)

# 尝试从config.py导入配置，如果失败则使用默认配置
try:
    app.config.from_object('config.Config')
    print("配置: 已加载 config.py 配置")

    # 打印数据库类型用于调试
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'postgresql+pg8000://' in db_uri:
        print("配置: 使用 PostgreSQL + pg8000 (Neon)")
    elif 'sqlite:///' in db_uri:
        print("配置: 使用本地 SQLite")
    else:
        print("配置: 未配置数据库")

except ImportError as e:
    print(f"警告: 未找到config.py，错误: {e}")
    print("警告: 使用硬编码默认配置")

    # 默认配置（仅在找不到config.py时使用）
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

    # 尝试从环境变量获取数据库连接
    database_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')

    if database_url:
        print(f"从环境变量获取数据库URL: {database_url[:50]}...")

        # 移除 sslmode 参数
        if 'sslmode=require' in database_url:
            database_url = database_url.replace('sslmode=require', '')
            # 清理多余的 ? 或 &
            database_url = database_url.replace('??', '?').rstrip('?')
            print("已移除 sslmode=require 参数")

        # 添加 pg8000 驱动
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+pg8000://', 1)
        elif database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql+pg8000://', 1)

        app.config['SQLALCHEMY_DATABASE_URI'] = database_url

        # 简单的引擎选项，不传递 ssl 参数
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_recycle': 300,
            'pool_pre_ping': True,
            'connect_args': {
                'timeout': 10,
            }
        }

        print("配置: 使用环境变量中的 PostgreSQL 数据库")
    else:
        print("警告: 未找到数据库连接字符串，使用本地 SQLite")
        # 本地开发时使用 SQLite
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/local.db'
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 邮件配置（可选）
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', '')

# 初始化扩展
csrf = CSRFProtect(app)

# 创建 SQLAlchemy 实例
db = SQLAlchemy()

# 初始化 SQLAlchemy 扩展
db.init_app(app)


# 数据库模型
class Chip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(64), index=True, unique=True, nullable=False)
    description = db.Column(db.String(200))
    stock = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)

    def to_dict(self):
        return {
            'id': self.id,
            'model': self.model,
            'description': self.description,
            'stock': self.stock,
            'price': self.price
        }


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)


class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)


# 表单定义
class SearchForm(FlaskForm):
    model = StringField('型号', validators=[DataRequired()])


class ContactForm(FlaskForm):
    company = StringField('公司名', validators=[DataRequired()])
    name = StringField('姓名', validators=[DataRequired()])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    phone = StringField('电话', validators=[DataRequired()])
    message = TextAreaField('留言')


class ChipForm(FlaskForm):
    model = StringField('型号', validators=[DataRequired()])
    description = StringField('描述', validators=[DataRequired()])
    stock = IntegerField('库存', validators=[DataRequired(), NumberRange(min=0)])
    price = FloatField('价格', validators=[DataRequired(), NumberRange(min=0)])


class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])


class EmailSettingForm(FlaskForm):
    email = EmailField('接收邮件的邮箱', validators=[DataRequired(), Email()])


# 应用初始化
with app.app_context():
    # 只有配置了数据库连接字符串时才尝试创建表
    if app.config.get('SQLALCHEMY_DATABASE_URI'):
        try:
            db.create_all()
            print("数据库表创建/检查完成。")

            # 确保有默认的邮箱设置
            if not Setting.query.filter_by(key='email_recipient').first():
                default_email = app.config.get('MAIL_USERNAME', '395610992@qq.com')
                setting = Setting(key='email_recipient', value=default_email)
                db.session.add(setting)
                db.session.commit()
                print("已创建默认邮箱设置。")

            # 添加一些示例芯片数据（如果数据库为空）
            if Chip.query.count() == 0:
                sample_chips = [
                    Chip(model='STM32F103C8T6', description='ARM Cortex-M3 32位MCU，64KB Flash，20KB RAM', stock=150,
                         price=12.5),
                    Chip(model='ATmega328P', description='8位AVR微控制器，32KB Flash，2KB SRAM', stock=300, price=3.2),
                    Chip(model='ESP32-WROOM-32', description='双核WiFi+蓝牙MCU模块，4MB Flash', stock=200, price=8.9),
                    Chip(model='Raspberry Pi Pico', description='RP2040双核ARM Cortex-M0+ MCU', stock=100, price=4.0),
                    Chip(model='MAX232', description='RS-232收发器芯片，用于串口通信', stock=500, price=1.5),
                ]
                for chip in sample_chips:
                    db.session.add(chip)
                db.session.commit()
                print("已添加示例芯片数据")
        except Exception as e:
            print(f"数据库初始化错误: {e}")
            print("警告: 数据库初始化失败，应用将继续运行但数据库功能可能不可用")
    else:
        print("警告: 未配置数据库连接，跳过表创建和数据初始化。")


# 获取接收邮件的地址
def get_email_recipient():
    try:
        setting = Setting.query.filter_by(key='email_recipient').first()
        return setting.value if setting else app.config.get('MAIL_USERNAME', '395610992@qq.com')
    except Exception:
        return app.config.get('MAIL_USERNAME', '395610992@qq.com')


# 发送联系邮件
def send_contact_email(contact):
    """
    使用阿里云邮件推送 API 发送联系表单邮件（针对 v0.4.2 修正版）
    """
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_dm20151123 import client as dm_client
    from alibabacloud_dm20151123 import models as dm_models
    # 1. 修正：从 alibabacloud_tea_util 导入 RuntimeOptions
    from alibabacloud_tea_util import models as util_models
    import json

    recipient = get_email_recipient()
    subject = f'芯片查询 - 来自 {contact.company} 的 {contact.name}'
    html_body = f""" 新的联系信息：<br>

公司名: {contact.company}<br>
姓名: {contact.name}<br>
邮箱: {contact.email}<br>
电话: {contact.phone}<br>
留言: {contact.message}<br>
提交时间: {contact.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""  # 这里保留您之前编写的HTML邮件正文（请勿删除或修改）

    try:
        # 1. 使用新版的Config和Client初始化
        config = open_api_models.Config(
            access_key_id=app.config['ALIYUN_ACCESS_KEY_ID'],
            access_key_secret=app.config['ALIYUN_ACCESS_KEY_SECRET'],
            # 修正：region_id 对于邮件推送服务不是必须的，但可以保留
            # region_id=app.config.get('ALIYUN_REGION_ID', 'cn-hangzhou')
        )
        config.endpoint = 'dm.aliyuncs.com'
        client = dm_client.Client(config)

        # 2. 构建新版API请求
        request = dm_models.SingleSendMailRequest()
        request.account_name = app.config['ALIYUN_ACCOUNT_NAME']  # 发信地址
        request.address_type = 1  # 1: 发信地址
        request.reply_to_address = False
        request.to_address = recipient
        request.subject = subject
        request.html_body = html_body
        request.from_alias = app.config.get('ALIYUN_FROM_ALIAS', '')  # 发信人昵称

        # 3. 创建RuntimeOptions（可选，用于设置超时等）
        runtime = util_models.RuntimeOptions()
        # 您可以在此设置运行时参数，例如：
        # runtime.read_timeout = 10000  # 读取超时10秒
        # runtime.connect_timeout = 5000 # 连接超时5秒

        # 4. 发送请求（传入 runtime）
        response = client.single_send_mail_with_options(request, runtime)

        # 5. 打印成功日志
        print(f"[阿里云邮件推送] 邮件发送成功！RequestId: {response.body.request_id}")
        return True

    except Exception as e:
        # 详细打印错误信息，便于调试
        print(f"[阿里云邮件推送] 邮件发送失败: {str(e)}")
        # 关键：即使邮件发送失败，也不影响主业务流程，依然返回True
        return True

# CSRF错误处理
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return jsonify({'error': 'CSRF验证失败，请刷新页面重试'}), 400


# 路由
@app.route('/')
def index():
    search_form = SearchForm()
    contact_form = ContactForm()
    return render_template('index.html', search_form=search_form, contact_form=contact_form)


@app.route('/search', methods=['POST'])
def search():
    form = SearchForm()

    # 如果是表单提交（带CSRF令牌）
    if form.validate_on_submit():
        model = form.model.data.strip()
    else:
        # 尝试从JSON中获取（用于API调用）
        try:
            if request.is_json:
                data = request.get_json()
                model = data.get('model', '').strip()
            else:
                # 尝试从表单数据中获取（不带CSRF的情况）
                model = request.form.get('model', '').strip()
        except:
            model = ''

    if not model:
        return jsonify({'error': '请输入有效的芯片型号'}), 400

    # 模糊查询，不区分大小写
    try:
        chip = Chip.query.filter(Chip.model.ilike(f'%{model}%')).first()
        if chip:
            return jsonify(chip.to_dict())
        else:
            return jsonify({'error': f'未找到型号包含"{model}"的芯片'}), 404
    except Exception as e:
        print(f"数据库查询错误: {e}")
        return jsonify({'error': '数据库查询失败，请稍后重试'}), 500


@app.route('/contact', methods=['POST'])
def contact():
    # 对于联系表单，我们稍微宽松一点，允许不带CSRF的提交
    try:
        if request.is_json:
            data = request.get_json()
            contact_record = Contact(
                company=data.get('company', ''),
                name=data.get('name', ''),
                email=data.get('email', ''),
                phone=data.get('phone', ''),
                message=data.get('message', '')
            )
        else:
            form = ContactForm()
            if form.validate_on_submit():
                contact_record = Contact(
                    company=form.company.data,
                    name=form.name.data,
                    email=form.email.data,
                    phone=form.phone.data,
                    message=form.message.data
                )
            else:
                # 即使表单验证失败，也尝试获取数据
                contact_record = Contact(
                    company=request.form.get('company', ''),
                    name=request.form.get('name', ''),
                    email=request.form.get('email', ''),
                    phone=request.form.get('phone', ''),
                    message=request.form.get('message', '')
                )

        # 检查必要字段
        if not contact_record.name or not contact_record.email:
            return jsonify({'error': '姓名和邮箱是必填项'}), 400

        db.session.add(contact_record)
        db.session.commit()

        # 尝试发送邮件
        send_contact_email(contact_record)

        return jsonify({'message': '信息已提交，我们会尽快联系您'})
    except Exception as e:
        print(f"联系表单错误: {e}")
        return jsonify({'message': '信息已提交，我们会尽快处理'})  # 即使出错也返回成功


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        # 简单的硬编码认证，实际应用中应使用更安全的方式
        if form.username.data == 'admin' and form.password.data == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('用户名或密码错误', 'danger')
    return render_template('login.html', form=form)


@app.route('/admin')
def admin_dashboard():
    # 检查是否已登录
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    try:
        chips = Chip.query.all()
    except Exception:
        chips = []

    email_form = EmailSettingForm()
    try:
        setting = Setting.query.filter_by(key='email_recipient').first()
        if setting:
            email_form.email.data = setting.value
    except Exception:
        pass

    return render_template('admin.html', chips=chips, email_form=email_form)


@app.route('/admin/chip/add', methods=['POST'])
def add_chip():
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未授权'}), 401

    form = ChipForm()
    if form.validate_on_submit():
        try:
            # 检查型号是否已存在
            if Chip.query.filter_by(model=form.model.data).first():
                return jsonify({'error': '该型号已存在'}), 400

            chip = Chip(
                model=form.model.data,
                description=form.description.data,
                stock=form.stock.data,
                price=form.price.data
            )
            db.session.add(chip)
            db.session.commit()
            return jsonify({'message': '芯片添加成功', 'chip': chip.to_dict()})
        except Exception as e:
            print(f"添加芯片错误: {e}")
            return jsonify({'error': '数据库操作失败'}), 500
    else:
        errors = []
        for field, errs in form.errors.items():
            for err in errs:
                errors.append(f"{field}: {err}")
        return jsonify({'error': '表单验证失败', 'details': errors}), 400


@app.route('/admin/chip/<int:id>', methods=['GET'])
def get_chip(id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未授权'}), 401

    try:
        chip = Chip.query.get_or_404(id)
        return jsonify(chip.to_dict())
    except Exception as e:
        print(f"获取芯片错误: {e}")
        return jsonify({'error': '数据库操作失败'}), 500


@app.route('/admin/chip/update/<int:id>', methods=['POST'])
def update_chip(id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未授权'}), 401

    try:
        chip = Chip.query.get_or_404(id)
    except Exception:
        return jsonify({'error': '芯片未找到'}), 404

    form = ChipForm()
    if form.validate_on_submit():
        try:
            # 检查型号是否已被其他芯片使用
            existing = Chip.query.filter(Chip.model == form.model.data, Chip.id != id).first()
            if existing:
                return jsonify({'error': '该型号已存在'}), 400

            chip.model = form.model.data
            chip.description = form.description.data
            chip.stock = form.stock.data
            chip.price = form.price.data
            db.session.commit()
            return jsonify({'message': '芯片更新成功', 'chip': chip.to_dict()})
        except Exception as e:
            print(f"更新芯片错误: {e}")
            return jsonify({'error': '数据库操作失败'}), 500
    else:
        errors = []
        for field, errs in form.errors.items():
            for err in errs:
                errors.append(f"{field}: {err}")
        return jsonify({'error': '表单验证失败', 'details': errors}), 400


@app.route('/admin/chip/delete/<int:id>', methods=['POST'])
def delete_chip(id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未授权'}), 401

    try:
        chip = Chip.query.get_or_404(id)
        db.session.delete(chip)
        db.session.commit()
        return jsonify({'message': '芯片删除成功'})
    except Exception as e:
        print(f"删除芯片错误: {e}")
        return jsonify({'error': '数据库操作失败'}), 500


@app.route('/admin/settings/email', methods=['POST'])
def update_email_setting():
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未授权'}), 401

    form = EmailSettingForm()
    if form.validate_on_submit():
        try:
            setting = Setting.query.filter_by(key='email_recipient').first()
            if not setting:
                setting = Setting(key='email_recipient', value=form.email.data)
                db.session.add(setting)
            else:
                setting.value = form.email.data
            db.session.commit()
            return jsonify({'message': '邮箱设置更新成功'})
        except Exception as e:
            print(f"更新邮箱设置错误: {e}")
            return jsonify({'error': '数据库操作失败'}), 500
    else:
        errors = []
        for field, errs in form.errors.items():
            for err in errs:
                errors.append(f"{field}: {err}")
        return jsonify({'error': '表单验证失败', 'details': errors}), 400


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


# 添加一个健康检查端点，供 Vercel 使用
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': '应用运行正常'})


# 删除这行，它是不必要的
# app = app

if __name__ == '__main__':
    # 本地开发时运行
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)