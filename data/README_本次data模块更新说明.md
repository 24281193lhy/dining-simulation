# data 模块更新说明

本次更新只围绕 `data/` 模块及其对应测试用例展开，目标是在不推翻项目结构的前提下，补齐数据持久化、统计分析、包级导出和测试兼容能力。

## 替换/新增文件

```text
data/
├── __init__.py
├── storage.py
└── statistics.py

tests/
├── test_storage.py
└── test_statistics.py
```

## 使用方式

把压缩包中的 `data/` 目录复制到项目根目录，覆盖原来的 `data/` 目录即可。

如果也想同步测试，请把压缩包中的 `tests/test_storage.py` 和 `tests/test_statistics.py` 覆盖到项目原来的 `tests/` 目录。

## 验证命令

在项目根目录执行：

```bash
python -m pytest tests/test_storage.py tests/test_statistics.py -q
```

本地独立验证结果：

```text
12 passed
```
