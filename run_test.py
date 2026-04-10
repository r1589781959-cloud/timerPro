#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
编码修复版测试运行器
"""
import sys
import io

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 导入并执行原测试脚本
exec(open('全系统计费模式完整测试.py', encoding='utf-8').read())
