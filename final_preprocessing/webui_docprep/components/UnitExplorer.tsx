
import React, { useState } from 'react';
import { 
  Search, 
  Filter, 
  ExternalLink, 
  FileJson, 
  ShieldCheck,
  History,
  Tag,
  Code,
  FileCode2,
  Box,
  ChevronRight,
  MoreVertical,
  ArrowRight,
  Fingerprint
} from 'lucide-react';
import { CATEGORY_COLORS } from '../constants';

const MOCK_UNITS = [
  { id: 'UNIT_2025_00938', category: 'direct', state: 'READY_FOR_DOCLING', route: 'pdf_text', files: 4, size: '2.4MB', timestamp: '14:22:10' },
  { id: 'UNIT_2025_00939', category: 'convert', state: 'PENDING_CONVERT', route: 'docx', files: 1, size: '450KB', timestamp: '14:23:45' },
  { id: 'UNIT_2025_00940', category: 'extract', state: 'PENDING_EXTRACT', route: 'extract', files: 12, size: '45.1MB', timestamp: '14:24:01' },
  { id: 'UNIT_2025_00941', category: 'mixed', state: 'EXCEPTION_1', route: 'mixed', files: 3, size: '1.2MB', timestamp: '14:24:30' },
  { id: 'UNIT_2025_00942', category: 'normalize', state: 'MERGED_PROCESSED', route: 'pdf_scan', files: 2, size: '8.1MB', timestamp: '14:25:12' },
  { id: 'UNIT_2025_00943', category: 'special', state: 'EXCEPTION_2', route: 'unknown', files: 1, size: '12KB', timestamp: '14:26:00' },
];

const UnitExplorer: React.FC = () => {
  const [selectedUnit, setSelectedUnit] = useState<string | null>(null);

  return (
    <div className="h-full flex flex-col gap-6 animate-in fade-in duration-700">
      
      {/* Search Bar */}
      <div className="flex items-center gap-4">
        <div className="flex-1 relative group">
          <div className="absolute inset-0 bg-blue-500/5 blur-xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
          <Search className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors" size={20} />
          <input 
            type="text" 
            placeholder="Search Units (ID, Route, Hash)..."
            className="w-full pl-14 pr-6 py-4 bg-white border border-slate-200 rounded-[24px] focus:ring-4 focus:ring-blue-500/10 focus:border-blue-300 outline-none transition-all font-medium text-slate-700 shadow-sm relative z-10"
          />
        </div>
        <button className="flex items-center gap-2 px-6 py-4 bg-white border border-slate-200 rounded-[24px] font-black text-slate-600 hover:bg-slate-50 transition-all shadow-sm text-xs uppercase tracking-widest">
          <Filter size={16} />
          Filters
        </button>
      </div>

      <div className="flex-1 grid grid-cols-1 xl:grid-cols-12 gap-6 min-h-0">
        
        {/* Unit List (Grid) */}
        <div className={`col-span-12 ${selectedUnit ? 'xl:col-span-8' : 'xl:col-span-12'} bg-white rounded-[32px] border border-slate-200 overflow-hidden flex flex-col shadow-sm transition-all duration-500`}>
          <div className="overflow-x-auto custom-scrollbar flex-1">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 bg-white/95 backdrop-blur-md z-10 border-b border-slate-100">
                <tr>
                  <th className="px-6 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest pl-8">Identity</th>
                  <th className="px-6 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Route</th>
                  <th className="px-6 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Status</th>
                  <th className="px-6 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Payload</th>
                  <th className="px-6 py-5"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {MOCK_UNITS.map((unit) => (
                  <tr 
                    key={unit.id} 
                    onClick={() => setSelectedUnit(unit.id)}
                    className={`group cursor-pointer transition-all hover:bg-blue-50/50 ${selectedUnit === unit.id ? 'bg-blue-50 border-l-4 border-blue-500' : 'border-l-4 border-transparent'}`}
                  >
                    <td className="px-6 py-5 pl-8">
                      <div className="flex items-center gap-4">
                         <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-slate-500 shadow-sm transition-colors ${selectedUnit === unit.id ? 'bg-white text-blue-600' : 'bg-slate-100 group-hover:bg-white'}`}>
                            <Box size={18} />
                         </div>
                         <div>
                            <div className="font-bold text-slate-800 text-sm tracking-tight">{unit.id}</div>
                            <div className="text-[10px] text-slate-400 font-mono mt-0.5">{unit.timestamp}</div>
                         </div>
                      </div>
                    </td>
                    <td className="px-6 py-5">
                       <div className="flex items-center gap-2">
                          <Code size={14} className="text-slate-400" />
                          <span className="text-xs font-mono font-bold text-slate-600 uppercase bg-slate-100 px-2 py-1 rounded-md">{unit.route}</span>
                       </div>
                    </td>
                    <td className="px-6 py-5">
                      <span className={`px-3 py-1.5 rounded-full text-[9px] font-black uppercase tracking-widest border border-current/10 ${CATEGORY_COLORS[unit.category] || 'bg-slate-100 text-slate-600'}`}>
                        {unit.state}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                       <div className="flex items-center gap-3">
                          <div className="text-right">
                             <div className="text-xs font-bold text-slate-700">{unit.files} Files</div>
                             <div className="text-[10px] text-slate-400 font-mono">{unit.size}</div>
                          </div>
                       </div>
                    </td>
                    <td className="px-6 py-5 text-right pr-8">
                       <ChevronRight size={18} className={`text-slate-300 transition-transform ${selectedUnit === unit.id ? 'text-blue-500 translate-x-1' : 'group-hover:text-slate-400'}`} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Details Panel (Sliding) */}
        {selectedUnit && (
          <div className="col-span-12 xl:col-span-4 bg-white rounded-[32px] border border-slate-200 p-0 flex flex-col shadow-xl shadow-slate-200/50 min-h-0 animate-in slide-in-from-right-8 duration-500 overflow-hidden relative">
             <div className="absolute top-0 right-0 p-8 opacity-5 pointer-events-none">
                <Fingerprint size={180} />
             </div>

              {/* Header */}
              <div className="p-8 border-b border-slate-100 bg-slate-50/30 backdrop-blur-sm relative z-10">
                 <div className="flex items-center justify-between mb-2">
                     <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Inspector</span>
                     <div className="flex gap-2">
                        <button className="p-2 bg-white border border-slate-200 text-slate-400 hover:text-blue-600 hover:border-blue-200 rounded-xl transition-all shadow-sm" title="Raw JSON">
                           <FileJson size={16} />
                        </button>
                        <button className="p-2 bg-white border border-slate-200 text-slate-400 hover:text-purple-600 hover:border-purple-200 rounded-xl transition-all shadow-sm" title="Audit Log">
                           <History size={16} />
                        </button>
                        <button className="p-2 bg-white border border-slate-200 text-slate-400 hover:text-red-600 hover:border-red-200 rounded-xl transition-all shadow-sm" onClick={() => setSelectedUnit(null)}>
                           <ArrowRight size={16} />
                        </button>
                     </div>
                 </div>
                 <h3 className="font-black text-2xl text-slate-800 tracking-tight break-all">{selectedUnit}</h3>
                 <div className="flex gap-2 mt-3">
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-[10px] font-bold uppercase rounded border border-blue-200">v2.1.0</span>
                    <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] font-bold uppercase rounded border border-slate-200">Protocol A</span>
                 </div>
              </div>

              {/* Body */}
              <div className="space-y-8 overflow-y-auto custom-scrollbar flex-1 p-8 relative z-10">
                 
                 {/* Metadata Card */}
                 <div className="p-5 bg-slate-900 rounded-[24px] text-white space-y-3 shadow-lg">
                    <DetailRow label="Unit Hash" value="8f4a...92b1" mono />
                    <DetailRow label="Origin" value="ingestion_daemon_01" />
                    <DetailRow label="Priority" value="High" />
                 </div>

                 {/* Timeline */}
                 <div>
                    <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                       <ShieldCheck size={14} className="text-blue-500" />
                       Lifecycle Trace
                    </h4>
                    <div className="space-y-0 relative">
                       {/* Vertical Line */}
                       <div className="absolute left-[7px] top-2 bottom-4 w-px bg-slate-200" />
                       
                       <HistoryStep state="RAW_INGEST" op="Magic Byte Detection" date="14:15:22" />
                       <HistoryStep state="CLASSIFIED" op="Route: PDF_TEXT" date="14:16:05" />
                       <HistoryStep state="PROCESSING" op="Normalization Engine" date="14:18:11" />
                       <HistoryStep state="READY_FOR_DOCLING" op="Validation Passed" date="14:22:10" last status="success" />
                    </div>
                 </div>

                 {/* Files */}
                 <div>
                    <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                       <FileCode2 size={14} className="text-purple-500" />
                       Payload Artifacts
                    </h4>
                    <div className="space-y-3">
                       <FileCard name="manifest.json" size="2KB" type="json" />
                       <FileCard name="source_doc.pdf" size="2.1MB" type="pdf" />
                       <FileCard name="audit_trail.log" size="15KB" type="log" />
                    </div>
                 </div>
              </div>

              {/* Footer Action */}
              <div className="p-6 border-t border-slate-100 bg-white relative z-10">
                 <button className="w-full py-4 bg-blue-600 text-white font-black rounded-[20px] hover:bg-blue-700 transition-all shadow-lg shadow-blue-200 tracking-tight flex justify-center items-center gap-2 group">
                   DOWNLOAD PACKAGE
                   <ExternalLink size={16} className="group-hover:translate-x-1 transition-transform" />
                 </button>
              </div>
          </div>
        )}
      </div>
    </div>
  );
};

const DetailRow = ({ label, value, mono }: any) => (
  <div className="flex justify-between items-center text-xs">
    <span className="text-slate-400 font-bold uppercase tracking-widest text-[9px] opacity-80">{label}</span>
    <span className={`${mono ? 'font-mono text-blue-300' : 'text-slate-200'} font-bold`}>{value}</span>
  </div>
);

const HistoryStep = ({ state, op, date, last, status }: any) => (
  <div className="relative pl-8 pb-6 last:pb-0">
    <div className={`absolute left-0 top-1 w-[15px] h-[15px] rounded-full border-[3px] border-white shadow-sm z-10 ${last ? 'bg-emerald-500' : 'bg-slate-300'}`} />
    <div className="flex justify-between items-center mb-1">
       <span className={`text-[10px] font-black tracking-widest ${last ? 'text-emerald-600' : 'text-slate-600'}`}>{state}</span>
       <span className="text-[9px] text-slate-400 font-mono">{date}</span>
    </div>
    <p className="text-[10px] text-slate-400 font-medium">{op}</p>
  </div>
);

const FileCard = ({ name, size, type }: any) => (
   <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between hover:border-blue-200 transition-colors cursor-pointer group">
      <div className="flex items-center gap-3 min-w-0">
         <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-black uppercase ${type === 'json' ? 'bg-amber-100 text-amber-700' : type === 'pdf' ? 'bg-red-100 text-red-700' : 'bg-slate-200 text-slate-600'}`}>
            {type}
         </div>
         <span className="text-xs font-bold text-slate-600 truncate group-hover:text-blue-600 transition-colors">{name}</span>
      </div>
      <span className="text-[9px] font-black text-slate-400 bg-white px-2 py-1 rounded-md border border-slate-100 shadow-sm">{size}</span>
   </div>
);

export default UnitExplorer;
