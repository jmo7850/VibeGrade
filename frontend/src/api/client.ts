import { API_URL } from './config';
import type {
  ScanResponse,
  ScanHistoryResponse,
  ScanStatusResponse,
  ReportResponse,
  FindingResponse,
  ScanCreate,
  RubricResponse,
  HealthResponse,
  ArchitectureResponse,
  Severity,
  Confidence,
  FindingStatus,
} from '../types';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ApiError(response.status, error.detail || 'Request failed');
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // Scans
  async createScan(data: ScanCreate): Promise<ScanResponse> {
    return this.request<ScanResponse>('/api/v1/scans', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getScanStatus(scanId: string): Promise<ScanStatusResponse> {
    return this.request<ScanStatusResponse>(`/api/v1/scans/${scanId}`);
  }

  async getScanReport(scanId: string): Promise<ReportResponse> {
    return this.request<ReportResponse>(`/api/v1/scans/${scanId}/report`);
  }

  async getScanFindings(
    scanId: string,
    params?: {
      severity?: Severity[];
      confidence?: Confidence[];
      status?: FindingStatus[];
      dimension?: string;
      tool?: string;
      file_path?: string;
      limit?: number;
      offset?: number;
    }
  ): Promise<FindingResponse[]> {
    const searchParams = new URLSearchParams();
    if (params?.severity?.length) searchParams.set('severity', params.severity.join(','));
    if (params?.confidence?.length) searchParams.set('confidence', params.confidence.join(','));
    if (params?.status?.length) searchParams.set('status', params.status.join(','));
    if (params?.dimension) searchParams.set('dimension', params.dimension);
    if (params?.tool) searchParams.set('tool', params.tool);
    if (params?.file_path) searchParams.set('file_path', params.file_path);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());

    const query = searchParams.toString();
    return this.request<FindingResponse[]>(`/api/v1/scans/${scanId}/findings${query ? `?${query}` : ''}`);
  }

  async getScanHistory(limit = 50, offset = 0): Promise<ScanHistoryResponse[]> {
    return this.request<ScanHistoryResponse[]>(`/api/v1/scans/history?limit=${limit}&offset=${offset}`);
  }

  // Report export
  async exportScanReport(scanId: string, format: 'json' | 'markdown' = 'json'): Promise<string> {
    const response = await fetch(`${this.baseUrl}/api/v1/scans/${scanId}/export?format=${format}`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ApiError(response.status, error.detail || 'Export failed');
    }
    return response.text();
  }

  // Architecture explorer
  async getScanArchitecture(scanId: string): Promise<ArchitectureResponse> {
    return this.request<ArchitectureResponse>(`/api/v1/scans/${scanId}/architecture`);
  }

  // Rubric
  async getRubric(): Promise<RubricResponse> {
    return this.request<RubricResponse>('/api/v1/rubric');
  }

  // Health
  async healthCheck(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/api/v1/scans/health');
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export const api = new ApiClient();