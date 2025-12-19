# Dynalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import FastAPI, Depends
from sqlmodel import Session, select
from lib.models import User, UserBase
from server.dynalert_api.lib.dbmgr import get_session

app = FastAPI()

@app.get("/api/users")
async def get_users(db_session: Session = Depends(get_session)):
    users = db_session.exec(select(User)).all()
    return users

@app.get("/api/user/{user_id}")
async def get_user(user_id: str, db_session: Session = Depends(get_session)):
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    return user

@app.post("/api/user")
def create_user(user: User, db_session: Session = Depends(get_session)):
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@app.delete("/api/user/{user_id}")
def delete_user(user_id: str, db_session: Session = Depends(get_session)):
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    if user:
        db_session.delete(user)
        db_session.commit()
        return {"message": "User deleted"}
    return {"message": "User not found"}

@app.put("/api/user/{user_id}")
def update_user(user_id: str, user_new: UserBase, db_session: Session = Depends(get_session)):
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    if user:
        user.firstname = user_new.firstname
        user.surname = user_new.surname
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return {"message": "User not found"}
