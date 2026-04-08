from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base
from datetime import datetime

class AuditLog(Base):
    """FIX: Audit trail for security and debugging. Tracks all sensitive operations."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    action = Column(String(100))  # e.g., "CALCULATE_ROUND", "DELETE_SESSION", "PLACE_BID"
    admin_id = Column(String, nullable=True, index=True)  # Who initiated the action
    session_id = Column(Integer, nullable=True, index=True)  # Which session
    user_id = Column(Integer, nullable=True, index=True)  # Which user (for player actions)
    details = Column(Text, nullable=True)  # JSON-serialized extra context
    
    def __repr__(self):
        return f"<AuditLog {self.timestamp} {self.action} by {self.admin_id or self.user_id}>"
