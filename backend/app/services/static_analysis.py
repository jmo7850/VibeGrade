"""Static analysis engine."""

import asyncio
import json
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.models import Confidence, Severity
from app.services.profiler import ProjectProfile
from app.services.rubric import get_rubric

logger = get_logger(__name__)


class ToolStatus(Enum):
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"
    ERROR = "error"


@dataclass
class ToolResult:
    tool: str
    status: ToolStatus
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    findings: list[dict[str, Any]] = None


@dataclass
class NormalizedFinding:
    tool: str
    tool_version: str
    rule_id: str
    rule_name: str
    file_path: str
    line_start: int
    line_end: int
    severity: Severity
    confidence: Confidence
    message: str
    metadata: dict[str, Any]


class ToolRunner:
    """Runs static analysis tools and normalizes output."""

    def __init__(self, workspace: Path, profile: "ProjectProfile"):
        self.workspace = workspace
        self.profile = profile
        self.timeout = 120  # seconds per tool

    async def run_all(self) -> list[NormalizedFinding]:
        """Run all applicable static analysis tools."""
        all_findings = []

        # Run tools based on project languages
        if "typescript" in self.profile.languages or "javascript" in self.profile.languages:
            all_findings.extend(await self._run_eslint())
            all_findings.extend(await self._run_typescript())

        # Semgrep for all languages (security-focused)
        all_findings.extend(await self._run_semgrep())

        # Trivy for dependency vulnerabilities
        all_findings.extend(await self._run_trivy())

        # detect-secrets for all projects
        all_findings.extend(await self._run_detect_secrets())

        return all_findings

    async def _run_tool(
        self, cmd: list[str], tool_name: str
    ) -> ToolResult:
        """Run a tool command with timeout."""
        start = time.time()
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout
            )
            duration_ms = int((time.time() - start) * 1000)
            return ToolResult(
                tool=tool_name,
                status=ToolStatus.AVAILABLE,
                exit_code=process.returncode,
                stdout=stdout.decode("utf-8", errors="ignore"),
                stderr=stderr.decode("utf-8", errors="ignore"),
                duration_ms=duration_ms,
            )
        except FileNotFoundError:
            return ToolResult(
                tool=tool_name,
                status=ToolStatus.NOT_INSTALLED,
                exit_code=None,
                stdout="",
                stderr=f"{tool_name} not found",
                duration_ms=int((time.time() - start) * 1000),
            )
        except TimeoutError:
            return ToolResult(
                tool=tool_name,
                status=ToolStatus.ERROR,
                exit_code=-1,
                stdout="",
                stderr=f"{tool_name} timed out after {self.timeout}s",
                duration_ms=self.timeout * 1000,
            )
        except Exception as e:
            return ToolResult(
                tool=tool_name,
                status=ToolStatus.ERROR,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    def _get_tool_version(self, tool: str) -> str:
        """Get tool version."""
        try:
            result = subprocess.run(
                [tool, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip().split("\n")[0]
        except Exception:
            return "unknown"

    async def _run_eslint(self) -> list[NormalizedFinding]:
        """Run ESLint."""
        result = await self._run_tool(
            ["eslint", "--format=json", "--no-error-on-unmatched-pattern", "."],
            "eslint",
        )
        if result.status != ToolStatus.AVAILABLE:
            logger.warning("ESLint not available", status=result.status.value)
            return []

        findings = []
        tool_version = self._get_tool_version("eslint")
        try:
            eslint_output = json.loads(result.stdout)
            for file_result in eslint_output:
                file_path = file_result.get("filePath", "").replace(str(self.workspace) + "/", "")
                for msg in file_result.get("messages", []):
                    severity = self._map_eslint_severity(msg.get("severity", 2))
                    findings.append(NormalizedFinding(
                        tool="eslint",
                        tool_version=tool_version,
                        rule_id=msg.get("ruleId", "unknown"),
                        rule_name=msg.get("ruleId", "unknown"),
                        file_path=file_path,
                        line_start=msg.get("line", 1),
                        line_end=msg.get("endLine", msg.get("line", 1)),
                        severity=severity,
                        confidence=Confidence.LIKELY,
                        message=msg.get("message", ""),
                        metadata={"column": msg.get("column")},
                    ))
        except json.JSONDecodeError:
            logger.warning("Failed to parse ESLint output")
        return findings

    async def _run_typescript(self) -> list[NormalizedFinding]:
        """Run TypeScript compiler check."""
        result = await self._run_tool(
            ["tsc", "--noEmit", "--pretty", "false"],
            "typescript",
        )
        if result.status != ToolStatus.AVAILABLE:
            return []

        findings = []
        tool_version = self._get_tool_version("tsc")
        # Parse tsc output (simplified)
        for line in result.stdout.split("\n"):
            if ": error TS" in line or ": warning TS" in line:
                # Format: file.ts(line,col): error TS1234: message
                parts = line.split(":")
                if len(parts) >= 4:
                    file_path = parts[0]
                    line_num = int(parts[1]) if parts[1].isdigit() else 1
                    severity_str = parts[3].strip().split()[0]
                    severity = Severity.HIGH if "error" in severity_str.lower() else Severity.MEDIUM
                    message = ":".join(parts[4:]).strip() if len(parts) > 4 else line
                    findings.append(NormalizedFinding(
                        tool="typescript",
                        tool_version=tool_version,
                        rule_id=parts[3].strip().split()[1] if len(parts[3].split()) > 1 else "unknown",
                        rule_name="TypeScript Error",
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        severity=severity,
                        confidence=Confidence.VERIFIED,
                        message=message,
                        metadata={},
                    ))
        return findings

    async def _run_semgrep(self) -> list[NormalizedFinding]:
        """Run Semgrep security rules."""
        result = await self._run_tool(
            ["semgrep", "--config=auto", "--json", "--quiet", "."],
            "semgrep",
        )
        if result.status != ToolStatus.AVAILABLE:
            logger.warning("Semgrep not available", status=result.status.value)
            return []

        findings = []
        tool_version = self._get_tool_version("semgrep")
        try:
            semgrep_output = json.loads(result.stdout)
            for result_item in semgrep_output.get("results", []):
                severity = self._map_semgrep_severity(result_item.get("extra", {}).get("severity", "INFO"))
                findings.append(NormalizedFinding(
                    tool="semgrep",
                    tool_version=tool_version,
                    rule_id=result_item.get("check_id", "unknown"),
                    rule_name=result_item.get("extra", {}).get("message", "Semgrep finding"),
                    file_path=result_item.get("path", "").replace(str(self.workspace) + "/", ""),
                    line_start=result_item.get("start", {}).get("line", 1),
                    line_end=result_item.get("end", {}).get("line", 1),
                    severity=severity,
                    confidence=Confidence.LIKELY,
                    message=result_item.get("extra", {}).get("message", ""),
                    metadata={
                        "metadata": result_item.get("extra", {}).get("metadata", {}),
                        "lines": result_item.get("extra", {}).get("lines", ""),
                    },
                ))
        except json.JSONDecodeError:
            logger.warning("Failed to parse Semgrep output")
        return findings

    async def _run_trivy(self) -> list[NormalizedFinding]:
        """Run Trivy filesystem scan."""
        result = await self._run_tool(
            ["trivy", "fs", "--format=json", "--quiet", "."],
            "trivy",
        )
        if result.status != ToolStatus.AVAILABLE:
            logger.warning("Trivy not available", status=result.status.value)
            return []

        findings = []
        tool_version = self._get_tool_version("trivy")
        try:
            trivy_output = json.loads(result.stdout)
            for result_item in trivy_output.get("Results", []):
                for vuln in result_item.get("Vulnerabilities", []):
                    severity = self._map_trivy_severity(vuln.get("Severity", "UNKNOWN"))
                    findings.append(NormalizedFinding(
                        tool="trivy",
                        tool_version=tool_version,
                        rule_id=vuln.get("VulnerabilityID", "unknown"),
                        rule_name=f"CVE: {vuln.get('VulnerabilityID', 'unknown')}",
                        file_path=result_item.get("Target", "").replace(str(self.workspace) + "/", ""),
                        line_start=1,
                        line_end=1,
                        severity=severity,
                        confidence=Confidence.VERIFIED,
                        message=f"{vuln.get('Title', 'Vulnerability')} in {vuln.get('PkgName', 'unknown')} {vuln.get('InstalledVersion', 'unknown')}",
                        metadata={
                            "pkg_name": vuln.get("PkgName"),
                            "installed_version": vuln.get("InstalledVersion"),
                            "fixed_version": vuln.get("FixedVersion"),
                            "references": vuln.get("References", []),
                        },
                    ))
        except json.JSONDecodeError:
            logger.warning("Failed to parse Trivy output")
        return findings

    async def _run_detect_secrets(self) -> list[NormalizedFinding]:
        """Run detect-secrets."""
        result = await self._run_tool(
            ["detect-secrets", "scan", "--all-files", "."],
            "detect_secrets",
        )
        if result.status != ToolStatus.AVAILABLE:
            logger.warning("detect-secrets not available", status=result.status.value)
            return []

        findings = []
        tool_version = self._get_tool_version("detect-secrets")
        try:
            secrets_output = json.loads(result.stdout)
            for file_path, secrets in secrets_output.get("results", {}).items():
                for secret in secrets:
                    findings.append(NormalizedFinding(
                        tool="detect_secrets",
                        tool_version=tool_version,
                        rule_id=secret.get("type", "secret"),
                        rule_name=f"Secret: {secret.get('type', 'unknown')}",
                        file_path=file_path.replace(str(self.workspace) + "/", ""),
                        line_start=secret.get("line_number", 1),
                        line_end=secret.get("line_number", 1),
                        severity=Severity.CRITICAL,
                        confidence=Confidence.VERIFIED,
                        message=f"Potential secret detected: {secret.get('type', 'unknown')}",
                        metadata={
                            "hashed_secret": secret.get("hashed_secret"),
                            "is_verified": secret.get("is_verified", False),
                        },
                    ))
        except json.JSONDecodeError:
            logger.warning("Failed to parse detect-secrets output")
        return findings

    def _map_eslint_severity(self, severity: int) -> Severity:
        """Map ESLint severity (1=warning, 2=error) to unified."""
        return Severity.HIGH if severity == 2 else Severity.MEDIUM

    def _map_semgrep_severity(self, severity: str) -> Severity:
        """Map Semgrep severity to unified."""
        mapping = {
            "ERROR": Severity.CRITICAL,
            "WARNING": Severity.HIGH,
            "INFO": Severity.MEDIUM,
        }
        return mapping.get(severity.upper(), Severity.MEDIUM)

    def _map_trivy_severity(self, severity: str) -> Severity:
        """Map Trivy severity to unified."""
        mapping = {
            "CRITICAL": Severity.CRITICAL,
            "HIGH": Severity.HIGH,
            "MEDIUM": Severity.MEDIUM,
            "LOW": Severity.LOW,
            "UNKNOWN": Severity.INFO,
        }
        return mapping.get(severity.upper(), Severity.INFO)


class StaticAnalysisEngine:
    """Orchestrates static analysis."""

    def __init__(self):
        self.rubric = get_rubric()

    async def analyze(self, workspace: Path, profile: "ProjectProfile") -> list[NormalizedFinding]:
        """Run static analysis on workspace."""
        runner = ToolRunner(workspace, profile)
        findings = await runner.run_all()
        logger.info("Static analysis complete", findings_count=len(findings))
        return findings
