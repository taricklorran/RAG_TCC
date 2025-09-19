import datetime
import os

import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

def generate_token(user_id: str, expires_in_minutes: int = 300) -> str:
    """Gera um token JWT para o usuário com expiração"""
    payload = {
        "sub": user_id,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_in_minutes)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {
        "message": "Token gerado com sucesso",
        "token": token,
        "success": True
    }
