import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

export function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'text-red-400';
    case 'high':
      return 'text-orange-400';
    case 'medium':
      return 'text-yellow-400';
    case 'low':
      return 'text-blue-400';
    case 'info':
      return 'text-dark-400';
    default:
      return 'text-dark-400';
  }
}

export function getSeverityBadge(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'badge-critical';
    case 'high':
      return 'badge-high';
    case 'medium':
      return 'badge-medium';
    case 'low':
      return 'badge-low';
    case 'info':
      return 'badge-info';
    default:
      return 'badge-info';
  }
}

export function getConfidenceBadge(confidence: string): string {
  switch (confidence) {
    case 'verified':
      return 'badge-verified';
    case 'likely':
      return 'badge-likely';
    case 'heuristic':
      return 'badge-heuristic';
    case 'info':
      return 'badge-info';
    default:
      return 'badge-info';
  }
}

export function getGradeBadge(grade: string): string {
  switch (grade.toUpperCase()) {
    case 'A':
      return 'grade-a';
    case 'B':
      return 'grade-b';
    case 'C':
      return 'grade-c';
    case 'D':
      return 'grade-d';
    case 'F':
      return 'grade-f';
    default:
      return 'grade-f';
  }
}

export function getProjectTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    web_app: 'Web Application',
    api: 'API / Backend',
    cli: 'CLI Tool',
    library: 'Library / Package',
    agent: 'AI Agent',
    mobile: 'Mobile App',
    unknown: 'Unknown',
  };
  return labels[type] || type;
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length - 3) + '...';
}

export function getScoreColor(score: number): string {
  if (score >= 90) return 'text-green-400';
  if (score >= 80) return 'text-brand-400';
  if (score >= 70) return 'text-yellow-400';
  if (score >= 60) return 'text-orange-400';
  return 'text-red-400';
}

export function getScoreBgColor(score: number): string {
  if (score >= 90) return 'bg-green-500';
  if (score >= 80) return 'bg-brand-500';
  if (score >= 70) return 'bg-yellow-500';
  if (score >= 60) return 'bg-orange-500';
  return 'bg-red-500';
}