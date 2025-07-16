import os
import re
from typing import Dict, List, Optional
from datetime import datetime
from packaging.version import parse as parse_version
from doc_flow_hub.log import get_logger
from doc_flow_hub.storage.filesystem import FileSystemStorage # 假设默认使用文件系统存储
from doc_flow_hub.config import DOC_STORAGE_ROOT # 从配置中导入存储根目录

logger = get_logger(__name__)

class DocFlowHubCore:
    def __init__(self, storage_root: Optional[str] = None):
        # 初始化存储模块，这里硬编码为 FileSystemStorage，未来可配置
        # 如果提供了 storage_root，则使用它，否则使用默认配置
        actual_storage_root = storage_root if storage_root is not None else DOC_STORAGE_ROOT
        self.storage = FileSystemStorage(actual_storage_root)
        logger.info(f"DocFlowHubCore initialized with storage root: {actual_storage_root}")

    def _parse_filename(self, filename: str) -> Dict:
        """
        解析文件名以提取项目名、版本号、文档类型和扩展名。
        约定文件名格式: {project_name}_{version}_{doc_type}.{extension}
        例如: project_phoenix_V1.0_PRD.pdf
              project_phoenix_V1.0_CR_001.pdf
        """
        # 新的正则表达式来解析文件名
        # 格式: {project_name}_V{version}_{doc_type}.{extension}
        # project_name 可以包含下划线，version 必须以 V 开头，doc_type 可以包含下划线
        regex = r"^(?P<project_name>.*?)_V(?P<version>\d+\.\d+(?:\.\d+)?(?:[a-zA-Z]\d*)?)_(?P<doc_type>.*?)(?:\.(?P<extension>[^.]+))?$"
        match = re.match(regex, filename)

        if not match:
            logger.error(f"Filename format error: {filename}")
            raise ValueError(f"Filename format error: {filename}")

        project_name = match.group('project_name')
        version = "V" + match.group('version')
        doc_type_raw = match.group('doc_type')
        extension = match.group('extension') if match.group('extension') else ""

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
            target_version = "V" + str(latest_version_parsed)
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