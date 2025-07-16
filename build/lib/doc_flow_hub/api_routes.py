from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Response
from fastapi.responses import JSONResponse, FileResponse
from doc_flow_hub.core import DocFlowHubCore
from doc_flow_hub.log import get_logger
import os
from typing import Optional

router = APIRouter()
doc_core = DocFlowHubCore()
logger = get_logger(__name__)

@router.post('/upload')
async def upload_document_route(file: UploadFile = File(...), filename: Optional[str] = Query(None)):
    """
    上传单个文档文件。
    """
    if not file:
        logger.error("No file part in the request for upload.")
        raise HTTPException(status_code=400, detail={"code": "INVALID_INPUT", "message": "No file part in the request"})
    
    actual_filename = filename if filename else file.filename
    
    if not actual_filename:
        logger.error("Filename not provided for upload.")
        raise HTTPException(status_code=400, detail={"code": "INVALID_INPUT", "message": "Filename not provided"})

    try:
        file_content = await file.read()
        result = doc_core.upload_document(file_content, actual_filename)
        logger.info(f"Document '{actual_filename}' uploaded successfully.")
        return JSONResponse(content=result, status_code=201)
    except ValueError as e:
        logger.error(f"Filename error during upload for '{actual_filename}': {e}")
        raise HTTPException(status_code=400, detail={"code": "FILENAME_ERROR", "message": str(e)})
    except IOError as e:
        logger.error(f"Storage error during upload for '{actual_filename}': {e}")
        raise HTTPException(status_code=500, detail={"code": "STORAGE_ERROR", "message": str(e)})
    except Exception as e:
        logger.exception(f"Unknown error during upload for '{actual_filename}'.")
        raise HTTPException(status_code=500, detail={"code": "UNKNOWN_ERROR", "message": str(e)})

@router.get('/documents')
async def get_document_route(
    project_name: str = Query(...),
    doc_type: str = Query(...),
    version: Optional[str] = Query(None),
    latest: bool = Query(False)
):
    """
    根据条件获取文档内容。
    """
    if not all([project_name, doc_type]):
        logger.error("Missing project_name or doc_type for document retrieval.")
        raise HTTPException(status_code=400, detail={"code": "INVALID_INPUT", "message": "project_name and doc_type are required"})

    try:
        doc_info = doc_core.retrieve_document(project_name, doc_type, version, latest)
        
        # 尝试根据文件扩展名设置MIME类型
        _, file_extension = os.path.splitext(doc_info['filename'])
        mime_type = {
            '.pdf': 'application/pdf',
            '.md': 'text/markdown',
            '.txt': 'text/plain',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.json': 'application/json',
            # 添加更多MIME类型
        }.get(file_extension.lower(), 'application/octet-stream') # 默认为二进制流
        
        return Response(content=doc_info['file_content'], media_type=mime_type,
                        headers={"Content-Disposition": f'attachment; filename="{doc_info["filename"]}"',
                                 "X-Document-Filename": doc_info['filename']})
    except ValueError as e:
        logger.error(f"Invalid parameters for document retrieval: {e}")
        raise HTTPException(status_code=400, detail={"code": "INVALID_PARAMS", "message": str(e)})
    except FileNotFoundError as e:
        logger.warning(f"Document not found: {e}")
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(e)})
    except Exception as e:
        logger.exception(f"Unknown error during document retrieval for {project_name}/{doc_type}.")
        raise HTTPException(status_code=500, detail={"code": "UNKNOWN_ERROR", "message": str(e)})

@router.get('/documents/list')
async def list_documents_route(
    project_name: Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None)
):
    """
    列出文档信息。
    """
    try:
        docs_list = doc_core.list_documents(project_name, doc_type)
        logger.info(f"Listed {len(docs_list)} documents.")
        return JSONResponse(content=docs_list, status_code=200)
    except Exception as e:
        logger.exception("Unknown error during listing documents.")
        raise HTTPException(status_code=500, detail={"code": "UNKNOWN_ERROR", "message": str(e)})

@router.get('/documents/related_changes')
async def get_related_changes_route(
    project_name: str = Query(...),
    version: str = Query(...),
    doc_type: str = Query(...) # 主文档类型，例如 PRD, LLD, USECASE
):
    """
    获取关联 CR/DCN 文档。
    """
    if not all([project_name, version, doc_type]):
        logger.error("Missing project_name, version, or doc_type for related changes retrieval.")
        raise HTTPException(status_code=400, detail={"code": "INVALID_INPUT", "message": "project_name, version, and doc_type are required"})

    try:
        related_docs = doc_core.get_related_change_documents(project_name, version, doc_type)
        logger.info(f"Retrieved {len(related_docs)} related change documents for {project_name} V{version} {doc_type}.")
        return JSONResponse(content=related_docs, status_code=200)
    except Exception as e:
        logger.exception(f"Unknown error during retrieving related changes for {project_name} V{version} {doc_type}.")
        raise HTTPException(status_code=500, detail={"code": "UNKNOWN_ERROR", "message": str(e)})