from pydantic import BaseModel
from typing import List

class Activity(BaseModel):
    name: str
    location: str
    details: str = ""
    transportation: str = ""
    source: str = ""

class DayPlan(BaseModel):
    day_number: int
    activities: List[Activity]
    total_estimated_cost: float = 0.0
    summary: str = ""

class Itinerary(BaseModel):
    days: List[DayPlan]
    conclusion: str
    ending_statement: str
