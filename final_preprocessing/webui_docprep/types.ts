
export type ProcessingCategory = 'direct' | 'convert' | 'extract' | 'normalize' | 'special' | 'mixed' | 'unknown' | 'empty';

export enum UnitState {
  RAW = 'RAW',
  CLASSIFIED_1 = 'CLASSIFIED_1',
  CLASSIFIED_2 = 'CLASSIFIED_2',
  CLASSIFIED_3 = 'CLASSIFIED_3',
  PENDING_CONVERT = 'PENDING_CONVERT',
  PENDING_EXTRACT = 'PENDING_EXTRACT',
  PENDING_NORMALIZE = 'PENDING_NORMALIZE',
  MERGED_DIRECT = 'MERGED_DIRECT',
  MERGED_PROCESSED = 'MERGED_PROCESSED',
  READY_FOR_DOCLING = 'READY_FOR_DOCLING',
  EXCEPTION_1 = 'EXCEPTION_1',
  EXCEPTION_2 = 'EXCEPTION_2',
  EXCEPTION_3 = 'EXCEPTION_3',
  MERGER_SKIPPED = 'MERGER_SKIPPED',
  ER_MERGE = 'ER_MERGE' // Added for failed final merge
}

export interface DirectoryNode {
  name: string;
  path: string;
  count: number;
  children?: DirectoryNode[];
  type?: 'folder' | 'file';
  status?: 'success' | 'error' | 'warning' | 'neutral';
}

export interface ExtensionMetric {
  ext: string;
  count: number;
  size_mb: number;
  success_rate: number;
}

export interface CycleStats {
  cycle: number;
  total_units: number;
  processed: number;
  failed: number;
  categories: Record<ProcessingCategory, number>;
  extensions: ExtensionMetric[];
}