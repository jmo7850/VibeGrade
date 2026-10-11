import { Link } from 'react-router-dom';
import { Github, Search, ChevronLeft, ChevronRight, Clock, BadgeCheck, AlertTriangle } from 'lucide-react';
import { useScanHistory } from '../hooks/useScan';
import { Button, Card, Badge } from '../components';
import { cn, formatDate, getGradeBadge, getScoreColor, getProjectTypeLabel } from '../utils/helpers';
import type { ScanHistoryResponse, ScanStatus } from '../types';

export function HistoryPage() {
  const { data: scans, isLoading, error } = useScanHistory(50, 0);

  if (isLoading) {
    return (
      <div className="min-h-screen py-12 px-6 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-brand-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-dark-400">Loading scan history...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen py-12 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Failed to Load History</h1>
          <p className="text-dark-400 mb-6">Could not retrieve scan history.</p>
          <Link to="/scan">
            <Button>Start a New Scan</Button>
          </Link>
        </div>
      </div>
    );
  }

  const isEmpty = !scans || scans.length === 0;

  return (
    <div className="min-h-screen py-8 px-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <Link to="/" className="inline-flex items-center gap-2 text-dark-400 hover:text-brand-400 text-sm mb-4 group">
              <ChevronLeft className="w-4 h-4 transition-transform group-hover:-translate-x-1" />
              Back to Home
            </Link>
            <h1 className="text-2xl lg:text-3xl font-bold text-white">Scan History</h1>
            <p className="text-dark-400 mt-1">Your recent repository assessments</p>
          </div>
          <Link to="/scan">
            <Button>
              <Search className="w-5 h-5 mr-2" />
              New Scan
            </Button>
          </Link>
        </div>

        {isEmpty ? (
          <Card className="text-center py-16">
            <Github className="w-16 h-16 text-dark-600 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">No Scans Yet</h2>
            <p className="text-dark-400 mb-6 max-w-md mx-auto">
              Start by scanning a public GitHub repository to see your scan history here.
            </p>
            <Link to="/scan">
              <Button size="lg">
                <Search className="w-5 h-5 mr-2" />
                Scan Your First Repository
              </Button>
            </Link>
          </Card>
        ) : (
          <div className="space-y-4">
            {scans?.map((scan) => (
              <ScanHistoryCard key={scan.id} scan={scan} />
            ))}
          </div>
        )}
        {/* Pagination placeholder */}
        <div className="mt-8 flex items-center justify-center gap-2">
          <Button variant="ghost" size="sm" disabled>
            <ChevronLeft className="w-4 h-4" />
            Previous
          </Button>
          <span className="text-dark-400 text-sm">Page 1 of 1</span>
          <Button variant="ghost" size="sm" disabled>
            Next
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function ScanHistoryCard({ scan }: { scan: ScanHistoryResponse }) {
  const getStatusBadge = (status: ScanStatus) => {
    switch (status) {
      case 'complete':
        return 'badge-verified';
      case 'failed':
        return 'badge-critical';
      case 'analyzing':
      case 'profiling':
      case 'scoring':
        return 'badge-info';
      default:
        return 'badge-info';
    }
  };

  const getStatusIcon = (status: ScanStatus) => {
    switch (status) {
      case 'complete':
        return <BadgeCheck className="w-4 h-4" />;
      case 'failed':
        return <AlertTriangle className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4 animate-spin" />;
    }
  };

  const hasScore = scan.status === 'complete' && scan.overall_score !== null;

  return (
    <Link to={scan.status === 'complete' ? `/report/${scan.id}` : `/scan/${scan.id}`} className="block">
      <Card className="hover:border-brand-800 transition-colors">
        <div className="flex flex-col lg:flex-row lg:items-center gap-6 p-6">
          {/* Repo Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap mb-2">
              <Link to={`https://github.com/${scan.repo_owner}/${scan.repo_name}`} target="_blank" rel="noopener" className="flex items-center gap-1 hover:text-brand-400 transition-colors">
                <Github className="w-5 h-5 text-dark-400" />
                <span className="font-medium text-white truncate max-w-[300px]">
                  {scan.repo_owner}/{scan.repo_name}
                </span>
              </Link>
              <Badge variant={getProjectTypeLabel(scan.project_type).toLowerCase().includes('web') ? 'info' : 'default'}>
                {getProjectTypeLabel(scan.project_type)}
              </Badge>
              {scan.critical_blockers > 0 && (
                <Badge variant="critical">
                  <AlertTriangle className="w-3 h-3 mr-1" />
                  {scan.critical_blockers} Blocker{scan.critical_blockers > 1 ? 's' : ''}
                </Badge>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-dark-500">
              <span className="flex items-center gap-1">
                <span className="font-mono bg-dark-800 px-1.5 py-0.5 rounded">{scan.commit_sha.slice(0, 8)}</span>
              </span>
              <span>Branch: <span className="font-mono text-dark-400">{scan.branch}</span></span>
              <span>Rubric: <span className="font-mono text-dark-400">{scan.rubric_version}</span></span>
            </div>
          </div>

          {/* Status & Score */}
          <div className="flex lg:flex-col lg:items-end gap-4 lg:w-64 flex-shrink-0">
            <div className="flex items-center gap-3">
              <span className={cn('badge', getStatusBadge(scan.status))}>
                {getStatusIcon(scan.status)}
                {scan.status.charAt(0).toUpperCase() + scan.status.slice(1)}
              </span>
            </div>

            {hasScore && scan.grade && (
              <>
                <div className="text-right">
                  <div className="flex items-baseline gap-2">
                    <span className={cn('text-3xl font-bold', getScoreColor(scan.overall_score!))}>{scan.overall_score}</span>
                    <span className="text-dark-400">/ 100</span>
                  </div>
                  <Badge className={getGradeBadge(scan.grade)} mt-1>{scan.grade}</Badge>
                </div>

                <div className="text-right text-sm text-dark-500">
                  <p>Coverage: {scan.coverage_percent?.toFixed(0) ?? '—'}%</p>
                  <p>Scanned {formatDate(scan.completed_at || scan.created_at)}</p>
                </div>
              </>
            )}

            {scan.status === 'complete' && !hasScore && (
              <div className="text-right text-sm text-dark-500">
                <p>No score recorded</p>
              </div>
            )}
          </div>
        </div>
      </Card>
    </Link>
  );
}