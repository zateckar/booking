from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ... import models, schemas
from ...database import get_db
from ...security import get_current_admin_user

router = APIRouter(
    prefix="/oidc",
    tags=["oidc"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.post("/", response_model=schemas.OIDCProvider)
def create_oidc_provider(
    provider: schemas.OIDCProviderCreate, db: Session = Depends(get_db)
):
    db_provider = models.OIDCProvider(**provider.dict())
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    return db_provider


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
    return provider


@router.delete("/{provider_id}", status_code=204)
def delete_oidc_provider(provider_id: int, db: Session = Depends(get_db)):
    provider = (
        db.query(models.OIDCProvider).filter(models.OIDCProvider.id == provider_id).first()
    )
    if not provider:
        raise HTTPException(status_code=404, detail="OIDC provider not found")
    db.delete(provider)
    db.commit()
    return {"ok": True}
