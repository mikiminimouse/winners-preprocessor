
import React, { useState, useMemo } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend
} from 'recharts';
import { 
  CheckCircle2,
  XCircle,
  FolderOpen,
  Folder,
  Box,
  ChevronRight,
  ChevronDown,
  AlertTriangle,
  FileText,
  Layers,
  Calendar,
  CalendarRange,
  FileCode,
  FileJson,
  Split,
  Activity,
  GitMerge,
  ArrowRight,
  Settings,
  FileSearch,
  ArrowDown,
  CornerDownRight,
  Share2,
  ListFilter,
  ShieldAlert,
  ArchiveRestore
} from 'lucide-react';

// --- Enhanced Types ---
type NodeType = 'folder' | 'unit' | 'file';
type NodeStatus = 'success' | 'warning' | 'error' | 'neutral' | 'processing';

interface StatNode {
  name: string;
  count?: number; 
  size?: string;  
  type: NodeType;
  status: NodeStatus;
  children?: StatNode[];
}

// --- Data Generators ---

const generateUnitFiles = (unitName: string, type: string): StatNode[] => {
  const files: StatNode[] = [
    { name: 'manifest.json', type: 'file', status: 'neutral', size: '2KB' },
    { name: 'audit.log.jsonl', type: 'file', status: 'neutral', size: '15KB' },
  ];

  if (type === 'pdf') {
    files.unshift({ name: 'payload.pdf', type: 'file', status: 'neutral', size: '1.4MB' });
  } else if (type === 'docx') {
    files.unshift({ name: 'document.docx', type: 'file', status: 'neutral', size: '450KB' });
  } else if (type === 'doc') {
    files.unshift({ name: 'legacy.doc', type: 'file', status: 'neutral', size: '1.1MB' });
  } else if (type === 'xlsx') {
    files.unshift({ name: 'spreadsheet.xlsx', type: 'file', status: 'neutral', size: '820KB' });
  } else if (type === 'zip') {
    files.unshift({ name: 'archive.zip', type: 'file', status: 'neutral', size: '5.2MB' });
  } else if (type === 'image') {
    files.unshift({ name: 'image.jpg', type: 'file', status: 'neutral', size: '3.1MB' });
  } else {
    files.unshift({ name: 'unknown_blob', type: 'file', status: 'neutral', size: '12KB' });
  }
  return files;
};

const generateMockUnits = (count: number, status: NodeStatus, fileType: string = 'pdf'): StatNode[] => {
  const units: StatNode[] = [];
  const displayLimit = 3; 
  for (let i = 0; i < displayLimit && i < count; i++) {
    const id = Math.random().toString(16).slice(2, 10);
    const name = `UNIT_ff${id}`;
    units.push({
      name: name,
      type: 'unit',
      status: status,
      count: 3, 
      children: generateUnitFiles(name, fileType)
    });
  }
  if (count > displayLimit) {
    units.push({ name: `... ${count - displayLimit} more units`, type: 'file', status: 'neutral', size: '' });
  }
  return units;
};

const generateExtensionFolders = (count: number, status: NodeStatus, types: string[]): StatNode[] => {
  const folders: StatNode[] = [];
  let remaining = count;
  const avg = Math.floor(count / types.length);
  types.forEach((ext, i) => {
     if (remaining <= 0) return;
     const c = (i === types.length - 1) ? remaining : avg;
     folders.push({
       name: ext,
       type: 'folder',
       status,
       count: c,
       children: generateMockUnits(c, status, ext)
     });
     remaining -= c;
  });
  return folders;
};

// --- Daily Tree Data ---
const DAILY_TREE_DATA: StatNode = {
  name: '2025-03-04',
  count: 6025,
  type: 'folder',
  status: 'neutral',
  children: [
    {
      name: 'Exceptions',
      count: 1213,
      type: 'folder',
      status: 'error',
      children: [
        {
          name: 'Exceptions_1', count: 400, type: 'folder', status: 'error', children: [
            { name: 'Ambiguous', count: 100, type: 'folder', status: 'error', children: generateMockUnits(100, 'error', 'bin') },
            { name: 'Mixed', count: 150, type: 'folder', status: 'warning', children: generateMockUnits(150, 'warning', 'zip') },
            { name: 'Empty', count: 50, type: 'folder', status: 'warning', children: generateExtensionFolders(50, 'warning', ['pdf', 'docx']) },
            { name: 'Special', count: 100, type: 'folder', status: 'neutral', children: generateExtensionFolders(100, 'neutral', ['sig', 'p7s']) },
          ]
        },
        {
          name: 'Exceptions_2', count: 570, type: 'folder', status: 'error', children: [
            { name: 'Ambiguous', count: 50, type: 'folder', status: 'error', children: generateMockUnits(50, 'error') },
            { name: 'Mixed', count: 100, type: 'folder', status: 'warning', children: generateMockUnits(100, 'warning', 'zip') },
            { name: 'Special', count: 230, type: 'folder', status: 'neutral', children: generateExtensionFolders(230, 'neutral', ['xml', 'json']) },
            { name: 'ErConvert', count: 100, type: 'folder', status: 'error', children: generateExtensionFolders(100, 'error', ['doc', 'rtf']) },
            { name: 'ErExtract', count: 50, type: 'folder', status: 'error', children: generateExtensionFolders(50, 'error', ['zip', 'rar']) },
            { name: 'ErNormalize', count: 20, type: 'folder', status: 'error', children: generateExtensionFolders(20, 'error', ['pdf']) },
          ]
        },
        { 
          name: 'Exceptions_3', count: 243, type: 'folder', status: 'error', children: [
             { name: 'Ambiguous', count: 30, type: 'folder', status: 'error', children: generateMockUnits(30, 'error') },
             { name: 'Mixed', count: 43, type: 'folder', status: 'warning', children: generateMockUnits(43, 'warning', 'zip') },
             { name: 'Special', count: 100, type: 'folder', status: 'neutral', children: generateExtensionFolders(100, 'neutral', ['dat', 'bin']) },
             { name: 'ErConvert', count: 30, type: 'folder', status: 'error', children: generateExtensionFolders(30, 'error', ['ppt']) },
             { name: 'ErExtract', count: 20, type: 'folder', status: 'error', children: generateExtensionFolders(20, 'error', ['7z']) },
             { name: 'ErNormalize', count: 10, type: 'folder', status: 'error', children: generateExtensionFolders(10, 'error', ['pdf']) },
          ]
        }
      ]
    },
    {
      name: 'Input',
      count: 12,
      type: 'folder',
      status: 'neutral',
      children: generateExtensionFolders(12, 'neutral', ['pdf', 'docx', 'jpg', 'zip'])
    },
    {
      name: 'Rady2Merge',
      count: 3800,
      type: 'folder',
      status: 'success', // Green
      children: [
        { 
          name: 'Direct', count: 1200, type: 'folder', status: 'neutral', children: [
            { name: 'Converted', count: 0, type: 'folder', status: 'neutral', children: [] },
            { name: 'Extracted', count: 0, type: 'folder', status: 'neutral', children: [] },
            { name: 'Normalized', count: 1200, type: 'folder', status: 'success', children: generateExtensionFolders(1200, 'success', ['pdf']) },
          ]
        },
        { 
          name: 'Processed_1', count: 1000, type: 'folder', status: 'neutral', children: [
            { name: 'Converted', count: 400, type: 'folder', status: 'success', children: generateExtensionFolders(400, 'success', ['pdf']) },
            { name: 'Extracted', count: 300, type: 'folder', status: 'success', children: generateExtensionFolders(300, 'success', ['pdf']) },
            { name: 'Normalized', count: 300, type: 'folder', status: 'success', children: generateExtensionFolders(300, 'success', ['pdf']) },
          ]
        },
        { 
          name: 'Processed_2', count: 800, type: 'folder', status: 'neutral', children: [
            { name: 'Converted', count: 300, type: 'folder', status: 'success', children: generateExtensionFolders(300, 'success', ['pdf']) },
            { name: 'Extracted', count: 200, type: 'folder', status: 'success', children: generateExtensionFolders(200, 'success', ['pdf']) },
            { name: 'Normalized', count: 300, type: 'folder', status: 'success', children: generateExtensionFolders(300, 'success', ['pdf']) },
          ]
        },
        { 
          name: 'Processed_3', count: 800, type: 'folder', status: 'neutral', children: [
            { name: 'Converted', count: 300, type: 'folder', status: 'success', children: generateExtensionFolders(300, 'success', ['pdf']) },
            { name: 'Extracted', count: 200, type: 'folder', status: 'success', children: generateExtensionFolders(200, 'success', ['pdf']) },
            { name: 'Normalized', count: 300, type: 'folder', status: 'success', children: generateExtensionFolders(300, 'success', ['pdf']) },
          ]
        },
      ]
    },
    {
      name: 'Processing',
      count: 850,
      type: 'folder',
      status: 'processing',
      children: [
        { 
          name: 'Processing_1', count: 400, type: 'folder', status: 'processing', children: [
            { name: 'Convert', count: 200, type: 'folder', status: 'processing', children: generateExtensionFolders(200, 'processing', ['doc', 'docx']) },
            { name: 'Extract', count: 150, type: 'folder', status: 'processing', children: generateExtensionFolders(150, 'processing', ['zip']) },
            { name: 'Normalize', count: 50, type: 'folder', status: 'processing', children: generateExtensionFolders(50, 'processing', ['pdf']) },
          ]
        },
        { 
          name: 'Processing_2', count: 300, type: 'folder', status: 'processing', children: [
            { name: 'Convert', count: 100, type: 'folder', status: 'processing', children: generateExtensionFolders(100, 'processing', ['xls']) },
            { name: 'Extract', count: 150, type: 'folder', status: 'processing', children: generateExtensionFolders(150, 'processing', ['tar.gz']) },
            { name: 'Normalize', count: 50, type: 'folder', status: 'processing', children: generateExtensionFolders(50, 'processing', ['pdf']) },
          ]
        },
        { 
          name: 'Processing_3', count: 150, type: 'folder', status: 'processing', children: [
            { name: 'Convert', count: 50, type: 'folder', status: 'processing', children: generateExtensionFolders(50, 'processing', ['ppt']) },
            { name: 'Extract', count: 50, type: 'folder', status: 'processing', children: generateExtensionFolders(50, 'processing', ['7z']) },
            { name: 'Normalize', count: 50, type: 'folder', status: 'processing', children: generateExtensionFolders(50, 'processing', ['pdf']) },
          ]
        },
      ]
    },
    {
      name: 'Ready2Docling',
      count: 4812,
      type: 'folder',
      status: 'success',
      children: generateExtensionFolders(4812, 'success', ['pdf', 'docx', 'xlsx', 'jpeg'])
    },
    { 
      name: 'ErMerge', 
      count: 0, 
      type: 'folder', 
      status: 'error', 
      children: [
        { 
          name: 'Direct', count: 0, type: 'folder', status: 'error', children: [
            { name: 'Converted', count: 0, type: 'folder', status: 'error', children: [] },
            { name: 'Extracted', count: 0, type: 'folder', status: 'error', children: [] },
            { name: 'Normalized', count: 0, type: 'folder', status: 'error', children: [] },
          ]
        },
        { 
          name: 'Processed_1', count: 0, type: 'folder', status: 'error', children: [
            { name: 'Converted', count: 0, type: 'folder', status: 'error', children: [] },
            { name: 'Extracted', count: 0, type: 'folder', status: 'error', children: [] },
            { name: 'Normalized', count: 0, type: 'folder', status: 'error', children: [] },
          ]
        },
        { 
          name: 'Processed_2', count: 0, type: 'folder', status: 'error', children: [
            { name: 'Converted', count: 0, type: 'folder', status: 'error', children: [] },
            { name: 'Extracted', count: 0, type: 'folder', status: 'error', children: [] },
            { name: 'Normalized', count: 0, type: 'folder', status: 'error', children: [] },
          ]
        },
        { 
          name: 'Processed_3', count: 0, type: 'folder', status: 'error', children: [
            { name: 'Converted', count: 0, type: 'folder', status: 'error', children: [] },
            { name: 'Extracted', count: 0, type: 'folder', status: 'error', children: [] },
            { name: 'Normalized', count: 0, type: 'folder', status: 'error', children: [] },
          ]
        },
      ]
    },
    {
      name: 'Total Exceptions',
      count: 1213,
      type: 'folder',
      status: 'error', 
      children: [
        {
          name: 'Exceptions_1', count: 400, type: 'folder', status: 'error', children: [
            { name: 'Ambiguous', count: 100, type: 'folder', status: 'error', children: generateMockUnits(100, 'error', 'bin') },
            { name: 'Mixed', count: 150, type: 'folder', status: 'warning', children: generateMockUnits(150, 'warning', 'zip') },
            { name: 'Empty', count: 50, type: 'folder', status: 'warning', children: generateExtensionFolders(50, 'warning', ['pdf', 'docx']) },
            { name: 'Special', count: 100, type: 'folder', status: 'neutral', children: generateExtensionFolders(100, 'neutral', ['sig', 'p7s']) },
          ]
        },
        {
          name: 'Exceptions_2', count: 570, type: 'folder', status: 'error', children: [
            { name: 'Ambiguous', count: 50, type: 'folder', status: 'error', children: generateMockUnits(50, 'error') },
            { name: 'Mixed', count: 100, type: 'folder', status: 'warning', children: generateMockUnits(100, 'warning', 'zip') },
            { name: 'Special', count: 230, type: 'folder', status: 'neutral', children: generateExtensionFolders(230, 'neutral', ['xml', 'json']) },
            { name: 'ErConvert', count: 100, type: 'folder', status: 'error', children: generateExtensionFolders(100, 'error', ['doc', 'rtf']) },
            { name: 'ErExtract', count: 50, type: 'folder', status: 'error', children: generateExtensionFolders(50, 'error', ['zip', 'rar']) },
            { name: 'ErNormalize', count: 20, type: 'folder', status: 'error', children: generateExtensionFolders(20, 'error', ['pdf']) },
          ]
        },
        { 
          name: 'Exceptions_3', count: 243, type: 'folder', status: 'error', children: [
             { name: 'Ambiguous', count: 30, type: 'folder', status: 'error', children: generateMockUnits(30, 'error') },
             { name: 'Mixed', count: 43, type: 'folder', status: 'warning', children: generateMockUnits(43, 'warning', 'zip') },
             { name: 'Special', count: 100, type: 'folder', status: 'neutral', children: generateExtensionFolders(100, 'neutral', ['dat', 'bin']) },
             { name: 'ErConvert', count: 30, type: 'folder', status: 'error', children: generateExtensionFolders(30, 'error', ['ppt']) },
             { name: 'ErExtract', count: 20, type: 'folder', status: 'error', children: generateExtensionFolders(20, 'error', ['7z']) },
             { name: 'ErNormalize', count: 10, type: 'folder', status: 'error', children: generateExtensionFolders(10, 'error', ['pdf']) },
          ]
        }
      ]
    }
  ]
};

// --- Sub-Components ---

const ArrowDefs = () => (
   <svg className="absolute w-0 h-0">
      <defs>
         <marker id="arrow-green" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="#10b981" />
         </marker>
         <marker id="arrow-blue" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="#3b82f6" />
         </marker>
         <marker id="arrow-red" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="#f43f5e" />
         </marker>
         <marker id="arrow-purple" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="#d8b4fe" />
         </marker>
         <marker id="arrow-yellow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="#facc15" />
         </marker>
         <marker id="arrow-indigo" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="#818cf8" />
         </marker>
         <marker id="arrow-slate" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="#cbd5e1" />
         </marker>
         {/* Gradients for Dash Flow */}
         <linearGradient id="grad-green" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="1" />
         </linearGradient>
      </defs>
   </svg>
);

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0];
    return (
      <div className="bg-white/95 backdrop-blur-md p-4 rounded-xl shadow-xl border border-slate-200/60 text-xs">
         <p className="font-bold text-slate-700 mb-1">{data.name || label}</p>
         <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{background: data.fill || data.color}} />
            <span className="font-mono font-bold text-slate-500">{data.value.toLocaleString()} units</span>
         </div>
         {data.payload.desc && <p className="text-[10px] text-slate-400 mt-2 max-w-[120px]">{data.payload.desc}</p>}
      </div>
    );
  }
  return null;
};

const RecursiveTree: React.FC<{ node: StatNode; totalUnits: number; depth?: number }> = ({ node, totalUnits, depth = 0 }) => {
  const [isOpen, setIsOpen] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;
  
  // Section Logic: Top-level children (Depth 1) are treated as "Sections" with full background cards.
  const isSection = depth === 1;

  const getSectionContainerStyle = (status: NodeStatus) => {
    if (!isSection) return '';
    switch(status) {
      case 'error': return 'bg-rose-50/50 border border-rose-100 rounded-[20px] mb-3 overflow-hidden pb-1';
      case 'warning': return 'bg-amber-50/50 border border-amber-100 rounded-[20px] mb-3 overflow-hidden pb-1';
      case 'success': return 'bg-emerald-50/50 border border-emerald-100 rounded-[20px] mb-3 overflow-hidden pb-1';
      case 'processing': return 'bg-blue-50/50 border border-blue-100 rounded-[20px] mb-3 overflow-hidden pb-1';
      case 'neutral': return 'bg-slate-100 border border-slate-200 rounded-[20px] mb-3 overflow-hidden pb-1 opacity-90';
      default: return 'bg-white border border-slate-200 rounded-[20px] mb-3 overflow-hidden pb-1';
    }
  };

  const getRowStyle = (status: NodeStatus) => {
    // If it's a section header, use a transparent/minimal style to blend with container
    if (isSection) {
        return 'mx-2 mt-2 px-3 py-2 rounded-xl transition-all hover:bg-black/5 border border-transparent';
    }
    
    // Standard nested items
    switch(status) {
      case 'error': return 'text-rose-600 bg-rose-50 border-rose-100';
      case 'warning': return 'text-amber-600 bg-amber-50 border-amber-100';
      case 'success': return 'text-emerald-600 bg-emerald-50 border-emerald-100';
      case 'processing': return 'text-blue-600 bg-blue-50 border-blue-100';
      default: return 'text-slate-600 bg-white border-slate-100 hover:bg-slate-50';
    }
  };

  const getTextColors = (status: NodeStatus) => {
     if (isSection) {
        switch(status) {
           case 'error': return 'text-rose-700';
           case 'warning': return 'text-amber-700';
           case 'success': return 'text-emerald-700';
           case 'processing': return 'text-blue-700';
           case 'neutral': return 'text-slate-600';
           default: return 'text-slate-700';
        }
     }
     return ''; // Default inherits or set by getRowStyle for nested
  };

  const pct = node.count !== undefined && totalUnits > 0 ? ((node.count / totalUnits) * 100).toFixed(1) : 0;
  const containerClass = getSectionContainerStyle(node.status);
  const rowClass = getRowStyle(node.status);
  const textColorClass = getTextColors(node.status);

  return (
    <div className={`select-none ${containerClass}`}>
      <div 
        onClick={() => hasChildren && setIsOpen(!isOpen)}
        className={`flex items-center gap-3 cursor-pointer ${rowClass} ${textColorClass}`}
        style={{ marginLeft: isSection ? '0px' : `${depth * 24}px` }}
      >
        <div className="flex items-center gap-2 flex-1">
          {hasChildren ? (
            isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />
          ) : (
            <span className="w-4" />
          )}
          
          {node.type === 'file' ? (
            <FileText size={16} className="opacity-70" />
          ) : node.type === 'unit' ? (
            <Box size={16} className="opacity-70" />
          ) : (
            isOpen ? <FolderOpen size={18} className="opacity-80" /> : <Folder size={18} className="opacity-80" />
          )}
          
          <span className="font-mono text-sm font-bold tracking-tight">{node.name}</span>
        </div>
        
        {node.size && (
           <span className="text-[10px] font-mono text-slate-400 bg-white/50 px-1.5 rounded">{node.size}</span>
        )}

        {node.count !== undefined && (
          <div className="flex items-center gap-3">
             <div className="w-16 h-1.5 bg-black/5 rounded-full overflow-hidden">
                <div className="h-full bg-current opacity-40" style={{ width: `${pct}%` }} />
             </div>
             <div className="px-2 py-0.5 bg-white/50 rounded-md text-xs font-bold border border-black/5 min-w-[3rem] text-center text-slate-700">
               {node.count}
             </div>
          </div>
        )}
      </div>

      {isOpen && hasChildren && (
        <div className={`${isSection ? 'px-2' : 'border-l-2 border-slate-100 ml-[15px] pl-1'}`}>
          {node.children!.map((child, idx) => (
            <RecursiveTree key={idx} node={child} totalUnits={totalUnits} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

const ColumnHeader = ({ title }: { title: string }) => (
  <div className="text-center py-2 px-4 bg-slate-900 text-white rounded-xl text-xs font-black uppercase tracking-widest shadow-lg shadow-slate-200 w-full">
    {title}
  </div>
);

const CycleSection = ({ title, connector, column }: any) => (
  <div className="flex flex-col gap-6">
    <div className="relative">
       <ColumnHeader title={title} />
    </div>
    <div className="flex gap-16">
      {connector}
      {column}
    </div>
  </div>
);

// --- Circuit Path Generators (Strict Orthogonal) ---

// Generate a Manhattan path (Horizontal -> Vertical -> Horizontal)
const getCircuitPath = (x1: number, y1: number, x2: number, y2: number) => {
  const r = 12; // Corner radius
  const midX = (x1 + x2) / 2;
  
  // Directions for sweep flags in Arc commands
  const dy = y2 - y1;
  const sigY = Math.sign(dy);
  
  // If points are aligned horizontally, just draw a line
  if (Math.abs(dy) < 1) {
      return `M ${x1} ${y1} L ${x2} ${y2}`;
  }

  // Calculate safe radius
  const safeR = Math.min(r, Math.abs(dy)/2, Math.abs(x2-x1)/2);
  
  // Path construction:
  // 1. Move to Start
  // 2. Line to first corner start
  // 3. Curve to vertical
  // 4. Line to second corner start
  // 5. Curve to horizontal
  // 6. Line to End
  
  return `M ${x1} ${y1} 
          L ${midX - safeR} ${y1} 
          Q ${midX} ${y1} ${midX} ${y1 + sigY * safeR}
          L ${midX} ${y2 - sigY * safeR}
          Q ${midX} ${y2} ${midX + safeR} ${y2}
          L ${x2} ${y2}`;
};

const PipelineConnector: React.FC<{
  source: string;
  isRecursive: boolean;
  isFinal?: boolean;
}> = ({ source, isRecursive, isFinal }) => {
  
  // Common connection port style
  const Port = ({ className }: { className?: string }) => (
      <div className={`w-2.5 h-2.5 rounded-full border-2 border-white shadow-sm absolute z-30 top-1/2 -translate-y-1/2 ${className}`}></div>
  );

  const NodeCard = ({ title, sub, icon: Icon, color, className, children }: any) => (
      <div className={`bg-white border rounded-xl p-2 flex items-center gap-2 shadow-sm relative z-10 ${className}`}>
          <div className={`p-1.5 rounded-lg ${color.bg} ${color.text} shrink-0`}>
              <Icon size={12} />
          </div>
          <div className="flex-1 min-w-0">
              <div className={`text-[9px] font-black uppercase tracking-tight ${color.textBold}`}>{title}</div>
              <div className={`text-[8px] font-medium leading-none mt-0.5 ${color.sub}`}>{sub}</div>
          </div>
          {children}
      </div>
  );

  if (isFinal) {
    return (
      <div className="flex flex-col items-center gap-12 w-[160px] pt-6 relative">
          {/* SVG Layer */}
          <svg className="absolute top-0 left-[-600px] w-[820px] h-[800px] pointer-events-none z-0 overflow-visible">
               <defs>
                   <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
                       <feDropShadow dx="0" dy="1" stdDeviation="1" floodColor="#000000" floodOpacity="0.1"/>
                   </filter>
               </defs>
               
               {/* 
                 FINAL MERGE ROUTES 
                 Target: Merging Ready (x=680, y=55 relative to container start)
                 Source 1 (Cycle 1 Rady2Merge): x=14, y=105
                 Source 2 (Cycle 2 Rady2Merge): x=474, y=105
               */}
               
               <path d={getCircuitPath(14, 105, 680, 55)} fill="none" stroke="#10b981" strokeWidth="2" markerEnd="url(#arrow-green)" filter="url(#shadow)" className="animate-[pulse_3s_ease-in-out_infinite]" />
               <path d={getCircuitPath(474, 105, 680, 55)} fill="none" stroke="#10b981" strokeWidth="2" markerEnd="url(#arrow-green)" filter="url(#shadow)" className="animate-[pulse_3s_ease-in-out_infinite]" />

               {/* 
                 EXCEPTION MERGE ROUTES 
                 Target: Merging Exception (x=680, y=390)
                 Source 1 (Cycle 1 Exceptions): x=34, y=285
                 Source 2 (Cycle 2 Exceptions): x=494, y=425
               */}
               <path d={getCircuitPath(34, 285, 680, 390)} fill="none" stroke="#f43f5e" strokeWidth="2" markerEnd="url(#arrow-red)" filter="url(#shadow)" strokeDasharray="4 2" />
               <path d={getCircuitPath(494, 425, 680, 390)} fill="none" stroke="#f43f5e" strokeWidth="2" markerEnd="url(#arrow-red)" filter="url(#shadow)" strokeDasharray="4 2" />

               {/* Outputs from Final Blocks */}
               {/* Ready -> Success */}
               <path d="M 760 55 L 820 55" fill="none" stroke="#10b981" strokeWidth="2" markerEnd="url(#arrow-green)" />
               {/* Ready -> Fail (ErMerge is lower, approx y=155 relative) */}
               <path d={getCircuitPath(760, 55, 820, 200)} fill="none" stroke="#f43f5e" strokeWidth="2" markerEnd="url(#arrow-red)" />
               
               {/* Exception -> Total */}
               <path d="M 760 390 L 820 390" fill="none" stroke="#f43f5e" strokeWidth="2" markerEnd="url(#arrow-red)" />

          </svg>

          <div className="absolute top-0 left-1/2 -translate-x-1/2 flex items-center gap-1.5 opacity-60">
            <Layers size={10} className="text-slate-400" />
            <span className="text-[9px] font-mono font-bold text-slate-500">All Cycles</span>
          </div>

          {/* Block 1: Merging Ready */}
          <div className="w-full relative mt-4">
             <NodeCard 
                title="Merging Ready" 
                sub="Direct + Processed_N" 
                icon={GitMerge} 
                color={{bg: 'bg-emerald-100', text: 'text-emerald-600', textBold: 'text-emerald-800', sub: 'text-emerald-500'}} 
                className="border-emerald-200 bg-emerald-50/50"
             >
                <Port className="bg-emerald-500 -left-1.5" />
                <Port className="bg-emerald-500 -right-1.5" />
             </NodeCard>
          </div>

          {/* Block 2: Merging Exceptions */}
          <div className="w-full relative mt-[300px]">
             <NodeCard 
                title="Merging Exception" 
                sub="Exceptions_1..N" 
                icon={ShieldAlert} 
                color={{bg: 'bg-rose-100', text: 'text-rose-600', textBold: 'text-rose-800', sub: 'text-rose-500'}} 
                className="border-rose-200 bg-rose-50/50"
             >
                <Port className="bg-rose-500 -left-1.5" />
                <Port className="bg-rose-500 -right-1.5" />
             </NodeCard>
          </div>

          <div className="absolute top-4 bottom-8 left-1/2 w-px bg-slate-200 -z-0 border-l border-dashed border-slate-300"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-12 w-[160px] pt-6 relative">
       {/* Source Indicator */}
       <div className="absolute top-0 left-1/2 -translate-x-1/2 flex items-center gap-1.5 opacity-60">
          <FolderOpen size={10} className="text-slate-400" />
          <span className="text-[9px] font-mono font-bold text-slate-500">{source}</span>
       </div>

       {/* Step 1: Processing */}
       {isRecursive && (
         <div className="w-full relative z-10 mt-4">
             <NodeCard 
                title="Processing" 
                sub="Conv • Ext • Norm" 
                icon={Settings} 
                color={{bg: 'bg-blue-100', text: 'text-blue-600', textBold: 'text-blue-800', sub: 'text-blue-500'}} 
                className="border-blue-200 bg-blue-50/50"
             >
                <Port className="bg-blue-500 -left-1.5" />
                <Port className="bg-blue-500 -right-1.5" />
             </NodeCard>
             
             {/* Internal Flow: Processing -> Classify */}
             <svg className="absolute left-1/2 -translate-x-1/2 top-full w-6 h-12 overflow-visible z-0">
               <line x1="3" y1="0" x2="3" y2="48" stroke="#3b82f6" strokeWidth="2" strokeDasharray="3 3" />
               <polygon points="3,48 0,44 6,44" fill="#3b82f6" />
             </svg>
         </div>
       )}

       {/* Step 2: Classification */}
       <div className={`w-full relative z-10 ${!isRecursive ? 'mt-4' : ''}`}>
         <NodeCard 
            title="Classification" 
            sub="Magic Bytes & Type" 
            icon={FileSearch} 
            color={{bg: 'bg-purple-100', text: 'text-purple-600', textBold: 'text-purple-800', sub: 'text-purple-500'}} 
            className="border-purple-200 bg-purple-50/50"
         >
            {/* Input Port if not recursive (direct from source) */}
            {!isRecursive && <Port className="bg-purple-500 -left-1.5" />}
            
            {/* Internal Output Port */}
            <div className="w-1.5 h-1.5 rounded-full bg-purple-400 absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2"></div>
         </NodeCard>

         {/* Internal Flow: Classify -> Distribute */}
         <svg className="absolute left-1/2 -translate-x-1/2 top-full w-6 h-12 overflow-visible z-0">
            <line x1="3" y1="0" x2="3" y2="48" stroke="#facc15" strokeWidth="2" strokeDasharray="3 3" />
            <polygon points="3,48 0,44 6,44" fill="#facc15" />
         </svg>
       </div>

       {/* Step 3: Distribution */}
       <div className="w-full relative z-10 flex flex-col items-start">
          <div className="w-[70%] self-start relative">
             <NodeCard 
                title="Distribution" 
                sub="Sort to Targets" 
                icon={Share2} 
                color={{bg: 'bg-slate-200', text: 'text-slate-600', textBold: 'text-slate-700', sub: 'text-slate-500'}} 
                className="border-slate-300 bg-slate-50/50"
             >
                <div className="w-1.5 h-1.5 rounded-full bg-yellow-400 absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2"></div>
                <Port className="bg-slate-500 -right-1.5" />
             </NodeCard>
          </div>
          
          {/* Output Arrows (Local to this Block) */}
          <svg className="absolute top-1/2 left-[70%] w-[200px] h-[600px] pointer-events-none z-0 overflow-visible" style={{top: '50%', transform: 'translateY(-50%)'}}>
             <defs>
                <filter id="line-shadow" x="-20%" y="-20%" width="140%" height="140%">
                   <feDropShadow dx="0" dy="1" stdDeviation="1" floodColor="#000000" floodOpacity="0.1"/>
                </filter>
             </defs>
             {/* 
                Paths differ for Recursive vs Non-Recursive because the relative vertical position of the Distribution block 
                changes compared to the target Cycle Column blocks.
                We use getCircuitPath with relative coordinates. 
                Origin (0,0) is center-right of Distribution block.
             */}
             
             {isRecursive ? (
                <>
                  {/* Green: Up to Rady2Merge (-93px) */}
                  <path d={getCircuitPath(0, 0, 100, -93)} fill="none" stroke="#10b981" strokeWidth="2" markerEnd="url(#arrow-green)" filter="url(#line-shadow)" />
                  {/* Blue: Down to Processing (+63px) */}
                  <path d={getCircuitPath(0, 0, 100, 63)} fill="none" stroke="#3b82f6" strokeWidth="2" markerEnd="url(#arrow-blue)" filter="url(#line-shadow)" />
                  {/* Red: Deep Down to Exceptions (+219px) */}
                  <path d={getCircuitPath(0, 0, 100, 219)} fill="none" stroke="#f43f5e" strokeWidth="2" markerEnd="url(#arrow-red)" filter="url(#line-shadow)" />
                </>
             ) : (
                <>
                  {/* Green: Up to Rady2Merge (-27px) */}
                  <path d={getCircuitPath(0, 0, 100, -27)} fill="none" stroke="#10b981" strokeWidth="2" markerEnd="url(#arrow-green)" filter="url(#line-shadow)" />
                  {/* Blue: Down to Processing (+129px) */}
                  <path d={getCircuitPath(0, 0, 100, 129)} fill="none" stroke="#3b82f6" strokeWidth="2" markerEnd="url(#arrow-blue)" filter="url(#line-shadow)" />
                  {/* Red: Deep Down to Exceptions (+285px) */}
                  <path d={getCircuitPath(0, 0, 100, 285)} fill="none" stroke="#f43f5e" strokeWidth="2" markerEnd="url(#arrow-red)" filter="url(#line-shadow)" />
                </>
             )}
          </svg>
       </div>

       <div className="absolute top-4 bottom-8 left-1/2 w-px bg-slate-200 -z-0 border-l border-dashed border-slate-300"></div>
    </div>
  );
};

const CycleColumn = ({ cycle, title, merge, process, excep, scaleFactor, hideHeader }: any) => {
  const getMergeLabel = () => {
    if (cycle === 1) return 'Direct';
    return `Processed_${cycle - 1}${cycle === 3 ? '+' : ''}`;
  };
  
  // Connection Port Component
  const Port = ({ className }: { className?: string }) => (
      <div className={`w-2.5 h-2.5 rounded-full border-2 border-white shadow-sm absolute z-30 top-1/2 -translate-y-1/2 ${className}`}></div>
  );

  return (
    <div className="flex flex-col gap-4 w-[220px]">
       {!hideHeader && <ColumnHeader title={title} />}
       
       {/* Ready2Merge Block */}
       <div className="bg-emerald-50 rounded-2xl p-4 border border-emerald-100 shadow-sm hover:shadow-md transition-all relative mt-4 group">
          <Port className="bg-emerald-500 -left-1.5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <Port className="bg-emerald-500 -right-1.5" /> {/* Output Port */}
          
          <div className="absolute -top-3 left-4 bg-emerald-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-widest">Ready2Merge</div>
          <div className="flex items-center justify-between mb-2"><GitMerge size={16} className="text-emerald-500" /><span className="text-[10px] font-black text-emerald-400">{((merge.total / (merge.total + process.total + excep.total)) * 100).toFixed(1)}%</span></div>
          <div className="text-2xl font-black text-emerald-900 mb-1">{merge.total.toLocaleString()}</div>
          <div className="text-xs font-bold text-emerald-600 uppercase tracking-tight mb-3">{getMergeLabel()}</div>
          <div className="space-y-1.5 border-t border-emerald-200/50 pt-2">
             {merge.items.map((item: any, i: number) => (
               <div key={i} className="flex justify-between items-center text-[10px]"><span className="font-bold text-emerald-800">{item.name}</span><span className="font-mono text-emerald-600/70">{Math.floor(item.val * scaleFactor).toLocaleString()}</span></div>
             ))}
          </div>
       </div>

       {/* Processing Block */}
       <div className="bg-blue-50 rounded-2xl p-4 border border-blue-100 shadow-sm hover:shadow-md transition-all relative group">
          <Port className="bg-blue-500 -left-1.5 opacity-0 group-hover:opacity-100 transition-opacity" />
          
          <div className="absolute -top-3 left-4 bg-blue-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-widest">Processing</div>
          <div className="flex items-center justify-between mb-2"><Split size={16} className="text-blue-500" /><span className="text-[10px] font-black text-blue-400">{((process.total / (merge.total + process.total + excep.total)) * 100).toFixed(1)}%</span></div>
          <div className="text-2xl font-black text-blue-900 mb-1">{process.total.toLocaleString()}</div>
          <div className="text-xs font-bold text-blue-600 uppercase tracking-tight mb-3">Processing_{cycle}</div>
          <div className="space-y-1.5 border-t border-blue-200/50 pt-2">
             {process.items.map((item: any, i: number) => (
               <div key={i} className="flex justify-between items-center text-[10px]"><span className="font-bold text-blue-800">{item.name}</span><span className="font-mono text-blue-600/70">{Math.floor(item.val * scaleFactor).toLocaleString()}</span></div>
             ))}
          </div>
       </div>

       {/* Exceptions Block */}
       <div className="bg-rose-50 rounded-2xl p-4 border border-rose-100 shadow-sm hover:shadow-md transition-all relative group">
          <Port className="bg-rose-500 -left-1.5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <Port className="bg-rose-500 -right-1.5" /> {/* Output Port */}

          <div className="absolute -top-3 left-4 bg-rose-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-widest">Exceptions</div>
          <div className="flex items-center justify-between mb-2"><AlertTriangle size={16} className="text-rose-500" /><span className="text-[10px] font-black text-rose-400">{((excep.total / (merge.total + process.total + excep.total)) * 100).toFixed(1)}%</span></div>
          <div className="text-2xl font-black text-rose-900 mb-1">{excep.total.toLocaleString()}</div>
          <div className="text-xs font-bold text-rose-600 uppercase tracking-tight mb-3">Exceptions_{cycle}</div>
          <div className="space-y-1.5 border-t border-rose-200/50 pt-2">
             {excep.items.map((item: any, i: number) => (
               <div key={i} className="flex justify-between items-center text-[10px]"><span className="font-bold text-rose-800">{item.name}</span><span className="font-mono text-rose-600/70">{Math.floor(item.val * scaleFactor).toLocaleString()}</span></div>
             ))}
          </div>
       </div>
    </div>
  );
};

// --- Statistics Component ---

const Statistics: React.FC = () => {
  const [viewMode, setViewMode] = useState<'single' | 'range'>('single');
  const [singleDate, setSingleDate] = useState<string>('2025-03-04');
  const [rangeDate, setRangeDate] = useState({ start: '2025-03-01', end: '2025-03-04' });

  const scaleFactor = viewMode === 'range' ? 3.4 : 1;
  const totalUnits = Math.floor(6025 * scaleFactor);

  const logicRoutes = [
    { name: 'Direct', value: Math.floor(1200 * scaleFactor), color: '#34d399', desc: 'No processing needed' },
    { name: 'Converted', value: Math.floor(1000 * scaleFactor), color: '#3b82f6', desc: 'From Office/Legacy' },
    { name: 'Extracted', value: Math.floor(700 * scaleFactor), color: '#fbbf24', desc: 'From Archives' },
    { name: 'Normalized', value: Math.floor(900 * scaleFactor), color: '#a78bfa', desc: 'Standardized PDF' },
  ];

  const exceptionBreakdown = [
    { name: 'Ambiguous', value: Math.floor(180 * scaleFactor), color: '#f43f5e' },
    { name: 'Mixed', value: Math.floor(293 * scaleFactor), color: '#fb7185' },
    { name: 'ErConvert', value: Math.floor(130 * scaleFactor), color: '#e11d48' },
    { name: 'Empty', value: Math.floor(80 * scaleFactor), color: '#fda4af' },
    { name: 'Special', value: Math.floor(430 * scaleFactor), color: '#94a3b8' },
  ];

  const readyBreakdown = [
    { name: 'PDF (Text)', value: Math.floor(1300 * scaleFactor), color: '#059669' },
    { name: 'PDF (Scan)', value: Math.floor(1200 * scaleFactor), color: '#10b981' },
    { name: 'PDF (Mixed)', value: Math.floor(500 * scaleFactor), color: '#34d399' },
    { name: 'DOCX', value: Math.floor(800 * scaleFactor), color: '#3b82f6' },
    { name: 'XLSX', value: Math.floor(600 * scaleFactor), color: '#6366f1' },
    { name: 'Images', value: Math.floor(412 * scaleFactor), color: '#f472b6' },
  ];

  const cycleData = {
    c1: {
      merge: { total: Math.floor(1200 * scaleFactor), items: [{name: 'Direct', val: 1200}]},
      process: { total: Math.floor(400 * scaleFactor), items: [{name: 'Convert', val: 200}, {name: 'Extract', val: 150}, {name: 'Normalize', val: 50}]},
      excep: { total: Math.floor(400 * scaleFactor), items: [{name: 'Ambiguous', val: 100}, {name: 'Mixed', val: 150}, {name: 'Empty', val: 50}, {name: 'Special', val: 100}]}
    },
    c2: {
      merge: { total: Math.floor(1000 * scaleFactor), items: [{name: 'Converted', val: 400}, {name: 'Extracted', val: 300}, {name: 'Normalized', val: 300}]},
      process: { total: Math.floor(300 * scaleFactor), items: [{name: 'Convert', val: 100}, {name: 'Extract', val: 150}, {name: 'Normalize', val: 50}]},
      excep: { total: Math.floor(570 * scaleFactor), items: [{name: 'Ambiguous', val: 50}, {name: 'Mixed', val: 100}, {name: 'Special', val: 230}, {name: 'ErConvert', val: 100}, {name: 'ErExtract', val: 50}, {name: 'ErNormalize', val: 20}]}
    },
    c3: {
      merge: { total: Math.floor(1600 * scaleFactor), items: [{name: 'Converted', val: 600}, {name: 'Extracted', val: 400}, {name: 'Normalized', val: 600}]},
      process: { total: Math.floor(150 * scaleFactor), items: [{name: 'Convert', val: 50}, {name: 'Extract', val: 50}, {name: 'Normalize', val: 50}]},
      excep: { total: Math.floor(243 * scaleFactor), items: [{name: 'Ambiguous', val: 30}, {name: 'Mixed', val: 43}, {name: 'Special', val: 100}, {name: 'ErConvert', val: 30}, {name: 'ErExtract', val: 20}, {name: 'ErNormalize', val: 10}]}
    },
    final: {
      ready: { total: Math.floor(4812 * scaleFactor), items: [{name: 'PDF (Mixed)', val: 500}, {name: 'PDF (Scan)', val: 1200}, {name: 'PDF (Text)', val: 1300}, {name: 'DOCX', val: 800}, {name: 'XLSX', val: 600}, {name: 'Images', val: 412}]},
      er_merge: { total: 0, items: []}
    }
  };

  const currentTreeData = useMemo(() => {
    const scaleNode = (node: StatNode): StatNode => {
      const isRoot = node.name === '2025-03-04' || node.name.includes(' - ');
      const newName = isRoot && viewMode === 'range' ? `${rangeDate.start} - ${rangeDate.end}` : node.name;
      return {
        ...node,
        name: newName,
        count: node.count !== undefined ? Math.floor(node.count * scaleFactor) : undefined,
        children: node.children?.map(scaleNode)
      };
    };
    return scaleNode(DAILY_TREE_DATA);
  }, [scaleFactor, viewMode, rangeDate]);

  return (
    <div className="space-y-8 animate-in fade-in duration-700 pb-20">
      <ArrowDefs />

      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-6 rounded-[32px] border border-slate-200 shadow-sm">
        <div>
          <h2 className="text-2xl font-black text-slate-800 tracking-tight">System Analytics</h2>
          <p className="text-slate-500 font-medium text-sm">Root: /final_preprocessing/Data</p>
        </div>
        <div className="flex flex-col items-end gap-3">
           <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
              <button onClick={() => setViewMode('single')} className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${viewMode === 'single' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>Single Date</button>
              <button onClick={() => setViewMode('range')} className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${viewMode === 'range' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>Date Range</button>
           </div>
           <div className="flex items-center gap-3">
            {viewMode === 'single' ? (
              <div className="flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-2xl border border-slate-200">
                <Calendar size={18} className="text-slate-500" />
                <select value={singleDate} onChange={(e) => setSingleDate(e.target.value)} className="bg-transparent border-none outline-none text-sm font-bold text-slate-700 min-w-[120px]">
                  <option value="2025-03-04">2025-03-04</option>
                  <option value="2025-03-03">2025-03-03</option>
                </select>
              </div>
            ) : (
               <div className="flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-2xl border border-slate-200">
                  <CalendarRange size={18} className="text-slate-500" />
                  <input type="date" value={rangeDate.start} onChange={(e) => setRangeDate({...rangeDate, start: e.target.value})} className="bg-transparent border-none outline-none text-sm font-bold text-slate-700 w-[110px]" />
                  <span className="text-slate-400 font-bold">-</span>
                  <input type="date" value={rangeDate.end} onChange={(e) => setRangeDate({...rangeDate, end: e.target.value})} className="bg-transparent border-none outline-none text-sm font-bold text-slate-700 w-[110px]" />
               </div>
            )}
            <div className="px-4 py-2 bg-slate-900 text-white rounded-2xl text-xs font-black uppercase whitespace-nowrap">Total: {totalUnits.toLocaleString()} Units</div>
          </div>
        </div>
      </div>

      {/* 1. DETAILED UNIT ROUTING FLOW */}
      <div className="bg-white rounded-[32px] border border-slate-200 p-8 shadow-sm overflow-hidden">
        <h3 className="font-bold text-slate-800 mb-8 flex items-center gap-2 text-lg">
          <Activity size={20} className="text-blue-500" />
          Detailed Multi-Cycle Cascade
        </h3>
        
        <div className="overflow-x-auto pb-4 custom-scrollbar">
          <div className="flex gap-4 min-w-max items-start">
            
            {/* Input Column - Separate Group */}
            <div className="flex flex-col gap-6">
                <ColumnHeader title="Data Entry" />
                <div className="flex flex-col gap-4 w-[160px]">
                   <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 shadow-sm relative mt-4 flex flex-col justify-between h-[140px]">
                      <div className="w-2.5 h-2.5 rounded-full border-2 border-white shadow-sm bg-slate-500 absolute top-1/2 -right-1.5 -translate-y-1/2 z-10" />
                      
                      <div className="absolute -top-3 left-4 bg-slate-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-widest">Entry</div>
                      <div className="flex items-center justify-between mb-2">
                         <FolderOpen size={16} className="text-slate-400" />
                         <span className="text-[10px] font-black text-slate-400">100%</span>
                      </div>
                      <div className="text-3xl font-black text-slate-800 mb-1">{Math.floor(12 * scaleFactor).toLocaleString()}</div>
                      <div className="text-xs font-bold text-slate-500 uppercase">Raw Input</div>
                   </div>
                </div>
            </div>

            {/* Cycle 1 Group */}
            <CycleSection 
                title="Cycle 1"
                connector={
                    <PipelineConnector 
                       source="Input"
                       isRecursive={false}
                    />
                }
                column={
                    <CycleColumn 
                      cycle={1} 
                      title="Cycle 1"
                      merge={cycleData.c1.merge} 
                      process={cycleData.c1.process} 
                      excep={cycleData.c1.excep} 
                      scaleFactor={scaleFactor}
                      hideHeader
                    />
                }
            />

            {/* Cycle 2 Group */}
            <CycleSection 
                title="Cycle 2"
                connector={
                    <PipelineConnector 
                       source="Processing_1"
                       isRecursive={true}
                    />
                }
                column={
                    <CycleColumn 
                      cycle={2} 
                      title="Cycle 2"
                      merge={cycleData.c2.merge} 
                      process={cycleData.c2.process} 
                      excep={cycleData.c2.excep} 
                      scaleFactor={scaleFactor}
                      hideHeader
                    />
                }
            />

            {/* Final Assembly Group */}
            <CycleSection 
                title="Final Assembly"
                connector={
                    <PipelineConnector 
                       source="Processing_2"
                       isRecursive={true}
                       isFinal={true}
                    />
                }
                column={
                    <div className="flex flex-col gap-4 w-[240px]">
                       {/* Ready2Docling Card */}
                       <div className="bg-emerald-50 rounded-2xl p-4 border border-emerald-100 shadow-sm relative mt-4">
                          {/* Connection Port */}
                          <div className="w-2.5 h-2.5 rounded-full border-2 border-white shadow-sm bg-emerald-500 absolute top-1/2 -left-1.5 -translate-y-1/2 z-10" />
                          
                          <div className="absolute -top-3 left-4 bg-emerald-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-widest">Ready2Docling</div>
                          <div className="flex items-center justify-between mb-4">
                             <CheckCircle2 size={16} className="text-emerald-500" />
                             <span className="text-[10px] font-black text-emerald-400">{((cycleData.final.ready.total / totalUnits) * 100).toFixed(1)}%</span>
                          </div>
                          <div className="text-3xl font-black text-emerald-900 mb-1">{cycleData.final.ready.total.toLocaleString()}</div>
                          <div className="text-xs font-bold text-emerald-600 uppercase tracking-tight mb-4">Ready2Docling</div>
                          <div className="space-y-1.5 border-t border-emerald-200/50 pt-3">
                             {cycleData.final.ready.items.map((item, idx) => (
                                <div key={idx} className="flex justify-between items-center text-[10px]">
                                   <span className="font-bold text-emerald-800">{item.name}</span>
                                   <div className="flex items-center gap-2">
                                      <span className="font-mono text-emerald-600/70">{item.val.toLocaleString()}</span>
                                      <div className="w-8 h-1 bg-emerald-200 rounded-full overflow-hidden">
                                         <div className="h-full bg-emerald-500" style={{width: `${(item.val / cycleData.final.ready.total) * 100}%`}} />
                                      </div>
                                   </div>
                                </div>
                             ))}
                          </div>
                       </div>

                       {/* ErMerge Card */}
                       <div className="bg-rose-50 rounded-2xl p-4 border border-rose-100 shadow-sm relative opacity-60 grayscale hover:grayscale-0 transition-all">
                          <div className="w-2.5 h-2.5 rounded-full border-2 border-white shadow-sm bg-rose-500 absolute top-1/2 -left-1.5 -translate-y-1/2 z-10" />
                          <div className="absolute -top-3 left-4 bg-rose-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-widest">Failed Merge</div>
                          <div className="flex items-center justify-between mb-2">
                             <XCircle size={16} className="text-rose-500" />
                             <span className="text-[10px] font-black text-rose-400">0%</span>
                          </div>
                          <div className="text-2xl font-black text-rose-900 mb-1">0</div>
                          <div className="text-xs font-bold text-rose-600 uppercase tracking-tight">ErMerge</div>
                       </div>

                       {/* Total Exceptions Card */}
                       <div className="bg-rose-50 rounded-2xl p-4 border border-rose-100 shadow-sm relative">
                          <div className="w-2.5 h-2.5 rounded-full border-2 border-white shadow-sm bg-rose-500 absolute top-1/2 -left-1.5 -translate-y-1/2 z-10" />
                          <div className="absolute -top-3 left-4 bg-rose-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-widest">Total Exceptions</div>
                          <div className="flex items-center justify-between mb-2">
                             <ArchiveRestore size={16} className="text-rose-500" />
                             <span className="text-[10px] font-black text-rose-400">20.1%</span>
                          </div>
                          <div className="text-2xl font-black text-rose-900 mb-1">1,213</div>
                          <div className="text-xs font-bold text-rose-600 uppercase tracking-tight">Total Exceptions</div>
                       </div>
                    </div>
                }
            />

          </div>
        </div>
      </div>

      {/* Logic Route Breakdown */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="bg-white rounded-[32px] border border-slate-200 p-8 shadow-sm flex flex-col">
          <h3 className="font-bold text-slate-800 mb-6 flex items-center gap-2">Logic Routes (Rady2Merge Layer)</h3>
          <div className="flex-1 flex flex-col justify-center gap-6">
             <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                   <PieChart>
                      <Pie data={logicRoutes} innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value" stroke="none">
                         {logicRoutes.map((entry, index) => <Cell key={index} fill={entry.color} />)}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                   </PieChart>
                </ResponsiveContainer>
             </div>
             <div className="space-y-3">
                {logicRoutes.map((route, i) => (
                  <div key={i} className="flex items-center justify-between">
                     <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{backgroundColor: route.color}} />
                        <div><div className="text-xs font-bold text-slate-700">{route.name}</div><div className="text-[10px] text-slate-400">{route.desc}</div></div>
                     </div>
                     <div className="text-right"><div className="text-xs font-black text-slate-700">{route.value.toLocaleString()}</div><div className="text-[10px] text-slate-400">{((route.value / totalUnits) * 100).toFixed(1)}%</div></div>
                  </div>
                ))}
             </div>
          </div>
        </div>

        <div className="bg-white rounded-[32px] border border-slate-200 p-8 shadow-sm flex flex-col">
          <h3 className="font-bold text-slate-800 mb-6 flex items-center gap-2">Exception DNA</h3>
          <div className="space-y-5">
             {exceptionBreakdown.map((item, i) => {
                const totalExceptions = Math.floor(1213 * scaleFactor);
                const pct = (item.value / totalExceptions) * 100;
                return (
                  <div key={i} className="space-y-1.5">
                     <div className="flex justify-between text-xs font-bold text-slate-600"><span>{item.name}</span><span>{item.value.toLocaleString()} ({pct.toFixed(1)}%)</span></div>
                     <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden"><div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: item.color }} /></div>
                  </div>
                );
             })}
          </div>
        </div>

        <div className="bg-white rounded-[32px] border border-slate-200 p-8 shadow-sm flex flex-col">
          <h3 className="font-bold text-slate-800 mb-6 flex items-center gap-2">Ready2Docling Composition</h3>
          <div className="flex-1">
             <ResponsiveContainer width="100%" height={200}>
                <BarChart data={readyBreakdown} layout="vertical" margin={{ left: 20, right: 20 }}>
                   <XAxis type="number" hide />
                   <YAxis dataKey="name" type="category" width={80} tick={{fontSize: 10, fontWeight: 600, fill: '#64748b'}} axisLine={false} tickLine={false} />
                   <Tooltip cursor={{fill: 'transparent'}} content={<CustomTooltip />} />
                   <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={16}>
                      {readyBreakdown.map((entry, index) => <Cell key={index} fill={entry.color} />)}
                   </Bar>
                </BarChart>
             </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-[32px] border border-slate-200 shadow-sm flex flex-col overflow-hidden h-[800px]">
        <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center sticky top-0 z-10 backdrop-blur-sm">
           <div className="flex items-center gap-3">
              <Layers className="text-slate-400" size={20} />
              <div><h3 className="font-bold text-lg text-slate-800">Recursive Directory Explorer</h3><p className="text-xs text-slate-400 font-medium">Full hierarchy with metrics</p></div>
           </div>
        </div>
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6"><RecursiveTree node={currentTreeData} totalUnits={totalUnits} /></div>
      </div>
    </div>
  );
};

export default Statistics;
