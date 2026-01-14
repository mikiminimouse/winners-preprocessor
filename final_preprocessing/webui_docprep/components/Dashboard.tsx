
import React, { useState } from 'react';
import { 
  Folder, 
  FolderOpen, 
  FileText, 
  ChevronRight, 
  ChevronDown, 
  AlertTriangle, 
  CheckCircle2, 
  Box, 
  Server,
  Activity,
  HardDrive,
  Cpu,
  Zap,
  Clock
} from 'lucide-react';
import { DirectoryNode } from '../types';
import { AreaChart, Area, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis } from 'recharts';

// --- Mock Data ---

const SYSTEM_HEALTH_DATA = Array.from({ length: 20 }, (_, i) => ({
  time: `T-${20-i}`,
  load: 40 + Math.random() * 30,
  throughput: 800 + Math.random() * 400
}));

// --- Data Generators (Ported & Adapted from Statistics.tsx) ---

const generateUnitFiles = (unitName: string, type: string, parentPath: string): DirectoryNode[] => {
  const files: DirectoryNode[] = [
    { name: 'manifest.json', path: `${parentPath}/manifest.json`, count: -1, type: 'file', status: 'neutral' },
    { name: 'audit.log.jsonl', path: `${parentPath}/audit.log.jsonl`, count: -1, type: 'file', status: 'neutral' },
  ];

  if (type === 'pdf') {
    files.unshift({ name: 'payload.pdf', path: `${parentPath}/payload.pdf`, count: -1, type: 'file', status: 'neutral' });
  } else if (type === 'docx') {
    files.unshift({ name: 'document.docx', path: `${parentPath}/document.docx`, count: -1, type: 'file', status: 'neutral' });
  } else if (type === 'xlsx') {
    files.unshift({ name: 'spreadsheet.xlsx', path: `${parentPath}/spreadsheet.xlsx`, count: -1, type: 'file', status: 'neutral' });
  } else if (type === 'zip') {
    files.unshift({ name: 'archive.zip', path: `${parentPath}/archive.zip`, count: -1, type: 'file', status: 'neutral' });
  } else {
    files.unshift({ name: 'unknown_blob', path: `${parentPath}/unknown_blob`, count: -1, type: 'file', status: 'neutral' });
  }
  return files;
};

const generateMockUnits = (count: number, status: any, parentPath: string, fileType: string = 'pdf'): DirectoryNode[] => {
  const units: DirectoryNode[] = [];
  const displayLimit = 3; 
  for (let i = 0; i < displayLimit && i < count; i++) {
    const id = Math.random().toString(16).slice(2, 10);
    const name = `UNIT_ff${id}`;
    const path = `${parentPath}/${name}`;
    units.push({
      name: name,
      path: path,
      type: 'folder', // Treated as folder in dashboard for recursion, distinct icon in renderer
      status: status,
      count: 3, 
      children: generateUnitFiles(name, fileType, path)
    });
  }
  if (count > displayLimit) {
    units.push({ name: `... ${count - displayLimit} more units`, path: `${parentPath}/more`, count: -1, type: 'file', status: 'neutral' });
  }
  return units;
};

const generateExtensionFolders = (count: number, status: any, types: string[], parentPath: string): DirectoryNode[] => {
  const folders: DirectoryNode[] = [];
  let remaining = count;
  const avg = Math.floor(count / types.length);
  types.forEach((ext, i) => {
     if (remaining <= 0) return;
     const c = (i === types.length - 1) ? remaining : avg;
     const path = `${parentPath}/${ext}`;
     folders.push({
       name: ext,
       path: path,
       type: 'folder',
       status: status,
       count: c,
       children: generateMockUnits(c, status, path, ext)
     });
     remaining -= c;
  });
  return folders;
};

const ROOT_PATH = 'root/winners_preprocessor/final_preprocessing/Data/2025-03-04';

const PROTOCOL_TREE: DirectoryNode = {
  name: '2025-03-04',
  path: ROOT_PATH,
  count: 6025,
  children: [
    {
      name: 'Exceptions',
      path: `${ROOT_PATH}/Exceptions`,
      count: 1213,
      status: 'error',
      children: [
        {
          name: 'Exceptions_1', path: `${ROOT_PATH}/Exceptions/Exceptions_1`, count: 400, status: 'error', children: [
            { name: 'Ambiguous', path: `${ROOT_PATH}/Exceptions/Exceptions_1/Ambiguous`, count: 100, status: 'error', children: generateMockUnits(100, 'error', `${ROOT_PATH}/Exceptions/Exceptions_1/Ambiguous`, 'bin') },
            { name: 'Mixed', path: `${ROOT_PATH}/Exceptions/Exceptions_1/Mixed`, count: 150, status: 'warning', children: generateMockUnits(150, 'warning', `${ROOT_PATH}/Exceptions/Exceptions_1/Mixed`, 'zip') },
            { name: 'Empty', path: `${ROOT_PATH}/Exceptions/Exceptions_1/Empty`, count: 50, status: 'warning', children: generateExtensionFolders(50, 'warning', ['pdf', 'docx'], `${ROOT_PATH}/Exceptions/Exceptions_1/Empty`) },
            { name: 'Special', path: `${ROOT_PATH}/Exceptions/Exceptions_1/Special`, count: 100, status: 'neutral', children: generateExtensionFolders(100, 'neutral', ['sig', 'p7s'], `${ROOT_PATH}/Exceptions/Exceptions_1/Special`) },
          ]
        },
        {
          name: 'Exceptions_2', path: `${ROOT_PATH}/Exceptions/Exceptions_2`, count: 570, status: 'error', children: [
            { name: 'Ambiguous', path: `${ROOT_PATH}/Exceptions/Exceptions_2/Ambiguous`, count: 50, status: 'error', children: generateMockUnits(50, 'error', `${ROOT_PATH}/Exceptions/Exceptions_2/Ambiguous`) },
            { name: 'Mixed', path: `${ROOT_PATH}/Exceptions/Exceptions_2/Mixed`, count: 100, status: 'warning', children: generateMockUnits(100, 'warning', `${ROOT_PATH}/Exceptions/Exceptions_2/Mixed`, 'zip') },
            { name: 'Special', path: `${ROOT_PATH}/Exceptions/Exceptions_2/Special`, count: 230, status: 'neutral', children: generateExtensionFolders(230, 'neutral', ['xml', 'json'], `${ROOT_PATH}/Exceptions/Exceptions_2/Special`) },
            { name: 'ErConvert', path: `${ROOT_PATH}/Exceptions/Exceptions_2/ErConvert`, count: 100, status: 'error', children: generateExtensionFolders(100, 'error', ['doc', 'rtf'], `${ROOT_PATH}/Exceptions/Exceptions_2/ErConvert`) },
            { name: 'ErExtract', path: `${ROOT_PATH}/Exceptions/Exceptions_2/ErExtract`, count: 50, status: 'error', children: generateExtensionFolders(50, 'error', ['zip', 'rar'], `${ROOT_PATH}/Exceptions/Exceptions_2/ErExtract`) },
            { name: 'ErNormalize', path: `${ROOT_PATH}/Exceptions/Exceptions_2/ErNormalize`, count: 20, status: 'error', children: generateExtensionFolders(20, 'error', ['pdf'], `${ROOT_PATH}/Exceptions/Exceptions_2/ErNormalize`) },
          ]
        },
        { 
          name: 'Exceptions_3', path: `${ROOT_PATH}/Exceptions/Exceptions_3`, count: 243, status: 'error', children: [
             { name: 'Ambiguous', path: `${ROOT_PATH}/Exceptions/Exceptions_3/Ambiguous`, count: 30, status: 'error', children: generateMockUnits(30, 'error', `${ROOT_PATH}/Exceptions/Exceptions_3/Ambiguous`) },
             { name: 'Mixed', path: `${ROOT_PATH}/Exceptions/Exceptions_3/Mixed`, count: 43, status: 'warning', children: generateMockUnits(43, 'warning', `${ROOT_PATH}/Exceptions/Exceptions_3/Mixed`, 'zip') },
             { name: 'Special', path: `${ROOT_PATH}/Exceptions/Exceptions_3/Special`, count: 100, status: 'neutral', children: generateExtensionFolders(100, 'neutral', ['dat', 'bin'], `${ROOT_PATH}/Exceptions/Exceptions_3/Special`) },
             { name: 'ErConvert', path: `${ROOT_PATH}/Exceptions/Exceptions_3/ErConvert`, count: 30, status: 'error', children: generateExtensionFolders(30, 'error', ['ppt'], `${ROOT_PATH}/Exceptions/Exceptions_3/ErConvert`) },
             { name: 'ErExtract', path: `${ROOT_PATH}/Exceptions/Exceptions_3/ErExtract`, count: 20, status: 'error', children: generateExtensionFolders(20, 'error', ['7z'], `${ROOT_PATH}/Exceptions/Exceptions_3/ErExtract`) },
             { name: 'ErNormalize', path: `${ROOT_PATH}/Exceptions/Exceptions_3/ErNormalize`, count: 10, status: 'error', children: generateExtensionFolders(10, 'error', ['pdf'], `${ROOT_PATH}/Exceptions/Exceptions_3/ErNormalize`) },
          ]
        }
      ]
    },
    {
      name: 'Input',
      path: `${ROOT_PATH}/Input`,
      count: 12,
      status: 'neutral',
      children: generateExtensionFolders(12, 'neutral', ['pdf', 'docx', 'jpg', 'zip'], `${ROOT_PATH}/Input`)
    },
    {
      name: 'Rady2Merge',
      path: `${ROOT_PATH}/Rady2Merge`,
      count: 3800,
      status: 'success',
      children: [
        { 
          name: 'Direct', path: `${ROOT_PATH}/Rady2Merge/Direct`, count: 1200, status: 'neutral', children: [
            { name: 'Converted', path: `${ROOT_PATH}/Rady2Merge/Direct/Converted`, count: 0, status: 'neutral', children: [] },
            { name: 'Extracted', path: `${ROOT_PATH}/Rady2Merge/Direct/Extracted`, count: 0, status: 'neutral', children: [] },
            { name: 'Normalized', path: `${ROOT_PATH}/Rady2Merge/Direct/Normalized`, count: 1200, status: 'success', children: generateExtensionFolders(1200, 'success', ['pdf'], `${ROOT_PATH}/Rady2Merge/Direct/Normalized`) },
          ]
        },
        { 
          name: 'Processed_1', path: `${ROOT_PATH}/Rady2Merge/Processed_1`, count: 1000, status: 'neutral', children: [
            { name: 'Converted', path: `${ROOT_PATH}/Rady2Merge/Processed_1/Converted`, count: 400, status: 'success', children: generateExtensionFolders(400, 'success', ['pdf'], `${ROOT_PATH}/Rady2Merge/Processed_1/Converted`) },
            { name: 'Extracted', path: `${ROOT_PATH}/Rady2Merge/Processed_1/Extracted`, count: 300, status: 'success', children: generateExtensionFolders(300, 'success', ['pdf'], `${ROOT_PATH}/Rady2Merge/Processed_1/Extracted`) },
            { name: 'Normalized', path: `${ROOT_PATH}/Rady2Merge/Processed_1/Normalized`, count: 300, status: 'success', children: generateExtensionFolders(300, 'success', ['pdf'], `${ROOT_PATH}/Rady2Merge/Processed_1/Normalized`) },
          ]
        },
        { 
          name: 'Processed_2', path: `${ROOT_PATH}/Rady2Merge/Processed_2`, count: 800, status: 'neutral', children: [
            { name: 'Converted', path: `${ROOT_PATH}/Rady2Merge/Processed_2/Converted`, count: 300, status: 'success', children: generateExtensionFolders(300, 'success', ['pdf'], `${ROOT_PATH}/Rady2Merge/Processed_2/Converted`) },
            { name: 'Extracted', path: `${ROOT_PATH}/Rady2Merge/Processed_2/Extracted`, count: 200, status: 'success', children: generateExtensionFolders(200, 'success', ['pdf'], `${ROOT_PATH}/Rady2Merge/Processed_2/Extracted`) },
            { name: 'Normalized', path: `${ROOT_PATH}/Rady2Merge/Processed_2/Normalized`, count: 300, status: 'success', children: generateExtensionFolders(300, 'success', ['pdf'], `${ROOT_PATH}/Rady2Merge/Processed_2/Normalized`) },
          ]
        },
        { 
          name: 'Processed_3', path: `${ROOT_PATH}/Rady2Merge/Processed_3`, count: 800, status: 'neutral', children: [
            { name: 'Converted', path: `${ROOT_PATH}/Rady2Merge/Processed_3/Converted`, count: 300, status: 'success', children: generateExtensionFolders(300, 'success', ['pdf'], `${ROOT_PATH}/Rady2Merge/Processed_3/Converted`) },
            { name: 'Extracted', path: `${ROOT_PATH}/Rady2Merge/Processed_3/Extracted`, count: 200, status: 'success', children: generateExtensionFolders(200, 'success', ['pdf'], `${ROOT_PATH}/Rady2Merge/Processed_3/Extracted`) },
            { name: 'Normalized', path: `${ROOT_PATH}/Rady2Merge/Processed_3/Normalized`, count: 300, status: 'success', children: generateExtensionFolders(300, 'success', ['pdf'], `${ROOT_PATH}/Rady2Merge/Processed_3/Normalized`) },
          ]
        },
      ]
    },
    {
      name: 'Processing',
      path: `${ROOT_PATH}/Processing`,
      count: 850,
      status: 'warning', // used generally for processing
      children: [
        { 
          name: 'Processing_1', path: `${ROOT_PATH}/Processing/Processing_1`, count: 400, status: 'warning', children: [
            { name: 'Convert', path: `${ROOT_PATH}/Processing/Processing_1/Convert`, count: 200, status: 'warning', children: generateExtensionFolders(200, 'warning', ['doc', 'docx'], `${ROOT_PATH}/Processing/Processing_1/Convert`) },
            { name: 'Extract', path: `${ROOT_PATH}/Processing/Processing_1/Extract`, count: 150, status: 'warning', children: generateExtensionFolders(150, 'warning', ['zip'], `${ROOT_PATH}/Processing/Processing_1/Extract`) },
            { name: 'Normalize', path: `${ROOT_PATH}/Processing/Processing_1/Normalize`, count: 50, status: 'warning', children: generateExtensionFolders(50, 'warning', ['pdf'], `${ROOT_PATH}/Processing/Processing_1/Normalize`) },
          ]
        },
        { 
          name: 'Processing_2', path: `${ROOT_PATH}/Processing/Processing_2`, count: 300, status: 'warning', children: [
            { name: 'Convert', path: `${ROOT_PATH}/Processing/Processing_2/Convert`, count: 100, status: 'warning', children: generateExtensionFolders(100, 'warning', ['xls'], `${ROOT_PATH}/Processing/Processing_2/Convert`) },
            { name: 'Extract', path: `${ROOT_PATH}/Processing/Processing_2/Extract`, count: 150, status: 'warning', children: generateExtensionFolders(150, 'warning', ['tar.gz'], `${ROOT_PATH}/Processing/Processing_2/Extract`) },
            { name: 'Normalize', path: `${ROOT_PATH}/Processing/Processing_2/Normalize`, count: 50, status: 'warning', children: generateExtensionFolders(50, 'warning', ['pdf'], `${ROOT_PATH}/Processing/Processing_2/Normalize`) },
          ]
        },
        { 
          name: 'Processing_3', path: `${ROOT_PATH}/Processing/Processing_3`, count: 150, status: 'warning', children: [
            { name: 'Convert', path: `${ROOT_PATH}/Processing/Processing_3/Convert`, count: 50, status: 'warning', children: generateExtensionFolders(50, 'warning', ['ppt'], `${ROOT_PATH}/Processing/Processing_3/Convert`) },
            { name: 'Extract', path: `${ROOT_PATH}/Processing/Processing_3/Extract`, count: 50, status: 'warning', children: generateExtensionFolders(50, 'warning', ['7z'], `${ROOT_PATH}/Processing/Processing_3/Extract`) },
            { name: 'Normalize', path: `${ROOT_PATH}/Processing/Processing_3/Normalize`, count: 50, status: 'warning', children: generateExtensionFolders(50, 'warning', ['pdf'], `${ROOT_PATH}/Processing/Processing_3/Normalize`) },
          ]
        },
      ]
    },
    {
      name: 'Ready2Docling',
      path: `${ROOT_PATH}/Ready2Docling`,
      count: 4812,
      status: 'success',
      children: generateExtensionFolders(4812, 'success', ['pdf', 'docx', 'xlsx', 'jpeg'], `${ROOT_PATH}/Ready2Docling`)
    },
    { 
      name: 'ErMerge', 
      path: `${ROOT_PATH}/ErMerge`,
      count: 0, 
      status: 'error', 
      children: [
        { 
          name: 'Direct', path: `${ROOT_PATH}/ErMerge/Direct`, count: 0, status: 'error', children: [
            { name: 'Converted', path: `${ROOT_PATH}/ErMerge/Direct/Converted`, count: 0, status: 'error', children: [] },
            { name: 'Extracted', path: `${ROOT_PATH}/ErMerge/Direct/Extracted`, count: 0, status: 'error', children: [] },
            { name: 'Normalized', path: `${ROOT_PATH}/ErMerge/Direct/Normalized`, count: 0, status: 'error', children: [] },
          ]
        },
        { 
          name: 'Processed_1', path: `${ROOT_PATH}/ErMerge/Processed_1`, count: 0, status: 'error', children: [
            { name: 'Converted', path: `${ROOT_PATH}/ErMerge/Processed_1/Converted`, count: 0, status: 'error', children: [] },
            { name: 'Extracted', path: `${ROOT_PATH}/ErMerge/Processed_1/Extracted`, count: 0, status: 'error', children: [] },
            { name: 'Normalized', path: `${ROOT_PATH}/ErMerge/Processed_1/Normalized`, count: 0, status: 'error', children: [] },
          ]
        },
        { 
          name: 'Processed_2', path: `${ROOT_PATH}/ErMerge/Processed_2`, count: 0, status: 'error', children: [
            { name: 'Converted', path: `${ROOT_PATH}/ErMerge/Processed_2/Converted`, count: 0, status: 'error', children: [] },
            { name: 'Extracted', path: `${ROOT_PATH}/ErMerge/Processed_2/Extracted`, count: 0, status: 'error', children: [] },
            { name: 'Normalized', path: `${ROOT_PATH}/ErMerge/Processed_2/Normalized`, count: 0, status: 'error', children: [] },
          ]
        },
        { 
          name: 'Processed_3', path: `${ROOT_PATH}/ErMerge/Processed_3`, count: 0, status: 'error', children: [
            { name: 'Converted', path: `${ROOT_PATH}/ErMerge/Processed_3/Converted`, count: 0, status: 'error', children: [] },
            { name: 'Extracted', path: `${ROOT_PATH}/ErMerge/Processed_3/Extracted`, count: 0, status: 'error', children: [] },
            { name: 'Normalized', path: `${ROOT_PATH}/ErMerge/Processed_3/Normalized`, count: 0, status: 'error', children: [] },
          ]
        },
      ]
    },
    {
      name: 'Total Exceptions',
      path: `${ROOT_PATH}/Total Exceptions`,
      count: 1213,
      status: 'error', 
      children: [
        {
          name: 'Exceptions_1', path: `${ROOT_PATH}/Total Exceptions/Exceptions_1`, count: 400, status: 'error', children: [
            { name: 'Ambiguous', path: `${ROOT_PATH}/Total Exceptions/Exceptions_1/Ambiguous`, count: 100, status: 'error', children: generateMockUnits(100, 'error', `${ROOT_PATH}/Total Exceptions/Exceptions_1/Ambiguous`, 'bin') },
            { name: 'Mixed', path: `${ROOT_PATH}/Total Exceptions/Exceptions_1/Mixed`, count: 150, status: 'warning', children: generateMockUnits(150, 'warning', `${ROOT_PATH}/Total Exceptions/Exceptions_1/Mixed`, 'zip') },
            { name: 'Empty', path: `${ROOT_PATH}/Total Exceptions/Exceptions_1/Empty`, count: 50, status: 'warning', children: generateExtensionFolders(50, 'warning', ['pdf', 'docx'], `${ROOT_PATH}/Total Exceptions/Exceptions_1/Empty`) },
            { name: 'Special', path: `${ROOT_PATH}/Total Exceptions/Exceptions_1/Special`, count: 100, status: 'neutral', children: generateExtensionFolders(100, 'neutral', ['sig', 'p7s'], `${ROOT_PATH}/Total Exceptions/Exceptions_1/Special`) },
          ]
        },
        {
          name: 'Exceptions_2', path: `${ROOT_PATH}/Total Exceptions/Exceptions_2`, count: 570, status: 'error', children: [
            { name: 'Ambiguous', path: `${ROOT_PATH}/Total Exceptions/Exceptions_2/Ambiguous`, count: 50, status: 'error', children: generateMockUnits(50, 'error', `${ROOT_PATH}/Total Exceptions/Exceptions_2/Ambiguous`) },
            { name: 'Mixed', path: `${ROOT_PATH}/Total Exceptions/Exceptions_2/Mixed`, count: 100, status: 'warning', children: generateMockUnits(100, 'warning', `${ROOT_PATH}/Total Exceptions/Exceptions_2/Mixed`, 'zip') },
            { name: 'Special', path: `${ROOT_PATH}/Total Exceptions/Exceptions_2/Special`, count: 230, status: 'neutral', children: generateExtensionFolders(230, 'neutral', ['xml', 'json'], `${ROOT_PATH}/Total Exceptions/Exceptions_2/Special`) },
            { name: 'ErConvert', path: `${ROOT_PATH}/Total Exceptions/Exceptions_2/ErConvert`, count: 100, status: 'error', children: generateExtensionFolders(100, 'error', ['doc', 'rtf'], `${ROOT_PATH}/Total Exceptions/Exceptions_2/ErConvert`) },
            { name: 'ErExtract', path: `${ROOT_PATH}/Total Exceptions/Exceptions_2/ErExtract`, count: 50, status: 'error', children: generateExtensionFolders(50, 'error', ['zip', 'rar'], `${ROOT_PATH}/Total Exceptions/Exceptions_2/ErExtract`) },
            { name: 'ErNormalize', path: `${ROOT_PATH}/Total Exceptions/Exceptions_2/ErNormalize`, count: 20, status: 'error', children: generateExtensionFolders(20, 'error', ['pdf'], `${ROOT_PATH}/Total Exceptions/Exceptions_2/ErNormalize`) },
          ]
        },
        { 
          name: 'Exceptions_3', path: `${ROOT_PATH}/Total Exceptions/Exceptions_3`, count: 243, status: 'error', children: [
             { name: 'Ambiguous', path: `${ROOT_PATH}/Total Exceptions/Exceptions_3/Ambiguous`, count: 30, status: 'error', children: generateMockUnits(30, 'error', `${ROOT_PATH}/Total Exceptions/Exceptions_3/Ambiguous`) },
             { name: 'Mixed', path: `${ROOT_PATH}/Total Exceptions/Exceptions_3/Mixed`, count: 43, status: 'warning', children: generateMockUnits(43, 'warning', `${ROOT_PATH}/Total Exceptions/Exceptions_3/Mixed`, 'zip') },
             { name: 'Special', path: `${ROOT_PATH}/Total Exceptions/Exceptions_3/Special`, count: 100, status: 'neutral', children: generateExtensionFolders(100, 'neutral', ['dat', 'bin'], `${ROOT_PATH}/Total Exceptions/Exceptions_3/Special`) },
             { name: 'ErConvert', path: `${ROOT_PATH}/Total Exceptions/Exceptions_3/ErConvert`, count: 30, status: 'error', children: generateExtensionFolders(30, 'error', ['ppt'], `${ROOT_PATH}/Total Exceptions/Exceptions_3/ErConvert`) },
             { name: 'ErExtract', path: `${ROOT_PATH}/Total Exceptions/Exceptions_3/ErExtract`, count: 20, status: 'error', children: generateExtensionFolders(20, 'error', ['7z'], `${ROOT_PATH}/Total Exceptions/Exceptions_3/ErExtract`) },
             { name: 'ErNormalize', path: `${ROOT_PATH}/Total Exceptions/Exceptions_3/ErNormalize`, count: 10, status: 'error', children: generateExtensionFolders(10, 'error', ['pdf'], `${ROOT_PATH}/Total Exceptions/Exceptions_3/ErNormalize`) },
          ]
        }
      ]
    }
  ]
};

// --- Sub-Components ---

const StatWidget = ({ title, value, sub, icon: Icon, color, trend }: any) => {
  const colorMap: any = {
    blue: 'text-blue-600 bg-blue-50 border-blue-100',
    emerald: 'text-emerald-600 bg-emerald-50 border-emerald-100',
    rose: 'text-rose-600 bg-rose-50 border-rose-100',
    purple: 'text-purple-600 bg-purple-50 border-purple-100',
  };

  return (
    <div className="bg-white rounded-[24px] p-5 border border-slate-100 shadow-sm hover:shadow-md transition-all group">
      <div className="flex justify-between items-start mb-4">
        <div className={`p-2.5 rounded-xl ${colorMap[color]} group-hover:scale-110 transition-transform`}>
           <Icon size={20} />
        </div>
        {trend && (
           <div className={`text-[10px] font-black px-2 py-0.5 rounded-full ${trend > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>
              {trend > 0 ? '+' : ''}{trend}%
           </div>
        )}
      </div>
      <div className="text-3xl font-black text-slate-800 tracking-tight mb-1">{value}</div>
      <div className="text-xs font-bold text-slate-400 uppercase tracking-wide">{title}</div>
      <div className="mt-3 pt-3 border-t border-slate-50 text-[10px] text-slate-400 font-medium">
         {sub}
      </div>
    </div>
  );
};

const DirectoryItem: React.FC<{ node: DirectoryNode; depth?: number }> = ({ node, depth = 0 }) => {
  const [isOpen, setIsOpen] = useState(depth < 2); // Auto-expand first 2 levels
  const hasChildren = node.children && node.children.length > 0;

  const getStatusColor = (status?: string) => {
    switch(status) {
      case 'error': return 'text-rose-600 bg-rose-50/50 border-rose-100';
      case 'warning': return 'text-amber-600 bg-amber-50/50 border-amber-100';
      case 'success': return 'text-emerald-600 bg-emerald-50/50 border-emerald-100';
      default: return 'text-slate-600 bg-white border-slate-100 hover:bg-slate-50';
    }
  };

  // Determine if this is a 'unit' level node (has children but isn't a simple folder container)
  const isUnit = node.name.startsWith('UNIT_');

  return (
    <div className="select-none relative">
      {depth > 0 && (
         <div className="absolute left-[-11px] top-0 bottom-0 w-px bg-slate-200" style={{ display: 'none' }} /> 
      )}
      <div 
        onClick={() => hasChildren && setIsOpen(!isOpen)}
        className={`flex items-center gap-3 py-2.5 px-3 my-1.5 rounded-xl border transition-all cursor-pointer ${getStatusColor(node.status)}`}
        style={{ marginLeft: `${depth * 20}px` }}
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="text-slate-400 shrink-0">
            {hasChildren ? (
              isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />
            ) : <div className="w-3.5" />}
          </div>
          
          {node.type === 'file' ? (
            <FileText size={16} className="opacity-70 shrink-0" />
          ) : isUnit ? (
            <Box size={16} className="opacity-80 shrink-0" />
          ) : (
            isOpen ? <FolderOpen size={16} className="opacity-80 shrink-0" /> : <Folder size={16} className="opacity-80 shrink-0" />
          )}
          
          <span className="font-mono text-xs font-bold tracking-tight truncate">{node.name}</span>
        </div>
        
        {node.count >= 0 && (
          <div className="px-2 py-0.5 bg-white/60 rounded-md text-[10px] font-black border border-black/5 shrink-0">
            {node.count}
          </div>
        )}
      </div>

      {isOpen && hasChildren && (
        <div className="relative">
           <div className="absolute left-[10px] top-0 bottom-2 w-px bg-slate-200" style={{ marginLeft: `${depth * 20}px` }} />
           {node.children!.map((child, idx) => (
             <DirectoryItem key={child.path + idx} node={child} depth={depth + 1} />
           ))}
        </div>
      )}
    </div>
  );
};

// --- Main Dashboard ---

const Dashboard: React.FC<{ protocolDate: string }> = ({ protocolDate }) => {
  return (
    <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-700 pb-12">
      
      {/* Top Hero Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
         {/* Live Status Card */}
         <div className="lg:col-span-2 bg-slate-900 rounded-[32px] p-8 text-white shadow-2xl relative overflow-hidden flex flex-col justify-between min-h-[280px]">
            <div className="absolute top-0 right-0 p-8 opacity-10">
               <Activity size={240} strokeWidth={1} />
            </div>
            
            <div className="relative z-10 flex justify-between items-start">
               <div>
                  <div className="flex items-center gap-2 text-blue-400 mb-2 font-mono text-xs font-bold uppercase tracking-widest">
                     <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                     Live System Telemetry
                  </div>
                  <h1 className="text-3xl font-black tracking-tight mb-1">Protocol: {protocolDate}</h1>
                  <p className="text-slate-400 text-sm font-medium opacity-80">Orchestrator Node: active • Latency: 12ms</p>
               </div>
               <div className="bg-slate-800/50 backdrop-blur-md px-4 py-2 rounded-xl border border-slate-700 text-xs font-mono text-slate-300">
                  PID: 8492
               </div>
            </div>

            <div className="relative z-10 h-32 w-full mt-6">
                <ResponsiveContainer width="100%" height="100%">
                   <AreaChart data={SYSTEM_HEALTH_DATA}>
                      <defs>
                         <linearGradient id="colorThroughput" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                         </linearGradient>
                      </defs>
                      <Area type="monotone" dataKey="throughput" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorThroughput)" />
                   </AreaChart>
                </ResponsiveContainer>
            </div>
         </div>

         {/* Summary Stats Grid */}
         <div className="grid grid-cols-2 gap-4">
            <StatWidget 
               title="Total Units" 
               value="6,025" 
               sub="Batch Size: 4.2GB" 
               icon={Box} 
               color="blue" 
               trend={12}
            />
            <StatWidget 
               title="Processed" 
               value="4,812" 
               sub="Completion: 79%" 
               icon={CheckCircle2} 
               color="emerald" 
               trend={5}
            />
            <StatWidget 
               title="Exceptions" 
               value="1,213" 
               sub="Rate: 20.1%" 
               icon={AlertTriangle} 
               color="rose" 
               trend={-2}
            />
            <StatWidget 
               title="Avg Time" 
               value="0.4s" 
               sub="Per Unit" 
               icon={Zap} 
               color="purple" 
            />
         </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 h-[600px]">
         
         {/* Directory Tree */}
         <div className="xl:col-span-2 bg-white rounded-[32px] border border-slate-200 shadow-sm flex flex-col overflow-hidden">
            <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center backdrop-blur-sm sticky top-0 z-10">
               <div className="flex items-center gap-3">
                  <div className="p-2 bg-white rounded-lg border border-slate-200 shadow-sm text-slate-500">
                     <HardDrive size={18} />
                  </div>
                  <div>
                     <h3 className="font-bold text-slate-800">File System Inspector</h3>
                     <p className="text-xs text-slate-400 font-medium">/root/winners_preprocessor/final_preprocessing/Data</p>
                  </div>
               </div>
               <div className="px-3 py-1 bg-white border border-slate-200 rounded-full text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                  Read-Only
               </div>
            </div>
            <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
               <DirectoryItem node={PROTOCOL_TREE} />
            </div>
         </div>

         {/* Right Sidebar: Critical Info */}
         <div className="flex flex-col gap-6 h-full">
            
            {/* Alerts Widget */}
            <div className="bg-white rounded-[32px] border border-slate-200 p-6 shadow-sm flex-1 flex flex-col">
               <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2 text-sm uppercase tracking-widest">
                  <AlertTriangle className="text-rose-500" size={16} />
                  Critical Attention
               </h3>
               <div className="space-y-3 overflow-y-auto custom-scrollbar flex-1 pr-2">
                  <div className="p-4 bg-rose-50 rounded-2xl border border-rose-100 transition-all hover:shadow-sm">
                     <div className="flex justify-between items-center mb-1">
                        <span className="text-[10px] font-black text-rose-600 uppercase tracking-wider">Exceptions_1/Special</span>
                        <span className="text-xs font-black text-white bg-rose-500 px-2 py-0.5 rounded-full">100 Units</span>
                     </div>
                     <p className="text-xs text-rose-700/80 mt-2 font-medium leading-relaxed">High volume of special signature files (p7s, sig) detected. Manual review recommended before Cycle 2.</p>
                  </div>
                  
                  <div className="p-4 bg-amber-50 rounded-2xl border border-amber-100 transition-all hover:shadow-sm">
                     <div className="flex justify-between items-center mb-1">
                        <span className="text-[10px] font-black text-amber-600 uppercase tracking-wider">Input Queue</span>
                        <span className="text-xs font-black text-white bg-amber-500 px-2 py-0.5 rounded-full">12 Units</span>
                     </div>
                     <p className="text-xs text-amber-700/80 mt-2 font-medium leading-relaxed">Remaining RAW units pending classification trigger. Pipeline currently idle.</p>
                  </div>

                  <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 transition-all hover:shadow-sm">
                     <div className="flex justify-between items-center mb-1">
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-wider">Disk Usage</span>
                        <span className="text-xs font-black text-slate-600">85%</span>
                     </div>
                     <div className="w-full bg-slate-200 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div className="bg-slate-500 h-full w-[85%]" />
                     </div>
                  </div>
               </div>
            </div>

            {/* Info Widget */}
            <div className="bg-blue-600 rounded-[32px] p-6 shadow-xl shadow-blue-200 text-white relative overflow-hidden">
               <div className="absolute -right-4 -bottom-4 opacity-20 text-white">
                  <Server size={100} />
               </div>
               <h3 className="font-bold mb-2 flex items-center gap-2">
                  <Cpu size={18} />
                  Final Merge Logic
               </h3>
               <p className="text-xs text-blue-100 leading-relaxed mb-4 font-medium opacity-90 relative z-10">
                  Units in <strong>Rady2Merge</strong> are staged but not committed. 
                  Execute "Final Consolidation" to move valid units to <strong>Ready2Docling</strong>.
               </p>
               <button className="relative z-10 w-full py-3 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl text-xs font-black uppercase tracking-widest transition-all">
                  View Merge Rules
               </button>
            </div>
         </div>
      </div>
    </div>
  );
};

export default Dashboard;
