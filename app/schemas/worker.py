from pydantic import BaseModel, Field


class WorkerStatus(BaseModel):
    is_running: bool
    scheduler_running: bool


class IntervalUpdate(BaseModel):
    interval_minutes: int = Field(..., ge=1, le=60, description="Интервал в минутах (1-60)")