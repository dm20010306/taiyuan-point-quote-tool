# RQ-016A Windows 路径审计与迁移门槛

日期：2026-10-02。状态：独立本地运行入口已建立，Windows 数据迁移与实机验收未完成；现有现场入口仍依赖 NAS。

当前 NAS 快照核对：正式项目 Markdown 3 份（安吉、江苏泰州、测试），共引用 4 张图纸，源 `data/uploads` 中对应的图纸文件均存在；品牌 Markdown 14 份。此前冲突项目 `10250b84ba044be6b7a456e052a534de` 只有历史备份，没有正式项目文件。

| 数据或操作 | 原 Windows 路径与 NAS 访问 | 本阶段路径 | 尚需核验 |
| --- | --- | --- | --- |
| 程序源码/API | NAS 工具目录直接运行 | 本地程序目录；启动器拒绝 UNC/映射网络盘 | 本地程序正式安装与更新由 E 阶段实现 |
| SQLite、导出 | `%LOCALAPPDATA%/TaiyuanPointQuote/data`，已有本地化 | 不变 | 现有缓存与知识库差异 |
| 项目、点位、报价 Markdown | `POINT_QUOTE_VAULT_ROOT` 指向 NAS | `%LOCALAPPDATA%/TaiyuanPointQuote/data/knowledge-base/06_客户档案/智能图纸与报价` | 缺失项目与历史版本核对 |
| 产品、品牌 Markdown | NAS `01_产品库` | 本地知识库同结构目录 | 有效产品 ID、品牌 ID 和目录归属 |
| Logo、产品图片 | NAS `09_附件` | 本地知识库同结构目录 | 文件数量、路径引用和实际可打开性 |
| 原始图纸、报价 Logo | NAS 工具 `data/uploads` | 本地 `data/uploads` | 数据库引用文件是否完整 |
| 网页运行副本、venv | `%USERPROFILE%/TaiyuanPointQuote`，网页从 NAS 镜像 | `%LOCALAPPDATA%/TaiyuanPointQuote`，网页从本地 app 镜像 | Windows 启动与 PDF 引擎 |
| Mac 使用 | NAS 主程序与主知识库 | 保持原有入口 | Mac/NAS 并行变更需在 C 阶段检查 |

`backend/app.py` 的 SQLite、uploads、exports，`backend/product_repository.py` 的产品/图片/Logo，以及 `backend/knowledge_repository.py` 的品牌/项目均从上述环境变量派生。普通业务请求只要使用新的本地启动链，就不会因这些路径访问 NAS。现有 `start-windows.bat` / `run-windows-api.bat` 仍访问 NAS，供迁移前过渡使用，不能算作 RQ-016A 已验收。旧自动 `knowledge_repository.sync()`、同步状态轮询、全局冲突阻断仍会在**本地知识库与本地 SQLite**之间运行；这是 RQ-016B 待停用的旧逻辑。项目内未发现 NAS 文件 watcher。

## 正式迁移前必须处理

1. 停止 Windows 工具，备份当前 Windows `%LOCALAPPDATA%/TaiyuanPointQuote/data` 和 NAS 知识库及旧 `data/uploads`。
2. 用户已明确选择当前 NAS 知识库为 Windows 本地数据来源。冲突项目 `10250b84ba044be6b7a456e052a534de` 的正式文件当前缺失；迁移后它不会自动出现，应在项目列表验收时核对。
3. 从 NAS 工具目录运行 `prepare-windows-local.bat`，脚本会暂存完整知识库副本、本工具程序与旧图纸，备份 Windows 原有 app/知识库/uploads/SQLite，再切换到本地。迁移完成后从本地 `start-windows-local.bat` 启动并核对项目、产品、品牌数量和文件引用。
4. 完成 Windows 实机断开 NAS 的首页、项目、点位、产品、品牌、报价、图纸、导出回归。未验证前不得发布 Stable。

本阶段的一次性迁移脚本只用于用户选定的当前知识库初始化。日常“上传备份到 NAS”与“从 NAS 恢复到本地”的差异预览、自动备份及确认属于 RQ-016C/D；迁移脚本不能代替它们。
