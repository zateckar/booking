"""
Claims mapping service for OIDC authentication
Handles dynamic mapping of OIDC claims to user profile data
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from jose import jwt

from . import models
from .logging_config import get_logger

logger = get_logger("claims_service")


class ClaimsProcessingError(Exception):
    """Exception raised when claims processing fails"""
    pass


class ClaimsMappingService:
    """Service for processing OIDC claims and mapping them to user profiles"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_claim_mappings(self) -> List[models.OIDCClaimMapping]:
        """Get all configured claim mappings"""
        return self.db.query(models.OIDCClaimMapping).all()
    
    def discover_claims_from_token(self, token: str) -> Dict[str, Any]:
        """Extract claims from OIDC token without verification for discovery purposes"""
        try:
            # First, try to parse as JWT token
            if token.count('.') == 2:  # JWT tokens have exactly 2 dots
                claims = jwt.get_unverified_claims(token)
                logger.info(f"Discovered {len(claims)} claims from JWT token")
                return claims
            else:
                # If not a JWT token, try to parse as JSON claims object
                claims = json.loads(token)
                if not isinstance(claims, dict):
                    raise ValueError("Claims must be a JSON object")
                logger.info(f"Discovered {len(claims)} claims from JSON object")
                return claims
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse token as JSON: {e}")
            raise ClaimsProcessingError(f"Invalid token format: must be a valid JWT token or JSON object")
        except Exception as e:
            logger.error(f"Failed to decode token for claims discovery: {e}")
            raise ClaimsProcessingError(f"Invalid token format: {e}")
    
    def process_oidc_claims(self, token_claims: Dict[str, Any], user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Process OIDC claims according to configured mappings
        
        Returns:
            Tuple of (is_admin, profile_data)
        """
        logger.info(f"Processing OIDC claims for user {user_id}")
        
        mappings = self.get_claim_mappings()
        logger.debug(f"Found {len(mappings)} configured claim mappings")
        
        profile_data = {}
        is_admin = False
        
        # Process each configured mapping
        for mapping in mappings:
            try:
                claim_value = self._extract_claim_value(token_claims, mapping)
                
                # Skip processing if claim value is None (missing optional claim)
                if claim_value is None:
                    continue
                
                # Handle role mappings for admin authorization
                if mapping.mapping_type == "role":
                    admin_granted = self._check_admin_role(claim_value, mapping)
                    if admin_granted:
                        is_admin = True
                        logger.info(f"Admin access granted based on role mapping '{mapping.claim_name}'")
                    
                    # Store the role data in profile
                    profile_data[mapping.mapped_field_name] = claim_value
                else:
                    # Store other mapped data
                    profile_data[mapping.mapped_field_name] = claim_value
                
                logger.debug(f"Mapped claim '{mapping.claim_name}' → '{mapping.mapped_field_name}': {claim_value}")
                
            except ClaimsProcessingError as e:
                logger.error(f"Failed to process claim '{mapping.claim_name}': {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error processing claim '{mapping.claim_name}': {e}")
                raise ClaimsProcessingError(f"Error processing claim '{mapping.claim_name}': {e}")
        
        # Update or create user profile
        self._update_user_profile(user_id, profile_data)
        
        logger.info(f"Claims processing completed for user {user_id}. Admin: {is_admin}, Profile fields: {len(profile_data)}")
        return is_admin, profile_data
    
    def _extract_claim_value(self, token_claims: Dict[str, Any], mapping: models.OIDCClaimMapping) -> Any:
        """Extract and validate claim value according to mapping configuration"""
        claim_value = token_claims.get(mapping.claim_name)
        
        # Handle missing claims
        if claim_value is None:
            if mapping.is_required:
                raise ClaimsProcessingError(f"Required claim '{mapping.claim_name}' is missing from token")
            
            # Use default value if provided
            if mapping.default_value:
                claim_value = mapping.default_value
                logger.debug(f"Using default value for missing claim '{mapping.claim_name}': {claim_value}")
            else:
                logger.debug(f"Optional claim '{mapping.claim_name}' is missing, skipping")
                return None
        
        # Type conversion based on mapping type
        try:
            if mapping.mapping_type == "array":
                if not isinstance(claim_value, list):
                    # Try to parse as JSON if it's a string
                    if isinstance(claim_value, str):
                        claim_value = json.loads(claim_value)
                    else:
                        claim_value = [claim_value]  # Convert single value to array
            elif mapping.mapping_type == "number":
                claim_value = float(claim_value) if isinstance(claim_value, str) else claim_value
            elif mapping.mapping_type == "boolean":
                if isinstance(claim_value, str):
                    claim_value = claim_value.lower() in ('true', '1', 'yes', 'on')
                else:
                    claim_value = bool(claim_value)
            elif mapping.mapping_type in ("string", "attribute"):
                # Handle attribute as a generic string conversion
                claim_value = str(claim_value)
            elif mapping.mapping_type == "role":
                # Keep role values as-is for proper role checking
                pass
            
            return claim_value
            
        except (json.JSONDecodeError, ValueError) as e:
            raise ClaimsProcessingError(f"Failed to convert claim '{mapping.claim_name}' to type '{mapping.mapping_type}': {e}")
    
    def _check_admin_role(self, claim_value: Any, mapping: models.OIDCClaimMapping) -> bool:
        """Check if claim value grants admin access according to role mapping"""
        if not mapping.role_admin_values or claim_value is None:
            return False
        
        try:
            admin_values = json.loads(mapping.role_admin_values)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Invalid role_admin_values format for mapping '{mapping.claim_name}': {mapping.role_admin_values}")
            return False
        
        # Handle array claims (like roles list)
        if isinstance(claim_value, list):
            return any(role in admin_values for role in claim_value)
        
        # Handle single value claims
        return str(claim_value) in admin_values
    
    def _update_user_profile(self, user_id: int, profile_data: Dict[str, Any]):
        """Update or create user profile with mapped claims data"""
        try:
            # Get existing profile or create new one
            profile = self.db.query(models.UserProfile).filter(
                models.UserProfile.user_id == user_id
            ).first()
            
            if not profile:
                profile = models.UserProfile(
                    user_id=user_id,
                    profile_data=json.dumps(profile_data),
                    last_oidc_update=datetime.now(timezone.utc)
                )
                self.db.add(profile)
                logger.info(f"Created new user profile for user {user_id}")
            else:
                # Merge with existing profile data
                try:
                    existing_data = json.loads(profile.profile_data) if profile.profile_data else {}
                except json.JSONDecodeError:
                    existing_data = {}
                
                # Update with new data
                existing_data.update(profile_data)
                
                profile.profile_data = json.dumps(existing_data)
                profile.last_oidc_update = datetime.now(timezone.utc)
                logger.info(f"Updated existing user profile for user {user_id}")
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update user profile for user {user_id}: {e}")
            raise ClaimsProcessingError(f"Failed to update user profile: {e}")
    
    def get_user_profile_data(self, user_id: int) -> Dict[str, Any]:
        """Get user profile data as dictionary"""
        profile = self.db.query(models.UserProfile).filter(
            models.UserProfile.user_id == user_id
        ).first()
        
        if not profile or not profile.profile_data:
            return {}
        
        try:
            return json.loads(profile.profile_data)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in user profile for user {user_id}")
            return {}
    
    def create_claim_mapping(self, mapping_data: Dict[str, Any]) -> models.OIDCClaimMapping:
        """Create a new claim mapping"""
        # Always ensure role_admin_values is properly formatted
        if "role_admin_values" in mapping_data:
            if isinstance(mapping_data["role_admin_values"], list):
                # Convert list to JSON string
                mapping_data["role_admin_values"] = json.dumps(mapping_data["role_admin_values"])
            elif mapping_data["role_admin_values"] is None:
                # Set to empty JSON array string for None values
                mapping_data["role_admin_values"] = "[]"
            else:
                # Validate existing string is valid JSON
                try:
                    json.loads(mapping_data["role_admin_values"])
                except (json.JSONDecodeError, TypeError) as e:
                    raise ClaimsProcessingError(f"Invalid role_admin_values format: {e}")
        else:
            # Set default empty array if not provided
            mapping_data["role_admin_values"] = "[]"
        
        mapping = models.OIDCClaimMapping(
            **mapping_data,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        
        logger.info(f"Created claim mapping: {mapping.claim_name} → {mapping.mapped_field_name}")
        return mapping
    
    def update_claim_mapping(self, mapping_id: int, update_data: Dict[str, Any]) -> models.OIDCClaimMapping:
        """Update an existing claim mapping"""
        mapping = self.db.query(models.OIDCClaimMapping).filter(
            models.OIDCClaimMapping.id == mapping_id
        ).first()
        
        if not mapping:
            raise ClaimsProcessingError(f"Claim mapping with ID {mapping_id} not found")
        
        # Handle role_admin_values format consistently
        if "role_admin_values" in update_data:
            if isinstance(update_data["role_admin_values"], list):
                # Convert list to JSON string
                update_data["role_admin_values"] = json.dumps(update_data["role_admin_values"])
            elif update_data["role_admin_values"] is None:
                # Set to empty JSON array string for None values
                update_data["role_admin_values"] = "[]"
            elif update_data["role_admin_values"] != "":
                # Validate existing string is valid JSON (skip empty strings)
                try:
                    json.loads(update_data["role_admin_values"])
                except (json.JSONDecodeError, TypeError) as e:
                    raise ClaimsProcessingError(f"Invalid role_admin_values format: {e}")
        
        # Update fields
        for field, value in update_data.items():
            if hasattr(mapping, field):
                setattr(mapping, field, value)
        
        mapping.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(mapping)
        
        logger.info(f"Updated claim mapping {mapping_id}: {mapping.claim_name} → {mapping.mapped_field_name}")
        return mapping
    
    def delete_claim_mapping(self, mapping_id: int):
        """Delete a claim mapping"""
        mapping = self.db.query(models.OIDCClaimMapping).filter(
            models.OIDCClaimMapping.id == mapping_id
        ).first()
        
        if not mapping:
            raise ClaimsProcessingError(f"Claim mapping with ID {mapping_id} not found")
        
        # Check if this is the required email mapping
        if mapping.claim_name == "email" and mapping.is_required:
            raise ClaimsProcessingError("Cannot delete required email claim mapping")
        
        self.db.delete(mapping)
        self.db.commit()
        
        logger.info(f"Deleted claim mapping {mapping_id}: {mapping.claim_name}")
    
    def get_claims_discovery_data(self, sample_token: str) -> Dict[str, Any]:
        """Discover claims from sample token and compare with existing mappings"""
        discovered_claims = self.discover_claims_from_token(sample_token)
        existing_mappings = self.get_claim_mappings()
        
        # Find unmapped claims
        mapped_claims = {mapping.claim_name for mapping in existing_mappings}
        unmapped_claims = [claim for claim in discovered_claims.keys() if claim not in mapped_claims]
        
        return {
            "discovered_claims": discovered_claims,
            "existing_mappings": existing_mappings,
            "unmapped_claims": unmapped_claims
        }
