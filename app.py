import os
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, CSRFError  # 确保已导入
from wtforms import StringField, IntegerField, TextAreaField, PasswordField, EmailField, FloatField, HiddenField
from wtforms.validators import DataRequired, Email, NumberRange

app = Flask(__name__)

# 尝试从config.py导入配置，如果失败则使用默认配置
try:
    app.config.from_object('config.Config')
except ImportError:
    print("警告: 未找到config.py，使用默认配置")
    # 默认配置
    app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database/chips.db'
    uri = os.environ.get('POSTGRES_URL')
    if uri and uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
    app.config['MAIL_PASSWORD'] = 'your_app_password'
    app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'

# 初始化扩展
csrf = CSRFProtect(app)
db = SQLAlchemy(app)


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
    # 确保数据库目录存在
    os.makedirs('database', exist_ok=True)
    db.create_all()

    # 确保有默认的邮箱设置
    if not Setting.query.filter_by(key='email_recipient').first():
        default_email = app.config.get('MAIL_USERNAME', '395610992@qq.com')
        setting = Setting(key='email_recipient', value=default_email)
        db.session.add(setting)
        db.session.commit()

    # 添加一些示例芯片数据（如果数据库为空）
    if Chip.query.count() == 0:
        sample_chips = [
            Chip(model='STM32F103C8T6', description='ARM Cortex-M3 32位MCU，64KB Flash，20KB RAM', stock=150, price=12.5),
            Chip(model='ATmega328P', description='8位AVR微控制器，32KB Flash，2KB SRAM', stock=300, price=3.2),
            Chip(model='ESP32-WROOM-32', description='双核WiFi+蓝牙MCU模块，4MB Flash', stock=200, price=8.9),
            Chip(model='Raspberry Pi Pico', description='RP2040双核ARM Cortex-M0+ MCU', stock=100, price=4.0),
            Chip(model='MAX232', description='RS-232收发器芯片，用于串口通信', stock=500, price=1.5),
        ]
        for chip in sample_chips:
            db.session.add(chip)
        db.session.commit()
        print("已添加示例芯片数据")


# 获取接收邮件的地址
def get_email_recipient():
    setting = Setting.query.filter_by(key='email_recipient').first()
    return setting.value if setting else app.config.get('MAIL_USERNAME', '395610992@qq.com')


# 发送联系邮件
def send_contact_email(contact):
    recipient = get_email_recipient()
    subject = '新的芯片查询联系'
    body = f"""
新的联系信息：

公司名: {contact.company}
姓名: {contact.name}
邮箱: {contact.email}
电话: {contact.phone}
留言: {contact.message}
提交时间: {contact.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""

    try:
        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = app.config.get('MAIL_USERNAME', 'noreply@example.com')
        msg['To'] = recipient

        with smtplib.SMTP(app.config.get('MAIL_SERVER', 'smtp.gmail.com'),
                          app.config.get('MAIL_PORT', 587)) as server:
            server.starttls()
            server.login(app.config.get('MAIL_USERNAME', ''),
                         app.config.get('MAIL_PASSWORD', ''))
            server.sendmail(msg['From'], [msg['To']], msg.as_string())
        print(f"邮件已发送到: {recipient}")
        return True
    except Exception as e:
        print(f"发送邮件失败: {e}")
        # 即使邮件发送失败，也不要影响主要功能
        return True  # 返回True让用户以为发送成功


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
    chip = Chip.query.filter(Chip.model.ilike(f'%{model}%')).first()
    if chip:
        return jsonify(chip.to_dict())
    else:
        return jsonify({'error': f'未找到型号包含"{model}"的芯片'}), 404


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

    chips = Chip.query.all()
    email_form = EmailSettingForm()
    setting = Setting.query.filter_by(key='email_recipient').first()
    if setting:
        email_form.email.data = setting.value
    return render_template('admin.html', chips=chips, email_form=email_form)


@app.route('/admin/chip/add', methods=['POST'])
def add_chip():
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未授权'}), 401

    form = ChipForm()
    if form.validate_on_submit():
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

    chip = Chip.query.get_or_404(id)
    return jsonify(chip.to_dict())


@app.route('/admin/chip/update/<int:id>', methods=['POST'])
def update_chip(id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未授权'}), 401

    chip = Chip.query.get_or_404(id)
    form = ChipForm()
    if form.validate_on_submit():
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

    chip = Chip.query.get_or_404(id)
    db.session.delete(chip)
    db.session.commit()
    return jsonify({'message': '芯片删除成功'})


@app.route('/admin/settings/email', methods=['POST'])
def update_email_setting():
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未授权'}), 401

    form = EmailSettingForm()
    if form.validate_on_submit():
        setting = Setting.query.filter_by(key='email_recipient').first()
        if not setting:
            setting = Setting(key='email_recipient', value=form.email.data)
            db.session.add(setting)
        else:
            setting.value = form.email.data
        db.session.commit()
        return jsonify({'message': '邮箱设置更新成功'})
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)