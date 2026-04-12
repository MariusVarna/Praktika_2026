import bcrypt

def verify_password(plain_password, hashed_password):
    """Verify a plain password against a hashed password using bcrypt."""
    # Convert parameters to bytes if they are strings
    password_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
    return bcrypt.checkpw(password_bytes, hash_bytes)

def get_password_hash(password):
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')
