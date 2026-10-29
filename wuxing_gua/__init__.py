# -*- coding: utf-8 -*-
"""
wuxing_gua —— 「对称群能不能用」判据的零依赖命令行封装

一句话定位：
    在黑盒转移数据上、状态压缩之前，先判这个对称群能不能用；不能用就拒答。

  · 黑盒    ：只需要转移表或 (s,a,s',r) 采样，不看模型内部（采样版连完整转移表都不要）
  · 压缩前  ：判据在轨道压缩之前执行，是压缩的前置门禁
  · 可拒答  ：三态结论（放行 / 拒答 / 样本不足），绝不因为"没看出差异"就放行

零依赖：纯 Python 标准库。判据核心 import 自本项目的 src/ 研究代码
（experiments_p3 / experiments_p4 / cheap_check_sample / experiments_e1，
均为纯标准库、import 无副作用——重实验逻辑全部在各自 main() 内），
出处逐文件注明在对应模块文件头，未复制、未改写判据逻辑。

运行：python -X utf8 -m wuxing_gua <discover|check|check-sample|selftest|demo> ...
详见本包 README.md。
"""

import os
import sys

__version__ = "1.0.0"

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_HERE)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

if not os.path.isdir(SRC_DIR):
    raise ImportError(
        "wuxing_gua 依赖项目根下的 src/ 研究代码（experiments_p3.py / experiments_p4.py / "
        "cheap_check_sample.py / experiments_e1.py），未找到：%s" % SRC_DIR)

# 判据核心直接 import 复用 src/ 研究实现。在 import 它们之前先禁止写字节码缓存，
# 保证研究目录（src/）不被本工具的运行改动（红线：不修改任何既有文件）。
sys.dont_write_bytecode = True
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
