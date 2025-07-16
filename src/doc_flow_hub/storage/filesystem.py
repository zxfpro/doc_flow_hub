import os
from typing import List, Dict, Tuple, Optional
from doc_flow_hub.log import get_logger
from datetime import datetime # 导入 datetime

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