from fastapi import HTTPException
import jwt
import os

SECRET_KEY = os.getenv("SECRET_KEY", "default_key")
ALGORITHM = "HS256"

def verificar_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido.")
    

