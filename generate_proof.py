import os
import sys
import subprocess
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

# --- File Paths ---
STUDENT_PRIVATE_KEY_FILE = "student_private.pem"
INSTRUCTOR_PUBLIC_KEY_FILE = "instructor_public.pem"

# --- Cryptographic Constants (MUST match specifications exactly) ---
# Hash Algorithm: SHA-256
HASH_ALGORITHM = hashes.SHA256()

def load_private_key(filename):
    """Loads a private key from a PEM file."""
    try:
        with open(filename, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None
            )
        return private_key
    except FileNotFoundError:
        print(f"Error: Private key file not found at {filename}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading private key: {e}")
        sys.exit(1)

def load_public_key(filename):
    """Loads a public key from a PEM file."""
    try:
        with open(filename, "rb") as key_file:
            public_key = serialization.load_pem_public_key(
                key_file.read()
            )
        return public_key
    except FileNotFoundError:
        print(f"Error: Public key file not found at {filename}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading public key: {e}")
        sys.exit(1)

def get_commit_hash():
    """Fetches the latest commit hash (40-character string)."""
    try:
        # Executes 'git log -1 --format=%H'
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%H'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error fetching commit hash. Ensure you have made at least one commit: {e}")
        sys.exit(1)

def sign_commit_hash(commit_hash: str, private_key: serialization.KeySerializationEncryption) -> bytes:
    """
    Signs the commit hash using RSA-PSS with SHA-256 and max salt.
    """
    # CRITICAL: Sign the ASCII bytes of the hash string.
    message_bytes = commit_hash.encode('utf-8')
    
    signature = private_key.sign(
        message_bytes,
        padding.PSS(
            mgf=padding.MGF1(HASH_ALGORITHM), # Required: MGF1 with SHA-256
            salt_length=padding.PSS.MAX_LENGTH # Required: Maximum salt length
        ),
        HASH_ALGORITHM                         # Required: SHA-256
    )
    return signature

def encrypt_signature(signature: bytes, public_key: serialization.KeySerializationEncryption) -> bytes:
    """
    Encrypts the signature bytes using RSA/OAEP with SHA-256.
    """
    encrypted_signature = public_key.encrypt(
        signature,
        padding.OAEP(
            mgf=padding.MGF1(HASH_ALGORITHM), # Required: MGF1 with SHA-256
            algorithm=HASH_ALGORITHM,         # Required: SHA-256
            label=None
        )
    )
    return encrypted_signature

def main():
    print("--- Starting Proof Generation (Step 13) ---")
    try:
        # Load keys
        student_private_key = load_private_key(STUDENT_PRIVATE_KEY_FILE)
        instructor_public_key = load_public_key(INSTRUCTOR_PUBLIC_KEY_FILE)
        
        # 1. Get the commit hash
        commit_hash = get_commit_hash()
        
        # 2. Sign the hash (RSA-PSS)
        signature_bytes = sign_commit_hash(commit_hash, student_private_key)
        
        # 3. Encrypt the signature (RSA/OAEP)
        encrypted_signature_bytes = encrypt_signature(signature_bytes, instructor_public_key)
        
        # 4. Base64 Encode the final output (Single Line)
        encrypted_signature_b64 = base64.b64encode(encrypted_signature_bytes).decode('utf-8')
        
        print("\n✅ Success! Final Proof Generated:")
        print(f"\n1. Commit Hash: {commit_hash}")
        print("2. Encrypted Signature (Base64, Single Line):")
        print(encrypted_signature_b64)
        print("\n----------------------------------")
        
    except Exception as e:
        print(f"\nCRITICAL FAILURE during Proof Generation: {e}")
        print("Ensure 'cryptography' is installed and key files are present in the root folder.")

if __name__ == "__main__":
    main()
# Final check