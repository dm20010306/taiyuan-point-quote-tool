# RQ-017C 程序与数据分离

日期：2026-10-02。状态：组包与启动代码已实现；Portable 已切断实时知识库同步；Windows 运行时尚未制作和实机验证，暂不发布。

## 包目录

```text
智能图纸报价工具/
  app/                         # 后端、静态网页、模板与版本文件
    backend/
    frontend/dist/
    assets/
  runtime/                     # 必须完整携带 Windows 原生运行依赖
    python/python.exe          # Python 及下列项目运行包
    python/Lib/site-packages/  # FastAPI、Uvicorn、Pillow、PyMuPDF 等
    node/node.exe              # Node.js，用于报价 V2 PDF 渲染
    node/node_modules/playwright/
    node/node_modules/playwright-core/
    browsers/                  # 与 Playwright 版本匹配的 Chromium chrome.exe
  data/                         # 当前知识库副本、uploads、可重建缓存
  config/settings.json
  backups/app/
  backups/data/
  version.json
  start-portable-windows.bat
```

Portable 模式下 FastAPI 从 `app/frontend/dist/` 同端口提供网页和 `/api`，网页运行不再启动 Vite。正式包必须把 Python、Node、Playwright、Chromium 和 Python 依赖放在 `runtime/`；最终用户不需要安装 Python 或 Node。`start-portable-windows.bat` 验证包结构、启动包内 API 并打开首页；`run-portable-api.bat` 仅调用包内运行时。API 和网页默认只监听 `127.0.0.1:8000`。开发目录继续使用 Vite 热更新。

Python 运行依赖至少包括 `fastapi`、`uvicorn`、`python-multipart`、`Pillow`、`PyMuPDF`、`openpyxl`、`reportlab` 和 `PyYAML`。Node 运行依赖包括 Node.js 可执行文件、`playwright`、`playwright-core` 与匹配版本的 Windows Chromium。`httpx`、`pytest` 和前端构建依赖只用于开发/验证，不进入用户运行时。

Portable 与传统 NAS 开发模式分支隔离。Portable 启动时只从当前包内 `data/` Markdown 恢复 SQLite 索引；项目业务修改直接写入本地项目 Markdown；产品文件由产品仓库直接写本地 `data/`。Portable 请求不调用 `knowledge_repository.sync()`，不创建后台同步任务，不检查 `SYNC_CONFLICT`，同步状态接口返回 `local`，前端不轮询同步状态或提供重试按钮。项目代码中没有 NAS 文件 watcher。Portable 模式的数据读写路径由包根目录解析，外部 `POINT_QUOTE_*` 环境变量不会改变 `data/` 根目录。

## 组包方式

先构建前端，再提供 Windows 运行时来源目录。该运行时必须包含可独立运行的 Windows Python 及项目依赖、Node、Playwright 和匹配的 Chromium；运行时构建本身需要在 Windows 环境准备，目前此环境没有经过 Windows 构建验证。随后运行：

```text
python tools/assemble_portable.py \
  --vault-source "知识库根目录" \
  --runtime-source "已准备好的 Windows runtime 来源目录" \
  --output "全新的工具包输出目录" \
  --channel beta --build 201
```

组包会把知识库根目录复制到 `data/`，排除当前工具源码、Git 元数据、回收站和 Obsidian 工作区缓存；再把原工具 `data/uploads/` 合并进 `data/uploads/`。同名但内容不同的图纸文件会令组包失败，避免覆盖。工具把输出先写到临时目录，完成后再整体改名。目标目录已存在时立即停止；现有 `data/`、`config/` 和 `backups/` 不会被覆盖。已有 `data/.meta.json` 原样保留。

组包脚本不会创建/升级已有安装，也不会下载运行时；它会验证运行时来源后复制到包内 `runtime/`。当前工作环境没有 Windows Python、Node 或 Chromium 运行时，尚不能生成完整包。正式包缺失前，不能把旧 `start-windows.bat` 或 `%LOCALAPPDATA%` 入口称为 Portable 启动方式。

## 验证与限制

- 自动化组包测试覆盖目录分离、原知识库和上传文件复制、数据版本元信息保留、目标已存在时拒绝覆盖，以及同名图纸冲突停止。
- Portable 临时包使用静态网页和 API 同端口启动测试；完整 Portable 路径及缓存重建测试继续通过。
- `backend/test_portable_data.py` 将旧同步引擎替换为调用即失败的哨兵；Portable 项目/品牌/产品/报价读写测试仍通过，证明运行时不经过实时同步、重试或冲突引擎。
- 3 条历史异步同步时序测试保留在开发模式测试中，改为显式触发重试后检查 Markdown 落盘；没有删除或伪装通过。它们覆盖传统开发模式，与 Portable 禁用实时同步的专项测试隔离。
- 本次仅在 macOS 验证组包逻辑，测试运行时是占位文件，没有生成 Windows 可执行包。Windows Python/Node 二进制、批处理、PowerShell、移动目录、断 NAS、PDF 导出都必须在 Windows 机器实际验证后才能发布。
- 用户验收清单中，自动化环境已覆盖首页/API、项目和点位读写、产品/品牌数据、报价金额、数据目录移动/缓存重建及 Excel 导出；Windows 双击启动、产品编辑界面、V2 PDF 导出、断 NAS、实际换盘符及文件夹移动均待 Windows 实机测试。

## Windows 正式包验收记录

| 项目 | 当前结果 |
| --- | --- |
| 1. 双击启动 | 未测；尚无含 Windows runtime 的工具包 |
| 2. 首页打开 | Mac 临时包通过同端口静态页面检查；Windows 未测 |
| 3. 项目列表读取 | Portable API 自动化通过；Windows 未测 |
| 4. 打开项目 | Portable API 自动化读取项目详情通过；Windows UI 未测 |
| 5. 添加点位 | Portable API 自动化通过；Windows UI 未测 |
| 6. 保存项目 | Portable 项目 Markdown 本地写入测试通过；Windows 未测 |
| 7. 产品库读取 | Portable API 自动化通过；Windows UI 未测 |
| 8. 产品修改 | Portable API 修改产品名称/价格并删除缓存后重新读取通过；完整产品编辑 UI 和 Windows 文件保存未测 |
| 9. 打开报价 | Portable API 自动化报价数据读取通过；Windows UI 未测 |
| 10. PDF 导出 | Windows Node/Playwright/Chromium 未打包，未测 |
| 11. 断开 NAS | Portable 路径隔离及无同步引擎测试通过；Windows 拔网/断 NAS 未测 |
| 12. 整包移动到其他盘符 | API 隔离测试移动了临时包目录；真实 Windows 盘符移动未测 |
| 13. data 不丢失 | 临时包删除 SQLite 并移动后由本地 Markdown/附件恢复通过；Windows 文件夹实测未测 |
| 14. 路径正确 | 路径解析专项和包根 data 隔离测试通过；Windows 启动后路径检查未测 |

因此目前还没有“Windows 实机通过”结果，也没有最终发布目录。正式包须在准备了 Windows 原生 runtime 后重新组装，并逐项完成 Windows 验收。
