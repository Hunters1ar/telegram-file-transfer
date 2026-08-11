from fastapi import APIRouter
from app.gateway.api.v1.files import router as files_router
from app.gateway.api.v1.upload import router as upload_router
from app.gateway.api.v1.download import router as download_router
from app.gateway.api.v1.analytics import router as analytics_router
from app.gateway.api.v1.folders import router as folders_router

router = APIRouter()

router.include_router(files_router, prefix="/files", tags=["Files"])
router.include_router(upload_router, prefix="/upload", tags=["Upload"])
router.include_router(download_router, prefix="/download", tags=["Download"])
router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
router.include_router(folders_router, prefix="/folders", tags=["Folders"])
