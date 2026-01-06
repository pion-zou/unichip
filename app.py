import os
import sys

# 修复路径问题
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, CSRFError
from wtforms import StringField, IntegerField, TextAreaField, PasswordField, EmailField, FloatField
from wtforms.validators import DataRequired, Email, NumberRange
from flask_babel import Babel, gettext as _

app = Flask(__name__)

# 设置基本配置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# 尝试从 config.py 导入更多配置
try:
    from config import Config

    app.config.from_object(Config)
    print("配置: 已加载 config.py 配置")

except ImportError as e:
    print(f"警告: 未找到config.py，错误: {e}")
    print("警告: 使用硬编码默认配置")

    # 数据库配置
    database_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    if database_url:
        print(f"从环境变量获取数据库URL: {database_url[:50]}...")
        # 移除 sslmode 参数
        if 'sslmode=require' in database_url:
            database_url = database_url.replace('sslmode=require', '')
            database_url = database_url.replace('??', '?').rstrip('?')
            print("已移除 sslmode=require 参数")

        # 添加 pg8000 驱动
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+pg8000://', 1)
        elif database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql+pg8000://', 1)

        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_recycle': 300,
            'pool_pre_ping': True,
            'connect_args': {'timeout': 10}
        }
        print("配置: 使用环境变量中的 PostgreSQL 数据库")
    else:
        print("警告: 未找到数据库连接字符串，使用本地 SQLite")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/local.db'
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 邮件配置
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', '')

# 初始化 Babel - Flask-Babel 4.0.0 的正确方式
babel = Babel(app)


@babel.localeselector
def get_locale():
    # 1. 从 session 获取
    if 'language' in session and session['language'] in app.config['BABEL_SUPPORTED_LOCALES']:
        return session['language']
    # 2. 从 URL 参数获取
    lang = request.args.get('lang')
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        return lang
    # 3. 从浏览器请求头获取
    return request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES']) or 'en'


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


class EmailCC(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class EmailSettingForm(FlaskForm):
    email = EmailField('接收邮件的邮箱', validators=[DataRequired(), Email()])
    cc_email = StringField('抄送邮箱（多个用逗号分隔）')


class EmailCCForm(FlaskForm):
    email = EmailField('抄送邮箱', validators=[DataRequired(), Email()])


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

            # 检查是否有示例抄送邮箱数据
            if EmailCC.query.count() == 0:
                # 可以添加一些示例抄送邮箱
                sample_cc_emails = [
                    EmailCC(email='backup1@example.com', is_active=True),
                    EmailCC(email='backup2@example.com', is_active=True),
                ]
                for cc_email in sample_cc_emails:
                    db.session.add(cc_email)
                db.session.commit()
                print("已添加示例抄送邮箱数据")

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


def get_email_cc_list():
    """获取所有激活的抄送邮箱"""
    try:
        cc_emails = EmailCC.query.filter_by(is_active=True).all()
        return [cc.email for cc in cc_emails]
    except Exception:
        return []


# 发送联系邮件
def send_contact_email(contact):
    """
    使用阿里云邮件推送 API 发送联系表单邮件，包含抄送功能
    """
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_dm20151123 import client as dm_client
    from alibabacloud_dm20151123 import models as dm_models
    from alibabacloud_tea_util import models as util_models
    import json

    recipient = get_email_recipient()
    cc_emails = get_email_cc_list()

    subject = f'芯片查询 - 来自 {contact.company} 的 {contact.name}'
    html_body = f""" 新的联系信息：<br>

公司名: {contact.company}<br>
姓名: {contact.name}<br>
邮箱: {contact.email}<br>
电话: {contact.phone}<br>
留言: {contact.message}<br>
提交时间: {contact.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""

    try:
        config = open_api_models.Config(
            access_key_id=app.config['ALIYUN_ACCESS_KEY_ID'],
            access_key_secret=app.config['ALIYUN_ACCESS_KEY_SECRET'],
        )
        config.endpoint = 'dm.aliyuncs.com'
        client = dm_client.Client(config)

        request = dm_models.SingleSendMailRequest()
        request.account_name = app.config['ALIYUN_ACCOUNT_NAME']
        request.address_type = 1
        request.reply_to_address = False

        # 构建收件人列表：主收件人 + 抄送邮箱
        to_address_list = [recipient] + cc_emails
        request.to_address = ",".join(to_address_list)  # 用逗号分隔多个收件人

        request.subject = subject
        request.html_body = html_body
        request.from_alias = app.config.get('ALIYUN_FROM_ALIAS', '')

        runtime = util_models.RuntimeOptions()
        response = client.single_send_mail_with_options(request, runtime)

        print(f"[阿里云邮件推送] 邮件发送成功！收件人: {len(to_address_list)}个，RequestId: {response.body.request_id}")
        return True

    except Exception as e:
        print(f"[阿里云邮件推送] 邮件发送失败: {str(e)}")
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
    return render_template('index.html', search_form=search_form, contact_form=contact_form, get_locale=get_locale)

# 在app.py现有路由后添加以下代码
# 1. ABOUT US 页面路由
@app.route('/about')
def about():
    search_form = SearchForm()  # 复用搜索表单（若页面需要）
    contact_form = ContactForm()  # 复用联系表单（若页面需要）
    return render_template('about.html', search_form=search_form, contact_form=contact_form, get_locale=get_locale)

# 2. LINE CARD 页面路由
@app.route('/line-card')
def line_card():
    search_form = SearchForm()
    contact_form = ContactForm()
    return render_template('line-card.html', search_form=search_form, contact_form=contact_form, get_locale=get_locale)

# 3. QUALITY CONTROL 页面路由
@app.route('/quality-control')
def quality_control():
    search_form = SearchForm()
    contact_form = ContactForm()
    return render_template('quality-control.html', search_form=search_form, contact_form=contact_form, get_locale=get_locale)

# 4. CONTACT US 页面路由
@app.route('/contact')
def contact_page():  # 注意：原已有/contact POST路由，这里用GET渲染页面，避免冲突
    search_form = SearchForm()
    contact_form = ContactForm()
    return render_template('contact.html', search_form=search_form, contact_form=contact_form, get_locale=get_locale)


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
            # 更新主收件邮箱
            setting = Setting.query.filter_by(key='email_recipient').first()
            if not setting:
                setting = Setting(key='email_recipient', value=form.email.data)
                db.session.add(setting)
            else:
                setting.value = form.email.data

            # 处理批量添加抄送邮箱
            if form.cc_email.data:
                cc_emails = [email.strip() for email in form.cc_email.data.split(',') if email.strip()]
                for email in cc_emails:
                    # 验证邮箱格式
                    if '@' in email and '.' in email:
                        # 检查是否已存在
                        existing = EmailCC.query.filter_by(email=email).first()
                        if not existing:
                            cc_email = EmailCC(email=email)
                            db.session.add(cc_email)

            db.session.commit()
            return jsonify({'message': '邮箱设置更新成功'})
        except Exception as e:
            print(f"更新邮箱设置错误: {e}")
            return jsonify({'error': '数据库操作失败'}), 500
    else:
        return jsonify({'error': '表单验证失败', 'details': form.errors}), 400


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


# 添加一个健康检查端点，供 Vercel 使用
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': '应用运行正常'})


@app.route('/set_language/<lang>')
def set_language(lang):
    supported_locales = app.config.get('BABEL_SUPPORTED_LOCALES', ['zh', 'en'])
    if lang in supported_locales:
        session['language'] = lang
    return redirect(request.referrer or url_for('index'))


@app.route('/admin/email/cc', methods=['GET', 'POST'])
def manage_email_cc():
    """管理抄送邮箱"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未授权'}), 401

    if request.method == 'GET':
        try:
            cc_emails = EmailCC.query.order_by(EmailCC.created_at.desc()).all()
            return jsonify({
                'cc_emails': [cc.to_dict() for cc in cc_emails]
            })
        except Exception as e:
            print(f"获取抄送邮箱错误: {e}")
            return jsonify({'error': '获取数据失败'}), 500

    elif request.method == 'POST':
        form = EmailCCForm()
        if form.validate_on_submit():
            try:
                # 检查邮箱是否已存在
                existing = EmailCC.query.filter_by(email=form.email.data).first()
                if existing:
                    return jsonify({'error': '该邮箱已存在'}), 400

                cc_email = EmailCC(email=form.email.data)
                db.session.add(cc_email)
                db.session.commit()
                return jsonify({'message': '抄送邮箱添加成功', 'cc_email': cc_email.to_dict()})
            except Exception as e:
                print(f"添加抄送邮箱错误: {e}")
                return jsonify({'error': '数据库操作失败'}), 500
        else:
            return jsonify({'error': '表单验证失败', 'details': form.errors}), 400


@app.route('/admin/email/cc/<int:id>', methods=['PUT', 'DELETE'])
def email_cc_detail(id):
    """更新或删除抄送邮箱"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未授权'}), 401

    try:
        cc_email = EmailCC.query.get_or_404(id)
    except Exception:
        return jsonify({'error': '抄送邮箱未找到'}), 404

    if request.method == 'PUT':
        # 切换激活状态
        try:
            data = request.get_json()
            if 'is_active' in data:
                cc_email.is_active = data['is_active']
                db.session.commit()
                return jsonify({'message': '状态更新成功', 'cc_email': cc_email.to_dict()})
            else:
                return jsonify({'error': '缺少必要参数'}), 400
        except Exception as e:
            print(f"更新抄送邮箱错误: {e}")
            return jsonify({'error': '更新失败'}), 500

    elif request.method == 'DELETE':
        try:
            db.session.delete(cc_email)
            db.session.commit()
            return jsonify({'message': '抄送邮箱删除成功'})
        except Exception as e:
            print(f"删除抄送邮箱错误: {e}")
            return jsonify({'error': '删除失败'}), 500


if __name__ == '__main__':
    # 本地开发时运行
    import sys
    print(f"Python版本: {sys.version}")
    print("启动Flask应用...")
    port = int(os.environ.get('PORT', 5000))
    print(f"监听端口: {port}")
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=True)
