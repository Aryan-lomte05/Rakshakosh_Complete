# RBAC Implementation Changelog

## Date: January 9, 2026

---

## Overview

Implemented a complete **Tier-Based RBAC (Role-Based Access Control)** system for the Rakshakosh project. This enables user authentication with JWT tokens and in-place file encryption/decryption based on user tier levels.

---

## New Files Created

### Authentication Module (`backend/auth/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports |
| `models.py` | Pydantic schemas for signup/login/user |
| `auth_service.py` | Password hashing (Argon2), JWT creation, user CRUD |
| `auth_api.py` | API endpoints: `/auth/signup`, `/auth/login`, `/auth/logout`, `/auth/me`, `/auth/tiers` |
| `middleware.py` | `get_current_user` dependency, `require_tier()` decorator |

### Documents Module (`backend/documents/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports |
| `document_service.py` | List files by tier, decrypt documents |
| `document_api.py` | API endpoints for document listing/download |
| `file_crypto.py` | **In-place encryption/decryption** for tier-based access |

### Database Module (`backend/db/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports |
| `mongodb.py` | Async MongoDB connection (motor), index creation |

### RBAC Module (`backend/rbac/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports |
| `tier_config.py` | **Tier definitions** - EDIT THIS to change access patterns |

### Test & Config Files

| File | Purpose |
|------|---------|
| `requirements_rbac.txt` | New dependencies (motor, passlib, argon2, PyJWT) |
| `backend/test_scripts/test_rbac.py` | Test script for RBAC functionality |

---

## Modified Files

| File | Changes |
|------|---------|
| `backend/api/main.py` | Added auth & documents routers, MongoDB lifecycle events |

---

## Tier Configuration

**Location:** `backend/rbac/tier_config.py`

```python
PROTECTED_FOLDER = "backend/test_docs"

TIER_DEFINITIONS = {
    1: {"name": "Intern", "patterns": ["a.pdf", "b.pdf"]},
    2: {"name": "Analyst", "patterns": ["c.pdf", "d.pdf"]},
    3: {"name": "Manager", "patterns": ["e.pdf"]},
    4: {"name": "Admin", "patterns": ["*"]},  # All files
}
```

**Inheritance:** Each tier can access its patterns + all lower tier patterns.

---

## API Endpoints

### Authentication

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/signup` | POST | ❌ | Register user (email, password, tier_level) |
| `/auth/login` | POST | ❌ | Login → **decrypts accessible files in folder** |
| `/auth/logout` | POST | ✅ JWT | Logout → **re-encrypts files** |
| `/auth/me` | GET | ✅ JWT | Get current user profile |
| `/auth/tiers` | GET | ❌ | List all tier definitions |

### Documents (Optional)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/documents` | GET | ✅ JWT | List accessible documents |
| `/documents/all` | GET | ✅ JWT | List all with access status |
| `/documents/{file}/download` | GET | ✅ JWT | Download/decrypt file |

---

## How It Works

### Flow

```
1. INITIAL SETUP:
   python -m backend.documents.file_crypto encrypt
   → All files in test_docs become .enc files

2. USER LOGS IN:
   POST /auth/login {email, password}
   → JWT token created
   → Tier-accessible files DECRYPTED in-place (a.pdf.enc → a.pdf)
   → User can now open/view decrypted files directly

3. USER LOGS OUT:
   POST /auth/logout (with JWT header)
   → Decrypted files REMOVED
   → Only .enc files remain
```

### Encryption Details

- **Algorithm:** AES-256-GCM (authenticated encryption)
- **Key Location:** `backend/security/master.key` (auto-generated)
- **Encrypted Format:** JSON with `ciphertext`, `nonce`, `algorithm`

---

## Dependencies Added

```
motor>=3.3.0           # MongoDB async driver
passlib[argon2]>=1.7.4 # Password hashing
argon2-cffi>=23.1.0    # Argon2 support
PyJWT>=2.8.0           # JWT tokens
pydantic[email]>=2.0.0 # Email validation
```

Install: `pip install -r requirements_rbac.txt`

---

## Testing Instructions

### Prerequisites

1. MongoDB running locally:
   ```bash
   mongod --dbpath ~/data/db
   ```

2. Files encrypted (run once):
   ```bash
   python -m backend.documents.file_crypto encrypt
   ```

### Start Server

```bash
source ~/venv/bin/activate  # or your local env
python -m backend.api.main
```

### Test via Swagger UI

Open: http://localhost:8000/docs

1. **Signup:** POST `/auth/signup`
   ```json
   {"email": "test@test.com", "password": "password123", "tier_level": 2}
   ```

2. **Login:** POST `/auth/login`
   ```json
   {"email": "test@test.com", "password": "password123"}
   ```
   → Check `backend/test_docs/` - files should be decrypted!

3. **Logout:** POST `/auth/logout` (add Authorization header with token)
   → Files should be re-encrypted

### CLI Testing

```bash
# Test tier config
python -m backend.rbac.tier_config

# Encrypt all files
python -m backend.documents.file_crypto encrypt

# Decrypt for tier 2
python -m backend.documents.file_crypto decrypt 2

# Re-encrypt all
python -m backend.documents.file_crypto cleanup
```

---

## What's Remaining (Not Implemented Yet)

- [ ] **Qdrant metadata filtering** - Add `access_tier` to chunk metadata for query filtering
- [ ] **Frontend integration** - Connect to RakshaKosh-frontend
- [ ] **User management panel** - Admin UI for managing users/tiers
- [ ] **Document upload with tier** - Set tier on ingestion

---

## File Locations Summary

```
backend/
├── auth/              # NEW - Authentication
├── db/                # NEW - MongoDB
├── documents/         # NEW - File access + crypto
├── rbac/              # NEW - Tier config
├── security/
│   └── master.key     # Auto-generated encryption key
└── test_docs/
    ├── a.pdf.enc      # Encrypted files
    ├── b.pdf.enc
    └── ...
```
