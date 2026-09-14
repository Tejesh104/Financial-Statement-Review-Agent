"""API routes for AI Chatbot grounded in financial statements."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_optional_user
from app.database.database import get_db
from app.models.chat import ChatMessage
from app.models.financial_data import FinancialData
from app.models.user import User
from app.api.dependencies import get_authorized_document
from app.services.chat.chat_service import GroundedChatbotService

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------- Request / Response Schemas ----------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User question about financial statement")


class ChatResponse(BaseModel):
    reply: str
    verified_data_used: bool
    model: str
    document_id: str
    created_at: str
    grounded: bool = True


class ChatHistoryItem(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ChatHistoryResponse(BaseModel):
    document_id: str
    messages: List[ChatHistoryItem]


# ---------- Endpoints ----------

@router.post(
    "/{document_id}",
    response_model=ChatResponse,
    summary="Ask financial questions to Grounded AI Chatbot",
    description=(
        "Sends a query to Finny AI assistant grounded strictly in verified financial data "
        "and observations of the authenticated user's document."
    )
)
def chat_with_document(
    document_id: str,
    body: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Grounded Chatbot interaction enforcing authorization and document grounding."""
    # 1. Authorize document access (returns 404 if unauthorized or not found)
    doc = get_authorized_document(document_id, db, user)

    # 2. Retrieve financial data
    fin_record = db.query(FinancialData).filter(FinancialData.document_id == doc.id).first()

    # 3. Process message
    result = GroundedChatbotService.process_message(
        user_message=body.message,
        doc=doc,
        fin_record=fin_record,
        user=user,
        db=db,
    )

    return ChatResponse(**result)


@router.get(
    "/{document_id}/history",
    response_model=ChatHistoryResponse,
    summary="Get conversation history for document",
    description="Returns the chat messages exchange between user and assistant for this document."
)
def get_chat_history(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Retrieve message history isolated to this user and document."""
    doc = get_authorized_document(document_id, db, user)

    query = db.query(ChatMessage).filter(ChatMessage.document_id == doc.id)
    if user is not None:
        query = query.filter(ChatMessage.user_id == user.id)

    records = query.order_by(ChatMessage.created_at.asc()).all()

    items = [
        ChatHistoryItem(
            id=r.id,
            role=r.role,
            content=r.content,
            created_at=r.created_at.isoformat()
        )
        for r in records
    ]

    return ChatHistoryResponse(
        document_id=doc.id,
        messages=items
    )


@router.delete(
    "/{document_id}/history",
    summary="Clear conversation history for document",
    description="Deletes all conversation messages for this user and document."
)
def clear_chat_history(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Clear chat history for this user and document."""
    doc = get_authorized_document(document_id, db, user)

    query = db.query(ChatMessage).filter(ChatMessage.document_id == doc.id)
    if user is not None:
        query = query.filter(ChatMessage.user_id == user.id)

    count = query.delete()
    db.commit()

    return {"message": f"Successfully deleted {count} messages.", "document_id": doc.id}
