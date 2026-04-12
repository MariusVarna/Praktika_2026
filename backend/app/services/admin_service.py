from sqlalchemy.orm import Session
from app import models
from app.schemas import schemas
from app.utils.security import get_password_hash, verify_password
from fastapi import HTTPException, status
import uuid

class AdminService:
    def __init__(self, db: Session):
        self.db = db

    def create_admin(self, admin_in: schemas.AdminCreate) -> schemas.AdminResponse:
        existing = self.db.query(models.Admin).filter(models.Admin.username == admin_in.username).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
        
        hashed_password = get_password_hash(admin_in.password)
        db_admin = models.Admin(
            username=admin_in.username,
            password_hash=hashed_password
        )
        self.db.add(db_admin)
        self.db.commit()
        self.db.refresh(db_admin)
        
        # In a real app, we'd use JWT. Here we'll return the username as a simple 'token' for the prototype
        return schemas.AdminResponse(
            id=db_admin.id,
            username=db_admin.username,
            admin_token=db_admin.username 
        )

    def login_admin(self, login_in: schemas.AdminLogin) -> schemas.AdminResponse:
        admin = self.db.query(models.Admin).filter(models.Admin.username == login_in.username).first()
        if not admin or not verify_password(login_in.password, admin.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
        
        return schemas.AdminResponse(
            id=admin.id,
            username=admin.username,
            admin_token=admin.username
        )
