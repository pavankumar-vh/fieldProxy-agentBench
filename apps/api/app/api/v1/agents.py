from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AgentVersion
from app.repositories import agent_version_out, dashboard_metrics
from app.schemas import AgentVersionOut, DashboardMetricsOut

router = APIRouter(tags=["agents"])


@router.get("/agents/metrics", response_model=DashboardMetricsOut)
def get_metrics(db: Session = Depends(get_db)):
    return dashboard_metrics(db)


@router.get("/agents", response_model=list[AgentVersionOut])
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(AgentVersion).order_by(AgentVersion.created_at.desc()).all()
    return [agent_version_out(db, av) for av in agents]


@router.get("/agents/{agent_id}", response_model=AgentVersionOut)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    av = db.get(AgentVersion, agent_id)
    if av is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return agent_version_out(db, av)
