from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models
from ..config import AUTOMATION_ENABLED, AUTOMATION_TICK_SECONDS
from ..database import get_db
from ..deps import require_admin
from ..services import automation_service as auto

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("/status")
def status(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return {"enabled": AUTOMATION_ENABLED, "tick_seconds": AUTOMATION_TICK_SECONDS,
            "jobs": [{"name": n, "description": d} for n, d in auto.JOBS_INFO.items()]}


@router.get("/runs")
def runs(db: Session = Depends(get_db), admin=Depends(require_admin)):
    rows = db.query(models.AutomationRun).order_by(models.AutomationRun.ran_at.desc()).limit(100).all()
    return [{"id": r.id, "job": r.job, "run_key": r.run_key, "status": r.status, "details": r.details, "ran_at": r.ran_at} for r in rows]


@router.post("/run")
def run(job: str = Query("all"), force: bool = Query(False), db: Session = Depends(get_db), admin=Depends(require_admin)):
    """Run jobs now. force=true ignores the time-of-day rules (handy for demos); without it, jobs only run if they're due."""
    if job == "all":
        return auto.run_all(db, force=force)
    if job not in auto.JOB_FUNCS:
        raise HTTPException(status_code=400, detail=f"Unknown job. Choose one of: {', '.join(auto.JOB_FUNCS)}")
    return {job: auto.run_job(db, job, force=force)}
