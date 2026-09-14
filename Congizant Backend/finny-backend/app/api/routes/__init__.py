from fastapi import APIRouter
from app.api.routes.upload import router as upload_router
from app.api.routes.documents import router as documents_router
from app.api.routes.validation import router as validation_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.agent1 import router as agent1_router
from app.api.routes.ml import router as ml_router
from app.api.routes.agent2 import router as agent2_router
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(upload_router, prefix="/documents", tags=["Upload"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(validation_router, prefix="/validation", tags=["Validation"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(agent1_router, prefix="/agent1", tags=["Agent 1"])
api_router.include_router(ml_router, prefix="/ml", tags=["ML Anomaly Detection"])
api_router.include_router(agent2_router, prefix="/agent2", tags=["Agent 2"])
api_router.include_router(chat_router, prefix="/chat", tags=["AI Chatbot"])
api_router.include_router(reports_router, prefix="/reports", tags=["Reports & History"])
