"""
Spider Framework – Pydantic-Schemas für API-Request/Response-Validierung.
"""

from __future__ import annotations
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
import time


def _now_ms() -> int:
    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# Node Schemas
# ---------------------------------------------------------------------------

class NodeCreate(BaseModel):
    """Request-Body zum Erstellen eines neuen Nodes."""
    id: Optional[str] = None          # wird auto-generiert wenn None
    parentId: Optional[str] = None
    name: str
    reasoning: str
    summary: str
    issuer: str
    status: str = "open"
    synonyms: str = ""
    active: bool = True


class NodeUpdate(BaseModel):
    """Request-Body zum Aktualisieren eines Nodes (alle Felder optional)."""
    name: Optional[str] = None
    reasoning: Optional[str] = None
    summary: Optional[str] = None
    issuer: Optional[str] = None
    status: Optional[str] = None
    synonyms: Optional[str] = None
    active: Optional[bool] = None
    reason: str = Field(..., description="Begründung der Änderung (Pflichtfeld für Audit-Log)")


class NodeReject(BaseModel):
    """Request-Body zum Ablehnen eines Nodes."""
    issuer: str
    reason: str


class NodeAccept(BaseModel):
    """Request-Body zum Akzeptieren eines Nodes."""
    issuer: str
    reason: str


class NodeResponse(BaseModel):
    """Response-Schema für einen einzelnen Node."""
    id: str
    parentId: Optional[str]
    active: bool
    reasoning: str
    summary: str
    creationDate: int
    rejectionDate: Optional[int]
    rejectionReason: Optional[str]
    acceptionDate: Optional[int]
    acceptionReason: Optional[str]
    issuer: str
    confidence: float
    reifegrad: float
    status: str
    name: str
    synonyms: str
    lastChange: int

    class Config:
        from_attributes = True


class NodeTreeResponse(NodeResponse):
    """Node mit verschachtelten Children."""
    children: List["NodeTreeResponse"] = []

    class Config:
        from_attributes = True


NodeTreeResponse.model_rebuild()


# ---------------------------------------------------------------------------
# Action Schemas
# ---------------------------------------------------------------------------

class ActionCreate(BaseModel):
    """Request-Body zum manuellen Erstellen einer Action."""
    knotenId: str
    issuer: str
    reason: str
    actionDescription: str
    change: str = "{}"            # JSON-String der Änderungen


class ActionResponse(BaseModel):
    """Response-Schema für eine Action."""
    id: str
    date: int
    knotenId: str
    issuer: str
    reason: str
    actionDescription: str
    change: str

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Generische Responses
# ---------------------------------------------------------------------------

class SuccessResponse(BaseModel):
    success: bool = True
    message: str = ""


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


class TreeStatsResponse(BaseModel):
    """Statistiken über den aktuellen Planungsbaum."""
    total_nodes: int
    active_nodes: int
    rejected_nodes: int
    accepted_nodes: int
    open_nodes: int
    in_progress_nodes: int
    root_reifegrad: float
    root_confidence: float
    completion_percentage: float      # root_reifegrad * 100

