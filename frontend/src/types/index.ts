export type UUID = string;

export interface ScanCreate {
  repo_url: string;
  branch?: string;
  commit_sha?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
  sandbox: string;
}

export type ScanStatus =
  | 'pending'
  | 'profiling'
  | 'analyzing'
  | 'scoring'
  | 'complete'
  | 'failed';

export type CheckStatus =
  | 'pending'
  | 'running'
  | 'passed'
  | 'failed'
  | 'skipped'
  | 'error';

export type CheckCategory = 'static' | 'verification' | 'dynamic';

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type Confidence = 'verified' | 'likely' | 'heuristic' | 'info';

export type FindingStatus =
  | 'detected'
  | 'triaged'
  | 'confirmed'
  | 'disputed'
  | 'resolved';

export type ProjectType =
  | 'web_app'
  | 'api'
  | 'cli'
  | 'library'
  | 'agent'
  | 'mobile'
  | 'unknown';

export interface ScanResponse {
  id: UUID;
  repo_url: string;
  repo_owner: string;
  repo_name: string;
  commit_sha: string;
  branch: string;
  project_type: ProjectType;
  status: ScanStatus;
  rubric_version: string;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ScanHistoryResponse extends ScanResponse {
  overall_score: number | null;
  grade: string | null;
  coverage_percent: number | null;
  critical_blockers: number;
}

export interface ScanStatusResponse {
  scan_id: UUID;
  status: ScanStatus;
  progress: number;
  current_stage: string;
  error?: string;
}

export interface CheckResponse {
  id: UUID;
  name: string;
  category: CheckCategory;
  status: CheckStatus;
  started_at: string | null;
  completed_at: string | null;
  exit_code: number | null;
  duration_ms: number | null;
  output_summary: string | null;
}

export interface FindingResponse {
  id: UUID;
  fingerprint: string;
  tool: string;
  rule_id: string;
  file_path: string;
  line_start: number;
  line_end: number;
  severity: Severity;
  confidence: Confidence;
  title: string;
  description: string;
  rubric_dimensions: string[];
  status: FindingStatus;
  first_seen: string;
  last_seen: string;
}

export interface DimensionScoreResponse {
  code: string;
  name: string;
  weight: number;
  score: number;
  max_score: number;
  applicable_checks: number;
  passed_checks: number;
  findings_count: number;
}

export interface ScoreResponse {
  overall_score: number;
  grade: string;
  readiness_verdict: string;
  coverage_percent: number;
  confidence_percent: number;
  critical_blockers: number;
  dimension_scores: DimensionScoreResponse[];
}

export interface ReportResponse {
  scan: ScanResponse;
  score: ScoreResponse;
  findings: FindingResponse[];
  checks: CheckResponse[];
  rubric_version: string;
}

export interface ArchitectureModule {
  name: string;
  path: string;
  file_count: number;
  languages: string[];
}

export interface ArchitectureDependency {
  from: string;
  to: string;
  type: string;
}

export interface ArchitectureResponse {
  project_type: string;
  languages: string[];
  frameworks: string[];
  package_managers: string[];
  entry_points: string[];
  modules: ArchitectureModule[];
  dependencies: ArchitectureDependency[];
  file_counts: Record<string, number>;
  total_files: number;
  has_database: boolean;
  has_dockerfile: boolean;
  has_ci: boolean;
  inferred: boolean;
}

export interface RubricSubcheckSchema {
  id: string;
  name: string;
  points: number;
  applies_to: string[];
  not_applies_to: string[];
  evidence_sources: string[];
  description: string;
  severity_map: Record<string, number>;
}

export interface RubricDimensionSchema {
  code: string;
  name: string;
  weight: number;
  description: string;
  subchecks: RubricSubcheckSchema[];
}

export interface RubricResponse {
  version: string;
  description: string;
  dimensions: RubricDimensionSchema[];
  project_type_rules: Record<string, unknown>;
  severity_mapping: Record<string, Record<string, string>>;
  confidence_by_category: Record<string, string>;
}