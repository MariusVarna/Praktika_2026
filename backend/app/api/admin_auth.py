from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.database import get_db
from app import models, schemas
from app.services.admin_service import AdminService

router = APIRouter()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/register", response_model=schemas.AdminResponse)
def register_admin(admin_in: schemas.AdminCreate, db: Session = Depends(get_db)):
    service = AdminService(db)
    return service.create_admin(admin_in)

@router.post("/login", response_model=schemas.AdminResponse)
def login_admin(login_in: schemas.AdminLogin, db: Session = Depends(get_db)):
    service = AdminService(db)
    return service.login_admin(login_in)

@router.post("/setup-first-admin")
async def setup_first_admin(admin_data: AdminSetup, db: Session = Depends(get_db)):
    """Create first admin (only works if no admins exist)"""
    from app.models import Admin
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    existing = db.query(Admin).first()
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")
    hashed = pwd_context.hash(admin_data.password)
    admin = Admin(username=admin_data.username, hashed_password=hashed)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    return {"message": "Admin created successfully", "username": admin.username}