# CLAUDE.md - AI Assistant Guide for MedliveAIGC

> **Last Updated**: 2025-11-14
> **Purpose**: Comprehensive guide for AI assistants working with the MedliveAIGC codebase

---

## 1. Project Overview

### 1.1 What is MedliveAIGC?

**MedliveAIGC** is a Medical AI-Generated Content (AIGC) System designed to automate the creation of structured, authoritative clinical guideline interpretations with full compliance, traceability, and human-in-the-loop validation.

**Primary Use Cases:**
- Extract content from medical guideline PDFs (e.g., Chinese Diabetes Prevention Guidelines 2024)
- Generate image-rich Markdown documentation with clinical interpretations
- Integrate with multiple LLM services (Medlive GPT-5, Claude, ChatGPT, Qwen, DeepSeek)
- Maintain audit trails for medical compliance (HIPAA, PIPL, GDPR, EU AI Act)

**Target Users:**
- Pharmaceutical companies
- Hospitals and healthcare institutions
- Clinicians and healthcare professionals

### 1.2 Core Capabilities

1. **PDF Content Extraction**: Dual-mode (remote-first, local fallback) extraction of text and images
2. **LLM-Powered Interpretation**: Structured clinical content generation with role-based prompting
3. **Markdown Assembly**: Automated document generation with embedded images and citations
4. **Compliance & Traceability**: UUID-based request tracking with duration metrics
5. **Fail-Safe Architecture**: Graceful degradation with automatic fallback mechanisms

---

## 2. Architecture & Design Patterns

### 2.1 MCP-Inspired Protocol

The codebase implements a **Model Context Protocol (MCP)** inspired architecture with three key patterns:

#### Pattern 1: Expert Roles (Role-Based Separation of Concerns)

Each module implements a domain expert with clear responsibilities:

| Expert | File | Responsibility |
|--------|------|----------------|
| `IntentExpert` | `framework_protocol.py` | Parses task text, identifies required tools/steps |
| `OrchestratorExpert` | `framework_protocol.py` + `mcp_orchestrator.py` | Chains tools with fail-safe & fallback logic |
| `AutoInstallerExpert` | `framework_protocol.py` | Auto-installs missing dependencies |
| `OutputAssemblerExpert` | `output_assembler.py` | Structures extracted content into markdown |

#### Pattern 2: Unified Request/Response Protocol

**All inter-module communication follows a standardized structure:**

```python
# Request Format
{
    "name": "tool_or_expert_name",
    "version": "v1",
    "params": {...},
    "meta": {"trace_id": "uuid-string"}
}

# Response Format
{
    "ok": bool,               # Success indicator
    "error": str | None,      # Error message if ok=false
    "data": {...},            # Actual payload
    "meta": {
        "duration_ms": int    # Execution time in milliseconds
    }
}
```

**Key Protocol Rules:**
- `ok=true` means success; `data` is valid
- `ok=false` means failure; `error` is required
- All large objects (images, text) are passed as **file paths**, never as binary data
- Every request includes a `trace_id` for end-to-end tracking

#### Pattern 3: Remote-First with Local Fallback

```
┌────────────────────────────────────┐
│   Try Remote: dots-ocr service     │
│   - HTTP POST to remote endpoint   │
│   - Extracts images + OCR text     │
└───────────┬────────────────────────┘
            │
            ▼
       [Success?] ──Yes──> Return unified response
            │
           No (timeout/error)
            │
            ▼
┌────────────────────────────────────┐
│   Fallback: Local PyMuPDF/PyPDF2   │
│   - No external service dependency │
│   - Returns same structure         │
└────────────────────────────────────┘
```

### 2.2 Data Flow Architecture

```
CLI Entry (mcp_generate_digest.py)
    │
    ├─> 1. AutoInstallerExpert.ensure()
    │       └─> Install: requests, pymupdf, PyPDF2
    │
    ├─> 2. OrchestratorExpert.orchestrate()
    │       ├─> Try: Remote dots-ocr service
    │       └─> Fallback: Local PyMuPDF extraction
    │       └─> Output: {"images": [...], "text_path": "..."}
    │
    └─> 3. OutputAssemblerExpert.compose()
            ├─> Load extracted text/images
            ├─> For each section:
            │   ├─> Build clinical expert prompt
            │   ├─> Call LLM (llm_proxy.ask)
            │   └─> Collect section content
            ├─> Assemble Markdown with images
            └─> Output: {"output_md": "...", "images": [...]}
```

---

## 3. File Structure & Organization

```
/home/user/MedliveAIGC/
├── docs/
│   └── mcp_protocol.md              # Complete protocol specification (223 lines)
│
├── dotsocr/                         # PDF/Image OCR module
│   ├── __init__.py                  # Package initialization
│   ├── remote_tools.py              # Dots-OCR service client (100 lines)
│   ├── local_pdf_tool.py            # Local PyMuPDF extraction (76 lines)
│   ├── test_image_ocr.py            # Remote image OCR test
│   ├── test_pdf_ocr.py              # Remote PDF OCR test
│   ├── img_path/                    # Sample images directory
│   └── pdf_path/                    # Sample PDFs directory
│
├── framework_protocol.py            # MCP protocol + Expert base classes (88 lines)
├── mcp_orchestrator.py              # Extraction orchestration (43 lines)
├── output_assembler.py              # Content assembly + LLM integration (133 lines)
├── llm_proxy.py                     # Medlive API wrapper (39 lines)
│
├── mcp_generate_digest.py           # Main CLI pipeline entry (54 lines)
├── generate_diabetes_digest.py      # Standalone diabetes guideline generator (154 lines)
├── test_all_models.py               # Multi-model LLM testing utility (240+ lines)
│
├── 合并稿_chatgpt.md                # Technical design rationale (Chinese)
├── compass_artifact_wf-*.md         # Medical AIGC research report
│
├── .gitignore                       # Git ignore patterns
└── README.md (missing - should be created if needed)
```

### 3.1 Module Responsibilities

| Module | Lines | Primary Responsibility |
|--------|-------|------------------------|
| `framework_protocol.py` | 88 | Core MCP protocol definitions, Expert base classes, request/response helpers |
| `mcp_orchestrator.py` | 43 | Orchestrates remote→local fallback for PDF extraction |
| `output_assembler.py` | 133 | Section-based content generation with LLM, Markdown assembly |
| `llm_proxy.py` | 39 | Unified interface to Medlive GPT-5 API with HMAC-MD5 auth |
| `dotsocr/remote_tools.py` | 100 | HTTP client for dots-ocr service, handles multiple response formats |
| `dotsocr/local_pdf_tool.py` | 76 | PyMuPDF/PyPDF2 implementation for offline extraction |
| `mcp_generate_digest.py` | 54 | End-to-end pipeline orchestrator (CLI entry point) |
| `generate_diabetes_digest.py` | 154 | Specialized workflow for diabetes guideline generation |

---

## 4. Development Workflow

### 4.1 Setting Up Development Environment

```bash
# Clone repository
git clone <repository-url>
cd MedliveAIGC

# Install dependencies (handled automatically by AutoInstallerExpert)
pip install requests pymupdf PyPDF2

# Verify installation
python -c "import fitz, PyPDF2, requests; print('All dependencies installed')"
```

### 4.2 Running the Pipeline

**Basic Usage:**

```bash
python mcp_generate_digest.py \
  --pdf "/path/to/guideline.pdf" \
  --out_dir "/path/to/output/images" \
  --output_md "/path/to/output/解读.md" \
  --dpi 200
```

**Parameters:**
- `--pdf`: Input PDF path (required)
- `--out_dir`: Directory for extracted images and text (required)
- `--output_md`: Output Markdown file path (required)
- `--dpi`: Image extraction DPI (default: 200, range: 150-300)

**Expected Output:**
```json
{
  "ok": true,
  "error": null,
  "data": {
    "output_md": "/path/to/output/解读.md",
    "images": [
      "/path/to/output/images/page1_img0.png",
      "/path/to/output/images/page3_img2.png"
    ]
  },
  "meta": {
    "duration_ms": 45678
  }
}
```

### 4.3 Testing Individual Components

**Test Remote OCR Service:**
```bash
python dotsocr/test_pdf_ocr.py
python dotsocr/test_image_ocr.py
```

**Test LLM Models:**
```bash
python test_all_models.py
```

**Test Local PDF Extraction:**
```python
from dotsocr.local_pdf_tool import call

params = {
    "pdf_path": "/path/to/test.pdf",
    "out_dir": "/path/to/output",
    "dpi": 200,
    "image_extract": True
}

result = call(params)
print(result)
```

---

## 5. Code Conventions & Standards

### 5.1 Python Style

- **Encoding**: Always use `# -*- coding: utf-8 -*-` at the top of files
- **Docstrings**: Module-level docstrings explain purpose, methods, and params structure
- **Type Hints**: Used sparingly; focus on `dict`, `List`, `Tuple` for complex structures
- **Error Handling**: Explicit `try/except` with meaningful error messages
- **Line Length**: Approximately 80-100 characters (not strictly enforced)

### 5.2 Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase with "Expert" suffix | `OutputAssemblerExpert` |
| Functions | snake_case, verb-based | `extract_pdf_text()`, `build_prompt()` |
| Variables | snake_case, descriptive | `text_path`, `section_ranges` |
| Constants | UPPER_SNAKE_CASE (class attributes) | `NAME = "orchestrator"` |
| Files | snake_case | `mcp_orchestrator.py` |

### 5.3 Protocol Adherence

**Always use protocol helpers for consistency:**

```python
from framework_protocol import make_request, make_response
import time

# Creating requests
request = make_request("expert_name", "v1", {"key": "value"})

# Creating responses
start = time.time()
# ... do work ...
response = make_response(True, data={"result": "..."}, start_ts=start)
```

**Never return raw dicts; always use `make_response()`:**

```python
# WRONG
return {"ok": True, "data": {...}}

# CORRECT
return make_response(True, data={...}, start_ts=start)
```

### 5.4 Error Handling Pattern

**Standard error handling in all expert methods:**

```python
def some_expert_method(self, params: dict) -> dict:
    start = time.time()

    # Validate required params
    if not params.get("required_field"):
        return make_response(False, error="缺少required_field参数", start_ts=start)

    # Try operation with fallback
    try:
        result = risky_operation(params)
    except Exception as e:
        return make_response(False, error=f"操作失败: {e}", start_ts=start)

    # Check result validity
    if not result.get("ok"):
        return make_response(False, error=f"子操作失败: {result.get('error')}", start_ts=start)

    # Success
    return make_response(True, data={...}, start_ts=start)
```

### 5.5 Import Organization

```python
# Standard library imports
import os
import re
import time
from typing import List, Tuple

# Third-party imports
import fitz  # PyMuPDF
from PyPDF2 import PdfReader

# Local imports
from framework_protocol import make_response
from llm_proxy import ask as llm_ask
```

---

## 6. Key Components Deep Dive

### 6.1 Framework Protocol (`framework_protocol.py`)

**Purpose**: Core MCP protocol definitions and Expert base classes

**Key Functions:**

```python
def make_request(name: str, version: str, params: dict) -> dict:
    """
    Creates standardized request with auto-generated trace_id

    Returns:
        {
            "name": name,
            "version": version,
            "params": params,
            "meta": {"trace_id": "uuid-v4"}
        }
    """

def make_response(ok: bool, data: dict = None, error: str = None, start_ts: float = None) -> dict:
    """
    Creates standardized response with duration calculation

    Args:
        ok: Success boolean
        data: Payload dictionary (default: {})
        error: Error message if ok=False
        start_ts: Start timestamp from time.time()

    Returns:
        {
            "ok": ok,
            "error": error,
            "data": data,
            "meta": {"duration_ms": calculated_duration}
        }
    """
```

**Expert Classes:**

```python
class IntentExpert:
    NAME = "intent_expert"
    VERSION = "v1"

    def identify(self, params: dict) -> dict:
        """
        Identifies required tools/steps from task text

        Params:
            {"text": str}  # Task description

        Returns:
            {"intents": [str], "confidence": float}
        """

class OrchestratorExpert:
    NAME = "orchestrator"
    VERSION = "v1"

    def orchestrate(self, params: dict, tools: dict) -> dict:
        """
        Orchestrates tool execution with fallback

        Params:
            {"pdf_path": str, "out_dir": str, "dpi": int}

        Tools:
            {"dotsocr_pdf": callable}

        Returns:
            Standard response with {"images": [...], "text_path": str}
        """

class AutoInstallerExpert:
    NAME = "autoinstaller"
    VERSION = "v1"

    def ensure(self, params: dict) -> dict:
        """
        Auto-installs missing dependencies

        Params:
            {"packages": [str]}

        Returns:
            Standard response with {"installed": [(pkg, status)]}
        """
```

### 6.2 Output Assembler (`output_assembler.py`)

**Purpose**: Structures extracted content into LLM-generated Markdown

**Key Functions:**

```python
def extract_pdf_text(pdf_path) -> List[Tuple[int, str]]:
    """
    Extracts text from PDF using PyMuPDF or PyPDF2

    Returns:
        [(page_number, text), ...]
    """

def load_text_file(text_path: str) -> str:
    """Loads text from file with UTF-8 encoding and error handling"""

def build_prompt(section: str, pages_hint: str = "") -> str:
    """
    Constructs clinical expert prompt for LLM

    Template:
        - Role: 临床指南解读专家（内分泌）
        - Goal: Generate image-rich guideline interpretation
        - Constraints: No hallucination, page citations, Markdown structure
        - Section: Specific clinical domain (e.g., "诊断与评估")

    Returns:
        Formatted prompt string
    """

def assemble_markdown(title: str, sections: List[Tuple[str, str]], images: List[str]) -> str:
    """
    Assembles final Markdown with title, sections, images, attribution

    Structure:
        # Title
        > Attribution footer
        ---
        ## 1. Section Name
        [LLM-generated content]
        ![Image](path/to/image.png)
    """
```

**OutputAssemblerExpert Class:**

```python
class OutputAssemblerExpert:
    NAME = "output_assembler"
    VERSION = "v1"

    def compose(self, params: dict) -> dict:
        """
        Main composition method

        Params:
            {
                "title": str,                              # Document title
                "pdf_path": str,                           # Source PDF
                "text_path": str | None,                   # Extracted text file
                "image_dir": str | None,                   # Image directory
                "images": List[str] | None,                # Image file paths
                "output_md": str,                          # Output Markdown path
                "section_ranges": List[Tuple[str,int,int]] # [(name, start_page, end_page)]
            }

        Default section_ranges:
            [
                ("总体解读与核心更新", 1, 6),
                ("诊断与评估", 7, 15),
                ("生活方式与初始治疗", 16, 25),
                ("药物治疗路径（T2D）", 26, 45),
                ("并发症与合并症管理", 46, 65),
                ("随访监测与指标", 66, 80)
            ]

        Process:
            1. Load text from text_path or extract from PDF
            2. Collect images from image_dir
            3. For each section:
                - Extract relevant pages
                - Build clinical expert prompt
                - Call LLM (llm_proxy.ask)
                - Collect section content
            4. Assemble Markdown
            5. Write to output_md

        Returns:
            Standard response with {"output_md": str, "images": List[str]}
        """
```

**Important Considerations:**

1. **Text Fallback**: If `text_path` is missing or text length < 1000 chars, automatically extracts from PDF
2. **Image Collection**: If `images` not provided, scans `image_dir` for PNG files
3. **Rate Limiting**: 1-second sleep between LLM calls to avoid throttling
4. **Token Efficiency**: Truncates text to 6000 chars per section
5. **Error Resilience**: Failed LLM calls insert placeholder text instead of breaking pipeline

### 6.3 LLM Proxy (`llm_proxy.py`)

**Purpose**: Unified interface to Medlive GPT-5 API with custom authentication

**Authentication Flow:**

```python
# Step 1: Generate timestamp
timestamp = int(time.time() * 1000)

# Step 2: Concatenate credentials
concat_str = f"{project_id}{timestamp}{user_id}"

# Step 3: Double MD5 hash
first_hash = hashlib.md5(concat_str.encode("utf-8")).hexdigest()
token = hashlib.md5(first_hash.encode("utf-8")).hexdigest()
```

**API Function:**

```python
def ask(question: str, model_key: str = None) -> Tuple[bool, str]:
    """
    Sends question to Medlive LLM API

    Args:
        question: User prompt/question
        model_key: Model identifier (default: GPT-5)

    Returns:
        (success: bool, answer: str)
        - success=True: answer contains LLM response
        - success=False: answer contains error message

    API Endpoint:
        POST https://chat001.medlive.cn/api/project/chat

    Request Body:
        {
            "project_id": str,
            "user_id": str,
            "timestamp": int,
            "token": str,         # HMAC-MD5 authentication
            "model_key": str,
            "question": str,
            "stream": 0
        }

    Timeout: 60 seconds
    """
```

**Supported Model Keys** (see `test_all_models.py` for full list):
- `model-20250811154752-vr0n93` (Medlive GPT-5)
- `model-20240920111949-gjy8zq` (Qwen-max)
- `model-20240920113031-e3ov1d` (GPT-4o)
- `model-20250113133051-a3u2q1` (DeepSeek-V3)
- And 10+ more models...

### 6.4 MCP Orchestrator (`mcp_orchestrator.py`)

**Purpose**: Orchestrates remote→local fallback for PDF extraction

**Implementation:**

```python
from dotsocr import remote_tools, local_pdf_tool

# Tool registration
tools = {
    "dotsocr_pdf": lambda p: remote_tools.call_pdf(p) if should_try_remote(p)
                             else local_pdf_tool.call(p)
}

# Orchestration with fallback
orchestrator = OrchestratorExpert()
response = orchestrator.orchestrate(params, tools)

# Response always has same structure regardless of tool used
{
    "ok": true,
    "data": {
        "images": ["/path/to/page1.png", ...],
        "text_path": "/path/to/extract_text.txt"
    }
}
```

### 6.5 Remote Tools (`dotsocr/remote_tools.py`)

**Purpose**: HTTP client for dots-ocr service with multi-format response handling

**Key Functions:**

```python
def call_pdf(params: dict) -> dict:
    """
    Calls remote PDF OCR service

    Params:
        {
            "pdf_path": str,
            "out_dir": str,
            "dpi": int,
            "image_extract": bool
        }

    Service:
        POST http://dots-ocr.mlproject.cn/extract
        - Multipart form-data with PDF file
        - Returns JSON, ZIP, or plain text

    Returns:
        {
            "ok": bool,
            "data": {
                "images": List[str],  # Saved to out_dir
                "text_path": str      # Saved to out_dir/extract_text_remote.txt
            }
        }
    """

def call_image(params: dict) -> dict:
    """
    Calls remote Image OCR service

    Similar to call_pdf but for single images
    """
```

**Response Format Handling:**

1. **JSON Response**: Parses `{"text": "...", "images": [{"filename": "...", "content": "base64"}]}`
2. **ZIP Response**: Extracts archive to `out_dir`
3. **Plain Text**: Saves as `extract_text_remote.txt`

### 6.6 Local PDF Tool (`dotsocr/local_pdf_tool.py`)

**Purpose**: Offline PDF extraction using PyMuPDF/PyPDF2

**Key Functions:**

```python
def call(params: dict) -> dict:
    """
    Local PDF extraction (no external service)

    Params:
        {
            "pdf_path": str,
            "out_dir": str,
            "dpi": int,
            "image_extract": bool
        }

    Process:
        1. Extract text page-by-page with fitz.get_text()
        2. Extract images with size filtering (>200x200 pixels)
        3. Save to out_dir

    Returns:
        Same structure as remote_tools.call_pdf
    """

def _extract_text(pdf_path: str) -> List[str]:
    """Uses PyMuPDF, falls back to PyPDF2"""

def _extract_images(pdf_path: str, out_dir: str, dpi: int) -> List[str]:
    """
    Extracts images with size filtering
    - Skips images < 200x200 pixels
    - Saves as pageX_imgY.png
    """
```

---

## 7. Common Tasks & How-Tos

### 7.1 Adding a New Expert

```python
# 1. Define in framework_protocol.py or separate file
class MyNewExpert:
    NAME = "my_expert"
    VERSION = "v1"

    def my_method(self, params: dict) -> dict:
        start = time.time()

        # Validate params
        required_field = params.get("required_field")
        if not required_field:
            return make_response(False, error="缺少required_field", start_ts=start)

        # Do work
        try:
            result = do_something(required_field)
        except Exception as e:
            return make_response(False, error=f"失败: {e}", start_ts=start)

        # Return success
        return make_response(True, data={"result": result}, start_ts=start)

# 2. Register in pipeline (mcp_generate_digest.py)
my_expert = MyNewExpert()
response = my_expert.my_method(params)

# 3. Document in docs/mcp_protocol.md
```

### 7.2 Adding Support for a New LLM

```python
# Edit llm_proxy.py

# 1. Add model configuration
MODEL_CONFIGS = {
    "new_model": {
        "endpoint": "https://api.example.com/v1/chat",
        "auth_method": "bearer",  # or "hmac", "api_key"
        "model_key": "model-id-12345"
    }
}

# 2. Update ask() function
def ask(question: str, model_key: str = None, llm_provider: str = "medlive") -> Tuple[bool, str]:
    if llm_provider == "new_provider":
        # Implement new provider logic
        return call_new_provider(question, model_key)

    # Existing Medlive logic
    ...

# 3. Test with test_all_models.py
# Add to MODELS list:
MODELS.append(("new_provider", "model-key-12345", "New Model Name"))
```

### 7.3 Customizing Section Ranges

```python
# Option 1: Pass as parameter
custom_sections = [
    ("概述", 1, 10),
    ("诊断标准", 11, 20),
    ("治疗方案", 21, 40),
    ("并发症", 41, 60)
]

assembler = OutputAssemblerExpert()
response = assembler.compose({
    "pdf_path": "/path/to/guide.pdf",
    "output_md": "/path/to/output.md",
    "section_ranges": custom_sections,  # Custom sections
    ...
})

# Option 2: Modify default in output_assembler.py
# Edit line 83-90 in OutputAssemblerExpert.compose()
section_ranges = params.get("section_ranges") or [
    ("Your Section 1", 1, 10),
    ("Your Section 2", 11, 20),
    ...
]
```

### 7.4 Debugging Failed Extractions

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test remote service
from dotsocr.remote_tools import call_pdf

params = {
    "pdf_path": "/path/to/test.pdf",
    "out_dir": "/path/to/output",
    "dpi": 200,
    "image_extract": True
}

response = call_pdf(params)
print(f"Remote result: {response}")

# If remote fails, test local
from dotsocr.local_pdf_tool import call

response = call(params)
print(f"Local result: {response}")

# Check text extraction
from output_assembler import extract_pdf_text

pages = extract_pdf_text("/path/to/test.pdf")
for page_num, text in pages:
    print(f"Page {page_num}: {len(text)} characters")
```

### 7.5 Testing LLM Integration

```python
# Test single model
from llm_proxy import ask

success, answer = ask("请解释糖尿病的诊断标准")
print(f"Success: {success}")
print(f"Answer: {answer}")

# Test all models
python test_all_models.py

# Expected output:
# Testing model 1/10: Medlive GPT-5
# ✓ Success (2.3s, 245 tokens)
# Testing model 2/10: Qwen-max
# ✓ Success (1.8s, 198 tokens)
# ...
```

### 7.6 Running Partial Pipeline

```python
# Skip extraction, use existing files
from output_assembler import OutputAssemblerExpert

assembler = OutputAssemblerExpert()
response = assembler.compose({
    "title": "指南解读",
    "pdf_path": None,                          # Not needed if text_path provided
    "text_path": "/path/to/existing_text.txt", # Use existing text
    "images": ["/path/to/img1.png", "/path/to/img2.png"],  # Use existing images
    "output_md": "/path/to/output.md",
    "section_ranges": [...]
})

print(response)
```

---

## 8. Testing & Quality Assurance

### 8.1 Unit Testing

**Current Testing Files:**
- `dotsocr/test_pdf_ocr.py` - Remote PDF OCR service test
- `dotsocr/test_image_ocr.py` - Remote image OCR service test
- `test_all_models.py` - Multi-model LLM evaluation

**Running Tests:**

```bash
# Test remote OCR
python dotsocr/test_pdf_ocr.py

# Test image OCR
python dotsocr/test_image_ocr.py

# Test all LLM models
python test_all_models.py
```

### 8.2 Integration Testing

**End-to-End Test:**

```bash
# Prepare test data
mkdir -p test_data/input test_data/output

# Run full pipeline
python mcp_generate_digest.py \
  --pdf "test_data/input/sample_guideline.pdf" \
  --out_dir "test_data/output/images" \
  --output_md "test_data/output/guideline_digest.md" \
  --dpi 200

# Verify outputs
ls test_data/output/images/      # Should contain extracted images
cat test_data/output/guideline_digest.md  # Should contain structured Markdown
```

### 8.3 Validation Checklist

**Before Committing Code:**

- [ ] All functions use `make_request()` / `make_response()` helpers
- [ ] Error handling includes `start_ts` and meaningful error messages
- [ ] File paths use `os.path.join()` for cross-platform compatibility
- [ ] Large objects (images, text) are passed as file paths, not binary data
- [ ] Trace IDs are preserved across function calls
- [ ] UTF-8 encoding is specified for all file operations
- [ ] Exception handling includes specific error types (not bare `except:`)
- [ ] Module-level docstrings explain purpose and params structure
- [ ] New experts are documented in `docs/mcp_protocol.md`

---

## 9. External Dependencies & Services

### 9.1 Python Libraries

| Library | Version | Purpose | Auto-Installed |
|---------|---------|---------|----------------|
| `requests` | Latest | HTTP client for remote OCR & LLM API | Yes |
| `PyMuPDF (fitz)` | Latest | Primary PDF text/image extraction | Yes |
| `PyPDF2` | Latest | Fallback PDF text extraction | Yes |
| `hashlib` | Built-in | HMAC-MD5 authentication for Medlive API | N/A |
| `json` | Built-in | Protocol serialization | N/A |
| `re` | Built-in | Text normalization | N/A |
| `uuid` | Built-in | Trace ID generation | N/A |

### 9.2 External Services

#### Medlive LLM API

**Endpoint**: `https://chat001.medlive.cn/api/project/chat`

**Authentication**: Custom HMAC-MD5 (double-hash token)

**Request Format**:
```json
{
  "project_id": "string",
  "user_id": "string",
  "timestamp": 1234567890,
  "token": "md5(md5(project_id + timestamp + user_id))",
  "model_key": "model-20250811154752-vr0n93",
  "question": "Your question here",
  "stream": 0
}
```

**Response Format**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "answer": "LLM response text",
    "usage": {
      "prompt_tokens": 123,
      "completion_tokens": 456
    }
  }
}
```

**Rate Limits**: Unknown (recommend 1-second delay between calls)

**Timeout**: 60 seconds

#### dots-ocr Service

**Endpoint**: `http://dots-ocr.mlproject.cn/extract`

**Method**: POST (multipart/form-data)

**Request Parameters**:
```
task: "pdf_ocr" | "image_ocr"
pdf: <binary file> (for PDF)
image: <binary file> (for image)
dpi: integer (default: 200)
image_extract: boolean (default: true)
```

**Response Formats**:
1. **JSON**: `{"text": "...", "images": [{"filename": "...", "content": "base64"}]}`
2. **ZIP**: Binary archive containing images and text files
3. **Plain Text**: Raw OCR output

**Error Handling**: Service failures automatically trigger local fallback

### 9.3 Configuration Management

**Current Approach**: Hardcoded credentials in code files

**Recommendation**: Move to environment variables or config file

```python
# Create config.py (add to .gitignore)
import os

# Medlive API
MEDLIVE_PROJECT_ID = os.getenv("MEDLIVE_PROJECT_ID", "default_project_id")
MEDLIVE_USER_ID = os.getenv("MEDLIVE_USER_ID", "default_user_id")
MEDLIVE_ENDPOINT = os.getenv("MEDLIVE_ENDPOINT", "https://chat001.medlive.cn/api/project/chat")

# dots-ocr Service
DOTS_OCR_ENDPOINT = os.getenv("DOTS_OCR_ENDPOINT", "http://dots-ocr.mlproject.cn/extract")

# Then import in llm_proxy.py
from config import MEDLIVE_PROJECT_ID, MEDLIVE_USER_ID, MEDLIVE_ENDPOINT
```

---

## 10. Gotchas & Important Considerations

### 10.1 File Path Handling

**Issue**: Windows paths with backslashes break in Markdown

```python
# WRONG
image_path = "E:\\output\\page1.png"
md = f"![image]({image_path})"  # Results in: ![image](E:\output\page1.png) - broken

# CORRECT
image_path = image_path.replace("\\", "/")
md = f"![image]({image_path})"  # Results in: ![image](E:/output/page1.png) - works
```

**Solution**: Always normalize paths in `assemble_markdown()` (line 65 of `output_assembler.py`)

### 10.2 Text Truncation

**Issue**: LLM context limits require text truncation

**Current Behavior**: `output_assembler.py` line 122 truncates to 6000 chars

```python
full_q = f"{prompt}\n\n=== 原文片段（p{s}-{e}）===\n{text[:6000]}"
```

**Consideration**: For very long sections (e.g., 50+ pages), important content may be lost

**Recommendation**: Implement chunking strategy or use multiple LLM calls

### 10.3 Rate Limiting

**Issue**: Medlive API may throttle rapid requests

**Current Mitigation**: 1-second sleep between section calls (`output_assembler.py` line 127)

```python
time.sleep(1)  # Avoid rate limiting
```

**Recommendation**: Monitor for 429 errors and implement exponential backoff

### 10.4 Image Size Filtering

**Issue**: PDFs may contain tiny logos/icons that aren't useful

**Current Behavior**: `local_pdf_tool.py` filters images < 200x200 pixels

```python
if width < 200 or height < 200:
    continue  # Skip small images
```

**Consideration**: Adjust threshold based on document type

### 10.5 Encoding Issues

**Issue**: Medical documents may contain special characters (e.g., ≥, ≤, µ, ±)

**Mitigation**: All file operations use `encoding="utf-8", errors="ignore"`

```python
with open(text_path, "r", encoding="utf-8", errors="ignore") as f:
    return f.read()
```

**Recommendation**: Use `errors="replace"` instead of `"ignore"` to see where encoding issues occur

### 10.6 Trace ID Persistence

**Issue**: Trace IDs are generated per request but not automatically propagated

**Current Behavior**: Each `make_request()` call generates a new UUID

**Recommendation**: Pass `trace_id` as parameter through pipeline:

```python
# Generate once at pipeline entry
trace_id = str(uuid.uuid4())

# Pass to all calls
request1 = make_request("orchestrator", "v1", params)
request1["meta"]["trace_id"] = trace_id  # Override with parent trace_id

request2 = make_request("assembler", "v1", params)
request2["meta"]["trace_id"] = trace_id  # Same trace_id
```

### 10.7 Memory Management

**Issue**: Loading large PDFs (100+ pages) into memory can cause issues

**Current Behavior**: `extract_pdf_text()` loads all pages at once

**Recommendation**: Use generator pattern for large documents:

```python
def extract_pdf_text_generator(pdf_path: str):
    doc = fitz.open(pdf_path)
    for i in range(len(doc)):
        yield (i + 1, doc[i].get_text("text"))
```

---

## 11. Debugging & Troubleshooting

### 11.1 Common Issues

#### Issue: "ModuleNotFoundError: No module named 'fitz'"

**Cause**: PyMuPDF not installed

**Solution**:
```bash
pip install pymupdf
```

#### Issue: Remote OCR service timeout

**Symptoms**: `make_response(False, error="dotsocr_pdf异常: ...")`

**Solution**:
1. Check network connectivity: `curl http://dots-ocr.mlproject.cn/extract`
2. Verify PDF file size (large files may timeout)
3. System automatically falls back to local extraction

#### Issue: LLM returns error "token验证失败"

**Cause**: Incorrect authentication token

**Solution**:
1. Verify `project_id` and `user_id` in `llm_proxy.py`
2. Check timestamp generation (must be milliseconds: `int(time.time() * 1000)`)
3. Ensure MD5 hash is lowercase

#### Issue: Generated Markdown missing images

**Cause**: Image paths not correctly saved or referenced

**Debug Steps**:
```python
# 1. Check if images were extracted
import os
print(os.listdir("/path/to/out_dir"))

# 2. Verify image paths in response
response = orchestrator.orchestrate(params, tools)
print(response["data"]["images"])

# 3. Check Markdown image links
with open("/path/to/output.md", "r") as f:
    content = f.read()
    print([line for line in content.split("\n") if "![" in line])
```

#### Issue: Text extraction returns empty string

**Cause**: PDF may be image-based (scanned document) without OCR layer

**Solution**:
1. Check if PDF contains selectable text: Open in viewer, try to copy text
2. If image-based, remote OCR service should handle it
3. Local extraction won't work for image-based PDFs (requires OCR)

### 11.2 Logging Strategies

**Add debug logging:**

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('medlive_aigc.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# In your code
logger.debug(f"Starting orchestration with params: {params}")
logger.info(f"Remote extraction completed: {len(images)} images")
logger.error(f"LLM call failed: {error_message}")
```

### 11.3 Performance Profiling

**Measure component timing:**

```python
import time

# Wrap operations
start = time.time()
response = orchestrator.orchestrate(params, tools)
orchestration_time = time.time() - start

start = time.time()
response = assembler.compose(params)
assembly_time = time.time() - start

print(f"Orchestration: {orchestration_time:.2f}s")
print(f"Assembly: {assembly_time:.2f}s")
print(f"Total: {orchestration_time + assembly_time:.2f}s")
```

**Expected Performance:**
- Remote OCR: 5-30 seconds (depends on PDF size)
- Local extraction: 1-10 seconds
- LLM call: 2-10 seconds per section
- Total pipeline: 30-180 seconds for 6-section document

---

## 12. Future Extensibility

### 12.1 Planned Enhancements

**Based on codebase analysis, consider these extensions:**

1. **Multi-Language Support**
   - Current: Chinese-only prompts and output
   - Enhancement: Add `language` parameter to `build_prompt()`
   - Files to modify: `output_assembler.py`

2. **Custom Prompt Templates**
   - Current: Hardcoded prompt in `build_prompt()`
   - Enhancement: Load prompts from templates directory
   - Implementation: `templates/{section_name}_{language}.txt`

3. **Streaming LLM Responses**
   - Current: `stream: 0` (wait for complete response)
   - Enhancement: Real-time streaming for better UX
   - Files to modify: `llm_proxy.py`

4. **Batch Processing**
   - Current: Single PDF per run
   - Enhancement: Process multiple PDFs in parallel
   - Implementation: New `mcp_batch_generate.py` entry point

5. **Quality Validation**
   - Current: No validation of LLM output quality
   - Enhancement: Add fact-checking, citation validation
   - Implementation: New `QualityValidatorExpert` class

6. **Export Formats**
   - Current: Markdown only
   - Enhancement: PDF, DOCX, HTML export
   - Implementation: New `ExportExpert` class with pandoc integration

### 12.2 Architecture Evolution

**Current State**: Monolithic pipeline

**Recommended Evolution**:

```
Current:
CLI → AutoInstall → Orchestrate → Assemble → Output

Future (Microservices):
API Gateway
    ├─> Extraction Service (remote + local)
    ├─> LLM Service (multi-provider)
    ├─> Assembly Service (template-based)
    └─> Storage Service (S3/Minio)
```

**Benefits**:
- Horizontal scaling for each component
- Independent deployment and versioning
- Better fault isolation
- Easier A/B testing of LLM models

### 12.3 Database Integration

**Current State**: File-based I/O only

**Recommended Enhancement**:

```python
# Add database tracking for audit compliance
class JobTracker:
    def create_job(self, trace_id: str, pdf_path: str) -> int:
        """Create job record, return job_id"""

    def update_status(self, job_id: int, status: str, data: dict):
        """Update job status (pending, processing, completed, failed)"""

    def get_job_history(self, job_id: int) -> List[dict]:
        """Retrieve full execution history for compliance audit"""

# Schema
CREATE TABLE jobs (
    job_id SERIAL PRIMARY KEY,
    trace_id UUID UNIQUE,
    pdf_path TEXT,
    status TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE TABLE job_steps (
    step_id SERIAL PRIMARY KEY,
    job_id INT REFERENCES jobs(job_id),
    expert_name TEXT,
    duration_ms INT,
    input_params JSONB,
    output_data JSONB,
    created_at TIMESTAMP
);
```

---

## 13. Compliance & Security

### 13.1 Medical Data Handling

**Current Approach**: Local file processing (no cloud storage)

**Compliance Considerations**:
- HIPAA (US): PHI handling requirements
- PIPL (China): Personal information protection
- GDPR (EU): Data processing regulations
- EU AI Act: High-risk AI system requirements

**Recommendations**:
1. **Data Minimization**: Process only necessary content
2. **Encryption at Rest**: Encrypt output files
3. **Audit Logging**: Track all document access (use trace IDs)
4. **Retention Policies**: Auto-delete files after processing
5. **Access Controls**: Implement user authentication

### 13.2 LLM Output Validation

**Current State**: No validation of LLM-generated content

**Risks**:
- Hallucinations (fabricated medical facts)
- Incorrect citations
- Missing disclaimers

**Recommended Validation**:

```python
class ContentValidator:
    def validate_section(self, section_text: str, source_pages: List[str]) -> dict:
        """
        Validates LLM output against source material

        Checks:
        1. All citations [pX-Y] exist in source
        2. No unsupported medical claims
        3. Proper disclaimer included
        4. Markdown structure valid

        Returns:
            {
                "is_valid": bool,
                "issues": [str],
                "confidence": float
            }
        """
```

### 13.3 API Security

**Current State**: Hardcoded credentials

**Security Risks**:
- Credentials in version control
- No credential rotation
- No access logs

**Recommendations**:

```python
# Use environment variables
import os
from pathlib import Path

def load_credentials():
    # Option 1: Environment variables
    project_id = os.getenv("MEDLIVE_PROJECT_ID")
    user_id = os.getenv("MEDLIVE_USER_ID")

    # Option 2: Secure credential file (outside repo)
    cred_file = Path.home() / ".medlive" / "credentials.json"
    if cred_file.exists():
        import json
        with open(cred_file) as f:
            creds = json.load(f)
            project_id = creds["project_id"]
            user_id = creds["user_id"]

    return project_id, user_id

# Audit logging
import logging
logger = logging.getLogger("medlive.security")

def ask(question: str, model_key: str = None) -> Tuple[bool, str]:
    logger.info(f"LLM request: user={user_id}, model={model_key}, len={len(question)}")
    # ... existing code ...
    logger.info(f"LLM response: success={success}, len={len(answer)}")
```

---

## 14. Quick Reference

### 14.1 File Paths

| Path | Description |
|------|-------------|
| `/home/user/MedliveAIGC/` | Project root |
| `framework_protocol.py` | Core protocol (88 lines) |
| `mcp_generate_digest.py` | CLI entry point (54 lines) |
| `output_assembler.py` | Content generation (133 lines) |
| `llm_proxy.py` | LLM API wrapper (39 lines) |
| `docs/mcp_protocol.md` | Protocol specification (223 lines) |
| `dotsocr/` | OCR tools package |

### 14.2 Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `make_request()` | `framework_protocol.py` | Create standardized request |
| `make_response()` | `framework_protocol.py` | Create standardized response |
| `orchestrate()` | `mcp_orchestrator.py` | Orchestrate extraction with fallback |
| `compose()` | `output_assembler.py` | Generate Markdown from extracts |
| `ask()` | `llm_proxy.py` | Call Medlive LLM API |
| `call_pdf()` | `dotsocr/remote_tools.py` | Remote PDF OCR |
| `call()` | `dotsocr/local_pdf_tool.py` | Local PDF extraction |

### 14.3 Important Conventions

- **All responses use `make_response()`** - Never return raw dicts
- **All file I/O uses UTF-8** - `encoding="utf-8", errors="ignore"`
- **All paths normalized** - `path.replace("\\", "/")` for Markdown
- **All errors captured** - `try/except` with meaningful messages
- **All requests tracked** - `trace_id` in metadata
- **All experts versioned** - `VERSION = "v1"` class attribute

### 14.4 Command Cheat Sheet

```bash
# Full pipeline
python mcp_generate_digest.py --pdf X.pdf --out_dir Y --output_md Z.md

# Test remote OCR
python dotsocr/test_pdf_ocr.py

# Test all LLM models
python test_all_models.py

# Install dependencies
pip install requests pymupdf PyPDF2

# Check file structure
find . -name "*.py" -type f | head -20

# View protocol docs
cat docs/mcp_protocol.md
```

---

## 15. Contact & Support

### 15.1 Documentation

- **Protocol Specification**: `docs/mcp_protocol.md`
- **Technical Design** (Chinese): `合并稿_chatgpt.md`
- **Research Report** (Chinese): `compass_artifact_wf-*.md`

### 15.2 Code Review Checklist

Before submitting changes, ensure:

- [ ] New code follows MCP protocol (uses `make_request`/`make_response`)
- [ ] Error handling includes `start_ts` parameter
- [ ] File operations use UTF-8 encoding
- [ ] Path separators normalized for cross-platform compatibility
- [ ] Trace IDs preserved through pipeline
- [ ] Module docstrings updated
- [ ] Tests pass (run `test_*.py` scripts)
- [ ] No hardcoded credentials (use environment variables)
- [ ] Changes documented in this file (CLAUDE.md)

### 15.3 Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2025-11-14 | Initial comprehensive documentation |

---

## 16. Working with This Codebase as an AI Assistant

### 16.1 Understanding User Intent

When users request changes, first determine:

1. **Scope**: Single file, module, or full pipeline?
2. **Type**: Bug fix, feature addition, or refactoring?
3. **Dependencies**: What other components are affected?

**Example Decision Tree**:

```
User: "Add support for DOCX export"
    ├─> Scope: New feature in output assembly
    ├─> Files: output_assembler.py (new ExportExpert class)
    ├─> Dependencies: May need python-docx library
    └─> Protocol: Add export_format parameter to compose()
```

### 16.2 Making Changes Safely

**Step-by-step approach**:

1. **Read relevant files** using Read tool
2. **Understand current behavior** by tracing data flow
3. **Identify modification points** (specific functions/lines)
4. **Make surgical edits** using Edit tool (not Write, unless new file)
5. **Preserve protocol compliance** (always use make_request/make_response)
6. **Test changes** (suggest test commands to user)
7. **Update documentation** (this file + mcp_protocol.md if protocol changes)

**Example**:

```python
# User wants to add DPI validation

# 1. Read framework_protocol.py to understand OrchestratorExpert
# 2. Identify modification point: orchestrate() method, line 50-65
# 3. Edit to add validation:

def orchestrate(self, params: dict, tools: dict) -> dict:
    start = time.time()
    pdf_path = params.get("pdf_path")
    out_dir = params.get("out_dir")
    dpi = params.get("dpi", 200)

    # NEW: Validate DPI range
    if not (150 <= dpi <= 300):
        return make_response(False, error=f"DPI必须在150-300之间，当前: {dpi}", start_ts=start)

    # Existing code continues...
```

### 16.3 Common User Requests & How to Handle

| Request Type | Approach | Files to Check |
|--------------|----------|----------------|
| "Add new LLM provider" | Edit `llm_proxy.py`, add auth logic | `llm_proxy.py`, `test_all_models.py` |
| "Change section structure" | Modify default in `compose()` | `output_assembler.py` line 83-90 |
| "Fix encoding error" | Check file I/O, ensure UTF-8 | All files with `open()` |
| "Speed up extraction" | Profile components, optimize bottlenecks | `mcp_orchestrator.py`, `dotsocr/` |
| "Add validation" | Create new validator function | `output_assembler.py` or new file |
| "Support new format" | Add export method to assembler | `output_assembler.py` |

### 16.4 Debugging Strategy

When user reports issues:

1. **Gather information**:
   - What command did they run?
   - What error message appeared?
   - What files were involved?

2. **Trace execution path**:
   - Start at CLI entry point
   - Follow data flow through experts
   - Identify where error occurred

3. **Reproduce locally** (suggest to user):
   ```bash
   # Minimal reproduction case
   python mcp_generate_digest.py --pdf test.pdf --out_dir out --output_md test.md
   ```

4. **Provide fix with explanation**:
   - Show exact line causing issue
   - Explain why it fails
   - Provide corrected code
   - Suggest how to prevent similar issues

### 16.5 Best Practices for AI Assistants

**DO:**
- ✓ Always read files before editing (never guess implementation)
- ✓ Use Edit tool for existing files (preserves structure)
- ✓ Follow existing code style and conventions
- ✓ Provide clear explanations of changes
- ✓ Suggest testing steps after modifications
- ✓ Update documentation when changing behavior

**DON'T:**
- ✗ Use Write tool on existing files (loses content)
- ✗ Make assumptions about credentials or paths
- ✗ Break protocol compliance (always use helpers)
- ✗ Ignore error handling (always include try/except)
- ✗ Hardcode values that should be parameters
- ✗ Skip documentation updates

---

**End of CLAUDE.md**

> This document is maintained by AI assistants working on MedliveAIGC.
> Last updated: 2025-11-14
> For questions or corrections, please update this file directly.
