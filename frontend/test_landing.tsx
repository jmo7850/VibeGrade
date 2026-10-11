import { Link } from 'react-router-dom';
import {
  Shield,
  CheckCircle,
  Search,
  BarChart3,
  Terminal,
  GitBranch,
  AlertTriangle,
  Sparkles,
  ArrowRight,
  Github,
} from 'lucide-react';
import { Button, Card, Badge } from '../components';

const features = [
  {
    icon: Shield,
    title: 'Security First',
    description: 'Detects secrets, injection vulnerabilities, dependency CVEs, and authentication gaps with verified confidence levels.',
  },
  {
    icon: CheckCircle,
    title: 'Functional Verification',
    description: 'Actually runs your build and tests in isolated sandboxes. No false passes—only executed, verified results.',
  },
  {
    icon: Search,
    title: 'Evidence-Based Grading',
    description: 'Every point deduction traces to a specific finding with file, line, and tool output. Reproducible from stored evidence.',
  },
  {
    icon: BarChart3,
    title: '10-Dimension Rubric',
    description: 'Functional correctness, security, architecture, testing, data integrity, completeness, performance, deployment, docs, and discipline.',
  },
  {
    icon: Terminal,
    title: 'Multi-Language Support',
    description: 'TypeScript/JavaScript, Python, Go, Rust, and more. Detects frameworks (Next.js, FastAPI, React, etc.) automatically.',
  },
  {
    icon: GitBranch,
    title: 'GitHub Integration',
    description: 'Submit any public GitHub repository. Private repo support and CI/CD integration coming in Phase 2.',
  },
];

const projectTypes = [
  { label: 'Web Apps', examples: 'Next.js, React, Vue, Svelte, Astro' },
  { label: 'APIs', examples: 'FastAPI, Express, Django, Go, Rust' },
  { label: 'CLI Tools', examples: 'Click, Typer, Cobra, Clap' },
  { label: 'AI Agents', examples: 'LangChain, CrewAI, Autogen' },
  { label: 'Libraries', examples: 'npm, PyPI, Cargo, Go modules' },
  { label: 'Mobile', examples: 'Expo, React Native, Flutter' },
];

export function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="relative overflow-hidden py-24 lg:py-32 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-900/30 border border-brand-800 text-brand-300 text-sm font-medium mb-6 animate-in">
            <Sparkles className="w-4 h-4" />
            <span>VibeGrade v0.1 — Evidence-driven quality evaluation</span>
          </div>

          <h1 className="text-5xl lg:text-7xl font-bold tracking-tight text-white mb-6 animate-in">
            Does your code actually{' '}
            <span className="text-brand-400">work</span>?
          </h1>

          <p className="text-xl lg:text-2xl text-dark-300 max-w-3xl mx-auto mb-10 animate-in">
            VibeGrade evaluates whether your software is engineered responsibly and how much evidence supports that conclusion.
            Not an AI detector. A quality evaluator.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-in">
            <Link to="/scan">
              <Button size="lg" className="group w-full sm:w-auto">
                <Search className="w-5 h-5 mr-2" />
                Scan a Repository
                <ArrowRight className="w-5 h-5 ml-2 transition-transform group-hover:translate-x-1" />
              </Button>
            </Link>
            <Link to="/scan" className="w-full sm:w-auto">
              <Button variant="ghost" size="lg" className="w-full sm:w-auto">
                <Github className="w-5 h-5 mr-2" />
                Try with Example Repo
              </Button>
            </Link>
          </div>

          <div className="mt-16 flex flex-wrap items-center justify-center gap-6 text-dark-500 text-sm animate-in">
            <Badge variant="info">TypeScript</Badge>
            <Badge variant="info">Python</Badge>
            <Badge variant="info">Go</Badge>
            <Badge variant="info">Rust</Badge>
            <Badge variant="info">JavaScript</Badge>
            <span className="px-2">+ more</span>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 px-6 bg-dark-900/50 border-y border-dark-800">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">How It Works</h2>
            <p className="text-dark-400 text-lg max-w-2xl mx-auto">
              Transparent, deterministic grading across 10 dimensions with full evidence traceability.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <Card key={feature.title} className="group hover:border-brand-800 transition-colors animate-in" style={{ animationDelay: `${index * 100}ms` }}>
                <div className="w-12 h-12 rounded-lg bg-brand-900/30 border border-brand-800 flex items-center justify-center mb-4 group-hover:bg-brand-900/50 transition-colors">
                  <feature.icon className="w-6 h-6 text-brand-400" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-dark-400">{feature.description}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Supported Project Types */}
      <section className="py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">Supported Project Types</h2>
            <p className="text-dark-400 text-lg max-w-2xl mx-auto">
              VibeGrade detects your project type and applies relevant checks automatically.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projectTypes.map((type) => (
              <Card key={type.label} className="hover:border-brand-800 transition-colors">
                <div className="flex items-start gap-3">
                  <Terminal className="w-6 h-6 text-brand-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <h3 className="font-semibold text-white">{type.label}</h3>
                    <p className="text-dark-500 text-sm mt-1">{type.examples}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Grading Rubric Preview */}
      <section className="py-24 px-6 bg-dark-900/50 border-y border-dark-800">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">Grading Rubric (v1.0)</h2>
            <p className="text-dark-400 text-lg max-w-2xl mx-auto">
              100 points across 10 dimensions. Applicability-aware—no unfair penalties for irrelevant checks.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-dark-700">
                  <th className="pb-3 font-medium text-dark-400">Dimension</th>
                  <th className="pb-3 font-medium text-dark-400 text-right">Weight</th>
                  <th className="pb-3 font-medium text-dark-400">Focus</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-800">
                {[
                  { name: 'Functional Correctness', weight: 20, focus: 'Build success, core workflows, error handling' },
                  { name: 'Security & Privacy', weight: 15, focus: 'Auth, secrets, injection, deps, config' },
                  { name: 'Architecture & Maintainability', weight: 12, focus: 'Boundaries, coupling, duplication, complexity' },
                  { name: 'Testing & Verification', weight: 12, focus: 'Coverage, quality, integration tests' },
                  { name: 'Data & Backend Integrity', weight: 10, focus: 'Schema, migrations, API contracts, transactions' },
                  { name: 'Completeness & Integration', weight: 10, focus: 'Dead code, placeholders, fake APIs, states' },
                  { name: 'Performance & Efficiency', weight: 6, focus: 'N+1 queries, bundle size, algorithms, cleanup' },
                  { name: 'Deployment & Operations', weight: 5, focus: 'Reproducible builds, env config, CI, observability' },
                  { name: 'Documentation & Reproducibility', weight: 5, focus: 'Setup, run commands, architecture, limitations' },
                  { name: 'Engineering Discipline', weight: 5, focus: 'Deps, typing, error handling, complexity' },
                ].map((dim) => (
                  <tr key={dim.name} className="hover:bg-dark-800/50">
                    <td className="py-4 font-medium text-white">{dim.name}</td>
                    <td className="py-4 text-right font-mono text-brand-400">{dim.weight} pts</td>
                    <td className="py-4 text-dark-500 text-sm">{dim.focus}</td>
                  </tr>
                ))}
                <tr className="bg-dark-800/50 font-bold">
                  <td className="py-4 text-white">Total</td>
                  <td className="py-4 text-right font-mono text-brand-400">100 pts</td>
                  <td className="py-4 text-dark-500"></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Security & Privacy */}
      <section className="py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <AlertTriangle className="w-12 h-12 text-brand-400 mb-4" />
              <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">Security by Design</h2>
              <p className="text-dark-400 text-lg mb-6">
                Every submitted repository is treated as untrusted input. Scanning runs in isolated, disposable environments
                with strict resource limits and no network access by default.
              </p>
              <ul className="space-y-3 text-dark-300">
                <li className="flex items-center gap-3"><CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" /> Docker sandbox with CPU, memory, PID, and time limits</li>
                <li className="flex items-center gap-3"><CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" /> Non-root user, read-only rootfs, dropped capabilities</li>
                <li className="flex items-center gap-3"><CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" /> Default deny network; explicit allowlist only</li>
                <li className="flex items-center gap-3"><CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" /> Source code never persisted; logs sanitized</li>
                <li className="flex items-center gap-3"><CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" /> Cross-scan isolation; per-user data access</li>
              </ul>
            </div>
            <div className="bg-dark-900 border border-dark-700 rounded-xl p-8">
              <h3 className="text-xl font-semibold text-white mb-4">Threat Model</h3>
              <p className="text-dark-400 mb-4">
                Full STRIDE analysis documented in <code className="font-mono text-brand-400">docs/THREAT_MODEL.md</code>.
                Key boundaries: Internet → API, API → Database, API → Sandbox, Sandbox → Host.
              </p>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2 p-2 bg-dark-800 rounded">
                  <Shield className="w-4 h-4 text-green-400" />
                  <span className="text-dark-300">Sandbox escape prevention</span>
                </div>
                <div className="flex items-center gap-2 p-2 bg-dark-800 rounded">
                  <Shield className="w-4 h-4 text-green-400" />
                  <span className="text-dark-300">Resource exhaustion mitigation</span>
                </div>
                <div className="flex items-center gap-2 p-2 bg-dark-800 rounded">
                  <Shield className="w-4 h-4 text-green-400" />
                  <span className="text-dark-300">Source code confidentiality</span>
                </div>
                <div className="flex items-center gap-2 p-2 bg-dark-800 rounded">
                  <Shield className="w-4 h-4 text-yellow-400" />
                  <span className="text-dark-300">GitHub API rate limits (MVP)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 bg-brand-900/20 border-y border-brand-800">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">Ready to Grade Your Code?</h2>
          <p className="text-dark-400 text-lg mb-8">
            Submit a public GitHub repository and get a real, evidence-based assessment in minutes.
          </p>
          <Link to="/scan">
            <Button size="lg" className="w-full sm:w-auto">
              <Search className="w-5 h-5 mr-2" />
              Start Your First Scan
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </Link>
          <p className="mt-6 text-dark-500 text-sm">
            No account required for public repositories. Private repo support coming soon.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-dark-800 bg-dark-950">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <h3 className="font-semibold text-white mb-4">VibeGrade</h3>
              <p className="text-dark-500 text-sm">
                Evidence-driven software quality evaluation for AI-built applications.
              </p>
            </div>
            <div>
              <h4 className="font-medium text-dark-300 mb-3">Documentation</h4>
              <ul className="space-y-2 text-sm text-dark-500">
                <li><a href="/docs/ARCHITECTURE.md" className="hover:text-brand-400 transition-colors">Architecture</a></li>
                <li><a href="/docs/GRADING_RUBRIC.md" className="hover:text-brand-400 transition-colors">Grading Rubric</a></li>
                <li><a href="/docs/THREAT_MODEL.md" className="hover:text-brand-400 transition-colors">Threat Model</a></li>
                <li><a href="/docs/IMPLEMENTATION_PLAN.md" className="hover:text-brand-400 transition-colors">Implementation Plan</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-dark-300 mb-3">Resources</h4>
              <ul className="space-y-2 text-sm text-dark-500">
                <li><a href="https://github.com/jmo7850/VibeGrade" className="hover:text-brand-400 transition-colors" target="_blank" rel="noopener">GitHub Repository</a></li>
                <li><a href="#" className="hover:text-brand-400 transition-colors">Competitor Analysis</a></li>
                <li><a href="#" className="hover:text-brand-400 transition-colors">Report an Issue</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-dark-300 mb-3">Legal</h4>
              <ul className="space-y-2 text-sm text-dark-500">
                <li><a href="#" className="hover:text-brand-400 transition-colors">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-brand-400 transition-colors">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="pt-8 border-t border-dark-800 text-center text-dark-500 text-sm">
            <p>Built with evidence, not vibes. © 2026 VibeGrade</p>
          </div>
        </div>
      </footer>
    </div>
  );
}