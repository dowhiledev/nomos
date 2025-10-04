"""Server and session configuration classes."""

from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# Constants
DEFAULT_SESSION_TTL = 3600
DEFAULT_CACHE_TTL = 3600
DEFAULT_KAFKA_TOPIC = "session_events"
DEFAULT_SERVER_PORT = 8000
DEFAULT_SERVER_HOST = "0.0.0.0"
DEFAULT_SERVER_WORKERS = 1


class SessionStoreType(str, Enum):
    """Enumeration for session store types."""
    MEMORY = "memory"
    PRODUCTION = "production"


class SessionConfig(BaseModel):
    """Configuration for session management.

    Attributes:
        store_type: Type of session store (memory or production).
        default_ttl: Default time-to-live for sessions in seconds.
        cache_ttl: Cache TTL for production store in seconds.
        database_url: Optional database URL for production store.
        redis_url: Optional Redis URL for session storage.
        kafka_brokers: Optional Kafka brokers for event streaming.
        kafka_topic: Kafka topic for session events.
        events_enabled: Whether session events are enabled.
    """
    store_type: SessionStoreType = SessionStoreType.MEMORY
    default_ttl: int = Field(DEFAULT_SESSION_TTL, description="Default session TTL in seconds")
    cache_ttl: int = Field(DEFAULT_CACHE_TTL, description="Cache TTL for production store in seconds")
    database_url: Optional[str] = Field(None, description="Database URL for production store")
    redis_url: Optional[str] = Field(None, description="Redis URL for session storage")
    kafka_brokers: Optional[str] = Field(None, description="Kafka brokers for event streaming")
    kafka_topic: str = Field(DEFAULT_KAFKA_TOPIC, description="Kafka topic for session events")
    events_enabled: bool = Field(False, description="Whether session events are enabled")

    @classmethod
    def from_env(cls) -> "SessionConfig":
        """Create SessionConfig from environment variables.

        Returns:
            SessionConfig: Configured instance from env vars.
        """
        import os

        return cls(
            store_type=SessionStoreType(os.getenv("SESSION_STORE", SessionStoreType.MEMORY.value)),
            default_ttl=int(os.getenv("SESSION_DEFAULT_TTL", str(DEFAULT_SESSION_TTL))),
            cache_ttl=int(os.getenv("SESSION_CACHE_TTL", str(DEFAULT_CACHE_TTL))),
            database_url=os.getenv("DATABASE_URL"),
            redis_url=os.getenv("REDIS_URL"),
            kafka_brokers=os.getenv("KAFKA_BROKERS"),
            kafka_topic=os.getenv("KAFKA_TOPIC", DEFAULT_KAFKA_TOPIC),
            events_enabled=os.getenv("SESSION_EVENTS", "false").lower() == "true",
        )

    def __str__(self) -> str:
        return f"SessionConfig(store_type={self.store_type}, default_ttl={self.default_ttl})"


class ServerSecurity(BaseModel):
    """Security configuration for the FastAPI server.

    Attributes:
        allowed_origins: List of allowed origins for CORS.
        enable_auth: Whether authentication is enabled.
        auth_type: Type of authentication (jwt or api_key).
        jwt_secret_key: Secret key for JWT authentication.
        api_key_url: URL for API key validation.
        enable_rate_limiting: Whether rate limiting is enabled.
        redis_url: Redis URL for rate limiting.
        rate_limit_times: Number of allowed requests per time period.
        rate_limit_seconds: Time period for rate limiting in seconds.
        enable_csrf_protection: Whether CSRF protection is enabled.
        csrf_secret_key: Secret key for CSRF protection.
        enable_token_endpoint: Whether JWT token endpoint is enabled (dev/test only).
    """
    allowed_origins: List[str] = Field(["*"], description="List of allowed origins for CORS")
    enable_auth: bool = Field(False, description="Flag to enable authentication")
    auth_type: Optional[Literal["jwt", "api_key"]] = Field(None, description="Type of authentication")
    jwt_secret_key: Optional[str] = Field(None, description="Secret key for JWT authentication")
    api_key_url: Optional[str] = Field(None, description="URL for API key validation")
    enable_rate_limiting: bool = Field(False, description="Flag to enable rate limiting")
    redis_url: Optional[str] = Field(None, description="Redis URL for rate limiting")
    rate_limit_times: Optional[int] = Field(None, description="Number of allowed requests per time period")
    rate_limit_seconds: Optional[int] = Field(None, description="Time period for rate limiting in seconds")
    enable_csrf_protection: bool = Field(False, description="Flag to enable CSRF protection")
    csrf_secret_key: Optional[str] = Field(None, description="Secret key for CSRF protection")
    enable_token_endpoint: bool = Field(False, description="Flag to enable JWT token endpoint (dev/test only)")

    def __str__(self) -> str:
        return f"ServerSecurity(enable_auth={self.enable_auth}, auth_type={self.auth_type})"


class ServerConfig(BaseModel):
    """Configuration for the FastAPI server.

    Attributes:
        port: Server port.
        host: Server host.
        workers: Number of server workers.
        security: Security configuration.
        session: Session configuration.
    """
    port: int = Field(DEFAULT_SERVER_PORT, description="Server port")
    host: str = Field(DEFAULT_SERVER_HOST, description="Server host")
    workers: int = Field(DEFAULT_SERVER_WORKERS, description="Number of server workers")
    security: ServerSecurity = Field(default_factory=ServerSecurity, description="Security configuration")
    session: SessionConfig = Field(default_factory=SessionConfig, description="Session configuration")

    def __str__(self) -> str:
        return f"ServerConfig(port={self.port}, host={self.host})"


__all__ = ["SessionStoreType", "SessionConfig", "ServerSecurity", "ServerConfig"]