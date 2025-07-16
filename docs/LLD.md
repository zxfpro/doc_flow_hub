# **LLD - 低阶设计文档**

**项目名称：** `doc_flow_hub`

**版本号：** V1.0

**文档创建日期：** 2023-10-27

---

## **1. 项目概述**

`doc_flow_hub` 是一个基于Python构建的文档管理服务，提供RESTful API，用于自动化归档、版本控制和调取项目文档。核心采用Flask/FastAPI等轻量级Web框架，文件存储初期采用本地文件系统。

## **2. 架构设计**

### **2.1. 系统模块图**

```mermaid
graph TD
    A[外部自动化系统/用户] --> B{API Gateway/Load Balancer}
    B --> C[Web Server (Gunicorn/Uvicorn)]
    C --> D[doc_flow_hub Application]

    D -- "Document Management" --> E[core.py]
    D -- "File I/O" --> F[Storage Module (File System/S3)]
    D -- "API Endpoints" --> G[api_routes.py]
    D -- "Logging" --> H[log.py]
    D -- "Configuration" --> I[config.py]

    subgraph Data
        F -- "Read/Write" --> J[Document Storage (e.g., /data/docs)]
    end

    subgraph Utilities
        H
        I
    end
```

### **2.2. 设计模式**

*   **MVC (Model-View-Controller) / 分层架构：**
    *   **Controller (API Endpoints):** 负责接收HTTP请求，调用业务逻辑。
    *   **Service/Core (core.py):** 封装核心业务逻辑，如文件名解析、文件存储/检索策略。
    *   **Model (Implicit):** 文档的逻辑模型（项目名、版本号、文档类型等）主要通过文件名解析和文件系统结构体现，而非显式的数据库ORM模型。
*   **Repository Pattern (存储模块):** 将文件存储的底层实现（本地文件系统、S3等）抽象化，方便未来切换。
*   **Singleton (配置/日志):** 配置和日志模块可能采用单例模式确保全局一致性。

## **3. 目录结构**

```
doc_flow_hub/
├── doc_flow_hub/
│   ├── __init__.py
│   ├── main.py             # 应用入口，初始化Web框架和注册路由
│   ├── config.py           # 应用程序配置，如存储路径、允许的文档类型
│   ├── log.py              # 日志模块
│   ├── server.py           # 封装Web Server启动逻辑 (如Gunicorn/Uvicorn)
│   ├── core.py             # 核心业务逻辑，文档解析、存储、检索、版本管理
│   ├── api_routes.py       # API路由定义
│   ├── utils.py            # 通用工具函数，如版本号解析排序
│   └── storage/            # 存储模块，抽象文件操作
│       ├── __init__.py
│       └── filesystem.py   # 基于文件系统的存储实现
│       └── base.py         # 存储接口定义 (未来可能扩展S3等)
├── tests/
│   ├── __init__.py
│   ├── test_api.py         # API测试
│   ├── test_core.py        # 核心逻辑测试
│   └── test_utils.py       # 工具函数测试
├── docs/                   # 项目文档（本PRD/LLD）
├── pyproject.toml          # 项目配置 (uv lock/add)
├── README.md
├── .gitignore
```

## **4. 数据模型 (逻辑)**

由于不使用数据库，文档的“数据模型”主要体现在**文件系统结构**和**文件名约定**上。

### **4.1. 文件系统结构**

所有文档将存储在配置的根目录下，按以下层级结构组织：

```
{DOC_STORAGE_ROOT}/
├── {project_name_1}/
│   ├── {version_1}/
│   │   ├── {project_name_1}_{version_1}_PRD.pdf
│   │   ├── {project_name_1}_{version_1}_LLD.pdf
│   │   ├── {project_name_1}_{version_1}_CR_001.pdf
│   │   └── {project_name_1}_{version_1}_USECASE.md
│   ├── {version_2}/
│   │   ├── {project_name_1}_{version_2}_PRD.pdf
│   │   └── {project_name_1}_{version_2}_LLD.pdf
│   └── ...
├── {project_name_2}/
│   ├── {version_A}/
│   └── ...
└── ...
```

### **4.2. 文件命名约定**

`{project_name}_{version}_{doc_type}.{extension}`

*   **`project_name` (字符串):** 项目的唯一标识，例如 `project_phoenix`。
*   **`version` (字符串):** 文档的版本号，例如 `V1.0`。用于版本管理和排序。
    *   对于CR/DCN，通常会包含其关联的主文档（PRD/LLD/USECASE）的版本号，例如 `project_phoenix_V1.0_CR_001.pdf`。这意味着 `_CR_001` 是 `doc_type` 的一部分，或者是 `doc_type_sub_identifier`。为了简化，我们统一在 `doc_type` 部分体现，如 `CR_001` 作为一个整体的文档类型后缀。
*   **`doc_type` (字符串):** 文档的类型。
    *   核心类型：`PRD`, `LLD`, `USECASE`, `CR`, `DCN`。
    *   对于CR/DCN的子标识符，可以将其视为 `doc_type` 的扩展，例如 `CR_001` 或 `DCN_A1`。解析时，系统会识别出 `CR` 或 `DCN`，并将其余部分作为子标识符。
*   **`extension` (字符串):** 文件扩展名，例如 `pdf`, `md`, `docx`。

**文件名解析逻辑 (`core.py`):**

将实现一个函数，如 `parse_filename(filename: str) -> Dict`，返回一个字典，包含 `project_name`, `version`, `doc_type`, `extension` 等信息。

```python
import re

def parse_filename(filename: str) -> dict:
    """
    解析文件名以提取项目名、版本号、文档类型和扩展名。
    约定文件名格式: {project_name}_{version}_{doc_type}.{extension}
    例如: project_phoenix_V1.0_PRD.pdf
          project_phoenix_V1.0_CR_001.pdf
    """
    # 匹配文件名直到最后一个 '.' 之前的部分，以及扩展名
    match = re.match(r'^(.*?)(?:\.([^.]+))?$', filename)
    if not match:
        raise ValueError(f"Invalid filename format: {filename}")

    base_name = match.group(1)
    extension = match.group(2) if match.group(2) else ""

    # 尝试匹配 {project_name}_{version}_{doc_type} 模式
    # 这里的正则表达式需要足够健壮，以处理各种可能的命名情况
    # 假设 project_name, version, doc_type 都不包含 '_'
    # 如果包含 '_'，需要更复杂的解析逻辑或更严格的命名约定
    parts = base_name.split('_')
    if len(parts) < 3:
        raise ValueError(f"Filename does not contain sufficient parts: {filename}")

    # 最简单的解析逻辑，假设前两个是项目名和版本号，其余是文档类型
    project_name = parts[0]
    version = parts[1]
    doc_type = "_".join(parts[2:]) # 拼接剩余部分作为 doc_type，以支持 CR_001 这种
    
    return {
        "project_name": project_name,
        "version": version,
        "doc_type": doc_type,
        "extension": extension,
        "full_filename": filename # 原始文件名
    }

def get_latest_version(versions: list[str]) -> str:
    """
    从版本号列表中获取最新版本。
    简单实现，可以处理 V1.0, V1.1, V2.0 等，但对于复杂语义化版本号需更完善的库。
    """
    # 排序逻辑，目前基于字符串排序，对于复杂版本号（如 V1.0.0, V1.0.1, V1.1.0），
    # 建议使用 packaging.version.parse 进行解析和比较。
    # 这里为了简化，假设版本号形式如 V1.0, V2.0.1，可通过简单字符串比较。
    from packaging.version import parse as parse_version
    
    if not versions:
        return None
    
    return str(max([parse_version(v) for v in versions]))

# 示例：
# info = parse_filename("project_phoenix_V1.0_PRD.pdf")
# print(info) # {'project_name': 'project_phoenix', 'version': 'V1.0', 'doc_type': 'PRD', 'extension': 'pdf', 'full_filename': 'project_phoenix_V1.0_PRD.pdf'}
# info_cr = parse_filename("project_phoenix_V1.0_CR_001.pdf")
# print(info_cr) # {'project_name': 'project_phoenix', 'version': 'V1.0', 'doc_type': 'CR_001', 'extension': 'pdf', 'full_filename': 'project_phoenix_V1.0_CR_001.pdf'}
# latest = get_latest_version(["V1.0", "V1.1", "V2.0", "V1.0.1"])
# print(latest) # V2.0
```

## **5. API 设计**

### **5.1. 基础URL**

`http://<host>:<port>`

### **5.2. API 认证 (未来扩展)**

*   当前版本不实现认证。
*   未来可考虑使用API Key或JWT。

### **5.3. API 端点**

#### **5.3.1. `POST /upload` - 归档文档**

*   **描述：** 上传单个文档文件。
*   **请求方法：** `POST`
*   **请求头：** `Content-Type: multipart/form-data`
*   **请求体：**
    *   `file` (文件): 待上传的文档文件。
*   **请求参数 (Query Parameters):**
    *   `filename` (字符串, 必需): 文件的原始名称，必须符合命名约定。
*   **成功响应：** `HTTP 201 Created`
    ```json
    {
        "message": "Document uploaded successfully",
        "project_name": "project_phoenix",
        "version": "V1.0",
        "doc_type": "PRD",
        "stored_path": "/data/docs/project_phoenix/V1.0/project_phoenix_V1.0_PRD.pdf"
    }
    ```
*   **错误响应：** `HTTP 400 Bad Request` (文件名不符约定), `HTTP 500 Internal Server Error` (存储失败)

#### **5.3.2. `GET /documents` - 调取文档**

*   **描述：** 根据条件获取文档内容。
*   **请求方法：** `GET`
*   **请求参数 (Query Parameters):**
    *   `project_name` (字符串, 必需): 项目名称。
    *   `doc_type` (字符串, 必需): 文档类型 (`PRD`, `LLD`, `CR`, `DCN`, `USECASE`，或 `CR_DCN` 用于获取关联变更文档)。
    *   `version` (字符串, 可选): 指定版本号。如果未提供，且 `latest` 为 `true`，则返回最新版本。
    *   `latest` (布尔, 可选): 如果为 `true`，则返回指定 `project_name` 和 `doc_type` 下的最新版本。默认为 `false`。
*   **成功响应：** `HTTP 200 OK`
    *   **响应头：** `Content-Type: application/octet-stream` (或根据文件类型推断), `X-Document-Filename: <filename>`
    *   **响应体：** 文档的二进制内容。
*   **错误响应：** `HTTP 404 Not Found` (文档不存在), `HTTP 400 Bad Request` (参数组合不合法)

#### **5.3.3. `GET /documents/list` - 列出文档信息**

*   **描述：** 获取已归档文档的列表信息。
*   **请求方法：** `GET`
*   **请求参数 (Query Parameters):**
    *   `project_name` (字符串, 可选): 筛选指定项目的文档。
    *   `doc_type` (字符串, 可选): 筛选指定文档类型的文档。
*   **成功响应：** `HTTP 200 OK`
    ```json
    [
        {
            "project_name": "project_phoenix",
            "version": "V1.0",
            "doc_type": "PRD",
            "filename": "project_phoenix_V1.0_PRD.pdf",
            "size_bytes": 102400,
            "upload_timestamp": "2023-10-27T10:00:00Z",
            "download_url": "/documents?project_name=project_phoenix&version=V1.0&doc_type=PRD"
        },
        {
            "project_name": "project_phoenix",
            "version": "V1.0",
            "doc_type": "CR_001",
            "filename": "project_phoenix_V1.0_CR_001.pdf",
            "size_bytes": 5120,
            "upload_timestamp": "2023-10-27T10:05:00Z",
            "download_url": "/documents?project_name=project_phoenix&version=V1.0&doc_type=CR_001"
        }
        // ...
    ]
    ```
*   **错误响应：** `HTTP 500 Internal Server Error`

## **6. 模块设计**

### **6.1. `core.py` - 核心业务逻辑**

*   **职责：** 封装文档的解析、存储策略调用、版本管理逻辑。
*   **关键函数：**
    *   `upload_document(file_content, filename: str)`:
        *   调用 `parse_filename`。
        *   根据解析结果调用 `storage.save_document`。
        *   管理文件路径和潜在的覆盖逻辑。
    *   `retrieve_document(project_name: str, version: str, doc_type: str, latest: bool = False)`:
        *   如果 `latest` 为 True，先调用 `storage.list_versions` 获取所有版本，然后 `get_latest_version` 确定最新版本路径。
        *   调用 `storage.load_document`。
    *   `list_documents(project_name: str = None, doc_type: str = None)`:
        *   调用 `storage.list_all_documents` 获取所有文档信息。
        *   根据参数进行过滤和格式化。
    *   `get_related_change_documents(project_name: str, version: str, doc_type: str)`:
        *   基于 `project_name` 和 `version` 组合，在存储中查找所有 `CR` 和 `DCN` 类型的文档。
        *   返回匹配的文档列表。

```python
# doc_flow_hub/doc_flow_hub/core.py

import os
import re
from typing import Dict, List, Optional
from datetime import datetime
from packaging.version import parse as parse_version
from .log import get_logger
from .storage.filesystem import FileSystemStorage # 假设默认使用文件系统存储
from .config import DOC_STORAGE_ROOT # 从配置中导入存储根目录

logger = get_logger(__name__)

class DocFlowHubCore:
    def __init__(self):
        # 初始化存储模块，这里硬编码为 FileSystemStorage，未来可配置
        self.storage = FileSystemStorage(DOC_STORAGE_ROOT)
        logger.info(f"DocFlowHubCore initialized with storage root: {DOC_STORAGE_ROOT}")

    def _parse_filename(self, filename: str) -> Dict:
        """
        解析文件名以提取项目名、版本号、文档类型和扩展名。
        约定文件名格式: {project_name}_{version}_{doc_type}.{extension}
        例如: project_phoenix_V1.0_PRD.pdf
              project_phoenix_V1.0_CR_001.pdf
        """
        match = re.match(r'^(.*?)(?:\.([^.]+))?$', filename)
        if not match:
            logger.error(f"Invalid filename format: {filename}")
            raise ValueError(f"Invalid filename format: {filename}")

        base_name = match.group(1)
        extension = match.group(2) if match.group(2) else ""

        parts = base_name.split('_')
        if len(parts) < 3: # 至少需要 project_name, version, doc_type
            logger.error(f"Filename does not contain sufficient parts for parsing: {filename}")
            raise ValueError(f"Filename does not contain sufficient parts: {filename}")

        project_name = parts[0]
        version = parts[1]
        doc_type_raw = "_".join(parts[2:]) # 拼接剩余部分作为 doc_type，以支持 CR_001 这种

        # 对 doc_type 进行规范化，例如只保留 PRD, LLD, CR, DCN, USECASE
        # 对于 CR_001, DCN_xyz 等，我们只关心 CR 或 DCN 的主类型
        doc_type_main = doc_type_raw.split('_')[0].upper() # 取第一个下划线前的部分，并转大写

        if doc_type_main not in ["PRD", "LLD", "CR", "DCN", "USECASE"]:
            logger.warning(f"Unknown main document type extracted: {doc_type_main} from {filename}")
            # 可以抛出错误，也可以允许未知类型，取决于业务需求。这里暂时允许，但在PRD中已明确类型。
            # 如果严格要求已知类型，可以在这里抛出 ValueError

        return {
            "project_name": project_name,
            "version": version,
            "doc_type": doc_type_main, # 规范化后的主类型
            "sub_type_identifier": doc_type_raw if doc_type_main in ["CR", "DCN"] else None, # 原始全类型作为子标识符
            "extension": extension,
            "original_filename": filename
        }

    def upload_document(self, file_content: bytes, filename: str) -> Dict:
        """
        上传文档并归档。
        :param file_content: 文档的二进制内容。
        :param filename: 文档的文件名，必须符合约定。
        :return: 归档后的文档信息。
        :raises ValueError: 如果文件名不符合约定。
        :raises IOError: 如果文件存储失败。
        """
        try:
            parsed_info = self._parse_filename(filename)
        except ValueError as e:
            logger.error(f"Failed to parse filename '{filename}': {e}")
            raise ValueError(f"Invalid filename: {e}")

        project_name = parsed_info['project_name']
        version = parsed_info['version']
        original_filename = parsed_info['original_filename']

        try:
            # 存储模块负责创建目录和保存文件
            stored_path = self.storage.save_document(
                file_content,
                project_name,
                version,
                original_filename
            )
            logger.info(f"Document '{original_filename}' for project '{project_name}' version '{version}' uploaded to {stored_path}")
            return {
                "message": "Document uploaded successfully",
                "project_name": project_name,
                "version": version,
                "doc_type": parsed_info['doc_type'],
                "sub_type_identifier": parsed_info['sub_type_identifier'],
                "original_filename": original_filename,
                "stored_path": stored_path
            }
        except Exception as e:
            logger.exception(f"Failed to save document '{original_filename}': {e}")
            raise IOError(f"Failed to save document: {e}")

    def retrieve_document(self, project_name: str, doc_type: str, version: Optional[str] = None, latest: bool = False) -> Dict:
        """
        调取指定文档。
        :param project_name: 项目名称。
        :param doc_type: 文档类型（PRD, LLD, CR, DCN, USECASE）。
        :param version: 指定版本号。
        :param latest: 是否获取最新版本。
        :return: 包含文档内容和元数据的字典。
        :raises FileNotFoundError: 如果文档不存在。
        :raises ValueError: 如果参数组合不合法。
        """
        if latest and version:
            raise ValueError("Cannot specify both 'version' and 'latest=True'.")
        if not latest and not version:
            # 如果没有指定版本号也没有指定latest，默认获取最新版本
            latest = True
            logger.info(f"Neither version nor latest=True specified for {project_name}/{doc_type}, defaulting to latest.")

        target_version = version
        target_filename = None # 如果是精确查找，可以根据类型和版本构造文件名，但最好直接从存储中查找

        if latest:
            # 获取该项目和文档类型的所有版本信息
            all_doc_files_info = self.storage.list_documents_in_project_version(project_name)
            
            # 过滤出指定 doc_type 的文件
            matching_docs = []
            for doc_info in all_doc_files_info:
                try:
                    parsed = self._parse_filename(doc_info['filename'])
                    if parsed['project_name'] == project_name and parsed['doc_type'] == doc_type.upper():
                        matching_docs.append((parsed['version'], doc_info['filename']))
                except ValueError:
                    continue # 忽略不符合命名约定的文件

            if not matching_docs:
                logger.warning(f"No documents found for project '{project_name}' and type '{doc_type}'.")
                raise FileNotFoundError(f"No documents found for project '{project_name}' and type '{doc_type}'.")

            # 找到最新版本
            # 使用 packaging.version 库进行版本解析和比较，更健壮
            versions_parsed = [(parse_version(v), filename) for v, filename in matching_docs]
            latest_version_parsed, latest_filename = max(versions_parsed, key=lambda x: x[0])
            target_version = str(latest_version_parsed)
            target_filename = latest_filename
            logger.info(f"Found latest version '{target_version}' for '{project_name}' '{doc_type}' as '{target_filename}'.")
        else:
            # 精确查找，需要根据文件名约定来推断文件名，或者更健壮地查询文件系统
            # 简化：假设我们会通过文件名 {project_name}_{version}_{doc_type}.{ext} 来定位
            # 但实际上，如果 doc_type 是 CR_001 这种，需要原始的 full_doc_type
            # 这里需要从存储层获取所有文件，然后过滤匹配
            all_doc_files_info = self.storage.list_documents_in_project_version(project_name, target_version)
            
            found_file = None
            for doc_info in all_doc_files_info:
                try:
                    parsed = self._parse_filename(doc_info['filename'])
                    # 严格匹配项目名、版本、主文档类型
                    if (parsed['project_name'] == project_name and
                        parsed['version'] == target_version and
                        parsed['doc_type'] == doc_type.upper()):
                        found_file = doc_info['filename']
                        break
                except ValueError:
                    continue

            if not found_file:
                logger.warning(f"Document '{project_name}_{target_version}_{doc_type}' not found.")
                raise FileNotFoundError(f"Document '{project_name}_{target_version}_{doc_type}' not found.")
            target_filename = found_file


        try:
            file_content, stored_path = self.storage.load_document(project_name, target_version, target_filename)
            return {
                "file_content": file_content,
                "filename": target_filename,
                "stored_path": stored_path,
                "project_name": project_name,
                "version": target_version,
                "doc_type": doc_type
            }
        except FileNotFoundError:
            logger.error(f"Document file not found at expected path for '{target_filename}'.")
            raise

    def list_documents(self, project_name: Optional[str] = None, doc_type: Optional[str] = None) -> List[Dict]:
        """
        列出所有或符合条件的文档信息。
        """
        all_docs_info = self.storage.list_all_documents_metadata()
        
        filtered_docs = []
        for doc_info in all_docs_info:
            try:
                parsed = self._parse_filename(doc_info['filename'])
                if (project_name is None or parsed['project_name'] == project_name) and \
                   (doc_type is None or parsed['doc_type'] == doc_type.upper()):
                    filtered_docs.append({
                        "project_name": parsed['project_name'],
                        "version": parsed['version'],
                        "doc_type": parsed['doc_type'],
                        "sub_type_identifier": parsed['sub_type_identifier'],
                        "filename": parsed['original_filename'],
                        "size_bytes": doc_info.get('size', 0),
                        "upload_timestamp": doc_info.get('last_modified', datetime.now()).isoformat() + "Z", # 假设存储层提供
                        "download_url": f"/documents?project_name={parsed['project_name']}&version={parsed['version']}&doc_type={parsed['doc_type']}" # 构造下载URL
                    })
            except ValueError:
                logger.warning(f"Skipping malformed filename in list_documents: {doc_info['filename']}")
                continue # 忽略无法解析的文件名

        return filtered_docs

    def get_related_change_documents(self, project_name: str, version: str, primary_doc_type: str) -> List[Dict]:
        """
        获取与指定主文档（PRD/LLD/USECASE）关联的CR和DCN文档。
        关联逻辑：查找文件名中包含相同 {project_name}_{version} 前缀的 CR 和 DCN 文档。
        """
        all_doc_files_info = self.storage.list_documents_in_project_version(project_name, version)
        
        related_docs = []
        for doc_info in all_doc_files_info:
            try:
                parsed = self._parse_filename(doc_info['filename'])
                if (parsed['project_name'] == project_name and
                    parsed['version'] == version and
                    parsed['doc_type'] in ["CR", "DCN"]):
                    
                    related_docs.append({
                        "project_name": parsed['project_name'],
                        "version": parsed['version'],
                        "doc_type": parsed['doc_type'],
                        "sub_type_identifier": parsed['sub_type_identifier'],
                        "filename": parsed['original_filename'],
                        "size_bytes": doc_info.get('size', 0),
                        "upload_timestamp": doc_info.get('last_modified', datetime.now()).isoformat() + "Z",
                        "download_url": f"/documents?project_name={parsed['project_name']}&version={parsed['version']}&doc_type={parsed['doc_type']}&filename={parsed['original_filename']}" # 增加 filename 参数以精确匹配
                    })
            except ValueError:
                continue

        logger.info(f"Found {len(related_docs)} related change documents for {project_name} V{version} {primary_doc_type}")
        return related_docs

```

### **6.2. `storage/filesystem.py` - 文件系统存储实现**

*   **职责：** 处理具体的文件系统操作，如创建目录、读写文件、列举文件。
*   **关键函数：**
    *   `save_document(file_content, project_name, version, filename)`: 负责将文件内容写入到 `DOC_STORAGE_ROOT/{project_name}/{version}/{filename}` 路径。
    *   `load_document(project_name, version, filename)`: 从指定路径读取文件内容。
    *   `list_documents_in_project_version(project_name, version)`: 列出特定项目和版本目录下的所有文件。
    *   `list_all_documents_metadata()`: 递归遍历 `DOC_STORAGE_ROOT`，收集所有文档的文件名、路径、大小、修改时间等元数据。

```python
# doc_flow_hub/doc_flow_hub/storage/filesystem.py

import os
from typing import List, Dict, Tuple, Optional
from ..log import get_logger

logger = get_logger(__name__)

class FileSystemStorage:
    def __init__(self, base_path: str):
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True) # 确保根目录存在
        logger.info(f"FileSystemStorage initialized with base path: {self.base_path}")

    def _get_doc_dir(self, project_name: str, version: str) -> str:
        """
        获取文档存储的目录路径。
        """
        doc_dir = os.path.join(self.base_path, project_name, version)
        os.makedirs(doc_dir, exist_ok=True) # 确保目录存在
        return doc_dir

    def save_document(self, file_content: bytes, project_name: str, version: str, filename: str) -> str:
        """
        将文档保存到文件系统。
        :param file_content: 文档的二进制内容。
        :param project_name: 项目名称。
        :param version: 版本号。
        :param filename: 文件的原始名称。
        :return: 文档的完整存储路径。
        """
        doc_dir = self._get_doc_dir(project_name, version)
        file_path = os.path.join(doc_dir, filename)
        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
            logger.debug(f"Document '{filename}' saved to {file_path}")
            return file_path
        except IOError as e:
            logger.error(f"Failed to save document '{filename}' to '{file_path}': {e}")
            raise

    def load_document(self, project_name: str, version: str, filename: str) -> Tuple[bytes, str]:
        """
        从文件系统加载文档内容。
        :param project_name: 项目名称。
        :param version: 版本号。
        :param filename: 文件的原始名称。
        :return: 文档的二进制内容和文件完整路径。
        """
        file_path = os.path.join(self._get_doc_dir(project_name, version), filename)
        if not os.path.exists(file_path):
            logger.warning(f"Document not found at path: {file_path}")
            raise FileNotFoundError(f"Document '{filename}' not found for project '{project_name}' version '{version}'.")
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            logger.debug(f"Document '{filename}' loaded from {file_path}")
            return content, file_path
        except IOError as e:
            logger.error(f"Failed to load document from '{file_path}': {e}")
            raise

    def list_documents_in_project_version(self, project_name: str, version: Optional[str] = None) -> List[Dict]:
        """
        列出特定项目下所有版本或特定版本下的所有文档文件名和元数据。
        :param project_name: 项目名称。
        :param version: 可选，如果提供，则只列出该版本下的文档。
        :return: 包含文档文件名和路径的列表。
        """
        project_path = os.path.join(self.base_path, project_name)
        if not os.path.exists(project_path):
            return []

        docs_info = []
        if version:
            # 查找特定版本
            version_path = os.path.join(project_path, version)
            if os.path.exists(version_path):
                for filename in os.listdir(version_path):
                    file_path = os.path.join(version_path, filename)
                    if os.path.isfile(file_path):
                        docs_info.append({
                            "filename": filename,
                            "path": file_path,
                            "size": os.path.getsize(file_path),
                            "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path))
                        })
        else:
            # 查找所有版本（用于最新版本查找等）
            for v_name in os.listdir(project_path):
                v_path = os.path.join(project_path, v_name)
                if os.path.isdir(v_path):
                    for filename in os.listdir(v_path):
                        file_path = os.path.join(v_path, filename)
                        if os.path.isfile(file_path):
                            docs_info.append({
                                "filename": filename,
                                "path": file_path,
                                "size": os.path.getsize(file_path),
                                "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path))
                            })
        logger.debug(f"Listed {len(docs_info)} documents for project '{project_name}' version '{version if version else 'all'}'.")
        return docs_info

    def list_all_documents_metadata(self) -> List[Dict]:
        """
        递归遍历所有存储的文档并返回它们的元数据。
        """
        all_docs = []
        for root, dirs, files in os.walk(self.base_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                try:
                    relative_path = os.path.relpath(file_path, self.base_path)
                    # 从相对路径中提取 project_name 和 version，为了兼容文件名解析，这里直接返回 filename
                    # 更健壮的方案是从 filename 解析出 project_name 和 version
                    
                    # 假定路径结构是 project_name/version/filename
                    path_parts = relative_path.split(os.sep)
                    if len(path_parts) >= 3: # 至少有 project_name, version, filename
                        project_name = path_parts[0]
                        version = path_parts[1]
                    else:
                        project_name = "unknown"
                        version = "unknown"

                    all_docs.append({
                        "filename": filename,
                        "path": file_path,
                        "project_name_from_path": project_name, # 辅助信息
                        "version_from_path": version, # 辅助信息
                        "size": os.path.getsize(file_path),
                        "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path))
                    })
                except Exception as e:
                    logger.error(f"Error processing file '{file_path}' for metadata: {e}")
        logger.debug(f"Listed total {len(all_docs)} documents metadata.")
        return all_docs
```

## **7. 错误处理**

*   **API层面：**
    *   使用标准HTTP状态码（400 Bad Request, 404 Not Found, 500 Internal Server Error）。
    *   返回JSON格式的错误信息，包含 `code`, `message`, `details`。
*   **应用层面：**
    *   使用Python异常机制。
    *   捕获特定异常并转换为友好的错误信息。
    *   记录详细的错误日志。

## **8. 测试策略**

*   **单元测试：** 针对 `core.py` (文件名解析、版本排序等), `storage/filesystem.py` (文件读写) 中的关键函数进行测试。
*   **集成测试：** 测试API端点与核心业务逻辑的集成，使用HTTP客户端模拟请求。
*   **端到端测试：** 模拟完整的上传、下载、查询流程。
*   **Mocking：** 在单元测试中，使用 `unittest.mock` 模拟文件系统操作、外部依赖等。

## **9. 部署考虑**

*   **容器化：** 推荐使用Docker进行容器化部署，简化环境配置。
*   **Web Server：** 使用Gunicorn/Uvicorn作为生产环境的WSGI/ASGI服务器。
*   **存储挂载：** 文档存储路径通过Docker volume挂载到宿主机或网络存储。
*   **日志收集：** 将日志输出到标准输出，配合Loguru/ELK等日志系统收集。

## **10. 示例**

### **10.1. 核心用例示例 (伪代码)**

#### **上传文档**

```python
# In main.py or api_routes.py
from doc_flow_hub.core import DocFlowHubCore

app = Flask(__name__) # 或 FastAPI

doc_core = DocFlowHubCore()

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"code": "INVALID_INPUT", "message": "No file part in the request"}), 400
    
    file = request.files['file']
    filename = request.args.get('filename') or file.filename # 从参数或文件对象获取文件名
    
    if not filename:
        return jsonify({"code": "INVALID_INPUT", "message": "Filename not provided"}), 400

    try:
        file_content = file.read()
        result = doc_core.upload_document(file_content, filename)
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"code": "FILENAME_ERROR", "message": str(e)}), 400
    except IOError as e:
        return jsonify({"code": "STORAGE_ERROR", "message": str(e)}), 500
    except Exception as e:
        return jsonify({"code": "UNKNOWN_ERROR", "message": str(e)}), 500

```

#### **获取最新 PRD**

```python
# In main.py or api_routes.py
from flask import send_file # 或 FastAPI StreamingResponse

@app.route('/documents', methods=['GET'])
def get_document():
    project_name = request.args.get('project_name')
    doc_type = request.args.get('doc_type')
    version = request.args.get('version')
    latest = request.args.get('latest', 'false').lower() == 'true'

    if not all([project_name, doc_type]):
        return jsonify({"code": "INVALID_INPUT", "message": "project_name and doc_type are required"}), 400

    try:
        doc_info = doc_core.retrieve_document(project_name, doc_type, version, latest)
        
        # 使用 send_file 或 StreamingResponse 返回文件
        response = make_response(doc_info['file_content'])
        response.headers['Content-Type'] = 'application/octet-stream' # 实际应根据文件扩展名设置MIME类型
        response.headers['Content-Disposition'] = f'attachment; filename="{doc_info["filename"]}"'
        response.headers['X-Document-Filename'] = doc_info['filename'] # 自定义头方便客户端获取文件名
        return response
    except ValueError as e:
        return jsonify({"code": "INVALID_PARAMS", "message": str(e)}), 400
    except FileNotFoundError as e:
        return jsonify({"code": "NOT_FOUND", "message": str(e)}), 404
    except Exception as e:
        return jsonify({"code": "UNKNOWN_ERROR", "message": str(e)}), 500

```

#### **获取关联 CR/DCN**

```python
# In main.py or api_routes.py

@app.route('/documents/related_changes', methods=['GET'])
def get_related_changes():
    project_name = request.args.get('project_name')
    version = request.args.get('version')
    doc_type = request.args.get('doc_type') # 主文档类型，例如 PRD, LLD, USECASE

    if not all([project_name, version, doc_type]):
        return jsonify({"code": "INVALID_INPUT", "message": "project_name, version, and doc_type are required"}), 400

    try:
        related_docs = doc_core.get_related_change_documents(project_name, version, doc_type)
        return jsonify(related_docs), 200
    except Exception as e:
        return jsonify({"code": "UNKNOWN_ERROR", "message": str(e)}), 500

```

### **10.2. 测试代码 (基于 Pytest)**

```python
# tests/test_core.py
import pytest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

# 导入 core 模块，假设是 doc_flow_hub.doc_flow_hub.core
from doc_flow_hub.doc_flow_hub.core import DocFlowHubCore
from doc_flow_hub.doc_flow_hub.config import DOC_STORAGE_ROOT # 确保 config 可访问

# 创建一个临时的存储目录用于测试
@pytest.fixture(scope="module")
def temp_storage_root(tmp_path_factory):
    # tmp_path_factory 是 pytest 提供的创建临时目录的工厂
    temp_dir = tmp_path_factory.mktemp("doc_test_storage")
    # 模拟 config 中的 DOC_STORAGE_ROOT
    with patch('doc_flow_hub.doc_flow_hub.config.DOC_STORAGE_ROOT', str(temp_dir)):
        yield str(temp_dir)
    # 测试结束后清理临时目录
    # 由于 tmp_path_factory 会自动清理，这里无需额外处理

@pytest.fixture(scope="function")
def doc_core_instance(temp_storage_root):
    # 为每个测试函数创建新的 DocFlowHubCore 实例，确保测试隔离
    core = DocFlowHubCore()
    # 清理每个测试开始前目录内容，确保测试环境干净
    # 实际 FileSystemStorage 会在每次 __init__ 时确保目录存在，但文件内容需要清理
    for root, dirs, files in os.walk(temp_storage_root, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    yield core


def test_parse_filename_valid():
    core = DocFlowHubCore() # _parse_filename 是内部方法，但可以独立测试
    
    info = core._parse_filename("projectA_V1.0_PRD.pdf")
    assert info['project_name'] == "projectA"
    assert info['version'] == "V1.0"
    assert info['doc_type'] == "PRD"
    assert info['extension'] == "pdf"
    assert info['original_filename'] == "projectA_V1.0_PRD.pdf"

    info_cr = core._parse_filename("projectB_V2.1_CR_007.md")
    assert info_cr['project_name'] == "projectB"
    assert info_cr['version'] == "V2.1"
    assert info_cr['doc_type'] == "CR" # 规范化后的主类型
    assert info_cr['sub_type_identifier'] == "CR_007" # 原始全类型
    assert info_cr['extension'] == "md"

    info_usecase = core._parse_filename("proj_C_V3.0.1_USECASE.txt")
    assert info_usecase['project_name'] == "proj_C"
    assert info_usecase['version'] == "V3.0.1"
    assert info_usecase['doc_type'] == "USECASE"
    assert info_usecase['extension'] == "txt"

def test_parse_filename_invalid():
    core = DocFlowHubCore()
    with pytest.raises(ValueError, match="Invalid filename format"):
        core._parse_filename("invalid_filename")
    with pytest.raises(ValueError, match="does not contain sufficient parts"):
        core._parse_filename("projectA_V1.0.pdf") # 缺少 doc_type


def test_upload_document(doc_core_instance, temp_storage_root):
    file_content = b"This is a test PRD content."
    filename = "test_proj_V1.0_PRD.txt"

    result = doc_core_instance.upload_document(file_content, filename)
    
    assert result['message'] == "Document uploaded successfully"
    assert result['project_name'] == "test_proj"
    assert result['version'] == "V1.0"
    assert result['doc_type'] == "PRD"
    assert "stored_path" in result
    
    # 验证文件是否实际存在于存储路径
    expected_path = os.path.join(temp_storage_root, "test_proj", "V1.0", filename)
    assert os.path.exists(expected_path)
    with open(expected_path, 'rb') as f:
        assert f.read() == file_content

def test_retrieve_document_exact_version(doc_core_instance):
    file_content_v1 = b"Content of V1.0 PRD."
    doc_core_instance.upload_document(file_content_v1, "proj_X_V1.0_PRD.pdf")
    
    retrieved = doc_core_instance.retrieve_document("proj_X", "PRD", version="V1.0")
    assert retrieved['file_content'] == file_content_v1
    assert retrieved['filename'] == "proj_X_V1.0_PRD.pdf"
    assert retrieved['version'] == "V1.0"


def test_retrieve_document_latest_version(doc_core_instance):
    doc_core_instance.upload_document(b"Content V1.0", "proj_Y_V1.0_LLD.doc")
    doc_core_instance.upload_document(b"Content V1.1", "proj_Y_V1.1_LLD.doc")
    doc_core_instance.upload_document(b"Content V2.0", "proj_Y_V2.0_LLD.doc")
    
    retrieved = doc_core_instance.retrieve_document("proj_Y", "LLD", latest=True)
    assert retrieved['file_content'] == b"Content V2.0"
    assert retrieved['filename'] == "proj_Y_V2.0_LLD.doc"
    assert retrieved['version'] == "V2.0"

    doc_core_instance.upload_document(b"Content V2.0.1", "proj_Y_V2.0.1_LLD.doc")
    retrieved = doc_core_instance.retrieve_document("proj_Y", "LLD", latest=True)
    assert retrieved['file_content'] == b"Content V2.0.1"
    assert retrieved['filename'] == "proj_Y_V2.0.1_LLD.doc"
    assert retrieved['version'] == "V2.0.1"


def test_retrieve_document_not_found(doc_core_instance):
    with pytest.raises(FileNotFoundError):
        doc_core_instance.retrieve_document("nonexistent_proj", "PRD", version="V1.0")
    
    doc_core_instance.upload_document(b"Content", "actual_proj_V1.0_PRD.pdf")
    with pytest.raises(FileNotFoundError):
        doc_core_instance.retrieve_document("actual_proj", "LLD", version="V1.0") # Wrong doc type
    with pytest.raises(FileNotFoundError):
        doc_core_instance.retrieve_document("actual_proj", "PRD", version="V2.0") # Wrong version

def test_list_documents(doc_core_instance):
    doc_core_instance.upload_document(b"A1", "proj_L_V1.0_PRD.pdf")
    doc_core_instance.upload_document(b"A2", "proj_L_V1.1_LLD.doc")
    doc_core_instance.upload_document(b"B1", "proj_M_V1.0_PRD.pdf")
    doc_core_instance.upload_document(b"A3", "proj_L_V1.0_CR_001.pdf") # Add a CR

    all_docs = doc_core_instance.list_documents()
    assert len(all_docs) == 4
    
    proj_l_docs = doc_core_instance.list_documents(project_name="proj_L")
    assert len(proj_l_docs) == 3
    assert any(d['filename'] == "proj_L_V1.0_PRD.pdf" for d in proj_l_docs)
    assert any(d['filename'] == "proj_L_V1.1_LLD.doc" for d in proj_l_docs)
    assert any(d['filename'] == "proj_L_V1.0_CR_001.pdf" for d in proj_l_docs)

    prd_docs = doc_core_instance.list_documents(doc_type="PRD")
    assert len(prd_docs) == 2
    assert any(d['filename'] == "proj_L_V1.0_PRD.pdf" for d in prd_docs)
    assert any(d['filename'] == "proj_M_V1.0_PRD.pdf" for d in prd_docs)

    proj_l_prd_docs = doc_core_instance.list_documents(project_name="proj_L", doc_type="PRD")
    assert len(proj_l_prd_docs) == 1
    assert proj_l_prd_docs[0]['filename'] == "proj_L_V1.0_PRD.pdf"

def test_get_related_change_documents(doc_core_instance):
    doc_core_instance.upload_document(b"P1", "proj_Z_V1.0_PRD.pdf")
    doc_core_instance.upload_document(b"L1", "proj_Z_V1.0_LLD.pdf")
    doc_core_instance.upload_document(b"C1", "proj_Z_V1.0_CR_001.pdf")
    doc_core_instance.upload_document(b"C2", "proj_Z_V1.0_CR_002.pdf")
    doc_core_instance.upload_document(b"D1", "proj_Z_V1.0_DCN_A.pdf")
    doc_core_instance.upload_document(b"P2", "proj_Z_V1.1_PRD.pdf") # Different version
    doc_core_instance.upload_document(b"C3", "proj_Z_V1.1_CR_001.pdf") # Different version

    # Get related changes for V1.0 PRD
    related_docs = doc_core_instance.get_related_change_documents("proj_Z", "V1.0", "PRD")
    assert len(related_docs) == 3
    filenames = {d['filename'] for d in related_docs}
    assert "proj_Z_V1.0_CR_001.pdf" in filenames
    assert "proj_Z_V1.0_CR_002.pdf" in filenames
    assert "proj_Z_V1.0_DCN_A.pdf" in filenames
    # PRD/LLD本身不应该被返回
    assert "proj_Z_V1.0_PRD.pdf" not in filenames
    assert "proj_Z_V1.0_LLD.pdf" not in filenames
    assert "proj_Z_V1.1_CR_001.pdf" not in filenames # 确保只关联V1.0

    # Get related changes for V1.1 PRD
    related_docs_v1_1 = doc_core_instance.get_related_change_documents("proj_Z", "V1.1", "PRD")
    assert len(related_docs_v1_1) == 1
    assert related_docs_v1_1[0]['filename'] == "proj_Z_V1.1_CR_001.pdf"

    # No related changes for a non-existent project/version
    no_docs = doc_core_instance.get_related_change_documents("nonexistent", "V1.0", "PRD")
    assert len(no_docs) == 0

```

## **11. 文档版本历史**

| 版本号 | 日期         | 描述             |
| :----- | :----------- | :--------------- |
| V1.0   | 2023-10-27   | 初始版本，包含PRD和LLD |
