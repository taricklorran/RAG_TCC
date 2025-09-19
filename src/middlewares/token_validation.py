import os
from typing import Optional

import jwt
from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

def bearer_token_validation(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token não fornecido")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token mal formatado")

    token = authorization.split(" ")[1]

    try:
        decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Token inválido")
