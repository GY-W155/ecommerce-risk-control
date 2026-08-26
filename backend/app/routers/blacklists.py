"""黑名单管理接口。"""
from __future__ import annotations

import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Blacklist
from ..schemas import BlacklistCreate, BlacklistDelete, BlacklistOut

router = APIRouter()


class BlacklistImportIn(BaseModel):
    blacklist_type: str
    text: str  # 每行一个值，或逗号/换行分隔
    remark: Optional[str] = None


@router.get("/blacklists", response_model=List[BlacklistOut])
def list_blacklists(
    blacklist_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Blacklist)
    if blacklist_type:
        q = q.filter(Blacklist.blacklist_type == blacklist_type)
    rows = q.order_by(Blacklist.id.desc()).all()
    return [BlacklistOut.model_validate(r) for r in rows]


@router.post("/blacklists", response_model=BlacklistOut)
def create_blacklist(body: BlacklistCreate, db: Session = Depends(get_db)):
    exists = (
        db.query(Blacklist)
        .filter(
            Blacklist.blacklist_type == body.blacklist_type,
            Blacklist.blacklist_value == body.blacklist_value,
        )
        .first()
    )
    if exists:
        raise HTTPException(400, "该值已在黑名单中")
    row = Blacklist(**body.model_dump(), status=1)
    db.add(row)
    db.commit()
    db.refresh(row)
    return BlacklistOut.model_validate(row)


@router.post("/blacklists/import")
def import_blacklist(body: BlacklistImportIn, db: Session = Depends(get_db)):
    values = re.split(r"[\n,;，；]+", body.text)
    values = [v.strip() for v in values if v.strip()]
    added, skipped = 0, 0
    for v in values:
        exists = (
            db.query(Blacklist)
            .filter(
                Blacklist.blacklist_type == body.blacklist_type,
                Blacklist.blacklist_value == v,
            )
            .first()
        )
        if exists:
            skipped += 1
            continue
        db.add(
            Blacklist(
                blacklist_type=body.blacklist_type,
                blacklist_value=v,
                remark=body.remark,
                status=1,
            )
        )
        added += 1
    db.commit()
    return {"added": added, "skipped": skipped}


@router.post("/blacklists/delete")
def delete_blacklists(body: BlacklistDelete, db: Session = Depends(get_db)):
    rows = db.query(Blacklist).filter(Blacklist.id.in_(body.ids)).all()
    for r in rows:
        db.delete(r)
    db.commit()
    return {"ok": True, "deleted": len(rows)}
