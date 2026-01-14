
import React from 'react';
import { 
  FileSearch, 
  RefreshCw, 
  Archive, 
  Layers, 
  GitMerge, 
  CheckCircle2, 
  AlertCircle,
  XCircle
} from 'lucide-react';

export const STAGE_CONFIG = {
  CLASSIFY: { icon: <FileSearch className="w-5 h-5" />, color: 'blue' },
  CONVERT: { icon: <RefreshCw className="w-5 h-5" />, color: 'indigo' },
  EXTRACT: { icon: <Archive className="w-5 h-5" />, color: 'amber' },
  NORMALIZE: { icon: <Layers className="w-5 h-5" />, color: 'emerald' },
  MERGE: { icon: <GitMerge className="w-5 h-5" />, color: 'purple' },
  READY: { icon: <CheckCircle2 className="w-5 h-5" />, color: 'green' },
  EXCEPTION: { icon: <AlertCircle className="w-5 h-5" />, color: 'red' },
  ER_MERGE: { icon: <XCircle className="w-5 h-5" />, color: 'rose' }
};

export const CATEGORY_COLORS: Record<string, string> = {
  direct: 'bg-green-100 text-green-700',
  convert: 'bg-blue-100 text-blue-700',
  extract: 'bg-amber-100 text-amber-700',
  normalize: 'bg-emerald-100 text-emerald-700',
  special: 'bg-purple-100 text-purple-700',
  mixed: 'bg-slate-100 text-slate-700',
  unknown: 'bg-red-100 text-red-700',
  er_merge: 'bg-rose-100 text-rose-700',
};