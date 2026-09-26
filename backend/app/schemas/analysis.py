from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)


class AnalyzeAcceptedResponse(BaseModel):
    job_id: str
    status: str = "in_progress"
