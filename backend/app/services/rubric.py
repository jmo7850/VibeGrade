"""Rubric loading and management."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class Subcheck(BaseModel):
    id: str
    name: str
    points: int
    applies_to: list[str] = Field(default_factory=list)
    not_applies_to: list[str] = Field(default_factory=list)
    evidence_sources: list[str] = Field(default_factory=list)
    description: str = ""
    severity_map: dict[str, float] = Field(default_factory=dict)


class Dimension(BaseModel):
    code: str
    name: str
    weight: int
    description: str = ""
    subchecks: list[Subcheck] = Field(default_factory=list)
    # Project-type-specific weight overrides (e.g., {"cli": 3, "web_app": 5})
    weight_overrides: dict[str, int] = Field(default_factory=dict)


class Rubric(BaseModel):
    version: str
    description: str = ""
    dimensions: list[Dimension] = Field(default_factory=list)
    project_type_rules: dict[str, Any] = Field(default_factory=dict)
    severity_mapping: dict[str, dict[str, str]] = Field(default_factory=dict)
    confidence_by_category: dict[str, str] = Field(default_factory=dict)

    def get_applicable_subchecks(self, project_type: str) -> list[Subcheck]:
        """Get all subchecks that apply to the given project type."""
        applicable = []
        for dim in self.dimensions:
            for subcheck in dim.subchecks:
                if self._subcheck_applies(subcheck, project_type):
                    applicable.append(subcheck)
        return applicable

    def _subcheck_applies(self, subcheck: Subcheck, project_type: str) -> bool:
        """Check if a subcheck applies to the project type."""
        # Check explicit exclusion
        if project_type in subcheck.not_applies_to:
            return False

        # Check applies_to list
        if subcheck.applies_to:
            if "all" in subcheck.applies_to:
                return True
            if project_type in subcheck.applies_to:
                return True
            return False

        # Check project-type-specific exclusion rules
        rules = self.project_type_rules.get(project_type, {})
        excluded = rules.get("excluded_subchecks", [])
        if subcheck.id in excluded:
            return False

        # Default: applies to all
        return True

    def get_subcheck(self, subcheck_id: str) -> Subcheck | None:
        """Get a subcheck by ID."""
        for dim in self.dimensions:
            for subcheck in dim.subchecks:
                if subcheck.id == subcheck_id:
                    return subcheck
        return None

    def get_dimension_for_subcheck(self, subcheck_id: str) -> Dimension | None:
        """Get the dimension that contains a subcheck."""
        for dim in self.dimensions:
            for subcheck in dim.subchecks:
                if subcheck.id == subcheck_id:
                    return dim
        return None

    def get_total_applicable_points(self, project_type: str) -> int:
        """Get total points for applicable subchecks."""
        return sum(sc.points for sc in self.get_applicable_subchecks(project_type))

    def get_dimension_weight(self, dimension_code: str, project_type: str) -> int:
        """Get effective weight for a dimension for a project type."""
        for dim in self.dimensions:
            if dim.code == dimension_code:
                return dim.weight_overrides.get(project_type, dim.weight)
        return 0

    def get_project_type_rules(self, project_type: str) -> dict[str, Any]:
        """Get rules for a specific project type."""
        return self.project_type_rules.get(project_type, {})


def load_rubric(rubric_path: Path) -> Rubric:
    """Load rubric from YAML file."""
    with open(rubric_path) as f:
        data = yaml.safe_load(f)
    return Rubric(**data)


@lru_cache
def get_rubric(rubric_version: str = "v1", rubric_path: Path | None = None) -> Rubric:
    """Get cached rubric instance."""
    if rubric_path is None:
        rubric_path = Path(__file__).parent.parent.parent.parent / "rubric" / f"{rubric_version}.yaml"
    return load_rubric(rubric_path)
