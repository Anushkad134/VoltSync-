import jwt
from jwt import PyJWKClient
from fastapi import HTTPException
from app.core.config import settings
from typing import Optional

# Using Clerk JWKS URL for JWT validation
jwks_client = PyJWKClient(settings.CLERK_JWKS_URL) if settings.CLERK_JWKS_URL else None

def verify_token(token: str) -> str:
    """
    Verifies the Clerk JWT token and returns the clerk_user_id (from the 'sub' claim).
    """
    if not token:
        raise HTTPException(status_code=401, detail={
            "error_code": "UNAUTHENTICATED",
            "message": "Authentication is required.",
            "status_code": 401
        })
        
    # For testing without a real Clerk environment, if JWKS URL is missing, we allow a specific mock token
    # Wait, the PRD says: "Clerk JWT validation works for protected endpoints".
    # We will enforce JWKS validation unless in test mode where we mock it at the dependency level.
    if not jwks_client:
        # If JWKS URL is not configured (e.g. tests or missing env), we still need to handle it.
        # But we shouldn't bypass security in production.
        raise HTTPException(status_code=401, detail={
            "error_code": "UNAUTHENTICATED",
            "message": "Authentication is not configured correctly on the server.",
            "status_code": 401
        })

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        data = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            # If your Clerk setup has an audience, add audience="your-audience" here
            options={"verify_aud": False}
        )
        clerk_user_id = data.get("sub")
        if not clerk_user_id:
            raise HTTPException(status_code=401, detail={
                "error_code": "UNAUTHENTICATED",
                "message": "Invalid token payload.",
                "status_code": 401
            })
        return clerk_user_id
        
    except jwt.exceptions.PyJWKClientError:
        raise HTTPException(status_code=401, detail={
            "error_code": "UNAUTHENTICATED",
            "message": "Unable to verify token signature.",
            "status_code": 401
        })
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={
            "error_code": "UNAUTHENTICATED",
            "message": "The authentication token is expired.",
            "status_code": 401
        })
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail={
            "error_code": "UNAUTHENTICATED",
            "message": "The authentication token is invalid.",
            "status_code": 401
        })
    except Exception as e:
        raise HTTPException(status_code=401, detail={
            "error_code": "UNAUTHENTICATED",
            "message": "Authentication failed.",
            "status_code": 401
        })
