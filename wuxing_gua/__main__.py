# -*- coding: utf-8 -*-
"""python -X utf8 -m wuxing_gua <子命令> 的入口。"""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
