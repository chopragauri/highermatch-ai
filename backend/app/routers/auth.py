from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(db: Session, user: models.User) -> schemas.UserOut:
    profile_complete = None
    if user.role == "candidate":
        profile = (
            db.query(models.CandidateProfile)
            .filter(models.CandidateProfile.user_id == user.id)
            .first()
        )
        profile_complete = profile.profile_complete if profile else False
    return schemas.UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        phone=user.phone,
        profile_complete=profile_complete,
        avatar_emoji=user.avatar_emoji,
    )


@router.post("/register", response_model=schemas.TokenResponse)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if payload.role == "hr":
        # This domain check is the actual access gate for HR accounts — it runs
        # server-side regardless of what the client sends, so a candidate cannot
        # register as HR simply by picking that role in the UI.
        if not security.email_domain_allowed_for_hr(email):
            raise HTTPException(
                status_code=403,
                detail=(
                    "HR registration is restricted to approved organization email "
                    "domains. Contact your admin if you believe this is an error."
                ),
            )
        org_domain = email.split("@")[-1]
    else:
        if not payload.phone:
            raise HTTPException(
                status_code=422, detail="Phone number is required for candidate registration"
            )
        org_domain = None

    user = models.User(
        email=email,
        phone=payload.phone,
        password_hash=security.hash_password(payload.password),
        role=payload.role,
        full_name=payload.full_name,
        org_domain=org_domain,
    )
    db.add(user)
    db.flush()

    if payload.role == "candidate":
        db.add(
            models.CandidateProfile(user_id=user.id, current_location=None, profile_complete=False)
        )

    db.commit()
    db.refresh(user)

    token = security.create_access_token({"sub": str(user.id), "role": user.role})
    return schemas.TokenResponse(access_token=token, user=_user_out(db, user))


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if not user or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = security.create_access_token({"sub": str(user.id), "role": user.role})
    return schemas.TokenResponse(access_token=token, user=_user_out(db, user))


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _user_out(db, user)


@router.patch("/me/avatar", response_model=schemas.UserOut)
def update_avatar(
    payload: schemas.AvatarUpdateRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.avatar_emoji = payload.avatar_emoji
    db.commit()
    db.refresh(user)
    return _user_out(db, user)
