from doc_flow_hub.main import create_app
from doc_flow_hub.log import get_logger
import uvicorn

logger = get_logger(__name__)

# 创建FastAPI应用实例
app = create_app()

if __name__ == '__main__':
    # 生产环境建议使用Gunicorn或Uvicorn等ASGI服务器
    # 例如，使用Uvicorn: uvicorn doc_flow_hub.server:app --host 0.0.0.0 --port 5000
    logger.info("Starting FastAPI application using Uvicorn development server.")
    uvicorn.run(app, host='0.0.0.0', port=5000)