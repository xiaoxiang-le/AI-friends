# 历史资料索引

此目录保存学习、环境和交付快照，不作为当前安装或生产部署步骤。最新入口为[README](../../README.md)，功能定义为[PRODUCT](../PRODUCT.md)，测试证据为[ACCEPTANCE](../ACCEPTANCE.md)。历史快照中的模型、工具版本、域名、绝对路径及命令可能失效。

| 资料 | 内容 |
|---|---|
| [旧本地运行记录](LOCAL-RUN-2026-10-10.md) | 当次 DeepSeek/阿里云配置示例与验收补充 |
| [历史交付清单](COMMITS-2026-10-11.md) | 当次17个功能提交及验证边界 |
| [课程笔记](lessons/) | 原 Lessons 目录的课程1至7与3.5笔记 |
| [根目录环境快照](environments/root-requirements.txt) | 原根 requirements.txt，不用于安装 |
| [后端环境快照](environments/backend-requirements.txt) | 原 backend/requirements.txt，不用于安装 |

历史环境清单保留其原始版本，可能包含当前不用的工具或不适用于其他平台的包；当前运行依赖仅以根目录 `requirements-runtime.txt` 为准。非容器部署备选配置在[deploy/legacy](../../deploy/legacy/)，容器配置在[docker](../../docker/)。
