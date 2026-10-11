"""Finding analysis and deduplication."""

import hashlib
from collections import defaultdict
from typing import Any

from app.core.logging import get_logger
from app.models import Confidence, Severity
from app.services.rubric import get_rubric
from app.services.static_analysis import NormalizedFinding

logger = get_logger(__name__)


class FindingAnalyzer:
    """Analyzes, deduplicates, and enriches findings."""

    def __init__(self):
        self.rubric = get_rubric()

    def analyze(
        self,
        findings: list[NormalizedFinding],
        project_type: str,
    ) -> list[dict[str, Any]]:
        """
        Process findings: deduplicate, assign dimensions, determine applicability.
        Returns list of enriched finding dicts ready for storage.
        """
        # Step 1: Deduplicate
        deduplicated = self._deduplicate(findings)

        # Step 2: Map to rubric dimensions
        enriched = self._map_to_dimensions(deduplicated, project_type)

        # Step 3: Apply applicability rules
        final = self._apply_applicability(enriched, project_type)

        logger.info("Finding analysis complete", input=len(findings), output=len(final))
        return final

    def _deduplicate(self, findings: list[NormalizedFinding]) -> list[NormalizedFinding]:
        """Deduplicate findings by fingerprint."""
        groups: dict[str, list[NormalizedFinding]] = defaultdict(list)

        for finding in findings:
            # Create stable fingerprint
            fingerprint = self._create_fingerprint(finding)
            groups[fingerprint].append(finding)

        deduplicated = []
        for _fingerprint, group in groups.items():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # Merge: keep highest severity, highest confidence
                merged = self._merge_findings(group)
                deduplicated.append(merged)

        return deduplicated

    def _create_fingerprint(self, finding: NormalizedFinding) -> str:
        """Create stable fingerprint for deduplication."""
        # Normalize rule_id across tools
        normalized_rule = self._normalize_rule_id(finding.tool, finding.rule_id)
        content = f"{finding.file_path}:{finding.line_start}:{normalized_rule}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _normalize_rule_id(self, tool: str, rule_id: str) -> str:
        """Normalize rule IDs across tools for deduplication."""
        # Map common rule categories
        if tool == "eslint":
            if rule_id in ("no-unused-vars", "@typescript-eslint/no-unused-vars"):
                return "unused-variable"
            if rule_id in ("no-console",):
                return "console-log"
        elif tool == "typescript":
            if "TS6133" in rule_id:  # unused variable
                return "unused-variable"
        elif tool == "semgrep":
            # Semgrep rules often have descriptive IDs
            if "unused" in rule_id.lower():
                return "unused-variable"
        return rule_id

    def _merge_findings(self, findings: list[NormalizedFinding]) -> NormalizedFinding:
        """Merge multiple findings into one."""
        # Sort by severity (critical first) then confidence (verified first)
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        confidence_order = {
            Confidence.VERIFIED: 0,
            Confidence.LIKELY: 1,
            Confidence.HEURISTIC: 2,
            Confidence.INFO: 3,
        }

        sorted_findings = sorted(
            findings,
            key=lambda f: (severity_order[f.severity], confidence_order[f.confidence])
        )
        primary = sorted_findings[0]

        # Combine metadata
        combined_metadata = {"sources": []}
        for f in findings:
            combined_metadata["sources"].append({
                "tool": f.tool,
                "rule_id": f.rule_id,
                "severity": f.severity.value,
                "confidence": f.confidence.value,
            })
            combined_metadata.update(f.metadata)

        return NormalizedFinding(
            tool=primary.tool,
            tool_version=primary.tool_version,
            rule_id=primary.rule_id,
            rule_name=primary.rule_name,
            file_path=primary.file_path,
            line_start=primary.line_start,
            line_end=primary.line_end,
            severity=primary.severity,
            confidence=primary.confidence,
            message=primary.message,
            metadata=combined_metadata,
        )

    def _map_to_dimensions(
        self, findings: list[NormalizedFinding], project_type: str
    ) -> list[dict[str, Any]]:
        """Map findings to rubric dimensions."""
        enriched = []

        for finding in findings:
            # Determine which dimensions this finding affects
            dimensions = self._find_affected_dimensions(finding)

            enriched.append({
                "finding": finding,
                "dimensions": dimensions,
                "applicable": True,  # Will be filtered in next step
            })

        return enriched

    def _find_affected_dimensions(self, finding: NormalizedFinding) -> list[str]:
        """Determine which rubric dimensions a finding affects."""
        dimensions = []

        # Security findings
        if finding.tool in ("semgrep", "trivy", "detect_secrets"):
            dimensions.append("security_privacy")

        # TypeScript/ESLint findings
        if finding.tool in ("typescript", "eslint"):
            # Check rule categories
            rule_lower = finding.rule_id.lower()
            if any(x in rule_lower for x in ["unused", "no-unused"]):
                dimensions.append("engineering_discipline")
            elif any(x in rule_lower for x in ["complexity", "max-lines", "max-depth"]):
                dimensions.append("architecture_maintainability")
            elif any(x in rule_lower for x in ["await", "promise", "async"]):
                dimensions.append("functional_correctness")
            elif any(x in rule_lower for x in ["security", "injection", "xss", "eval"]):
                dimensions.append("security_privacy")
            else:
                dimensions.append("engineering_discipline")

        # Internal README checks
        if finding.tool == "readme":
            dimensions.append("documentation_reproducibility")

        # Internal architecture checks
        if finding.tool == "arch":
            dimensions.append("architecture_maintainability")

        # Internal profiler checks (rule-specific mapping)
        if finding.tool == "profiler":
            rule_map = {
                "profiler.missing_ci": "deployment_operations",
                "profiler.no_dockerfile": "deployment_operations",
                "profiler.missing_lockfile": "engineering_discipline",
                "profiler.no_package_manager": "engineering_discipline",
                "profiler.no_tests": "testing_verification",
            }
            dimensions.append(rule_map.get(finding.rule_id, "engineering_discipline"))

        # Verification findings (failed builds/tests)
        if finding.tool == "verification":
            rule_map = {
                "test_failure": "testing_verification",
                "build_failure": "functional_correctness",
                "install_failure": "functional_correctness",
            }
            dimensions.append(rule_map.get(finding.rule_id, "functional_correctness"))

        # Default fallback
        if not dimensions:
            dimensions.append("engineering_discipline")

        return dimensions

    def _apply_applicability(
        self, enriched: list[dict[str, Any]], project_type: str
    ) -> list[dict[str, Any]]:
        """Filter findings based on project type applicability."""
        applicable_subcheck_ids = set()
        for subcheck in self.rubric.get_applicable_subchecks(project_type):
            applicable_subcheck_ids.add(subcheck.id)

        # For now, we don't filter findings - we just mark them
        # The scoring engine will handle applicability
        for item in enriched:
            # Check if any of the finding's dimensions have applicable subchecks
            has_applicable = False
            for dim_code in item["dimensions"]:
                self.rubric.get_dimension_for_subcheck(dim_code)  # This won't work directly
                # Better: check if dimension has any applicable subchecks
                for dim_obj in self.rubric.dimensions:
                    if dim_obj.code in item["dimensions"]:
                        for sc in dim_obj.subchecks:
                            if sc.id in applicable_subcheck_ids:
                                has_applicable = True
                                break
                if has_applicable:
                    break
            item["applicable"] = has_applicable

        return enriched
