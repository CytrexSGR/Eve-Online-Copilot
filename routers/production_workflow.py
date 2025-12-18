"""
Production Workflow Router

API endpoints for production job management and tracking.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from services.production.workflow_service import ProductionWorkflowService

router = APIRouter(prefix="/api/production/workflow", tags=["production-workflow"])
service = ProductionWorkflowService()


class MaterialDecision(BaseModel):
    material_type_id: int
    quantity_needed: int
    decision: str  # 'make' or 'buy'
    cost_per_unit: Optional[float] = None
    total_cost: Optional[float] = None


class CreateJobRequest(BaseModel):
    character_id: int
    item_type_id: int
    blueprint_type_id: int
    me_level: int = 0
    te_level: int = 0
    runs: int = 1
    materials: List[MaterialDecision]
    facility_id: Optional[int] = None
    system_id: Optional[int] = None


class UpdateJobRequest(BaseModel):
    status: Optional[str] = None
    actual_revenue: Optional[float] = None


@router.post("/jobs")
async def create_production_job(request: CreateJobRequest):
    """
    Create a new production job

    Args:
        request: Job creation data

    Returns:
        Created job data
    """
    result = service.create_job(
        character_id=request.character_id,
        item_type_id=request.item_type_id,
        blueprint_type_id=request.blueprint_type_id,
        me_level=request.me_level,
        te_level=request.te_level,
        runs=request.runs,
        materials=[m.dict() for m in request.materials],
        facility_id=request.facility_id,
        system_id=request.system_id
    )

    if 'error' in result:
        raise HTTPException(status_code=500, detail=result['error'])

    return result


@router.get("/jobs")
async def get_production_jobs(
    character_id: int = Query(..., description="Character ID"),
    status: Optional[str] = Query(None, description="Status filter")
):
    """
    Get production jobs for a character

    Args:
        character_id: Character ID
        status: Optional status filter

    Returns:
        List of jobs
    """
    result = service.get_jobs(character_id, status)
    return result


@router.patch("/jobs/{job_id}")
async def update_production_job(
    job_id: int,
    request: UpdateJobRequest
):
    """
    Update production job status

    Args:
        job_id: Job ID
        request: Update data

    Returns:
        Update status
    """
    result = service.update_job(
        job_id=job_id,
        status=request.status,
        actual_revenue=request.actual_revenue
    )

    if 'error' in result:
        raise HTTPException(status_code=500, detail=result['error'])

    return result
