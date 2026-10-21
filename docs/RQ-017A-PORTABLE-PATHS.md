# RQ-017A Portable 路径审计

日期：2026-10-02。状态：解析层已接入后端主要模块，正式工具包及 Windows 移动验收未完成。

## 目标目录与解析

```text
智能图纸报价工具/
  version.json
  app/backend/app.py
  app/assets/templates/
  runtime/
  data/01_产品库/
  data/06_客户档案/智能图纸与报价/
  data/09_附件/
  data/uploads/
  config/
  backups/
```

`backend/path_resolver.py` 从当前模块实际所在目录向上寻找 `version.json` 与 `app/backend/app.py`，因此移动整个目录后会在下次启动解析出新根目录。`data/` 同时是知识库根目录，旧有产品、品牌、项目和附件结构不变。旧开发目录找不到 Portable 标记时，仍使用现有环境变量和 NAS 路径；测试用独立 `POINT_QUOTE_DATA_DIR` 仍隔离到同级临时 vault。

业务数据中的文件引用应为相对路径。解析层将 `\\` 归一化为 `/`，拒绝 Windows 盘符、UNC、POSIX 绝对路径和 `..`。当前产品笔记的 `note_path`、图片名及项目快照中的图纸名均以相对路径保存；对正式项目和产品 Markdown 的文本扫描未发现机器绝对路径。

## 本阶段接入范围

| 模块 | 已统一解析的路径 |
| --- | --- |
| `backend/app.py` | app、SQLite 数据目录、uploads、exports |
| `backend/product_repository.py` | 产品知识库、产品图片、品牌 Logo |
| `backend/knowledge_repository.py` | 品牌与项目 Markdown、历史备份和冲突日志 |
| `backend/diagnostics.py` | 本地诊断日志 |
| `backend/pptx_export.py` | 程序内 PPTX 模板，旧路径作为兼容读取 |

## 尚未完成

- 现有 `prepare-windows-local.bat/.ps1` 与 `start-windows-local.bat` 固定使用 `%LOCALAPPDATA%`，不是最终 Portable 安装和启动入口。B/C 阶段需创建完整工具包并切换脚本。
- 还没有实际 `version.json`、`runtime/`、`config/` 与完整 `data/` 发布包；D～F 阶段的版本检查、更新、回退尚未实现。
- `dataVersion`、旧数据迁移和 Windows 换盘符/断 NAS 测试留待 G 阶段。当前 RQ-017 不得标记已解决。
