from sqlalchemy import Boolean, Column, Integer, String
from datetime import datetime, timezone

from .base import BaseModel, TimezoneAwareDateTime


class OIDCProvider(BaseModel):
    __tablename__ = "oidc_providers"

    issuer = Column(String, unique=True, index=True)
    display_name = Column(String)  # User-friendly name for login button
    client_id = Column(String)
    client_secret = Column(String)
    well_known_url = Column(String)
    scopes = Column(String, default="openid email profile")  # Space-separated list of scopes


class OIDCClaimMapping(BaseModel):
    __tablename__ = "oidc_claim_mappings"

    claim_name = Column(String, index=True)  # OIDC claim key from token
    mapped_field_name = Column(String, index=True)  # Custom field name chosen by admin
    mapping_type = Column(String)  # "role", "string", "array", "number", "boolean"
    is_required = Column(Boolean, default=False)
    role_admin_values = Column(String)  # JSON array of role values that grant admin access
    default_value = Column(String)  # Default value if claim is missing
    display_label = Column(String)  # Human-readable label for UI/reports
    description = Column(String)  # Admin notes
    created_at = Column(TimezoneAwareDateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TimezoneAwareDateTime, default=lambda: datetime.now(timezone.utc))
