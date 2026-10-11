import { Shield, Database, Key, Trash2, Settings as SettingsIcon, Moon, Search, Github } from 'lucide-react';
import { Button, Card, CardHeader, CardContent, Input, Badge } from '../components';

export function SettingsPage() {
  return (
    <div className="min-h-screen py-8 px-6">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-white mb-2">Settings</h1>
          <p className="text-dark-400">Manage your VibeGrade preferences and account</p>
        </div>

        {/* Appearance */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-brand-900/30 border border-brand-800 flex items-center justify-center">
                <Moon className="w-5 h-5 text-brand-400" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Appearance</h3>
                <p className="text-dark-500 text-sm">Customize how VibeGrade looks</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-white">Dark Mode</p>
                <p className="text-dark-500 text-sm">VibeGrade is dark-first by design</p>
              </div>
              <Badge variant="verified">Enabled</Badge>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-white">Compact Mode</p>
                <p className="text-dark-500 text-sm">Reduce spacing for more density</p>
              </div>
              <Button variant="ghost" size="sm">Coming Soon</Button>
            </div>
          </CardContent>
        </Card>

        {/* Scan Preferences */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-brand-900/30 border border-brand-800 flex items-center justify-center">
                <Search className="w-5 h-5 text-brand-400" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Scan Preferences</h3>
                <p className="text-dark-500 text-sm">Configure default scan behavior</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="label">Default Branch</label>
              <Input placeholder="main" defaultValue="main" />
              <p className="text-dark-500 text-sm mt-1">Branch to scan when none specified</p>
            </div>
            <div>
              <label className="label">Maximum Repository Size (MB)</label>
              <Input type="number" defaultValue={500} min={100} max={2000} />
              <p className="text-dark-500 text-sm mt=1">Larger repos may time out</p>
            </div>
            <div>
              <label className="label">Scan Timeout (seconds)</label>
              <Input type="number" defaultValue={300} min={60} max={1800} />
              <p className="text-dark-500 text-sm mt=1">Maximum time for a complete scan</p>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-white">Include AI Explanations</p>
                <p className="text-dark-500 text-sm">Uses external AI provider (requires API key)</p>
              </div>
              <Badge variant="heuristic">Experimental</Badge>
            </div>
          </CardContent>
        </Card>

        {/* AI Analysis */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-brand-900/30 border border-brand-800 flex items-center justify-center">
                <SettingsIcon className="w-5 h-5 text-brand-400" />
              </div>
              <div>
                <h3 className="font-semibold text-white">AI Analysis</h3>
                <p className="text-dark-500 text-sm">Configure AI-powered explanations and remediation</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-dark-800/50 border border-dark-700 rounded-lg">
              <div className="flex items-start gap-3">
                <Shield className="w-5 h-5 text-yellow-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium text-white">AI Analysis Requires Configuration</p>
                  <p className="text-dark-400 text-sm mt-1">
                    AI-powered explanations and remediation prompts require an external AI provider
                    (OpenAI, Anthropic, or local Ollama). This feature is disabled by default
                    to ensure VibeGrade works offline and without external dependencies.
                  </p>
                </div>
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="label">AI Provider</label>
                <select className="input" disabled>
                  <option>OpenAI (GPT-4)</option>
                  <option>Anthropic (Claude)</option>
                  <option>Local (Ollama)</option>
                </select>
              </div>
              <div>
                <label className="label">API Key</label>
                <Input type="password" placeholder="sk-..." disabled />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-white">Send Code to AI Provider</p>
                <p className="text-dark-500 text-sm">Allow sending source code snippets for context-aware analysis</p>
              </div>
              <input type="checkbox" className="w-5 h-5 rounded border-dark-600 bg-dark-800 text-brand-500" disabled />
            </div>
          </CardContent>
        </Card>

        {/* Data & Privacy */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-brand-900/30 border border-brand-800 flex items-center justify-center">
                <Database className="w-5 h-5 text-brand-400" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Data & Privacy</h3>
                <p className="text-dark-500 text-sm">Control your data retention and privacy</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-dark-800/50 border border-dark-700 rounded-lg">
              <div className="flex items-start gap-3">
                <Shield className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium text-white">No Persistent Source Code Storage</p>
                  <p className="text-dark-400 text-sm mt-1">
                    VibeGrade never stores your source code. Repositories are cloned to temporary
                    workspaces, analyzed, and immediately deleted. Only normalized findings and
                    evidence metadata are persisted.
                  </p>
                </div>
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="label">Scan Retention (days)</label>
                <Input type="number" defaultValue={90} min={1} max={365} />
                <p className="text-dark-500 text-sm mt-1">Auto-delete scans older than this</p>
              </div>
              <div>
                <label className="label">Evidence Retention (days)</label>
                <Input type="number" defaultValue={90} min={1} max={365} />
                <p className="text-dark-500 text-sm mt=1">Auto-delete evidence blobs</p>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-white">Anonymous Usage Analytics</p>
                <p className="text-dark-500 text-sm">Help improve VibeGrade with anonymous usage data</p>
              </div>
              <input type="checkbox" className="w-5 h-5 rounded border-dark-600 bg-dark-800 text-brand-500" defaultChecked />
            </div>
          </CardContent>
        </Card>

        {/* GitHub Integration */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-brand-900/30 border border-brand-800 flex items-center justify-center">
                <Github className="w-5 h-5 text-brand-400" />
              </div>
              <div>
                <h3 className="font-semibold text-white">GitHub Integration</h3>
                <p className="text-dark-500 text-sm">Configure GitHub API access for higher rate limits</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-dark-800/50 border border-dark-700 rounded-lg">
              <div className="flex items-start gap-3">
                <Key className="w-5 h-5 text-brand-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium text-white">Personal Access Token</p>
                  <p className="text-dark-400 text-sm mt-1">
                    Add a GitHub Personal Access Token (classic) to increase API rate limits from 60/hr to 5,000/hr.
                    No scopes required for public repositories. Token is stored securely and never logged.
                  </p>
                </div>
              </div>
            </div>
            <div>
              <label className="label">GitHub Token</label>
              <Input
                type="password"
                placeholder="ghp_..."
                hint="Token is encrypted at rest. No scopes needed for public repos."
              />
            </div>
            <Button variant="secondary" onClick={() => alert('Token validation not implemented yet')}>
              Validate Token
            </Button>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-red-800">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-red-900/30 border border-red-800 flex items-center justify-center">
                <Trash2 className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <h3 className="font-semibold text-red-300">Danger Zone</h3>
                <p className="text-dark-500 text-sm">Irreversible actions</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-red-900/20 border border-red-800 rounded-lg">
              <div className="flex items-start gap-3">
                <Trash2 className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium text-red-300">Delete All Scan Data</p>
                  <p className="text-red-400 text-sm mt-1">
                    This will permanently delete all your scan history, findings, evidence, and reports.
                    This action cannot be undone.
                  </p>
                </div>
              </div>
            </div>
            <Button variant="danger" onClick={() => alert('Delete all data not implemented yet')}>
              <Trash2 className="w-4 h-4 mr-2" />
              Delete All My Data
            </Button>
          </CardContent>
        </Card>

        {/* Version Info */}
        <Card>
          <CardContent className="pt-0">
            <div className="flex items-center justify-between text-sm text-dark-500">
              <span>VibeGrade v0.1.0 (MVP)</span>
              <span>Built with evidence, not vibes</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}