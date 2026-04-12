from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.services.admin_service import AdminService

router = APIRouter()

@router.post("/register", response_model=schemas.AdminResponse)
def register_admin(admin_in: schemas.AdminCreate, db: Session = Depends(get_db)):
    service = AdminService(db)
    return service.create_admin(admin_in)

@router.post("/login", response_model=schemas.AdminResponse)
def login_admin(login_in: schemas.AdminLogin, db: Session = Depends(get_db)):
    service = AdminService(db)
    return service.login_admin(login_in)
