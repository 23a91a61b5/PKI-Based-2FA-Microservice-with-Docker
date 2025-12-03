from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import os
import base64

# Import all core logic from the utility file
from .crypto_utils import (
    load_private_key, decrypt_seed, save_hex_seed, 
    generate_totp_code, verify_totp_code
)

# --- Pydantic Schemas for Request Body Validation ---

class DecryptSeedRequest(BaseModel):
    encrypted_seed: str

class VerifyCodeRequest(BaseModel):
    code: str

# --- API Application Setup ---

app = FastAPI(
    title="Secure 2FA Microservice", 
    version="1.0.0"
)

# CRITICAL: Load the private key once at startup from the expected Docker path
PRIVATE_KEY_PATH = "student_private.pem" # Assumes key is in the app's root context
STUDENT_PRIVATE_KEY = load_private_key(PRIVATE_KEY_PATH)

# Helper function to read the persistent seed from the volume path
def get_hex_seed(path: str = "/data/seed.txt") -> str | None:
    """Reads the persistent seed from the Docker volume path."""
    try:
        with open(path, 'r') as f:
            # Read and strip to get the 64-char hex string
            return f.read().strip()
    except FileNotFoundError:
        return None
    except Exception:
        return None


# --- Endpoint 1: POST /decrypt-seed ---
# Goal: Decrypt seed, validate, and store persistently.
@app.post("/decrypt-seed", status_code=status.HTTP_200_OK)
async def handle_decrypt_seed(request: DecryptSeedRequest):
    # Implementation checklist: Load student private key
    if STUDENT_PRIVATE_KEY is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail={"error": "Decryption failed (Key unavailable on server startup)"}
        )
    
    try:
        # Implementation checklist: Base64 decode, Decrypt using RSA/OAEP-SHA256, Validate 64-char hex
        hex_seed = decrypt_seed(request.encrypted_seed, STUDENT_PRIVATE_KEY)
        
        # Implementation checklist: Save to /data/seed.txt
        save_hex_seed(hex_seed, "/data/seed.txt")
        
        # Implementation checklist: Return {"status": "ok"}
        return {"status": "ok"}
        
    except (ValueError, base64.binascii.Error) as e:
        # Catches invalid input format or validation failure
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Decryption failed"})
        
    except Exception as e:
        # Catches decryption failure (e.g., Key/Parameter Mismatch)
        print(f"Decryption error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Decryption failed"})


# --- Endpoint 2: GET /generate-2fa ---
# Goal: Generate current TOTP code.
@app.get("/generate-2fa", status_code=status.HTTP_200_OK)
async def handle_generate_2fa():
    # Implementation checklist: Check if /data/seed.txt exists
    hex_seed = get_hex_seed()
    if hex_seed is None:
        # Response (500 Internal Server Error): {"error": "Seed not decrypted yet"}
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail={"error": "Seed not decrypted yet"}
        )
        
    try:
        # Implementation checklist: Read hex seed, Generate TOTP code, Calculate remaining seconds
        result = generate_totp_code(hex_seed)
        
        # Response (200 OK): {"code": "123456", "valid_for": 30}
        return result
        
    except Exception as e:
        print(f"TOTP generation error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal error generating 2FA code."})


# --- Endpoint 3: POST /verify-2fa ---
# Goal: Verify a user-submitted code.
@app.post("/verify-2fa", status_code=status.HTTP_200_OK)
async def handle_verify_2fa(request: VerifyCodeRequest):
    # Implementation checklist: Validate code is provided (and 6 digits)
    if not request.code or not request.code.isdigit() or len(request.code) != 6:
        # Response (400 Bad Request): {"error": "Missing code"}
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "Missing code"})
        
    # Implementation checklist: Check if /data/seed.txt exists
    hex_seed = get_hex_seed()
    if hex_seed is None:
        # Response (500 Internal Server Error): {"error": "Seed not decrypted yet"}
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail={"error": "Seed not decrypted yet"}
        )
        
    try:
        # Implementation checklist: Read hex seed, Verify TOTP code with ±1 period tolerance
        is_valid = verify_totp_code(hex_seed, request.code, valid_window=1)
        
        # Response (200 OK): {"valid": true/false}
        return {"valid": is_valid}
        
    except Exception as e:
        print(f"TOTP verification error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "Internal error verifying 2FA code."})