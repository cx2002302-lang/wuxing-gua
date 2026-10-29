# -*- coding: utf-8 -*-
"""
errors.py —— 错误类型与退出码的映射约定

  InputError   → 退出码 3（输入或内部错误）：文件缺失 / JSON 解析失败 /
                 模型或样本不符合 README 输入格式 / 模型与群规模不一致
  GroupInvalid → 退出码 1（拒答：群不可用/非法）：群文件能解析、但内容不是
                 合法的置换群（元素不是双射、长度不一致、goals/n_actions 字段非法）

即：文件读不了算输入错误；读得进来但"这个群"本身不成立，按判据口径算拒答。
"""


class InputError(Exception):
    """输入错误（退出码 3）"""


class GroupInvalid(Exception):
    """群不可用/非法（退出码 1：拒答）"""
