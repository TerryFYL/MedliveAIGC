# MCP 标准交互协议（v1）

本文件定义了在本项目中 Agent、Experts、Tools、LLM 代理与管线入口之间的统一交互协议。协议以最小但完整的“请求-响应”结构为核心，强调统一字段、可落地资源路径与稳健的容错与回退策略。

---

## 1. 目的与范围
- 统一所有角色的调用数据结构与约定，降低耦合与提升可维护性。
- 支持远端 OCR 服务与本地提取工具的无缝切换与回退。
- 支持端到端内容生成（Markdown + 图片），确保可重入与可追踪。

## 2. 角色定义
- Agent（命令行入口）：`mcp_generate_digest.py`
  - 负责解析 CLI 参数、组织 Experts/Tools/LLM 调用、落地最终产物。
- Experts（专家层，接口在 `framework_protocol.py`）：
  - IntentExpert
    - 方法：`identify(params)` → `{ "intents": [str], "confidence": float }`
    - 用途：解析任务文本，决定需要的步骤（当前为多任务场景入口）。
  - OrchestratorExpert
    - 方法：`orchestrate(params, tools)` → 标准响应（见第 3 节）
    - 远端优先，本地回退；异常与失败均捕获并有统一错误语义。
  - AutoInstallerExpert
    - 方法：`ensure(params)` → 标准响应
    - 用途：自动安装缺失依赖，保证运行环境。
  - OutputAssemblerExpert（实现于 `output_assembler.py`）
    - 方法：`compose(params)` → 标准响应
    - 负责将文本与图片组织为结构化 Markdown，必要时对 PDF 执行补充文本提取。
- Tools（工具层）：
  - 远端 OCR 工具：`dotsocr/remote_tools.py`
    - `call_pdf(params)` / `call_image(params)`，对接远端服务，落地产物并返回统一结构。
  - 本地 PDF 工具：`dotsocr/local_pdf_tool.py`
    - `call(params)`，在远端失败或异常时作为回退路径。
- LLM 代理：`llm_proxy.py`
  - 方法：`ask(params)`，统一封装模型与参数，返回文本与用量信息。

## 3. 消息模型（统一请求/响应）
- 请求（Request）：
  ```json
  {
    "name": "string",
    "version": "string",
    "params": {"key": "value"},
    "meta": {"trace_id": "uuid-string"}
  }
  ```
- 响应（Response）：
  ```json
  {
    "ok": true,
    "error": null,
    "data": {"key": "value"},
    "meta": {"duration_ms": 1234}
  }
  ```
- 字段约定：
  - `ok=true` 表示业务成功且 `data` 有效；`ok=false` 表示失败，`error` 必填。
  - `meta.trace_id` 由请求侧生成；`meta.duration_ms` 由响应侧计算（毫秒）。
  - 大对象（图片、文本）以“文件路径”形式在 `data` 中返回，避免传输二进制大对象。

## 4. 通用数据结构（跨层约定）
- PDF 提取结果（Tools → Orchestrator → OutputAssembler）：
  ```json
  {
    "images": ["E:/.../page1.png", "E:/.../page2.png"],
    "text_path": "E:/.../extract_text_local.txt"
  }
  ```
- 组装结果（OutputAssembler → Agent）：
  ```json
  {
    "output_md": "E:/.../指南解读_...md",
    "images": ["E:/.../page1.png", "E:/.../page2.png"]
  }
  ```
- 依赖安装结果（AutoInstaller → Agent/管线）：
  ```json
  {
    "installed": [["pymupdf", "ok"], ["PyPDF2", "installed"]]
  }
  ```

## 5. 调用流程（端到端管线）
- CLI 参数（Agent）：
  - `--pdf <pdf_path>`：输入 PDF 路径。
  - `--out_dir <out_dir>`：图片与中间文本输出目录。
  - `--output_md <markdown_path>`：最终 Markdown 输出路径。
  - `--dpi <int>`：提取图片的 DPI（默认 180-200）。
- 执行顺序：
  1) AutoInstallerExpert.ensure → 安装缺失依赖；
  2) OrchestratorExpert.orchestrate → 远端优先提取，失败/异常则本地回退；
  3) OutputAssemblerExpert.compose → 组织文本与图片，必要时补充 PDF 文本提取；
  4) 输出统一响应并落地资源（Markdown + 图片目录）。

## 6. 远端 OCR 服务协议（工具对接规范）
- 服务地址：`http://dots-ocr.mlproject.cn/extract`
- 任务类型：
  - PDF OCR：`task="pdf_ocr"`，上传 `pdf` 文件；支持 `dpi`、`image_extract` 参数。
  - Image OCR：`task="image_ocr"`，上传 `image` 文件。
- 响应形式：
  - JSON：`{"text": "...", "images": [{"filename": "...", "content": "..."}]}`
  - ZIP：打包图片与文本文件。
  - 纯文本：仅 OCR 文本内容。
- 工具适配策略（`remote_tools`）：
  - 无论响应形式如何，全部产物落地至 `out_dir`，返回 `images[]` 与 `text_path` 的统一结构。

## 7. 错误处理与回退策略
- 远端异常捕获（Orchestrator）：
  - 调用远端工具时 `try/except` 捕获网络/协议异常；返回 `ok=false` 携带 `error` 字段。
- 回退逻辑：
  - 远端 `ok=false` 或抛异常 → 调用 `local_pdf_tool.call` 执行；输出结构保持统一。
- 文本不足补救（Assembler）：
  - 若 `text_path` 缺失或文本不足，自动对 `pdf_path` 执行页文本提取，保障可以生成 Markdown。
- 依赖安装失败（AutoInstaller）：
  - 立即返回 `ok=false` 与错误信息；上层停止执行并提示。

## 8. 版本与扩展约定
- 名称与版本：
  - Agent：`"mcp_generate_digest"`（CLI 名称）
  - Experts：`intent_expert@v1`、`orchestrator@v1`、`autoinstaller@v1`、`output_assembler@v1`
  - Tools：`dotsocr_pdf@v1`（远端实现）、`local_pdf@v1`（本地实现）
- 追踪与审计：
  - 使用 `meta.trace_id` 对一次业务调用做端到端关联追踪。
- 可扩展参数：
  - `OutputAssembler.compose` 支持 `section_ranges`（如：`[[1,5],[6,10]]`）用于章节范围控制。
  - 可新增管线参数如 `--no_fallback`（禁用回退）、`--use_existing_images`（使用既有图片并跳过提取）。

## 9. 示例（请求/响应片段）
- Orchestrator 请求：
  ```json
  {
    "name": "orchestrator",
    "version": "v1",
    "params": {"pdf_path": "E:/.../guide.pdf", "out_dir": "E:/.../digest_images", "dpi": 180},
    "meta": {"trace_id": "b3e9..."}
  }
  ```
- Orchestrator 响应：
  ```json
  {
    "ok": true,
    "error": null,
    "data": {
      "images": ["E:/.../page1.png", "E:/.../page2.png"],
      "text_path": "E:/.../extract_text_local.txt"
    },
    "meta": {"duration_ms": 123456}
  }
  ```
- OutputAssembler 请求：
  ```json
  {
    "name": "output_assembler",
    "version": "v1",
    "params": {
      "pdf_path": "E:/.../guide.pdf",
      "text_path": "E:/.../extract_text_local.txt",
      "images": ["E:/.../page1.png"],
      "out_md_path": "E:/.../指南解读_...md",
      "section_ranges": [[1,5],[6,10]]
    },
    "meta": {"trace_id": "b3e9..."}
  }
  ```
- OutputAssembler 响应：
  ```json
  {
    "ok": true,
    "error": null,
    "data": {
      "output_md": "E:/.../指南解读_...md",
      "images": ["E:/.../page1.png"]
    },
    "meta": {"duration_ms": 98765}
  }
  ```
- LLM 代理请求与响应：
  ```json
  {
    "name": "llm_proxy",
    "version": "v1",
    "params": {
      "prompt": "请按第1-5页生成要点...",
      "system": "你是医学内容生成助手",
      "model": "gpt-4o-mini",
      "temperature": 0.2,
      "max_tokens": 2000
    },
    "meta": {"trace_id": "b3e9..."}
  }
  ```
  ```json
  {
    "ok": true,
    "error": null,
    "data": {
      "text": "生成内容...",
      "usage": {"prompt_tokens": 123, "completion_tokens": 456}
    },
    "meta": {"duration_ms": 2345}
  }
  ```

## 10. 兼容性与实现参考
- 远端测试脚本：`dotsocr/test_pdf_ocr.py`、`dotsocr/test_image_ocr.py`。
- 远端工具：`dotsocr/remote_tools.py`（`call_pdf`、`call_image`）。
- 本地工具：`dotsocr/local_pdf_tool.py`（`call`）。
- 协议工具方法：`framework_protocol.py` 中的 `make_request` / `make_response`。

## 11. 变更记录
- v1（当前）：初版协议，包含角色定义、统一消息模型、远端/本地工具对接、容错与回退策略、示例片段与扩展约定。

---

## 12. 附录：CLI 使用示例
```powershell
python E:\BaiduSyncdisk\博士后经历\内部0_AIGC平台搭建\04AIGCFrameWork\mcp_generate_digest.py \
  --pdf "E:\\...\\guide.pdf" \
  --out_dir "E:\\...\\digest_images" \
  --output_md "E:\\...\\指南解读_...md" \
  --dpi 180
```

备注：若远端服务发生超时或网络异常，Orchestrator 会捕获并回退到本地工具，最终仍按统一结构返回产物路径；OutputAssembler 在文本不足时会自动补充 PDF 文本提取，保证端到端生成的稳定性。