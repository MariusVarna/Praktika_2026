from app.database import engine, Base, SessionLocal
from app.models import Admin
from app.utils.security import get_password_hash

# Create tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Delete existing admin if exists
db.query(Admin).filter(Admin.username == "admin").delete()
db.commit()

# Create new admin with bcrypt hash
admin = Admin(
    username="admin",
    password_hash=get_password_hash("admin123")  # Uses bcrypt
)
db.add(admin)
db.commit()

print("Admin created! Username: admin, Password: admin123")
db.close()