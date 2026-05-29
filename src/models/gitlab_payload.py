"""
MergeMind — GitLab Webhook Payload Models

Pydantic V2 definitions for incoming GitLab Merge Request events.
Ensures strict validation of webhook payloads before processing.
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class GitLabUser(BaseModel):
    """Represents a GitLab user involved in an event."""
    id: int
    username: str
    name: str
    email: Optional[str] = None


class GitLabProject(BaseModel):
    """Represents a GitLab project."""
    id: int
    name: str
    web_url: str
    namespace: str


class MergeRequestAttributes(BaseModel):
    """Core attributes of a Merge Request."""
    id: int
    iid: int = Field(alias="iid", description="The project-level ID of the MR")
    title: str
    description: Optional[str] = ""
    state: str
    source_branch: str
    target_branch: str
    author_id: int
    created_at: datetime
    updated_at: datetime
    url: str
    action: str = Field(
        description="The action that triggered the event (e.g., open, update, merge)"
    )


class GitLabMergeRequestEvent(BaseModel):
    """The root payload for a GitLab Merge Request webhook event."""
    object_kind: Literal["merge_request"]
    user: GitLabUser
    project: GitLabProject
    object_attributes: MergeRequestAttributes
