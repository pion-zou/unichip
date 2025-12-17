# test_babel_extract.py
import os
import sys
from babel.messages.extract import extract_from_dir
from jinja2 import Environment, FileSystemLoader


def test_extraction():
    # 设置模板目录
    template_dir = 'templates'

    # 创建Jinja2环境
    env = Environment(loader=FileSystemLoader(template_dir))

    # 测试单个文件
    test_file = os.path.join(template_dir, 'index.html')

    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()

            # 手动查找翻译字符串
            import re
            pattern = r'\{\{\s*_\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)\s*\}\}'
            matches = re.findall(pattern, content)

            print(f"在 {test_file} 中找到 {len(matches)} 个翻译字符串:")
            for match in matches:
                print(f"  - '{match}'")
    else:
        print(f"文件 {test_file} 不存在")


if __name__ == '__main__':
    test_extraction()