import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Github, Search, AlertCircle, CheckCircle, Loader2, ArrowLeft } from 'lucide-react';
import { useCreateScan, useScanStatus } from '../hooks/useScan';
import { Button, Input, Card, Badge, ProgressBar } from '../components';
import { cn } from '../utils/helpers';

const STATUS_STAGES = [
  { key: 'pending', label: 'Queued', icon: Loader2 },
  { key: 'profiling', label: 'Cloning & Profiling', icon: Github },
  { key: 'analyzing', label: 'Static Analysis', icon: Search },
  { key: 'scoring', label: 'Calculating Score', icon: CheckCircle },
  { key: 'complete', label: 'Complete', icon: CheckCircle },
  { key: 'failed', label: 'Failed', icon: AlertCircle },
];

const STAGE_ORDER = ['pending', 'profiling', 'analyzing', 'scoring', 'complete', 'failed'];

export function ScanPage() {
  const navigate = useNavigate();
  const [repoUrl, setRepoUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submittedScanId, setSubmittedScanId] = useState<string | null>(null);

  const createScan = useCreateScan();
  const { data: scanStatus } = useScanStatus(submittedScanId, !!submittedScanId);
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Basic URL validation
    if (!repoUrl.trim()) {
      setError('Please enter a GitHub repository URL');
      return;
    }

    if (!repoUrl.includes('github.com')) {
      setError('Only GitHub repositories are supported');
      return;
    }

    try {
      const result = await createScan.mutateAsync({
        repo_url: repoUrl.trim(),
      });
      setSubmittedScanId(result.id);
      // Navigate to report page when complete
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to start scan. Please try again.');
      }
    }
  };

  // Auto-navigate to report when complete
  if (scanStatus?.status === 'complete' && submittedScanId) {
    navigate(`/report/${submittedScanId}`, { replace: true });
  }

  if (submittedScanId && scanStatus) {
    const progress = scanStatus.progress;

    return (
      <div className="min-h-screen py-12 px-6">
        <div className="max-w-3xl mx-auto">
          {/* Back link */}
          <Link to="/" className="inline-flex items-center gap-2 text-dark-400 hover:text-brand-400 text-sm mb-8 group">
            <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-1" />
            Back to Home
          </Link>

          <Card className="animate-in">
            <div className="text-center mb-8">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-900/30 border border-brand-800 text-brand-300 text-sm font-medium mb-4">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Scan in Progress</span>
              </div>
              <h1 className="text-2xl lg:text-3xl font-bold text-white mb-2">Analyzing Repository</h1>
              <p className="text-dark-400">This usually takes 30-120 seconds depending on repository size</p>
            </div>

            {/* Progress Steps */}
            <div className="mb-8">
              {STATUS_STAGES.map((stage, index) => {
                const isCurrent = STAGE_ORDER.indexOf(scanStatus.status) === index && scanStatus.status !== 'complete' && scanStatus.status !== 'failed';
                const isComplete = STAGE_ORDER.indexOf(scanStatus.status) > index;

                return (
                  <div key={stage.key} className="flex items-center gap-4 mb-4 last:mb-0">
                    <div className={cn(
                      'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-colors',
                      isComplete ? 'bg-green-500 text-white' :
                      isCurrent ? 'bg-brand-500 text-white animate-pulse' :
                      'bg-dark-800 text-dark-500'
                    )}>
                      <stage.icon className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className={cn(
                          isComplete ? 'text-green-300' :
                          isCurrent ? 'text-brand-300 font-medium' :
                          'text-dark-400'
                        )}>
                          {stage.label}
                        </span>
                        {isCurrent && (
                          <span className="text-xs text-dark-500 animate-pulse">{scanStatus.current_stage}</span>
                        )}
                      </div>
                      <ProgressBar value={isComplete ? 100 : isCurrent ? progress : 0} size="sm" color={isComplete ? 'green' : 'brand'} />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Overall Progress */}
            <div className="mb-6">
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="text-dark-400">Overall Progress</span>
                <span className="font-mono text-brand-400">{progress}%</span>
              </div>
              <ProgressBar value={progress} color={scanStatus.status === 'failed' ? 'red' : 'brand'} showLabel />
            </div>

            {scanStatus.status === 'failed' && (
              <div className="p-4 bg-red-900/20 border border-red-800 rounded-lg text-red-300">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  <strong>Scan Failed</strong>
                </div>
                <p className="mt-2 text-sm">{scanStatus.error || 'An unknown error occurred'}</p>
                <Button variant="secondary" className="mt-4" onClick={() => setSubmittedScanId(null)}>
                  Try Another Repository
                </Button>
              </div>
            )}
          </Card>

          {/* Example repos while waiting */}
          {scanStatus.status !== 'complete' && scanStatus.status !== 'failed' && (
            <div className="mt-8">
              <h3 className="text-lg font-semibold text-dark-300 mb-4">Try These Examples While You Wait</h3>
              <div className="grid sm:grid-cols-2 gap-4">
                {[
                  { name: 'FastAPI', url: 'https://github.com/tiangolo/fastapi' },
                  { name: 'Next.js', url: 'https://github.com/vercel/next.js' },
                  { name: 'React', url: 'https://github.com/facebook/react' },
                  { name: 'TypeScript', url: 'https://github.com/microsoft/TypeScript' },
                ].map((example) => (
                  <Link key={example.name} to={`/scan?url=${encodeURIComponent(example.url)}`} className="block">
                    <Card className="hover:border-brand-800 transition-colors p-4">
                      <div className="flex items-center gap-3">
                        <Github className="w-6 h-6 text-brand-400" />
                        <span className="font-medium text-white">{example.name}</span>
                      </div>
                    </Card>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Initial scan form
  return (
    <div className="min-h-screen py-12 px-6">
      <div className="max-w-3xl mx-auto">
        {/* Back link */}
        <Link to="/" className="inline-flex items-center gap-2 text-dark-400 hover:text-brand-400 text-sm mb-8 group">
          <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-1" />
          Back to Home
        </Link>

        <Card className="animate-in">
          <div className="text-center mb-8">
            <Github className="w-12 h-12 text-brand-400 mx-auto mb-4" />
            <h1 className="text-2xl lg:text-3xl font-bold text-white mb-2">Scan a Repository</h1>
            <p className="text-dark-400">
              Enter a public GitHub repository URL to get an evidence-based quality assessment.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <Input
              label="GitHub Repository URL"
              placeholder="https://github.com/owner/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              error={error ?? undefined}
              hint="Supports github.com/owner/repo, github.com/owner/repo/tree/branch, etc."
              autoFocus
            />

            <div className="bg-dark-800/50 border border-dark-700 rounded-lg p-4">
              <h4 className="font-medium text-dark-300 mb-3 flex items-center gap-2">
                <Github className="w-4 h-4 text-brand-400" />
                Example Repositories
              </h4>
              <div className="grid sm:grid-cols-2 gap-2 text-sm">
                {[
                  { name: 'FastAPI', url: 'https://github.com/tiangolo/fastapi' },
                  { name: 'Next.js', url: 'https://github.com/vercel/next.js' },
                  { name: 'React', url: 'https://github.com/facebook/react' },
                  { name: 'TypeScript', url: 'https://github.com/microsoft/TypeScript' },
                ].map((example) => (
                  <button
                    key={example.name}
                    type="button"
                    onClick={() => setRepoUrl(example.url)}
                    className="text-left p-2 rounded bg-dark-900 hover:bg-dark-800 text-dark-300 hover:text-white transition-colors flex items-center gap-2"
                  >
                    <Github className="w-4 h-4 text-brand-400" />
                    {example.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="pt-4">
              <Button type="submit" className="w-full" size="lg" disabled={createScan.isPending}>
                {createScan.isPending ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Starting Scan...
                  </>
                ) : (
                  <>
                    <Search className="w-5 h-5" />
                    Start Scan
                  </>
                )}
              </Button>
            </div>

            <p className="text-center text-dark-500 text-sm">
              No account required. Public repositories only.{' '}
              <a href="#" className="text-brand-400 hover:underline">Private repo support coming soon</a>.
            </p>
          </form>
        </Card>

        {/* Info cards */}
        <div className="mt-8 grid md:grid-cols-3 gap-4">
          <Card>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-brand-900/30 border border-brand-800 flex items-center justify-center">
                <Search className="w-5 h-5 text-brand-400" />
              </div>
              <div>
                <h4 className="font-semibold text-white">Static Analysis</h4>
                <p className="text-dark-500 text-sm">ESLint, TypeScript, Semgrep, Trivy, detect-secrets</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-brand-900/30 border border-brand-800 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <h4 className="font-semibold text-white">Build & Test Verification</h4>
                <p className="text-dark-500 text-sm">Actually runs install, build, and test commands</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-brand-900/30 border border-brand-800 flex items-center justify-center">
                <Badge className="w-5 h-5 text-green-400" variant="verified">A</Badge>
              </div>
              <div>
                <h4 className="font-semibold text-white">Deterministic Scoring</h4>
                <p className="text-dark-500 text-sm">100-point rubric with coverage & confidence</p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}