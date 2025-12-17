# manual_extract.py
import os
import re
from pathlib import Path


def extract_from_file(file_path):
    """从文件中提取翻译字符串"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配 {{ _('...') }} 模式
    pattern1 = r'\{\{\s*_\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)\s*\}\}'
    # 匹配 {{ _("...") }} 模式
    pattern2 = r'\{\{\s*_\s*\(\s*"([^"]+)"\s*\)\s*\}\}'
    # 匹配 {{ _('...') }} 单引号模式
    pattern3 = r'\{\{\s*_\s*\(\s*\'([^\']+)\'\s*\)\s*\}\}'

    all_matches = []
    for pattern in [pattern1, pattern2, pattern3]:
        matches = re.findall(pattern, content)
        all_matches.extend(matches)

    return set(all_matches)


def create_pot_file(translations, output_file='messages.pot'):
    """创建.pot文件"""
    pot_content = '''# Translations template for PROJECT.
# Copyright (C) 2023 ORGANIZATION
# This file is distributed under the same license as the PROJECT project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2023.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: PROJECT VERSION\\n"
"Report-Msgid-Bugs-To: EMAIL@ADDRESS\\n"
"POT-Creation-Date: 2023-12-16 18:00+0800\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=utf-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Generated-By: Babel 2.17.0\\n"

'''

    for text in sorted(translations):
        pot_content += f'\n#: templates/index.html\n'
        pot_content += f'msgid "{text}"\n'
        pot_content += f'msgstr ""\n'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pot_content)

    print(f"已创建 {output_file}，包含 {len(translations)} 个翻译字符串")


def main():
    # 查找所有HTML文件
    translations = set()

    # 检查index.html
    index_file = Path('templates/index.html')
    if index_file.exists():
        print(f"处理文件: {index_file}")
        file_translations = extract_from_file(index_file)
        translations.update(file_translations)
        print(f"  找到 {len(file_translations)} 个翻译字符串")

    # 检查其他HTML文件
    templates_dir = Path('templates')
    for html_file in templates_dir.glob('*.html'):
        if html_file.name != 'index.html':
            print(f"处理文件: {html_file}")
            file_translations = extract_from_file(html_file)
            translations.update(file_translations)
            print(f"  找到 {len(file_translations)} 个翻译字符串")

    # 显示所有找到的翻译
    print(f"\n总共找到 {len(translations)} 个唯一的翻译字符串:")
    for i, text in enumerate(sorted(translations), 1):
        print(f"{i:3}. '{text}'")

    # 创建.pot文件
    if translations:
        create_pot_file(translations)

        # 初始化翻译
        init_translations()
    else:
        print("未找到翻译字符串")


def init_translations():
    """初始化翻译文件"""
    if not Path('messages.pot').exists():
        print("错误: messages.pot 文件不存在")
        return

    # 创建translations目录
    os.makedirs('translations', exist_ok=True)

    # 初始化英文翻译
    print("\n初始化英文翻译...")
    os.system('pybabel init -i messages.pot -d translations -l en')

    print("\n初始化中文翻译...")
    os.system('pybabel init -i messages.pot -d translations -l zh')

    print("\n初始化法文翻译...")
    os.system('pybabel init -i messages.pot -d translations -l fr')

    print("\n初始化日文翻译...")
    os.system('pybabel init -i messages.pot -d translations -l ja')

    print("\n翻译文件已创建在 translations/ 目录中")
    print("请编辑 translations/*/LC_MESSAGES/messages.po 文件添加翻译")
    print("然后运行: pybabel compile -d translations")


if __name__ == '__main__':
    main()