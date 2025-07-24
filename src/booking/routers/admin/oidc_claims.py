"""
Admin endpoints for unified OIDC provider and claims mapping management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json
import logging

from ... import models, schemas
from ...database import get_db
from ...security import get_current_admin_user
from ...claims_service import ClaimsMappingService, ClaimsProcessingError
from ...logging_config import get_logger

router = APIRouter()
logger = get_logger("oidc_claims_admin")


# OIDC Provider endpoints
@router.post("/providers", response_model=schemas.OIDCProvider)
def create_oidc_provider(
    provider: schemas.OIDCProviderCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Create a new OIDC provider"""
    try:
        db_provider = models.OIDCProvider(**provider.dict())
        db.add(db_provider)
        db.commit()
        db.refresh(db_provider)
        
        logger.info(f"Created OIDC provider: {db_provider.issuer}")
        return db_provider
    except Exception as e:
        logger.error(f"Error creating OIDC provider: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating OIDC provider: {str(e)}")


@router.get("/providers", response_model=List[schemas.OIDCProvider])
def get_oidc_providers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get all OIDC providers"""
    try:
        providers = db.query(models.OIDCProvider).all()
        logger.info(f"Retrieved {len(providers)} OIDC providers")
        return providers
    except Exception as e:
        logger.error(f"Error retrieving OIDC providers: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving OIDC providers: {str(e)}")


@router.get("/providers/{provider_id}", response_model=schemas.OIDCProvider)
def get_oidc_provider(
    provider_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get a single OIDC provider by ID"""
    try:
        provider = db.query(models.OIDCProvider).filter(models.OIDCProvider.id == provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail="OIDC provider not found")
        
        logger.info(f"Retrieved OIDC provider {provider_id}")
        return provider
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving OIDC provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving OIDC provider: {str(e)}")


@router.put("/providers/{provider_id}", response_model=schemas.OIDCProvider)
def update_oidc_provider(
    provider_id: int, 
    provider_update: schemas.OIDCProviderUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Update an OIDC provider"""
    try:
        provider = db.query(models.OIDCProvider).filter(models.OIDCProvider.id == provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail="OIDC provider not found")
        
        update_data = provider_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(provider, field, value)
        
        db.commit()
        db.refresh(provider)
        
        logger.info(f"Updated OIDC provider {provider_id}")
        return provider
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating OIDC provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating OIDC provider: {str(e)}")


@router.delete("/providers/{provider_id}", status_code=204)
def delete_oidc_provider(
    provider_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Delete an OIDC provider"""
    try:
        provider = db.query(models.OIDCProvider).filter(models.OIDCProvider.id == provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail="OIDC provider not found")
        
        db.delete(provider)
        db.commit()
        
        logger.info(f"Deleted OIDC provider {provider_id}")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting OIDC provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting OIDC provider: {str(e)}")


# Claims Mapping endpoints
@router.get("/claims-mappings", response_model=List[schemas.OIDCClaimMapping])
def get_claim_mappings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get all configured claim mappings"""
    try:
        claims_service = ClaimsMappingService(db)
        mappings = claims_service.get_claim_mappings()
        
        # Convert role_admin_values from JSON string to list for response
        result = []
        for mapping in mappings:
            mapping_dict = {
                "id": mapping.id,
                "claim_name": mapping.claim_name,
                "mapped_field_name": mapping.mapped_field_name,
                "mapping_type": mapping.mapping_type,
                "is_required": mapping.is_required,
                "role_admin_values": [],
                "default_value": mapping.default_value,
                "display_label": mapping.display_label,
                "description": mapping.description,
                "created_at": mapping.created_at,
                "updated_at": mapping.updated_at
            }
            
            if mapping.role_admin_values:
                try:
                    mapping_dict["role_admin_values"] = json.loads(mapping.role_admin_values)
                except json.JSONDecodeError:
                    mapping_dict["role_admin_values"] = []
            
            result.append(schemas.OIDCClaimMapping(**mapping_dict))
        
        logger.info(f"Retrieved {len(result)} claim mappings")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving claim mappings: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving claim mappings: {str(e)}")


@router.get("/claims-mappings/{mapping_id}", response_model=schemas.OIDCClaimMapping)
def get_claim_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get a single claim mapping by ID"""
    try:
        claims_service = ClaimsMappingService(db)
        mapping = db.query(models.OIDCClaimMapping).filter(models.OIDCClaimMapping.id == mapping_id).first()
        
        if not mapping:
            raise HTTPException(status_code=404, detail="Claim mapping not found")
        
        # Convert for response
        response_dict = {
            "id": mapping.id,
            "claim_name": mapping.claim_name,
            "mapped_field_name": mapping.mapped_field_name,
            "mapping_type": mapping.mapping_type,
            "is_required": mapping.is_required,
            "role_admin_values": [],
            "default_value": mapping.default_value,
            "display_label": mapping.display_label,
            "description": mapping.description,
            "created_at": mapping.created_at,
            "updated_at": mapping.updated_at
        }
        
        if mapping.role_admin_values:
            try:
                response_dict["role_admin_values"] = json.loads(mapping.role_admin_values)
            except json.JSONDecodeError:
                response_dict["role_admin_values"] = []
        
        logger.info(f"Retrieved claim mapping {mapping_id}")
        return schemas.OIDCClaimMapping(**response_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving claim mapping {mapping_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving claim mapping: {str(e)}")


@router.post("/claims-mappings", response_model=schemas.OIDCClaimMapping)
def create_claim_mapping(
    mapping_data: schemas.OIDCClaimMappingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Create a new claim mapping"""
    try:
        claims_service = ClaimsMappingService(db)
        
        # Convert Pydantic model to dict
        mapping_dict = mapping_data.model_dump()
        
        # Create the mapping
        mapping = claims_service.create_claim_mapping(mapping_dict)
        
        # Convert for response
        response_dict = {
            "id": mapping.id,
            "claim_name": mapping.claim_name,
            "mapped_field_name": mapping.mapped_field_name,
            "mapping_type": mapping.mapping_type,
            "is_required": mapping.is_required,
            "role_admin_values": mapping_data.role_admin_values,  # Use original list
            "default_value": mapping.default_value,
            "display_label": mapping.display_label,
            "description": mapping.description,
            "created_at": mapping.created_at,
            "updated_at": mapping.updated_at
        }
        
        logger.info(f"Created claim mapping: {mapping.claim_name} → {mapping.mapped_field_name}")
        return schemas.OIDCClaimMapping(**response_dict)
        
    except ClaimsProcessingError as e:
        logger.warning(f"Invalid claim mapping data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating claim mapping: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating claim mapping: {str(e)}")


@router.put("/claims-mappings/{mapping_id}", response_model=schemas.OIDCClaimMapping)
def update_claim_mapping(
    mapping_id: int,
    mapping_data: schemas.OIDCClaimMappingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Update an existing claim mapping"""
    try:
        claims_service = ClaimsMappingService(db)
        
        # Convert Pydantic model to dict, excluding None values
        update_dict = {k: v for k, v in mapping_data.model_dump().items() if v is not None}
        
        # Update the mapping
        mapping = claims_service.update_claim_mapping(mapping_id, update_dict)
        
        # Convert for response
        role_admin_values = []
        if mapping.role_admin_values:
            try:
                role_admin_values = json.loads(mapping.role_admin_values)
            except json.JSONDecodeError:
                role_admin_values = []
        
        response_dict = {
            "id": mapping.id,
            "claim_name": mapping.claim_name,
            "mapped_field_name": mapping.mapped_field_name,
            "mapping_type": mapping.mapping_type,
            "is_required": mapping.is_required,
            "role_admin_values": role_admin_values,
            "default_value": mapping.default_value,
            "display_label": mapping.display_label,
            "description": mapping.description,
            "created_at": mapping.created_at,
            "updated_at": mapping.updated_at
        }
        
        logger.info(f"Updated claim mapping {mapping_id}: {mapping.claim_name} → {mapping.mapped_field_name}")
        return schemas.OIDCClaimMapping(**response_dict)
        
    except ClaimsProcessingError as e:
        logger.warning(f"Invalid claim mapping update: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating claim mapping: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating claim mapping: {str(e)}")


@router.delete("/claims-mappings/{mapping_id}")
def delete_claim_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Delete a claim mapping"""
    try:
        claims_service = ClaimsMappingService(db)
        claims_service.delete_claim_mapping(mapping_id)
        
        logger.info(f"Deleted claim mapping {mapping_id}")
        return {"message": f"Claim mapping {mapping_id} deleted successfully"}
        
    except ClaimsProcessingError as e:
        logger.warning(f"Cannot delete claim mapping: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting claim mapping: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting claim mapping: {str(e)}")


@router.post("/claims-discovery", response_model=schemas.ClaimsDiscoveryResponse)
def discover_claims(
    request: schemas.ClaimsDiscoveryRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Discover claims from a sample OIDC token"""
    try:
        claims_service = ClaimsMappingService(db)
        discovery_data = claims_service.get_claims_discovery_data(request.sample_token)
        
        # Convert existing mappings to schema format
        existing_mappings = []
        for mapping in discovery_data["existing_mappings"]:
            role_admin_values = []
            if mapping.role_admin_values:
                try:
                    role_admin_values = json.loads(mapping.role_admin_values)
                except json.JSONDecodeError:
                    role_admin_values = []
            
            mapping_dict = {
                "id": mapping.id,
                "claim_name": mapping.claim_name,
                "mapped_field_name": mapping.mapped_field_name,
                "mapping_type": mapping.mapping_type,
                "is_required": mapping.is_required,
                "role_admin_values": role_admin_values,
                "default_value": mapping.default_value,
                "display_label": mapping.display_label,
                "description": mapping.description,
                "created_at": mapping.created_at,
                "updated_at": mapping.updated_at
            }
            existing_mappings.append(schemas.OIDCClaimMapping(**mapping_dict))
        
        response_data = {
            "discovered_claims": discovery_data["discovered_claims"],
            "existing_mappings": existing_mappings,
            "unmapped_claims": discovery_data["unmapped_claims"]
        }
        
        logger.info(f"Discovered {len(discovery_data['discovered_claims'])} claims, {len(discovery_data['unmapped_claims'])} unmapped")
        return schemas.ClaimsDiscoveryResponse(**response_data)
        
    except ClaimsProcessingError as e:
        logger.warning(f"Claims discovery failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during claims discovery: {e}")
        raise HTTPException(status_code=500, detail=f"Error during claims discovery: {str(e)}")


@router.get("/user-profiles/{user_id}")
def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get user profile with mapped claims data"""
    try:
        # Get user
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get profile data
        claims_service = ClaimsMappingService(db)
        profile_data = claims_service.get_user_profile_data(user_id)
        
        # Get user profile record
        profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
        
        response = {
            "user_id": user_id,
            "email": user.email,
            "is_admin": user.is_admin,
            "profile_data": profile_data,
            "last_oidc_update": profile.last_oidc_update.isoformat() if profile and profile.last_oidc_update else None
        }
        
        logger.info(f"Retrieved user profile for user {user_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving user profile: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving user profile: {str(e)}")


@router.get("/user-profiles")
def get_all_user_profiles(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get all user profiles with mapped claims data"""
    try:
        # Get users with profiles
        users_query = db.query(models.User).offset(offset).limit(limit)
        users = users_query.all()
        
        claims_service = ClaimsMappingService(db)
        
        profiles = []
        for user in users:
            profile_data = claims_service.get_user_profile_data(user.id)
            
            # Get profile record for last update time
            profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user.id).first()
            
            profiles.append({
                "user_id": user.id,
                "email": user.email,
                "is_admin": user.is_admin,
                "profile_data": profile_data,
                "last_oidc_update": profile.last_oidc_update.isoformat() if profile and profile.last_oidc_update else None
            })
        
        # Get total count
        total_count = db.query(models.User).count()
        
        logger.info(f"Retrieved {len(profiles)} user profiles (offset: {offset}, limit: {limit})")
        return {
            "profiles": profiles,
            "total_count": total_count,
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error retrieving user profiles: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving user profiles: {str(e)}")
