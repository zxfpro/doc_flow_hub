from fastapi import FastAPI
from doc_flow_hub.api_routes import router
from doc_flow_hub.log import get_logger
import uvicorn

logger = get_logger(__name__)

def create_app():
    app = FastAPI()
    app.include_router(router)
    logger.info("FastAPI application created and router included.")
    return app

app = create_app()

if __name__ == '__main__':
    # 在开发环境中直接运行，生产环境应使用Gunicorn/Uvicorn
    logger.info("Starting FastAPI application in development mode.")
    uvicorn.run(app, host="0.0.0.0", port=5000)