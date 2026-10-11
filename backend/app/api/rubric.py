"""API routes for rubric."""

from fastapi import APIRouter

from app.schemas import RubricResponse
from app.services.rubric import get_rubric as get_rubric_service

router = APIRouter(prefix="/api/v1/rubric", tags=["rubric"])


@router.get("", response_model=RubricResponse)
async def get_rubric():
    """Get current rubric configuration."""
    rubric = get_rubric_service()

    return RubricResponse(
        version=rubric.version,
        description=rubric.description,
        dimensions=[
            {
                "code": dim.code,
                "name": dim.name,
                "weight": dim.weight,
                "description": dim.description,
                "subchecks": [
                    {
                        "id": sc.id,
                        "name": sc.name,
                        "points": sc.points,
                        "applies_to": sc.applies_to,
                        "not_applies_to": sc.not_applies_to,
                        "evidence_sources": sc.evidence_sources,
                        "description": sc.description,
                        "severity_map": sc.severity_map,
                    }
                    for sc in dim.subchecks
                ],
            }
            for dim in rubric.dimensions
        ],
        project_type_rules=rubric.project_type_rules,
        severity_mapping=rubric.severity_mapping,
        confidence_by_category=rubric.confidence_by_category,
    )
