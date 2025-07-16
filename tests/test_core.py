import pytest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

# 导入 core 模块，假设是 doc_flow_hub.doc_flow_hub.core
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from doc_flow_hub.core import DocFlowHubCore
from doc_flow_hub.config import DOC_STORAGE_ROOT # 确保 config 可访问

# 创建一个临时的存储目录用于测试
@pytest.fixture(scope="module")
def temp_storage_root(tmp_path_factory):
    # tmp_path_factory 是 pytest 提供的创建临时目录的工厂
    temp_dir = tmp_path_factory.mktemp("doc_test_storage")
    # 模拟 config 中的 DOC_STORAGE_ROOT
    with patch('doc_flow_hub.config.DOC_STORAGE_ROOT', str(temp_dir)):
        yield str(temp_dir)
    # 测试结束后清理临时目录
    # 由于 tmp_path_factory 会自动清理，这里无需额外处理

@pytest.fixture(scope="function")
def doc_core_instance(temp_storage_root):
    # 为每个测试函数创建新的 DocFlowHubCore 实例，确保测试隔离
    core = DocFlowHubCore(storage_root=temp_storage_root)
    # 清理每个测试开始前目录内容，确保测试环境干净
    # 实际 FileSystemStorage 会在每次 __init__ 时确保目录存在，但文件内容需要清理
    for root, dirs, files in os.walk(temp_storage_root, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    yield core


def test_parse_filename_valid(temp_storage_root):
    core = DocFlowHubCore(storage_root=temp_storage_root) # _parse_filename 是内部方法，但可以独立测试
    
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

def test_parse_filename_invalid(temp_storage_root):
    core = DocFlowHubCore(storage_root=temp_storage_root)
    with pytest.raises(ValueError, match="Filename format error"):
        core._parse_filename("invalid_filename")
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