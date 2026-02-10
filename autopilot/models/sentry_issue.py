"""Sentry API issue model for the autopilot polling pipeline."""

from pydantic import BaseModel


class SentryIssue(BaseModel):
    """Parsed issue from the Sentry API /issues/ endpoint."""

    id: str
    title: str
    culprit: str
    level: str
    status: str
    first_seen: str
    last_seen: str
    count: int
    permalink: str
    short_id: str
    metadata: dict

    @classmethod
    def from_api_response(cls, data: dict) -> "SentryIssue":
        return cls(
            id=data["id"],
            title=data.get("title", "Unknown error"),
            culprit=data.get("culprit", "unknown"),
            level=data.get("level", "error"),
            status=data.get("status", "unresolved"),
            first_seen=data.get("firstSeen", ""),
            last_seen=data.get("lastSeen", ""),
            count=data.get("count", 0),
            permalink=data.get("permalink", ""),
            short_id=data.get("shortId", ""),
            metadata=data.get("metadata", {}),
        )
