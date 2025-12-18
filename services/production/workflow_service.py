"""
Production Workflow Service

Business logic for production job management and tracking.
"""

from typing import Dict, List, Any, Optional
from services.production.workflow_repository import ProductionWorkflowRepository


class ProductionWorkflowService:
    """Service for production workflow operations"""

    def __init__(self):
        self.repo = ProductionWorkflowRepository()

    def create_job(
        self,
        character_id: int,
        item_type_id: int,
        blueprint_type_id: int,
        me_level: int,
        te_level: int,
        runs: int,
        materials: List[Dict[str, Any]],
        facility_id: Optional[int] = None,
        system_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new production job

        Args:
            character_id: Character ID
            item_type_id: Item to produce
            blueprint_type_id: Blueprint to use
            me_level: Material Efficiency
            te_level: Time Efficiency
            runs: Number of runs
            materials: List of materials with make-or-buy decisions
            facility_id: Optional facility
            system_id: Optional system

        Returns:
            Created job data
        """
        # Calculate costs
        total_cost = sum(m.get('total_cost', 0) for m in materials)

        # Create job
        job_id = self.repo.create_job(
            character_id=character_id,
            item_type_id=item_type_id,
            blueprint_type_id=blueprint_type_id,
            me_level=me_level,
            te_level=te_level,
            runs=runs,
            facility_id=facility_id,
            system_id=system_id,
            total_cost=total_cost,
            expected_revenue=None
        )

        if not job_id:
            return {'error': 'Failed to create job'}

        # Add materials
        for material in materials:
            self.repo.add_job_material(
                job_id=job_id,
                material_type_id=material['material_type_id'],
                quantity_needed=material['quantity_needed'],
                decision=material['decision'],
                cost_per_unit=material.get('cost_per_unit'),
                total_cost=material.get('total_cost')
            )

        return {
            'job_id': job_id,
            'status': 'planned',
            'total_cost': total_cost
        }

    def get_jobs(
        self,
        character_id: int,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get jobs for a character

        Args:
            character_id: Character ID
            status: Optional status filter

        Returns:
            List of jobs
        """
        jobs = self.repo.get_jobs(character_id, status)

        return {
            'character_id': character_id,
            'status_filter': status,
            'jobs': jobs,
            'total_jobs': len(jobs)
        }

    def update_job(
        self,
        job_id: int,
        status: Optional[str] = None,
        actual_revenue: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update job status

        Args:
            job_id: Job ID
            status: New status
            actual_revenue: Actual revenue (when completed)

        Returns:
            Success status
        """
        success = self.repo.update_job(
            job_id=job_id,
            status=status,
            actual_revenue=actual_revenue
        )

        if not success:
            return {'error': 'Failed to update job'}

        return {
            'job_id': job_id,
            'updated': True
        }
