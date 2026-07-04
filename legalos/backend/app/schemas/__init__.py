"""Pydantic request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models import PlanTier, UserRole


# --- Auth ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = ""
    organization: str = ""  # creates a tenant; empty = personal workspace (Free HR)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    tenant_id: uuid.UUID

    model_config = {"from_attributes": True}


# --- Chat ---
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=32_000)
    conversation_id: uuid.UUID | None = None
    agent: str = "hr"
    provider: str | None = None  # override default AI provider


class SourceOut(BaseModel):
    chunk_id: str
    score: float
    excerpt: str
    title: str | None = None
    url: str | None = None


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    content: str
    sources: list[dict] = []
    blocked: bool = False


class ConversationOut(BaseModel):
    id: uuid.UUID
    agent: str
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Documents ---
class DocumentOut(BaseModel):
    id: uuid.UUID
    title: str
    category: str
    status: str
    mime_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Search ---
class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=20)


# --- Agents / plans ---
class AgentOut(BaseModel):
    slug: str
    name: str
    description: str
    min_tier: PlanTier
    available: bool


class PlanOut(BaseModel):
    tier: PlanTier
    messages_per_day: int
    documents_per_day: int
    max_users: int
    document_upload: bool
    corporate_knowledge_base: bool
    multi_agent: bool
    agents: list[str]


# --- Legislation ---
class ActOut(BaseModel):
    id: uuid.UUID
    source: str
    title: str
    url: str
    act_type: str
    current_revision: int
    last_checked_at: datetime | None

    model_config = {"from_attributes": True}


class TrackActRequest(BaseModel):
    title: str
    url: str
    source: str = "lex.uz"
    act_type: str = "law"
