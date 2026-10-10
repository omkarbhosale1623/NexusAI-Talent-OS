"""NexusAI Talent OS — Auth Routes"""
import hashlib, secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.models import User, Tenant, AuthSession
from app.schemas.schemas import SignUpRequest, LoginRequest, AuthResponse, UserProfile, MessageResponse
import bcrypt

router = APIRouter()

def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt(12)).decode()

def verify_password(plain: str, hashed: str) -> bool:
    try: return bcrypt.checkpw(plain.encode(), hashed.encode())
    except: return False

def create_token(user_id: str, org_id: str) -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash

@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignUpRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise HTTPException(400, "Email already registered")
    slug = body.company_name.lower().replace(" ", "-")[:60] + "-" + secrets.token_hex(3)
    tenant = Tenant(name=body.company_name, slug=slug)
    db.add(tenant); await db.flush()
    user = User(org_id=tenant.id, email=body.email.lower(),
                password_hash=hash_password(body.password),
                full_name=body.full_name, role="admin")
    db.add(user); await db.flush()
    raw, token_hash = create_token(user.id, tenant.id)
    from app.core.config import settings
    session = AuthSession(user_id=user.id, org_id=tenant.id, token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(hours=settings.SESSION_EXPIRE_HOURS))
    db.add(session); await db.commit()
    return AuthResponse(token=raw, user_id=user.id, org_id=tenant.id,
        full_name=user.full_name, email=user.email, role=user.role, plan=tenant.plan)

@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    user.last_login = datetime.utcnow()
    raw, token_hash = create_token(user.id, user.org_id)
    from app.core.config import settings
    session = AuthSession(user_id=user.id, org_id=user.org_id, token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(hours=settings.SESSION_EXPIRE_HOURS))
    db.add(session); await db.commit()
    tenant = await db.get(Tenant, user.org_id)
    return AuthResponse(token=raw, user_id=user.id, org_id=user.org_id,
        full_name=user.full_name, email=user.email, role=user.role,
        plan=tenant.plan if tenant else "free")

@router.get("/me", response_model=UserProfile)
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "Not authenticated")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    tenant = await db.get(Tenant, user.org_id)
    return UserProfile(id=user.id, org_id=user.org_id, email=user.email,
        full_name=user.full_name, role=user.role,
        plan=tenant.plan if tenant else "free", created_at=user.created_at)

@router.post("/signout", response_model=MessageResponse)
async def signout():
    return MessageResponse(message="Signed out")
