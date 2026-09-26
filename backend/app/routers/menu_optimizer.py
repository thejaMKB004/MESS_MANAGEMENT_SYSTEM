from datetime import date as date_cls
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import require_admin
from ..services.menu_optimizer_service import get_suggestions

router = APIRouter(prefix="/menu-optimizer", tags=["menu-optimizer"])


@router.get("/suggestions")
def suggestions(
    from_: date_cls = Query(None, alias="from"),
    to: date_cls = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return get_suggestions(db, from_, to)
