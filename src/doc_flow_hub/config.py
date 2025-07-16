import os

# 文档存储的根目录
# 建议在生产环境中通过环境变量配置
DOC_STORAGE_ROOT = os.getenv("DOC_STORAGE_ROOT", "data/docs")

# 允许的文档类型
ALLOWED_DOC_TYPES = ["PRD", "LLD", "USECASE", "CR", "DCN"]

# API 认证 (未来扩展)
# API_KEYS = {"your_api_key": "your_api_secret"}