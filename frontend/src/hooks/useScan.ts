import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { ScanCreate, Severity, Confidence, FindingStatus } from '../types';

export function useCreateScan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ScanCreate) => api.createScan(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scan-history'] });
    },
  });
}

export function useScanStatus(scanId: string | null, enabled = true) {
  return useQuery({
    queryKey: ['scan-status', scanId],
    queryFn: () => api.getScanStatus(scanId!),
    enabled: enabled && !!scanId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      if (data.status === 'complete' || data.status === 'failed') return false;
      return 2000; // Poll every 2 seconds while running
    },
  });
}

export function useScanReport(scanId: string | null, enabled = true) {
  return useQuery({
    queryKey: ['scan-report', scanId],
    queryFn: () => api.getScanReport(scanId!),
    enabled: enabled && !!scanId,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
}

export function useScanFindings(
  scanId: string | null,
  params?: {
    severity?: Severity[];
    confidence?: Confidence[];
    status?: FindingStatus[];
    dimension?: string;
    tool?: string;
    file_path?: string;
    limit?: number;
    offset?: number;
  },
  enabled = true
) {
  return useQuery({
    queryKey: ['scan-findings', scanId, params],
    queryFn: () => api.getScanFindings(scanId!, params),
    enabled: enabled && !!scanId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useScanHistory(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['scan-history', limit, offset],
    queryFn: () => api.getScanHistory(limit, offset),
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}
export function useRubric() {
  return useQuery({
    queryKey: ['rubric'],
    queryFn: () => api.getRubric(),
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}

export function useHealthCheck() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.healthCheck(),
    refetchInterval: 1000 * 60 * 5, // 5 minutes
  });
}