# DocFlowHub 使用教程

## 1. 环境准备

确保您的系统安装了 Python 3.8+ 和 `uv` 包管理器。

### 安装 `uv`

如果您尚未安装 `uv`，可以通过以下命令安装：

```bash
pip install uv
```

## 2. 项目安装

克隆项目仓库并安装依赖：

```bash
git clone https://github.com/your-repo/doc_flow_hub.git
cd doc_flow_hub
uv pip install -r requirements.txt
```

## 3. 运行应用

DocFlowHub 是一个 FastAPI 应用。您可以使用 Uvicorn 运行它：

```bash
uvicorn src.doc_flow_hub.main:app --reload
```

应用将在 `http://127.0.0.1:8000` 启动。您可以通过访问 `http://127.0.0.1:8000/docs` 查看 OpenAPI 交互式文档。

## 4. 核心功能使用

DocFlowHub 提供了文档管理的核心功能，包括上传、检索和列出文档。

### 4.1. 上传文档

使用 `POST /upload` 接口上传文档。

**示例 (使用 `curl`)**:

```bash
curl -X POST "http://127.0.0.1:8000/upload" \
-H "accept: application/json" \
-H "Content-Type: multipart/form-data" \
-F "file=@/path/to/your/document/projectA_V1.0_PRD.pdf"
```

请确保文件名遵循以下约定：`{project_name}_V{version}_{doc_type}.{extension}`。
例如：`projectA_V1.0_PRD.pdf`, `projectB_V2.1_CR_007.md`。

### 4.2. 检索文档

使用 `GET /documents/{project_name}/{doc_type}` 接口检索文档。

**示例 (检索最新版本)**:

```bash
curl -X GET "http://127.0.0.1:8000/documents/projectA/PRD?latest=true" \
-H "accept: application/json"
```

**示例 (检索指定版本)**:

```bash
curl -X GET "http://127.0.0.1:8000/documents/projectA/PRD?version=V1.0" \
-H "accept: application/json"
```

### 4.3. 列出文档

使用 `GET /documents` 接口列出所有已上传的文档。

**示例 (列出所有文档)**:

```bash
curl -X GET "http://127.0.0.1:8000/documents" \
-H "accept: application/json"
```

**示例 (按项目名过滤)**:

```bash
curl -X GET "http://127.0.0.1:8000/documents?project_name=projectA" \
-H "accept: application/json"
```

**示例 (按文档类型过滤)**:

```bash
curl -X GET "http://127.0.0.1:8000/documents?doc_type=PRD" \
-H "accept: application/json"
```

## 5. 测试

项目包含单元测试。您可以使用 `pytest` 运行它们：

```bash
pytest tests/