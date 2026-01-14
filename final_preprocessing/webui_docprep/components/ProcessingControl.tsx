
import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, 
  RotateCw, 
  Activity, 
  FileSearch, 
  Archive, 
  GitMerge,
  CheckCircle2,
  Terminal,
  Cpu,
  FolderOpen,
  Split,
  ShieldAlert,
  Share2,
  RefreshCw,
  Zap,
  Calendar,
  Search,
  ChevronDown,
  ArchiveRestore,
  XCircle,
  Database,
  Loader2
} from 'lucide-react';

// --- Types & Constants ---

type PipelinePhase = 'cycle1' | 'cycle2' | 'final';

interface EngineConfig {
  id: PipelinePhase;
  title: string;
  description: string;
  source: string;
  stages: ('processing' | 'classification' | 'distribution' | 'final_merge')[];
  outputs: {
    merge?: string;
    next?: string;
    exception: string;
  };
}

const PIPELINE_CONFIG: Record<PipelinePhase, EngineConfig> = {
  cycle1: {
    id: 'cycle1',
    title: 'Cycle 1: Ingestion & Classify',
    description: 'Magic byte detection and initial routing of raw Input.',
    source: 'Input',
    stages: ['classification', 'distribution'],
    outputs: {
      merge: 'Rady2Merge/Direct',
      next: 'Processing/Processing_1',
      exception: 'Exceptions/Exceptions_1'
    }
  },
  cycle2: {
    id: 'cycle2',
    title: 'Cycle (2+):  Processing & Refinement',
    description: 'Conversion, Archive extraction & Normalization of complex nested artifacts.',
    source: 'Processing_1',
    stages: ['processing', 'classification', 'distribution'],
    outputs: {
      merge: 'Rady2Merge/Processed_1',
      next: 'Processing/Processing_2',
      exception: 'Exceptions/Exceptions_2'
    }
  },
  final: {
    id: 'final',
    title: 'Final Assembly',
    description: 'Consolidation of all Ready2Merge buckets into final output.',
    source: 'Rady2Merge (All)',
    stages: ['final_merge'],
    outputs: {
      merge: 'Ready2Docling', // Success
      exception: 'ErMerge'    // Failure
    }
  }
};

// --- Coordinates System (Compressed for Fit) ---
const POS = {
  SOURCE: { x: 90, y: 225 },
  SOURCE_TOP: { x: 90, y: 140 }, 
  SOURCE_BOT: { x: 90, y: 310 },
  
  // Center Column - Compressed X
  PROC: { x: 290, y: 100 },
  CLASS: { x: 290, y: 225 },
  DIST: { x: 290, y: 350 },
  
  MERGE_READY: { x: 290, y: 160 },
  MERGE_EXCEP: { x: 290, y: 350 },
  
  // Right Column - Compressed X
  DEST_TOP: { x: 500, y: 100 },
  DEST_MID: { x: 500, y: 225 },
  DEST_BOT: { x: 500, y: 350 },
};

// Compact Dimensions
const NODE_DIMS = { w: 160, h: 56 };
// Dimensions for the detailed Processor node
const PROC_DIMS = { w: 180, h: 120 };
const SOURCE_DIMS = { w: 130, h: 72 };

// --- Components ---

const BatchContextSelector = ({ protocolDate, unitCount = 6025 }: { protocolDate: string, unitCount?: number }) => (
    <div className="bg-white rounded-[24px] border border-slate-200 p-4 mb-6 shadow-sm flex flex-col lg:flex-row items-center justify-between gap-4">
      <div className="flex items-center gap-4 w-full lg:w-auto">
        <div className="p-3 bg-slate-100 rounded-xl text-slate-500">
           <FolderOpen size={20} />
        </div>
        <div>
           <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Active Batch Context</div>
           <div className="flex items-center gap-2 font-mono text-sm font-bold text-slate-700">
              <span className="text-slate-400">/root/.../Data/</span>
              <span className="text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-100">{protocolDate}</span>
           </div>
        </div>
      </div>

      <div className="flex items-center gap-4 w-full lg:w-auto bg-slate-50 p-2 rounded-xl border border-slate-100">
         <div className="flex items-center gap-3 px-3 py-1.5 bg-white border border-slate-200 rounded-lg cursor-pointer hover:border-blue-300 transition-colors">
            <Calendar size={14} className="text-slate-500" />
            <span className="text-xs font-bold text-slate-700">{protocolDate}</span>
            <ChevronDown size={14} className="text-slate-300" />
         </div>
         <div className="h-4 w-px bg-slate-300" />
         <div className="flex items-center gap-3 px-3">
             <span className="text-xs font-medium text-slate-500">Units Detected:</span>
             <span className="text-xs font-black text-slate-800 bg-white px-2 py-0.5 rounded border border-slate-200">{unitCount.toLocaleString()}</span>
         </div>
      </div>
      
      <div className="flex items-center gap-2">
         <button className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all" title="Refresh Directory">
            <RefreshCw size={18} />
         </button>
         <button className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold shadow-lg shadow-slate-200 hover:bg-slate-800 transition-all">
            <Search size={14} />
            Scan Directory
         </button>
      </div>
    </div>
);

const PipelineNode = ({ 
  icon, 
  title, 
  subtitle, 
  colorClass, 
  bgClass, 
  borderClass, 
  textClass,
  active,
  count = 0,
  total = 0,
  x, y,
  subStages // New prop for sequential stages
}: any) => {
  const isProc = !!subStages;
  const width = isProc ? PROC_DIMS.w : NODE_DIMS.w;
  const height = isProc ? PROC_DIMS.h : NODE_DIMS.h;

  return (
    <div 
      className={`absolute rounded-xl border flex flex-col shadow-sm transition-all duration-500 z-20 bg-white/95 backdrop-blur-sm overflow-hidden ${
        active ? `${borderClass} ring-4 ring-opacity-20 ${colorClass.replace('text-', 'ring-')} scale-105 shadow-xl` : 'border-slate-200'
      } ${isProc ? 'p-0' : 'px-2 py-1.5 flex-row items-center gap-2'}`}
      style={{ 
        left: x, 
        top: y, 
        transform: 'translate(-50%, -50%)',
        width: width,
        height: height
      }}
    >
       {isProc ? (
         // Expanded Layout for Processor
         <div className="flex flex-col h-full w-full">
            {/* Header */}
            <div className={`px-3 py-2 flex items-center gap-3 border-b border-slate-100 ${active ? 'bg-slate-50/50' : ''}`}>
               <div className={`p-1.5 rounded-lg ${bgClass} ${textClass} transition-all duration-500 relative overflow-hidden shrink-0`}>
                  {icon}
                  {active && <div className="absolute inset-0 bg-white/30 animate-pulse" />}
               </div>
               <div className="flex-1 min-w-0">
                  <div className={`text-[10px] font-black uppercase tracking-tight truncate ${active ? textClass : 'text-slate-600'}`}>{title}</div>
                  {count > 0 && <div className="text-[9px] font-mono font-bold text-slate-400">{count} units</div>}
               </div>
            </div>
            
            {/* List Body */}
            <div className="flex-1 flex flex-col justify-center p-2 gap-1.5 bg-white">
               {subStages.map((stage: string, i: number) => {
                  // Simulate sequential activation visually when node is active
                  const isStageActive = active; 
                  return (
                     <div key={i} className="flex items-center justify-between px-2 py-1 rounded-md transition-colors">
                        <div className="flex items-center gap-2.5">
                           {/* Status Spinner/Dot */}
                           <div className="relative w-3.5 h-3.5 flex items-center justify-center">
                              {isStageActive ? (
                                <>
                                  <div className={`absolute inset-0 rounded-full opacity-25 ${textClass.replace('text-', 'bg-')} animate-ping`} style={{ animationDuration: '2s', animationDelay: `${i * 300}ms` }} />
                                  <Loader2 className={`w-3.5 h-3.5 ${textClass} animate-spin`} style={{ animationDuration: '3s' }} />
                                </>
                              ) : (
                                <div className="w-1.5 h-1.5 rounded-full bg-slate-200" />
                              )}
                           </div>
                           <span className={`text-[9px] font-bold uppercase tracking-wider ${isStageActive ? 'text-slate-700' : 'text-slate-400'}`}>{stage}</span>
                        </div>
                        {isStageActive && (
                           <div className={`w-1.5 h-1.5 rounded-full ${textClass.replace('text-', 'bg-')} shadow-sm animate-pulse`} style={{ animationDelay: `${i * 200}ms` }} />
                        )}
                     </div>
                  );
               })}
            </div>
         </div>
       ) : (
         // Compact Layout (Original)
         <>
           <div className={`p-1.5 rounded-lg ${bgClass} ${textClass} transition-all duration-500 relative overflow-hidden shrink-0`}>
              {icon}
              {active && <div className="absolute inset-0 bg-white/30 animate-pulse" />}
           </div>
           <div className="flex-1 min-w-0 overflow-hidden flex flex-col justify-center">
              <div className="flex justify-between items-center mb-0.5">
                 <div className={`text-[9px] font-black uppercase tracking-tight truncate ${active ? textClass : 'text-slate-600'}`}>{title}</div>
                 {count > 0 && (
                   <div className={`text-[8px] px-1 py-px rounded font-mono font-bold ${bgClass} ${textClass}`}>
                     {count}
                   </div>
                 )}
              </div>
              <div className={`text-[8px] font-medium leading-none truncate text-slate-400`}>{subtitle}</div>
              {active && (
                <div className="h-0.5 w-full bg-slate-100 rounded-full mt-1.5 overflow-hidden">
                   <div className={`h-full ${colorClass.replace('text-', 'bg-')} animate-[progress_1s_ease-in-out_infinite]`} style={{width: '60%'}} />
                </div>
              )}
           </div>
         </>
       )}
    </div>
  );
};

const SourceBucket = ({ label, active, count, x, y }: { label: string, active: boolean, count: number, x: number, y: number }) => (
  <div 
    className={`absolute p-3 rounded-2xl border transition-all duration-500 z-10 flex flex-col justify-between ${
      active ? 'bg-slate-50 border-blue-300 shadow-md ring-2 ring-blue-50' : 'bg-white border-slate-200 shadow-sm'
    }`}
    style={{ 
      left: x, 
      top: y, 
      transform: 'translate(-50%, -50%)',
      width: SOURCE_DIMS.w,
      height: SOURCE_DIMS.h
    }}
  >
     <div className="flex items-center justify-between text-slate-500">
        <div className="flex items-center gap-1.5">
            <FolderOpen size={14} className={active ? 'text-blue-500' : ''} />
            <span className="text-[9px] font-bold uppercase tracking-widest">Source</span>
        </div>
        {active && <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-ping" />}
     </div>
     <div className="flex items-end justify-between gap-2">
         <div className="text-[10px] font-black text-slate-800 break-words font-mono leading-tight truncate w-full" title={label}>{label}</div>
     </div>
     <div className="text-[10px] font-bold text-slate-400 font-mono text-right">{count}</div>
  </div>
);

const DestNode = ({ label, sub, icon: Icon, color, active, count, x, y }: any) => {
    let styles = { bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-600', iconBg: 'bg-slate-100', iconColor: 'text-slate-500' };
    
    if (active || count > 0) {
        if (color === 'emerald') styles = { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', iconBg: 'bg-emerald-100', iconColor: 'text-emerald-600' };
        if (color === 'blue') styles = { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', iconBg: 'bg-blue-100', iconColor: 'text-blue-600' };
        if (color === 'rose') styles = { bg: 'bg-rose-50', border: 'border-rose-200', text: 'text-rose-700', iconBg: 'bg-rose-100', iconColor: 'text-rose-600' };
    }

    return (
        <div 
            className={`absolute px-2.5 py-2 rounded-xl border flex items-center gap-2 transition-all duration-500 z-10 ${styles.bg} ${styles.border} ${active ? 'scale-105 shadow-md ring-2 ring-opacity-50 ' + styles.border : ''}`}
            style={{ 
                left: x, 
                top: y, 
                transform: 'translate(-50%, -50%)',
                width: NODE_DIMS.w,
            }}
        >
           <div className={`p-1 ${styles.iconBg} ${styles.iconColor} rounded-lg shrink-0`}>
              <Icon size={14} />
           </div>
           <div className="flex-1 min-w-0 overflow-hidden">
              <div className="flex justify-between items-center">
                  <div className={`text-[9px] font-black uppercase tracking-wider truncate ${styles.text}`}>{label}</div>
                  {count > 0 && <span className={`text-[8px] font-mono font-bold ${styles.text}`}>{count}</span>}
              </div>
              <div className="text-[8px] font-bold text-slate-400 truncate font-mono" title={sub}>{sub}</div>
           </div>
        </div>
    );
}

// --- Connector Logic ---

const ConnectorLines = ({ config, step }: { config: EngineConfig, step: number }) => {
  const isFinal = config.id === 'final';
  const hasProcessing = config.stages.includes('processing');
  
  // Helper functions
  const drawPath = (id: string, start: {x: number, y: number}, end: {x: number, y: number}, color: string, active: boolean) => {
    const mx = (start.x + end.x) / 2;
    const d = `M ${start.x} ${start.y} C ${mx} ${start.y}, ${mx} ${end.y}, ${end.x - 6} ${end.y}`;
    return (
        <g key={id}>
            <path d={d} fill="none" stroke={active ? color : '#e2e8f0'} strokeWidth={active ? 2 : 1.5} markerEnd={active ? `url(#arrow-${color.replace('#', '')})` : ''} className="transition-all duration-500" />
            {active && (
                <circle r="3" fill={color}>
                    <animateMotion dur="1s" repeatCount="indefinite" path={d} />
                </circle>
            )}
        </g>
    );
  };

  const drawVertical = (id: string, x: number, y1: number, y2: number, color: string, active: boolean) => {
      const d = `M ${x} ${y1} L ${x} ${y2 - 6}`;
      return (
        <g key={id}>
          <path d={d} fill="none" stroke={active ? color : '#e2e8f0'} strokeWidth={active ? 2 : 1.5} markerEnd={active ? `url(#arrow-${color.replace('#', '')})` : ''} className="transition-all duration-500" />
          {active && (
              <circle r="3" fill={color}>
                  <animateMotion dur="0.8s" repeatCount="indefinite" path={d} />
              </circle>
          )}
        </g>
      );
  };

  // Node edges based on dimensions, handling special Processor case
  const getDims = (pos: {x: number, y: number}) => {
     if (pos === POS.PROC) return PROC_DIMS;
     return NODE_DIMS;
  }

  const getNodeIn = (pos: {x:number, y:number}) => ({ x: pos.x - getDims(pos).w/2, y: pos.y });
  const getNodeOut = (pos: {x:number, y:number}) => ({ x: pos.x + getDims(pos).w/2, y: pos.y });
  const getNodeBot = (pos: {x:number, y:number}) => ({ x: pos.x, y: pos.y + getDims(pos).h/2 });
  const getNodeTop = (pos: {x:number, y:number}) => ({ x: pos.x, y: pos.y - getDims(pos).h/2 });
  
  const srcEdge = { x: POS.SOURCE.x + SOURCE_DIMS.w/2, y: POS.SOURCE.y };
  const srcTopEdge = { x: POS.SOURCE_TOP.x + SOURCE_DIMS.w/2, y: POS.SOURCE_TOP.y };
  const srcBotEdge = { x: POS.SOURCE_BOT.x + SOURCE_DIMS.w/2, y: POS.SOURCE_BOT.y };

  const colors = { blue: '#3b82f6', purple: '#a855f7', green: '#10b981', rose: '#f43f5e', slate: '#94a3b8' };

  return (
    <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible z-0">
      <defs>
         <marker id="arrow-10b981" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#10b981" /></marker>
         <marker id="arrow-3b82f6" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#3b82f6" /></marker>
         <marker id="arrow-a855f7" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#a855f7" /></marker>
         <marker id="arrow-f43f5e" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#f43f5e" /></marker>
         <marker id="arrow-94a3b8" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#94a3b8" /></marker>
      </defs>

      {/* 1. Source -> First Stage */}
      {!isFinal ? (
          hasProcessing ? (
              // Cycle 2/3: Source -> Processing (Top)
              drawPath('src-proc', srcEdge, getNodeIn(POS.PROC), colors.blue, step === 1)
          ) : (
              // Cycle 1: Source -> Classification (Mid)
              drawPath('src-class', srcEdge, getNodeIn(POS.CLASS), colors.purple, step === 1)
          )
      ) : (
          <>
             {/* Final: Source Rady2Merge -> Merging Ready */}
             {drawPath('src-ready', srcTopEdge, getNodeIn(POS.MERGE_READY), colors.green, step === 1) }
             {/* Final: Source Exceptions -> Merging Exception */}
             {drawPath('src-excep', srcBotEdge, getNodeIn(POS.MERGE_EXCEP), colors.rose, step === 1) }
          </>
      )}

      {/* 2. Internal Stack Connections */}
      {!isFinal && hasProcessing && (
          // Processing -> Classification
          drawVertical('proc-class', POS.PROC.x, getNodeBot(POS.PROC).y, getNodeTop(POS.CLASS).y, colors.purple, step === 2)
      )}

      {!isFinal && (
          // Classification -> Distribution
          drawVertical('class-dist', POS.CLASS.x, getNodeBot(POS.CLASS).y, getNodeTop(POS.DIST).y, colors.slate, step === (hasProcessing ? 3 : 2))
      )}

      {/* 3. Distribution/Nodes -> Destinations */}
      {!isFinal && (
          <>
             {drawPath('dist-merge', getNodeOut(POS.DIST), getNodeIn(POS.DEST_TOP), colors.green, step === (hasProcessing ? 4 : 3))}
             {drawPath('dist-next', getNodeOut(POS.DIST), getNodeIn(POS.DEST_MID), colors.blue, step === (hasProcessing ? 4 : 3))}
             {drawPath('dist-excep', getNodeOut(POS.DIST), getNodeIn(POS.DEST_BOT), colors.rose, step === (hasProcessing ? 4 : 3))}
          </>
      )}

      {isFinal && (
          <>
             {/* Merging Ready -> Success */}
             {drawPath('ready-succ', getNodeOut(POS.MERGE_READY), getNodeIn(POS.DEST_TOP), colors.green, step === 2)}
             {/* Merging Ready -> ErMerge */}
             {drawPath('ready-fail', getNodeOut(POS.MERGE_READY), getNodeIn(POS.DEST_MID), colors.rose, step === 2)}
             {/* Merging Exception -> Total */}
             {drawPath('excep-total', getNodeOut(POS.MERGE_EXCEP), getNodeIn(POS.DEST_BOT), colors.rose, step === 2)}
          </>
      )}

    </svg>
  );
};

// --- Main Component ---

const ProcessingControl: React.FC<{ protocolDate: string }> = ({ protocolDate }) => {
  const [activePhase, setActivePhase] = useState<PipelinePhase>('cycle1');
  const [isRunning, setIsRunning] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [simStep, setSimStep] = useState(0); // 0=Idle, 1=Source->Node, 2=Internal, 3=Dist, 4=Out
  
  // Metrics State
  const [metrics, setMetrics] = useState<Record<string, number>>({});
  const [logs, setLogs] = useState<string[]>([]);
  const logContainerRef = useRef<HTMLDivElement>(null);

  const config = PIPELINE_CONFIG[activePhase];
  const hasProcessing = config.stages.includes('processing');

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Reset metrics on phase change
  useEffect(() => {
      setMetrics({});
      setSimStep(0);
      setIsRunning(false);
      setIsComplete(false);
      setLogs([]);
  }, [activePhase]);

  const addLog = (msg: string) => {
    const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
    setLogs(prev => [...prev, `[${timestamp}] ${msg}`]);
  };

  const updateMetric = (key: string, amount: number) => {
      setMetrics(prev => ({...prev, [key]: (prev[key] || 0) + amount}));
  };

  const runSimulation = () => {
      if (isRunning) return;
      setIsRunning(true);
      setIsComplete(false);
      setMetrics({});
      setLogs([]);
      setSimStep(1); // Start flow from source

      addLog(`INITIATING ${activePhase.toUpperCase()} PIPELINE...`);

      // Simulation Timeline
      const TICK = 800; // Time per step

      // Step 1: Source Emits
      const s1 = setInterval(() => {
          updateMetric('source', 15);
      }, 50);

      setTimeout(() => {
          clearInterval(s1);
          setSimStep(2); // Move to next stage
          
          if (activePhase === 'final') {
              addLog("Merging Logic Active...");
              // Final Phase Logic
              const s2 = setInterval(() => {
                  updateMetric('merge_ready', 10);
                  updateMetric('merge_excep', 5);
              }, 50);
              
              setTimeout(() => {
                  clearInterval(s2);
                  setSimStep(3); // To Dests
                  
                  const s3 = setInterval(() => {
                      updateMetric('dest_succ', 8);
                      updateMetric('dest_fail', 2);
                      updateMetric('dest_total', 5);
                  }, 50);

                  setTimeout(() => {
                      clearInterval(s3);
                      setIsRunning(false);
                      setIsComplete(true);
                      setSimStep(0);
                      addLog("FINAL MERGE COMPLETE.");
                  }, TICK * 2);

              }, TICK);

          } else {
              // Cycle Logic
              if (hasProcessing) {
                  addLog("Processing Core Active...");
                  const s2 = setInterval(() => { updateMetric('proc', 15); }, 50);
                  setTimeout(() => { clearInterval(s2); setSimStep(3); }, TICK);
              } else {
                  setSimStep(3); // Skip straight to distribution logic if no processing
              }

              // Timed entry to Classify/Distribute
              setTimeout(() => {
                  addLog("Classification & Distribution...");
                  const targetStep = hasProcessing ? 4 : 3;
                  setSimStep(targetStep); 
                  
                  const s3 = setInterval(() => {
                      updateMetric('class', 15);
                      updateMetric('dist', 15);
                  }, 50);

                  setTimeout(() => {
                      clearInterval(s3);
                      setSimStep(targetStep + 1); // To Outs

                      const s4 = setInterval(() => {
                          updateMetric('out_merge', 8);
                          updateMetric('out_next', 4);
                          updateMetric('out_excep', 3);
                      }, 50);

                      setTimeout(() => {
                          clearInterval(s4);
                          setIsRunning(false);
                          setIsComplete(true);
                          setSimStep(0);
                          addLog("CYCLE COMPLETE.");
                      }, TICK * 2);
                  }, TICK);

              }, hasProcessing ? TICK : 100);
          }
      }, TICK);
  };

  // Helper to check if a node is active based on step
  const isActive = (nodeKey: string) => {
      if (!isRunning) return false;
      // Logic mapping steps to nodes
      if (activePhase === 'final') {
          if (nodeKey === 'source') return simStep === 1;
          if (nodeKey === 'merge_ready' || nodeKey === 'merge_excep') return simStep === 2;
          if (nodeKey.startsWith('dest_')) return simStep === 3;
      } else {
          if (nodeKey === 'source') return simStep === 1;
          if (hasProcessing) {
              if (nodeKey === 'proc') return simStep === 2;
              if (nodeKey === 'class') return simStep === 3; // Vertical flow
              if (nodeKey === 'dist') return simStep === 4;
              if (nodeKey.startsWith('out_')) return simStep === 5;
          } else {
              if (nodeKey === 'class') return simStep === 2;
              if (nodeKey === 'dist') return simStep === 3;
              if (nodeKey.startsWith('out_')) return simStep === 4;
          }
      }
      return false;
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in slide-in-from-bottom-8 duration-700 pb-20">
      
      {/* 0. Batch Context Selector */}
      <BatchContextSelector protocolDate={protocolDate} />

      {/* 1. Header & Navigation */}
      <div className="bg-white rounded-[32px] border border-slate-200 p-2 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4 sticky top-0 z-50">
         <div className="flex items-center gap-4 px-6 py-2">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-lg ${activePhase === 'final' ? 'bg-purple-600 shadow-purple-200' : 'bg-blue-600 shadow-blue-200'}`}>
               <Activity size={20} />
            </div>
            <div>
               <h2 className="text-lg font-black text-slate-800 tracking-tight">Pipeline Operator</h2>
               <p className="text-xs text-slate-500 font-medium">Protocol: <span className="font-mono font-bold text-slate-700">{protocolDate}</span></p>
            </div>
         </div>

         <div className="flex bg-slate-100 p-1.5 rounded-[24px]">
            {(['cycle1', 'cycle2', 'final'] as PipelinePhase[]).map((phase) => (
               <button 
                 key={phase}
                 onClick={() => !isRunning && setActivePhase(phase)}
                 disabled={isRunning}
                 className={`px-5 py-2.5 rounded-[20px] text-xs font-black transition-all ${
                   activePhase === phase 
                   ? 'bg-white text-slate-800 shadow-md transform scale-105' 
                   : 'text-slate-400 hover:text-slate-600 hover:bg-slate-200/50'
                 } ${isRunning ? 'opacity-50 cursor-not-allowed' : ''}`}
               >
                 {phase === 'final' ? 'FINAL MERGE' : phase.toUpperCase().replace('CYCLE', 'CYCLE ')}
               </button>
            ))}
         </div>
      </div>

      {/* 2. Visual Pipeline Editor */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[500px]">
         
         {/* Visual Stage Flow - Added horizontal scrolling backup */}
         <div className="lg:col-span-2 bg-white rounded-[40px] border border-slate-200 relative overflow-hidden flex flex-col shadow-sm">
            <div className="absolute inset-0 bg-[radial-gradient(#e2e8f0_1px,transparent_1px)] [background-size:20px_20px] opacity-40 pointer-events-none" />
            
            <div className="p-8 border-b border-slate-100 bg-white/60 backdrop-blur-md z-30 flex justify-between items-start pointer-events-none">
               <div>
                  <h3 className="text-xl font-black text-slate-800">{config.title}</h3>
                  <p className="text-slate-500 text-sm max-w-md mt-1">{config.description}</p>
               </div>
               <div className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border transition-colors ${
                 isRunning 
                 ? 'bg-blue-100 text-blue-700 border-blue-200 animate-pulse' 
                 : isComplete 
                     ? 'bg-green-100 text-green-700 border-green-200' 
                     : 'bg-slate-100 text-slate-500 border-slate-200'
               }`}>
                  {isRunning ? 'Running' : (isComplete ? 'Ready' : 'Raw')}
               </div>
            </div>

            {/* Canvas for Absolute Positioning - Added overflow handling just in case */}
            <div className="flex-1 relative z-20 w-full h-full overflow-hidden">
               <div className="w-full h-full min-w-[560px] relative"> {/* min-width ensures layout integrity */}
                  
                  {/* SVG Wiring Layer */}
                  <ConnectorLines config={config} step={simStep} />

                  {/* LEFT: Source Bucket(s) */}
                  {activePhase === 'final' ? (
                      <>
                        <SourceBucket label={config.source} active={isActive('source')} count={metrics['source'] || 0} x={POS.SOURCE_TOP.x} y={POS.SOURCE_TOP.y} />
                        <SourceBucket label="Exceptions (All)" active={isActive('source')} count={metrics['source'] || 0} x={POS.SOURCE_BOT.x} y={POS.SOURCE_BOT.y} />
                      </>
                  ) : (
                      <SourceBucket label={config.source} active={isActive('source')} count={metrics['source'] || 0} x={POS.SOURCE.x} y={POS.SOURCE.y} />
                  )}

                  {/* CENTER: Pipeline Stages */}
                  {config.stages.includes('processing') && (
                      <PipelineNode 
                        icon={<Archive size={14} />}
                        title="Processor Core"
                        subStages={['Convert', 'Extract', 'Norm']}
                        colorClass="text-blue-600"
                        bgClass="bg-blue-100"
                        borderClass="border-blue-200"
                        textClass="text-blue-700"
                        active={isActive('proc')}
                        count={metrics['proc']}
                        x={POS.PROC.x} y={POS.PROC.y}
                      />
                  )}

                  {config.stages.includes('classification') && (
                      <PipelineNode 
                        icon={<FileSearch size={14} />}
                        title="Decision Engine"
                        subtitle="Magic Bytes & Type"
                        colorClass="text-purple-600"
                        bgClass="bg-purple-100"
                        borderClass="border-purple-200"
                        textClass="text-purple-700"
                        active={isActive('class')}
                        count={metrics['class']}
                        x={POS.CLASS.x} y={POS.CLASS.y}
                      />
                  )}

                  {config.stages.includes('distribution') && (
                      <PipelineNode 
                        icon={<Share2 size={14} />}
                        title="Distribution"
                        subtitle="Sort to Targets"
                        colorClass="text-slate-600"
                        bgClass="bg-slate-200"
                        borderClass="border-slate-300"
                        textClass="text-slate-700"
                        active={isActive('dist')}
                        count={metrics['dist']}
                        x={POS.DIST.x} y={POS.DIST.y}
                      />
                  )}

                  {/* Final Merge Nodes */}
                  {config.stages.includes('final_merge') && (
                      <>
                        <PipelineNode 
                          icon={<GitMerge size={14} />}
                          title="Merging Ready"
                          subtitle="Direct + Processed_N"
                          colorClass="text-emerald-600"
                          bgClass="bg-emerald-100"
                          borderClass="border-emerald-200"
                          textClass="text-emerald-800"
                          active={isActive('merge_ready')}
                          count={metrics['merge_ready']}
                          x={POS.MERGE_READY.x} y={POS.MERGE_READY.y}
                        />
                        <PipelineNode 
                          icon={<ShieldAlert size={14} />}
                          title="Merging Exception"
                          subtitle="Exceptions_1..N"
                          colorClass="text-rose-600"
                          bgClass="bg-rose-100"
                          borderClass="border-rose-200"
                          textClass="text-rose-800"
                          active={isActive('merge_excep')}
                          count={metrics['merge_excep']}
                          x={POS.MERGE_EXCEP.x} y={POS.MERGE_EXCEP.y}
                        />
                      </>
                  )}
                      
                  {/* RIGHT: Destinations */}
                  
                  {activePhase === 'final' ? (
                      <>
                        <DestNode label="Success" sub="Ready2Docling" icon={CheckCircle2} color="emerald" active={isActive('dest_succ')} count={metrics['dest_succ']} x={POS.DEST_TOP.x} y={POS.DEST_TOP.y} />
                        <DestNode label="ErMerge" sub="Conflict / Fail" icon={XCircle} color="rose" active={isActive('dest_fail')} count={metrics['dest_fail']} x={POS.DEST_MID.x} y={POS.DEST_MID.y} />
                        <DestNode label="Total Exceptions" sub="Aggregated Logs" icon={ArchiveRestore} color="rose" active={isActive('dest_total')} count={metrics['dest_total']} x={POS.DEST_BOT.x} y={POS.DEST_BOT.y} />
                      </>
                  ) : (
                      <>
                        {config.outputs.merge && (
                            <DestNode label="Merge" sub={config.outputs.merge.split('/').pop()} icon={GitMerge} color="emerald" active={isActive('out_merge')} count={metrics['out_merge']} x={POS.DEST_TOP.x} y={POS.DEST_TOP.y} />
                        )}
                        {config.outputs.next && (
                            <DestNode label="Next Cycle" sub={config.outputs.next.split('/').pop()} icon={Split} color="blue" active={isActive('out_next')} count={metrics['out_next']} x={POS.DEST_MID.x} y={POS.DEST_MID.y} />
                        )}
                        {config.outputs.exception && (
                            <DestNode label="Exception" sub={config.outputs.exception.split('/').pop()} icon={ShieldAlert} color="rose" active={isActive('out_excep')} count={metrics['out_excep']} x={POS.DEST_BOT.x} y={POS.DEST_BOT.y} />
                        )}
                      </>
                  )}
               </div>
            </div>
         </div>

         {/* Console & Action */}
         <div className="flex flex-col gap-6">
            <div className="bg-slate-900 rounded-[32px] p-6 flex-1 flex flex-col shadow-xl text-slate-300 font-mono text-xs overflow-hidden relative border border-slate-800">
               <div className="flex items-center gap-2 mb-4 text-slate-500 border-b border-slate-800 pb-2">
                  <Terminal size={14} />
                  <span className="uppercase font-bold tracking-widest">System Log</span>
               </div>
               <div ref={logContainerRef} className="flex-1 overflow-y-auto custom-scrollbar space-y-2 relative z-10">
                  {logs.length === 0 ? (
                     <div className="h-full flex flex-col items-center justify-center text-slate-700 opacity-50">
                        <Cpu size={32} strokeWidth={1} />
                        <span className="mt-2 text-[10px]">Awaiting Command</span>
                     </div>
                  ) : (
                     logs.map((log, i) => (
                        <div key={i} className="animate-in slide-in-from-left-2 fade-in duration-300 flex">
                           <span className="text-slate-600 mr-2 shrink-0">{log.split(']')[0]}]</span>
                           <span className={log.includes('EXCEPTION') ? 'text-rose-400' : 'text-slate-300'}>{log.split(']')[1]}</span>
                        </div>
                     ))
                  )}
               </div>
            </div>

            <button 
               onClick={runSimulation}
               disabled={isRunning}
               className={`h-24 rounded-[32px] font-black text-xl flex items-center justify-center gap-4 shadow-xl transition-all active:scale-95 border-t border-white/10 ${
                  isRunning 
                  ? 'bg-slate-100 text-slate-400 cursor-wait' 
                  : activePhase === 'final'
                     ? 'bg-purple-600 text-white hover:bg-purple-700 shadow-purple-600/30'
                     : 'bg-blue-600 text-white hover:bg-blue-700 shadow-blue-600/30'
               }`}
            >
               {isRunning ? <RotateCw className="animate-spin" /> : (activePhase === 'final' ? <Zap fill="currentColor" /> : <Play fill="currentColor" />)}
               {isRunning ? 'EXECUTING...' : (activePhase === 'final' ? 'EXECUTE MERGE' : 'RUN CYCLE')}
            </button>
         </div>
      </div>

      <style>{`
        @keyframes progress {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(250%); }
        }
      `}</style>
    </div>
  );
};

export default ProcessingControl;
