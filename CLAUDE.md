# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MedliveAIGC is a medical content generation system that extracts text and images from PDF medical guidelines and generates structured Markdown digests using LLM. The primary use case is generating illustrated clinical guideline interpretations (e.g., 2024 China Diabetes Prevention and Treatment Guidelines).

## Key Commands

### PDF Extraction (Orchestrator)
```bash
python mcp_orchestrator.py --pdf "<pdf_path>" --out_dir "<out_dir>" --dpi 200
```
Extracts images and text from PDF using remote OCR service (with local fallback).

### Full Generation Pipeline
```bash
python mcp_generate_digest.py --pdf "<pdf_path>" --out_dir "<images_dir>" --output_md "<output.md>" --dpi 200
```
Complete pipeline: dependency installation → PDF extraction → LLM-based Markdown generation.

### Standalone Diabetes Digest
```bash
python generate_diabetes_digest.py
```
Original implementation with hardcoded paths (see line 5-7 for configuration).

### Testing OCR Tools
```bash
# Test remote PDF OCR
python dotsocr/test_pdf_ocr.py

# Test remote image OCR
python dotsocr/test_image_ocr.py
```

## Architecture

### MCP Protocol Pattern
All components follow a unified request/response protocol defined in `framework_protocol.py`:

**Request Structure:**
```python
{
  "name": str,
  "version": str,
  "params": dict,
  "meta": {"trace_id": uuid}
}
```

**Response Structure:**
```python
{
  "ok": bool,
  "error": str | None,
  "data": dict,
  "meta": {"duration_ms": int}
}
```

Use `make_request()` and `make_response()` helpers for consistency.

### Expert Roles (framework_protocol.py)

1. **IntentExpert** - Task intent identification
   - Method: `identify(params)` → `{"intents": [str], "confidence": float}`

2. **OrchestratorExpert** - Tool orchestration with remote-first, local-fallback strategy
   - Method: `orchestrate(params, tools)` → standard response
   - Calls remote OCR, falls back to local on failure

3. **AutoInstallerExpert** - Automatic dependency installation
   - Method: `ensure(params)` → standard response
   - Auto-installs: requests, pymupdf, PyPDF2

4. **OutputAssemblerExpert** (output_assembler.py) - Markdown composition
   - Method: `compose(params)` → standard response
   - Calls LLM for each section, assembles with images

### Tool Layer

**Remote OCR** (`dotsocr/remote_tools.py`):
- `call_pdf(params)` - PDF extraction via http://dots-ocr.mlproject.cn/extract
- `call_image(params)` - Image extraction via same endpoint
- Returns: `{"images": [paths], "text_path": path}`

**Local PDF** (`dotsocr/local_pdf_tool.py`):
- `call(params)` - Local extraction using PyMuPDF or PyPDF2 fallback
- Used when remote service fails/times out

### LLM Proxy

`llm_proxy.py` provides `ask(question: str, timeout: int)` → `(ok: bool, answer: str)`
- Uses Medlive GPT-5 API (chat001.medlive.cn)
- Authentication: MD5-based token with timestamp
- Model key: `MODEL_KEY` constant (line 9)
- API key: `API_KEY` constant (line 10)

### Pipeline Flow

1. **mcp_generate_digest.py** orchestrates the complete flow:
   ```
   AutoInstallerExpert.ensure()
     → orchestrate_extract() [remote → local fallback]
     → OutputAssemblerExpert.compose() [LLM generation]
     → Markdown output with embedded images
   ```

2. **Section-based generation**:
   - Default sections (output_assembler.py:83-90):
     - 总体解读与核心更新 (pages 1-6)
     - 诊断与评估 (pages 7-15)
     - 生活方式与初始治疗 (pages 16-25)
     - 药物治疗路径（T2D）(pages 26-45)
     - 并发症与合并症管理 (pages 46-65)
     - 随访监测与指标 (pages 66-80)
   - Override with `section_ranges` parameter

3. **Prompt structure** (output_assembler.py:49-55):
   - Role: 临床指南解读专家（内分泌）
   - Constraints: page citations [pX-Y], Chinese output, Markdown structured
   - Required content: 执行摘要、核心更新、诊断/评估、治疗路径、特殊人群、随访监测、风险红旗、证据与引用

## Error Handling & Fallback Strategy

1. **Remote OCR failure**: Orchestrator catches exceptions/errors → automatically falls back to local_pdf_tool
2. **Text extraction failure**: OutputAssembler detects insufficient text → re-extracts from PDF directly
3. **LLM failure**: Section marked with error message, pipeline continues
4. **Dependency missing**: AutoInstaller attempts pip install, returns error if fails

## Data Conventions

- All file paths stored in response `data` (not binary content)
- Images filtered by size: min 200x200 pixels (local_pdf_tool.py:53)
- Text cleaned: whitespace normalized (generate_diabetes_digest.py:19)
- DPI default: 200 (adjustable via CLI)

## Important Notes

- Remote OCR endpoint: `http://dots-ocr.mlproject.cn/extract` (remote_tools.py:13)
- Image extraction limited to avoid oversized outputs (max_images parameter)
- LLM calls include 1-second delay between sections (output_assembler.py:127)
- PDF text truncated to 6000 chars per section for LLM context (output_assembler.py:122)
- All intermediate outputs (text files, images) saved to `out_dir`

## Configuration

When modifying LLM behavior:
- Model key: `llm_proxy.py:9`
- API key: `llm_proxy.py:10`
- Authentication logic: `llm_proxy.py:14-18`
- API endpoint: `llm_proxy.py:19`

When modifying section ranges:
- Default ranges: `output_assembler.py:83-90`
- Pass custom `section_ranges` to `OutputAssemblerExpert.compose()`

## Protocol Documentation

See `docs/mcp_protocol.md` for comprehensive protocol specification including:
- Message model details
- Role definitions
- Remote OCR service protocol
- Request/response examples
- Version and extension conventions
