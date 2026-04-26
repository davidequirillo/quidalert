# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import APIRouter, Depends
from sqlmodel import Session, select, delete, desc
from core.exceptions import forbidden_exception
from models.general import User, WhiteListEntry, EmailListDict
from dependencies import get_db_session, get_current_user

router = APIRouter(
    tags=["Whitelist entries"]
)

@router.get("/api/whitelist-entries")
def get_whitelist_entries(
                email: str | None = None,
                authorizer: str | None = None,
                last_seen_id: int = 0,
                limit: int = 100,
                current_user: User = Depends(get_current_user),
                db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    if last_seen_id < 0:
        last_seen_id = 0
    if limit not in [10, 100, 1000]:
        limit = 100
    entries = []
    next_cursor = 0
    if email:
        entries = db_session.exec(
            select(WhiteListEntry).where(
                WhiteListEntry.email == email.lower())).all()    
    else:
        statement = select(WhiteListEntry)
        if (not current_user.is_admin): # officers can see (in bulk) only their own entries
            statement = statement.where(WhiteListEntry.created_by == current_user.email)
        if authorizer:
            authorizer_email = authorizer.lower()
            statement = statement.where(WhiteListEntry.created_by == authorizer_email)
        if last_seen_id > 0:
            statement = statement.where(WhiteListEntry.id < last_seen_id) # type: ignore
        statement = statement.order_by(desc(WhiteListEntry.id)).limit(limit)
        entries = db_session.exec(statement).all()
        if entries:
            next_cursor = entries[-1].id
    return { "entries": entries, "next_cursor": next_cursor }

@router.post("/api/whitelist-entries")
def add_whitelist_entries(
                dict: EmailListDict,
                current_user: User = Depends(get_current_user),
                db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    failed_emails = []
    added_count = 0
    existing_count = 0
    skipped_count = 0
    for e in dict.emails:
        try:
            if (e is None) or (e.strip() == ""):
                skipped_count += 1
                continue
            entry = WhiteListEntry.model_validate({
                "email": e.strip().lower(), 
                "created_by": current_user.email
            })
            if db_session.exec(
                select(WhiteListEntry).where(WhiteListEntry.email == entry.email)
            ).first():
                existing_count += 1
                continue # skip entry if already exists
            db_session.add(entry)
            db_session.flush()
            added_count += 1
        except Exception:
            failed_emails.append(e)
            continue
        if (added_count > 0) and (added_count % 1000 == 0): # commit every 1000 entries to avoid long transactions
            try:
                db_session.commit()
            except Exception:
                db_session.rollback()
    if (added_count > 0) and (added_count % 1000 != 0): # commit remaining entries
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()
    return {
        "message": "Entries processed",
        "total_count": len(dict.emails),
        "skipped_count": skipped_count,
        "added_count": added_count,
        "existing_count": existing_count,
        "failed_count": len(failed_emails), 
        "failed_emails": failed_emails
    }

@router.delete("/api/whitelist-entries/{mode}")
def delete_whitelist_entries(
                mode: str,
                email: str | None = None,
                current_user: User = Depends(get_current_user),
                db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    deleted_count = 0
    total_count = 0
    if mode == "single" and email:
        q = select(WhiteListEntry).where(WhiteListEntry.email == email.lower())
        entry = db_session.exec(q).first()
        if entry: # officers can delete only their own entries
            total_count = 1
            if (not current_user.is_admin) and (entry.created_by != current_user.email):
                raise forbidden_exception()
            db_session.delete(entry)
            db_session.commit()
            deleted_count = 1
    elif mode == "mine":
        statement = delete(WhiteListEntry).where(WhiteListEntry.created_by == current_user.email) # type: ignore
        result = db_session.exec(statement)
        deleted_count = result.rowcount
        total_count = deleted_count
        db_session.commit()
    elif mode == "all":
        if not current_user.is_admin: # officers cannot delete all entries
            raise forbidden_exception()
        statement = delete(WhiteListEntry).where(True) # type: ignore
        result = db_session.exec(statement)
        deleted_count = result.rowcount
        total_count = deleted_count
        db_session.commit()
    return {
        "message": "Entries deleted",
        "total_count": total_count,
        "deleted_count": deleted_count
    }
