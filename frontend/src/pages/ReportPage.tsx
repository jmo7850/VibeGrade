import { useParams, Link } from 'react-router-dom';
import { useState } from 'react';
import {
  Shield,
  CheckCircle,
  AlertTriangle,
  FileText,
  Search,
  Download,
  ExternalLink,
  Copy,
  ChevronDown,
} from 'lucide-react';
import { useScanReport, useScanFindings } from '../hooks/useScan';
import { api } from '../api/client';
import {
  Button,
  Badge,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  ProgressBar,
  Input,
} from '../components';
import { cn, formatDate, getSeverityBadge, getConfidenceBadge, getGradeBadge, getScoreColor, truncate, getProjectTypeLabel } from '../utils/helpers';
import type { Severity, Confidence } from '../types';

const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low', 'info'];
const CONFIDENCE_ORDER: Confidence[] = ['verified', 'likely', 'heuristic', 'info'];

export function ReportPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const { data: report, isLoading, error } = useScanReport(scanId!, !!scanId);
  const { data: findings, isLoading: findingsLoading } = useScanFindings(scanId!, {}, !!scanId);

  // Filter state
  const [severityFilter, setSeverityFilter] = useState<Severity[]>([]);
  const [confidenceFilter, setConfidenceFilter] = useState<Confidence[]>([]);
  const [dimensionFilter, setDimensionFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedFindings, setExpandedFindings] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState<'json' | 'markdown' | null>(null);

  const handleExport = async (format: 'json' | 'markdown') => {
    setExporting(format);
    try {
      const content = await api.exportScanReport(scanId!, format);
      const blob = new Blob(
        [content],
        { type: format === 'json' ? 'application/json' : 'text/markdown' }
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `vibegrade-${scan.repo_name}-${scan.commit_sha.slice(0, 8)}.${format === 'json' ? 'json' : 'md'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // Export failure is non-fatal; user can retry
    } finally {
      setExporting(null);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen py-12 px-6 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-brand-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-dark-400">Loading report...</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen py-12 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Report Not Found</h1>
          <p className="text-dark-400 mb-6">The scan report could not be loaded.</p>
          <Link to="/scan">
            <Button>Scan a Repository</Button>
          </Link>
        </div>
      </div>
    );
  }

  const { scan, score, checks } = report;
  const displayFindings = findings || report.findings;

  // Filter findings
  const filteredFindings = displayFindings.filter((f) => {
    if (severityFilter.length && !severityFilter.includes(f.severity)) return false;
    if (confidenceFilter.length && !confidenceFilter.includes(f.confidence)) return false;
    if (dimensionFilter && !f.rubric_dimensions.includes(dimensionFilter)) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (!f.title.toLowerCase().includes(query) &&
          !f.description.toLowerCase().includes(query) &&
          !f.file_path.toLowerCase().includes(query) &&
          !f.tool.toLowerCase().includes(query)) {
        return false;
      }
    }
    return true;
  });

  // Sort findings: critical first, then by confidence
  const sortedFindings = [...filteredFindings].sort((a, b) => {
    const sevDiff = SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity);
    if (sevDiff !== 0) return sevDiff;
    return CONFIDENCE_ORDER.indexOf(a.confidence) - CONFIDENCE_ORDER.indexOf(b.confidence);
  });

  // Get unique dimensions for filter
  const allDimensions = Array.from(new Set(displayFindings.flatMap(f => f.rubric_dimensions))).sort();

  const handleToggleFinding = (findingId: string) => {
    setExpandedFindings(prev => {
      const next = new Set(prev);
      if (next.has(findingId)) next.delete(findingId);
      else next.add(findingId);
      return next;
    });
  };

  const copyFindingPrompt = (finding: typeof displayFindings[0]) => {
    const prompt = `## Fix Required: ${finding.title}

**File:** ${finding.file_path}:${finding.line_start}
**Severity:** ${finding.severity} (${finding.confidence})
**Tool:** ${finding.tool} (${finding.rule_id})

**Description:** ${finding.description}

**Suggested Fix:** Please address the issue described above. Ensure the fix:
1. Resolves the root cause
2. Includes appropriate tests
3. Follows project coding standards

**Verification:** Run the test suite to confirm the fix works.`;

    navigator.clipboard.writeText(prompt);
  };

  return (
    <div className="min-h-screen py-8 px-6">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <Link to="/" className="inline-flex items-center gap-2 text-dark-400 hover:text-brand-400 text-sm mb-4 group">
              <ChevronDown className="w-4 h-4 transition-transform group-hover:rotate-180" />
              Back to Home
            </Link>
            <div className="flex items-center gap-4">
              <h1 className="text-2xl lg:text-3xl font-bold text-white">
                {scan.repo_owner}/{scan.repo_name}
              </h1>
              <Badge variant="grade">{score.grade}</Badge>
            </div>
            <p className="text-dark-500 text-sm mt-1">
              Commit <code className="font-mono bg-dark-800 px-1.5 py-0.5 rounded">{scan.commit_sha.slice(0, 8)}</code> on {scan.branch} • {getProjectTypeLabel(scan.project_type)} • Scanned {formatDate(scan.completed_at || scan.created_at)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => handleExport('json')} disabled={exporting !== null}>
              <Download className="w-4 h-4 mr-2" />
              {exporting === 'json' ? 'Exporting...' : 'Export JSON'}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => handleExport('markdown')} disabled={exporting !== null}>
              <FileText className="w-4 h-4 mr-2" />
              {exporting === 'markdown' ? 'Exporting...' : 'Export Markdown'}
            </Button>
            <a href={`https://github.com/${scan.repo_owner}/${scan.repo_name}/tree/${scan.commit_sha}`} target="_blank" rel="noopener" className="text-dark-400 hover:text-brand-400 p-2">
              <ExternalLink className="w-5 h-5" />
            </a>
          </div>
        </div>

        {/* Alert for critical blockers */}
        {score.critical_blockers > 0 && (
          <div className="p-4 bg-red-900/20 border border-red-800 rounded-xl">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-6 h-6 text-red-400 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-red-300">Critical Security Blockers Detected</h3>
                <p className="text-red-400 text-sm">
                  {score.critical_blockers} critical security finding{score.critical_blockers > 1 ? 's' : ''} with verified/likely confidence.
                  This project is <strong>not production ready</strong> regardless of overall score.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Score Overview */}
        <div className="grid lg:grid-cols-4 gap-6">
          {/* Main Score */}
          <Card className="lg:col-span-2 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-brand-500/10 rounded-full blur-3xl" />
            <div className="relative flex flex-col items-center py-8">
              <div className="relative w-48 h-48 mb-6">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="96" cy="96" r="88"
                    className="text-dark-800"
                    strokeWidth="12" fill="none"
                  />
                  <circle
                    cx="96" cy="96" r="88"
                    className={getScoreColor(score.overall_score)}
                    strokeWidth="12" fill="none"
                    strokeDasharray={553}
                    strokeDashoffset={553 * (1 - score.overall_score / 100)}
                    strokeLinecap="round"
                    style={{ transition: 'stroke-dashoffset 1s ease-out' }}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-5xl lg:text-6xl font-bold text-white">{score.overall_score}</span>
                  <span className="text-dark-400 text-sm">/ 100</span>
                </div>
              </div>
              <div className="flex items-center gap-4 mb-4">
                <Badge className={getGradeBadge(score.grade)}>{score.grade}</Badge>
                <span className="text-dark-400">{score.readiness_verdict}</span>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-4 text-sm text-dark-400">
                <span className="flex items-center gap-1">
                  <Shield className="w-4 h-4" />
                  Coverage: {score.coverage_percent}%
                </span>
                <span className="flex items-center gap-1">
                  <CheckCircle className="w-4 h-4" />
                  Confidence: {score.confidence_percent}%
                </span>
                {score.critical_blockers > 0 && (
                  <span className="flex items-center gap-1 text-red-400">
                    <AlertTriangle className="w-4 h-4" />
                    {score.critical_blockers} Blocker{score.critical_blockers > 1 ? 's' : ''}
                  </span>
                )}
              </div>
            </div>
          </Card>

          {/* Dimension Scores */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Dimension Scores
                <Badge variant="info">{score.dimension_scores.length} Dimensions</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {score.dimension_scores.map((dim) => (
                <div key={dim.code} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-dark-300 font-medium">{dim.name}</span>
                    <span className={cn('font-mono font-semibold', getScoreColor(dim.score))}>{dim.score.toFixed(0)}%</span>
                  </div>
                  <ProgressBar value={dim.score} color={dim.score >= 80 ? 'green' : dim.score >= 60 ? 'brand' : dim.score >= 40 ? 'yellow' : 'red'} size="sm" />
                  <div className="flex items-center justify-between text-xs text-dark-500">
                    <span>{dim.passed_checks}/{dim.applicable_checks} checks passed</span>
                    <span>{dim.findings_count} findings</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Scan Metadata */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">Scan Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-dark-500">Repository</span>
                <p className="font-mono text-white">{scan.repo_owner}/{scan.repo_name}</p>
              </div>
              <div>
                <span className="text-dark-500">Commit</span>
                <p className="font-mono text-white">{scan.commit_sha}</p>
              </div>
              <div>
                <span className="text-dark-500">Branch</span>
                <p className="font-mono text-white">{scan.branch}</p>
              </div>
              <div>
                <span className="text-dark-500">Project Type</span>
                <p className="text-white capitalize">{getProjectTypeLabel(scan.project_type)}</p>
              </div>
              <div>
                <span className="text-dark-500">Rubric Version</span>
                <p className="font-mono text-white">{scan.rubric_version}</p>
              </div>
              <div>
                <span className="text-dark-500">Scan Duration</span>
                <p className="font-mono text-white">
                  {scan.started_at && scan.completed_at
                    ? Math.round((new Date(scan.completed_at).getTime() - new Date(scan.started_at).getTime()) / 1000) + 's'
                    : 'N/A'}
                </p>
              </div>
              <div>
                <span className="text-dark-500">Checks Run</span>
                <p className="font-mono text-white">{checks.length}</p>
              </div>
              <div>
                <span className="text-dark-500">Findings</span>
                <p className="font-mono text-white">{displayFindings.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Checks Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">Checks Executed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {checks.map((check) => (
                <div key={check.id} className="flex items-center justify-between p-3 bg-dark-800/50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className={cn(
                      'w-2 h-2 rounded-full',
                      check.status === 'passed' && 'bg-green-500',
                      check.status === 'failed' && 'bg-red-500',
                      check.status === 'skipped' && 'bg-yellow-500',
                      check.status === 'error' && 'bg-red-500',
                      check.status === 'pending' && 'bg-dark-500 animate-pulse'
                    )} />
                    <div>
                      <p className="font-medium text-white">{check.name}</p>
                      <p className="text-dark-500 text-sm capitalize">{check.category}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-dark-400">
                    <Badge variant={check.status === 'passed' ? 'verified' : check.status === 'failed' ? 'critical' : check.status === 'skipped' ? 'medium' : 'info'}>
                      {check.status}
                    </Badge>
                    {check.duration_ms && <span>{(check.duration_ms / 1000).toFixed(1)}s</span>}
                    {check.exit_code !== null && check.exit_code !== 0 && (
                      <span className="text-red-400 font-mono">exit {check.exit_code}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Findings */}
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <CardTitle className="flex items-center gap-2">
                  Findings
                  <Badge variant="info">{filteredFindings.length}/{displayFindings.length}</Badge>
                </CardTitle>
                <p className="text-dark-500 text-sm mt-1">Filter and explore detected issues with evidence</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {/* Severity filters */}
                <div className="flex items-center gap-1 bg-dark-800 rounded-lg p-1">
                  {SEVERITY_ORDER.map((sev) => (
                    <button
                      key={sev}
                      onClick={() => setSeverityFilter(prev =>
                        prev.includes(sev) ? prev.filter(s => s !== sev) : [...prev, sev]
                      )}
                      className={cn(
                        'px-2 py-1 rounded text-xs font-medium transition-colors',
                        severityFilter.includes(sev) ? getSeverityBadge(sev) : 'text-dark-500 hover:text-dark-300'
                      )}
                    >
                      {sev} {displayFindings.filter(f => f.severity === sev).length}
                    </button>
                  ))}
                </div>
                {/* Confidence filters */}
                <div className="flex items-center gap-1 bg-dark-800 rounded-lg p-1">
                  {CONFIDENCE_ORDER.map((conf) => (
                    <button
                      key={conf}
                      onClick={() => setConfidenceFilter(prev =>
                        prev.includes(conf) ? prev.filter(c => c !== conf) : [...prev, conf]
                      )}
                      className={cn(
                        'px-2 py-1 rounded text-xs font-medium transition-colors',
                        confidenceFilter.includes(conf) ? getConfidenceBadge(conf) : 'text-dark-500 hover:text-dark-300'
                      )}
                    >
                      {conf} {displayFindings.filter(f => f.confidence === conf).length}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Dimension filter */}
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <label className="text-sm text-dark-400">Dimension:</label>
              <select
                value={dimensionFilter}
                onChange={(e) => setDimensionFilter(e.target.value)}
                className="input w-auto"
              >
                <option value="">All Dimensions</option>
                {allDimensions.map((dim) => (
                  <option key={dim} value={dim}>{dim}</option>
                ))}
              </select>
              <Input
                placeholder="Search findings..."
                value={searchQuery}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
                className="w-64"
              />
            </div>

            {findingsLoading ? (
              <div className="text-center py-8 text-dark-500">Loading findings...</div>
            ) : sortedFindings.length === 0 ? (
              <div className="text-center py-12 text-dark-500">
                <Search className="w-12 h-12 mx-auto mb-4 text-dark-600" />
                <p className="text-lg">No findings match your filters</p>
                <p className="text-sm">Try adjusting your filters or search query</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {sortedFindings.map((finding) => {
                  const isExpanded = expandedFindings.has(finding.id);
                  return (
                    <FindingRow
                      key={finding.id}
                      finding={finding}
                      isExpanded={isExpanded}
                      onToggle={() => handleToggleFinding(finding.id)}
                      onCopyPrompt={() => copyFindingPrompt(finding)}
                    />
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Remediation Workspace */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">Remediation Workspace</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-dark-400 mb-6">
              Copy prioritized fix prompts for your coding agent. Findings are ordered by severity × confidence × dimension weight.
            </p>
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {sortedFindings.slice(0, 10).map((finding, index) => (
                <div key={finding.id} className="p-3 bg-dark-800/50 rounded-lg border border-dark-700">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-brand-400 font-mono text-sm">#{index + 1}</span>
                        <Badge variant={getSeverityBadge(finding.severity).replace('badge-', '') as any}>{finding.severity}</Badge>
                        <Badge variant={getConfidenceBadge(finding.confidence).replace('badge-', '') as any}>{finding.confidence}</Badge>
                        <span className="text-dark-500 text-sm">{finding.tool}</span>
                      </div>
                      <p className="font-medium text-white truncate">{finding.title}</p>
                      <p className="text-dark-400 text-sm mt-1">{truncate(finding.file_path, 80)}:{finding.line_start}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyFindingPrompt(finding)}
                      className="flex-shrink-0"
                    >
                      <Copy className="w-4 h-4 mr-1" />
                      Copy Prompt
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Finding Row Component
function FindingRow({
  finding,
  isExpanded,
  onToggle,
  onCopyPrompt,
}: {
  finding: any;
  isExpanded: boolean;
  onToggle: () => void;
  onCopyPrompt: () => void;
}) {
  return (
    <div className={cn('border border-dark-700 rounded-lg overflow-hidden transition-all', isExpanded ? 'border-brand-800' : '')}>
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-center justify-between gap-4 hover:bg-dark-800/50 transition-colors text-left"
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <Badge variant={getSeverityBadge(finding.severity).replace('badge-', '') as any} className="flex-shrink-0">
            {finding.severity}
          </Badge>
          <Badge variant={getConfidenceBadge(finding.confidence).replace('badge-', '') as any} className="flex-shrink-0">
            {finding.confidence}
          </Badge>
          <span className="font-medium text-white truncate flex-1">{finding.title}</span>
          <span className="text-dark-500 text-sm font-mono flex-shrink-0">{truncate(finding.file_path, 50)}:{finding.line_start}</span>
          <span className="text-dark-500 text-xs flex-shrink-0">{finding.tool}</span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={onCopyPrompt}>
            <Copy className="w-4 h-4" />
          </Button>
          <ChevronDown className={cn('w-5 h-5 text-dark-500 transition-transform', isExpanded && 'rotate-180')} />
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-dark-700 p-4 bg-dark-800/50 space-y-4">
          <div className="grid sm:grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-dark-500">File</span>
              <p className="font-mono text-white">{finding.file_path}:{finding.line_start}-{finding.line_end}</p>
            </div>
            <div>
              <span className="text-dark-500">Tool / Rule</span>
              <p className="font-mono text-white">{finding.tool} / {finding.rule_id}</p>
            </div>
            <div>
              <span className="text-dark-500">Dimensions</span>
              <p className="text-white">{finding.rubric_dimensions.join(', ') || 'N/A'}</p>
            </div>
            <div>
              <span className="text-dark-500">Status</span>
              <Badge variant="info">{finding.status}</Badge>
            </div>
          </div>

          <div>
            <span className="text-dark-500 text-sm">Description</span>
            <p className="text-white mt-1 whitespace-pre-wrap">{finding.description}</p>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={onCopyPrompt}>
              <Copy className="w-4 h-4 mr-1" />
              Copy Agent Prompt
            </Button>
            <Button variant="ghost" size="sm">
              <FileText className="w-4 h-4 mr-1" />
              View Evidence
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}