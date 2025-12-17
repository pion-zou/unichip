# test_translation_load.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, session
from flask_babel import Babel, gettext as _
import gettext

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test'
app.config['BABEL_DEFAULT_LOCALE'] = 'zh'
app.config['BABEL_SUPPORTED_LOCALES'] = ['zh', 'en', 'fr', 'ja']
app.config['BABEL_TRANSLATION_DIRECTORIES'] = './translations'

babel = Babel(app)


@babel.localeselector
def get_locale():
    if 'language' in session:
        return session['language']
    return 'zh'


# 测试不同语言的翻译
with app.app_context():
    # 设置session
    with app.test_request_context():
        test_cases = [
            ('zh', '电子芯片库存查询系统'),
            ('en', 'Electronic Chip Inventory Query System'),
            ('fr', 'Système de Requête d\'Inventaire de Puce Électronique'),
            ('ja', '電子チップ在庫照会システム')
        ]

        for lang, expected in test_cases:
            session['language'] = lang
            print(f"测试语言: {lang}")

            # 测试翻译
            translated = _('电子芯片库存查询系统')
            print(f"  期望: {expected}")
            print(f"  实际: {translated}")
            print(f"  匹配: {'✅' if translated == expected else '❌'}")
            print()