#!/usr/bin/env python3
"""
测试Flask应用初始化状态的脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

try:
    print("=== 测试Flask应用初始化 ===")
    print(f"Python版本: {sys.version}")
    print(f"当前目录: {os.getcwd()}")
    
    # 导入Flask应用
    from app import app
    
    print("✓ 成功导入Flask应用")
    
    # 检查配置
    print(f"✓ 应用配置加载成功")
    print(f"  - 支持的语言: {app.config.get('BABEL_SUPPORTED_LOCALES', '未配置')}")
    print(f"  - 默认语言: {app.config.get('BABEL_DEFAULT_LOCALE', '未配置')}")
    print(f"  - 翻译目录: {app.config.get('BABEL_TRANSLATION_DIRECTORIES', '未配置')}")
    
    # 检查路由
    print("✓ 检查应用路由")
    for rule in app.url_map.iter_rules():
        if 'language' in rule.rule:
            print(f"  - 语言相关路由: {rule.rule}")
    
    print("=== 测试完成 ===")
    print("应用初始化正常，没有发现明显错误。")
    
except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback
    traceback.print_exc()