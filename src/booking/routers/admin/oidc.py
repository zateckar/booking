from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from ... import models, schemas, oidc
from ...database import get_db
from ...security import get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/oidc",
    tags=["oidc"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.post("/", response_model=schemas.OIDCProvider)
def create_oidc_provider(
    provider: schemas.OIDCProviderCreate, db: Session = Depends(get_db)
):
    try:
        db_provider = models.OIDCProvider(**provider.dict())
        db.add(db_provider)
        db.commit()
        db.refresh(db_provider)
        
        # Register the new provider with OAuth
        try:
            oidc.register_provider(db_provider)
            logger.info(f"Successfully created and registered OIDC provider: {db_provider.display_name}")
        except Exception as e:
            logger.error(f"Failed to register new OIDC provider {db_provider.display_name}: {e}")
            # Don't fail the creation, just log the error
        
        return db_provider
    except Exception as e:
        logger.error(f"Failed to create OIDC provider: {e}")
        raise HTTPException(status_code=500, detail="Failed to create OIDC provider")


@router.get("/", response_model=list[schemas.OIDCProvider])
def read_oidc_providers(db: Session = Depends(get_db)):
    return db.query(models.OIDCProvider).all()


@router.get("/{provider_id}", response_model=schemas.OIDCProvider)
def read_oidc_provider(provider_id: int, db: Session = Depends(get_db)):
    provider = (
        db.query(models.OIDCProvider).filter(models.OIDCProvider.id == provider_id).first()
    )
    if not provider:
        raise HTTPException(status_code=404, detail="OIDC provider not found")
    return provider


@router.put("/{provider_id}", response_model=schemas.OIDCProvider)
def update_oidc_provider(
    provider_id: int, 
    provider_update: schemas.OIDCProviderUpdate, 
    db: Session = Depends(get_db)
):
    try:
        provider = (
            db.query(models.OIDCProvider).filter(models.OIDCProvider.id == provider_id).first()
        )
        if not provider:
            raise HTTPException(status_code=404, detail="OIDC provider not found")
        
        update_data = provider_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(provider, field, value)
        
        db.commit()
        db.refresh(provider)
        
        # Refresh provider registration with updated configuration
        try:
            oidc.refresh_provider_registration(provider_id)
            logger.info(f"Successfully updated and re-registered OIDC provider: {provider.display_name}")
        except Exception as e:
            logger.error(f"Failed to refresh OIDC provider registration {provider.display_name}: {e}")
            # Don't fail the update, just log the error
        
        return provider
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update OIDC provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update OIDC provider")


@router.delete("/{provider_id}", status_code=204)
def delete_oidc_provider(provider_id: int, db: Session = Depends(get_db)):
    try:
        provider = (
            db.query(models.OIDCProvider).filter(models.OIDCProvider.id == provider_id).first()
        )
        if not provider:
            raise HTTPException(status_code=404, detail="OIDC provider not found")
        
        # Store provider info before deletion for cleanup
        provider_display_name = provider.display_name
        
        # Delete from database
        db.delete(provider)
        db.commit()
        
        # Remove provider registration
        try:
            oidc.remove_provider_registration(provider_id, provider_display_name)
            logger.info(f"Successfully deleted and unregistered OIDC provider: {provider_display_name}")
        except Exception as e:
            logger.error(f"Failed to unregister deleted OIDC provider {provider_display_name}: {e}")
            # Don't fail the deletion, just log the error
        
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete OIDC provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete OIDC provider")
