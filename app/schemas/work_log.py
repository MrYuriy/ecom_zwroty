from datetime import date

from pydantic import BaseModel, Field

# A whole shift and a bit; anything longer is a typo rather than a day's work.
_MAX_MINUTES = 24 * 60


class WorkLogSave(BaseModel):
    minutes: int = Field(ge=0, le=_MAX_MINUTES)


class WorkLogOut(BaseModel):
    work_date: date
    minutes: int
    author_name: str | None = None
