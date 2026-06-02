"""
NCU credential manager — AES-256-GCM + macOS Keychain

Usage:
    python ncu_auth.py login    # prompt for user/pass + passphrase, store encrypted
    python ncu_auth.py status   # check if credentials are stored
    python ncu_auth.py logout   # remove credentials.enc and Keychain entry

Internal API (used by selenium_checkin.py):
    account, password = ncu_auth.get_credentials()
"""

import sys
import os
import getpass
import secrets
import struct

import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

KEYCHAIN_SERVICE = "ncu-checkin"
KEYCHAIN_USER    = "passphrase"
CREDS_FILE       = os.path.join(os.path.dirname(__file__), "credentials.enc")

# ── Key derivation ────────────────────────────────────────────────────────────

def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    return kdf.derive(passphrase.encode())


# ── Encrypt / decrypt ─────────────────────────────────────────────────────────

def _encrypt(plaintext: str, passphrase: str) -> bytes:
    salt  = os.urandom(16)
    nonce = os.urandom(12)
    key   = _derive_key(passphrase, salt)
    ct    = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    # layout: [2B salt_len][salt][2B nonce_len][nonce][ciphertext+tag]
    return (
        struct.pack(">H", len(salt)) + salt +
        struct.pack(">H", len(nonce)) + nonce +
        ct
    )


def _decrypt(data: bytes, passphrase: str) -> str:
    offset = 0
    salt_len  = struct.unpack_from(">H", data, offset)[0]; offset += 2
    salt      = data[offset:offset + salt_len];             offset += salt_len
    nonce_len = struct.unpack_from(">H", data, offset)[0]; offset += 2
    nonce     = data[offset:offset + nonce_len];            offset += nonce_len
    ct        = data[offset:]
    key       = _derive_key(passphrase, salt)
    return AESGCM(key).decrypt(nonce, ct, None).decode()


# ── Keychain helpers ──────────────────────────────────────────────────────────

def _store_passphrase(passphrase: str) -> None:
    keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_USER, passphrase)


def _load_passphrase() -> str | None:
    return keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_USER)


def _delete_passphrase() -> None:
    try:
        keyring.delete_password(KEYCHAIN_SERVICE, KEYCHAIN_USER)
    except keyring.errors.PasswordDeleteError:
        pass


# ── Public API ────────────────────────────────────────────────────────────────

def get_credentials() -> tuple[str, str]:
    """Decrypt stored credentials and return (account, password)."""
    if not os.path.exists(CREDS_FILE):
        raise RuntimeError("No credentials stored. Run: python ncu_auth.py login")

    passphrase = _load_passphrase()
    if not passphrase:
        raise RuntimeError("Passphrase not found in Keychain. Run: python ncu_auth.py login")

    with open(CREDS_FILE, "rb") as f:
        data = f.read()

    try:
        plaintext = _decrypt(data, passphrase)
    except Exception:
        raise RuntimeError("Decryption failed — wrong passphrase or corrupted file.")

    if ":" not in plaintext:
        raise RuntimeError("Unexpected credential format in credentials.enc")

    account, password = plaintext.split(":", 1)
    return account, password


# ── CLI commands ──────────────────────────────────────────────────────────────

def cmd_login():
    print("NCU Credential Setup")
    print("─" * 30)
    account    = input("Student ID / Account: ").strip()
    password   = getpass.getpass("Password: ")
    if not account or not password:
        print("[error] Account and password are required.")
        sys.exit(1)

    passphrase = secrets.token_urlsafe(32)  # 256-bit, never shown to user

    encrypted = _encrypt(f"{account}:{password}", passphrase)
    with open(CREDS_FILE, "wb") as f:
        f.write(encrypted)
    os.chmod(CREDS_FILE, 0o600)

    _store_passphrase(passphrase)

    # Clear sensitive locals
    password = passphrase = confirm = None  # noqa: F841

    print("\n✓ credentials.enc written (AES-256-GCM)")
    print("✓ Passphrase stored in macOS Keychain")
    print("\nFuture check-ins are fully automated — no input needed.")


def cmd_status():
    has_file       = os.path.exists(CREDS_FILE)
    has_passphrase = _load_passphrase() is not None
    print(f"credentials.enc : {'✓ found' if has_file else '✗ missing'}")
    print(f"Keychain entry  : {'✓ found' if has_passphrase else '✗ missing'}")
    if has_file and has_passphrase:
        try:
            account, _ = get_credentials()
            print(f"Decryption test : ✓ ok  (account: {account})")
        except Exception as e:
            print(f"Decryption test : ✗ {e}")


def cmd_logout():
    if os.path.exists(CREDS_FILE):
        os.remove(CREDS_FILE)
        print("✓ credentials.enc removed")
    _delete_passphrase()
    print("✓ Keychain entry removed")


COMMANDS = {
    "login":  cmd_login,
    "status": cmd_status,
    "logout": cmd_logout,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: python ncu_auth.py <login|status|logout>")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
