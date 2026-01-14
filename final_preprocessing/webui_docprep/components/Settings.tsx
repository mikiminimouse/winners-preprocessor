
import React, { useState } from 'react';
import { 
    Save, 
    Shield, 
    HardDrive, 
    Cpu, 
    Terminal, 
    ToggleLeft, 
    ToggleRight, 
    Sliders,
    Check
} from 'lucide-react';

const Settings: React.FC = () => {
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('general');
  const [aiConfidence, setAiConfidence] = useState(85);

  const handleSave = () => {
    setIsSaving(true);
    setTimeout(() => setIsSaving(false), 1500);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in slide-in-from-bottom-4 duration-700 pb-12">
      
      {/* Header */}
      <div className="flex items-center justify-between bg-white p-6 rounded-[32px] border border-slate-200 shadow-sm">
         <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-500">
               <Sliders size={24} />
            </div>
            <div>
               <h2 className="text-xl font-black text-slate-800 tracking-tight">System Configuration</h2>
               <p className="text-xs text-slate-500 font-medium">Manage engine parameters and security policies</p>
            </div>
         </div>
         <button 
            onClick={handleSave}
            className={`flex items-center gap-2 px-8 py-4 text-white font-bold rounded-[20px] transition-all shadow-lg ${isSaving ? 'bg-green-500 shadow-green-200' : 'bg-blue-600 hover:bg-blue-700 shadow-blue-200 hover:scale-105 active:scale-95'}`}
         >
            {isSaving ? <Check size={20} /> : <Save size={20} />}
            {isSaving ? 'Saved!' : 'Apply Changes'}
         </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
         
         {/* Sidebar Nav (Desktop) / Top Nav (Mobile) */}
         <div className="md:col-span-1 space-y-2">
            {[
               { id: 'general', icon: HardDrive, label: 'General & Paths' },
               { id: 'security', icon: Shield, label: 'Security Limits' },
               { id: 'ai', icon: Cpu, label: 'AI Decision Engine' },
            ].map(tab => (
               <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 p-4 rounded-2xl text-sm font-bold transition-all ${
                     activeTab === tab.id 
                     ? 'bg-white text-blue-600 shadow-md ring-1 ring-slate-100' 
                     : 'text-slate-500 hover:bg-white/50 hover:text-slate-700'
                  }`}
               >
                  <tab.icon size={18} />
                  {tab.label}
               </button>
            ))}
         </div>

         {/* Main Content */}
         <div className="md:col-span-2 space-y-6">
            
            {/* General Tab */}
            {activeTab === 'general' && (
               <div className="bg-white rounded-[32px] border border-slate-200 p-8 shadow-sm animate-in fade-in zoom-in-95 duration-300">
                  <h3 className="text-lg font-black text-slate-800 mb-6 flex items-center gap-2">
                     <HardDrive className="text-blue-500" size={20} />
                     System Paths
                  </h3>
                  <div className="space-y-6">
                     <ConfigField 
                        label="Data Root Directory" 
                        value="/root/winners_preprocessor/final_preprocessing/Data" 
                        icon={Terminal}
                        desc="Absolute path to the ingestion volume"
                     />
                     <ConfigField 
                        label="LibreOffice Binary" 
                        value="/usr/bin/libreoffice" 
                        icon={Terminal}
                        desc="Path to the headless office conversion engine"
                     />
                     <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 flex items-center justify-between">
                        <div>
                           <div className="text-sm font-bold text-slate-700">Debug Logging</div>
                           <div className="text-xs text-slate-400">Enable verbose output for cycle operations</div>
                        </div>
                        <ToggleSwitch checked={true} />
                     </div>
                  </div>
               </div>
            )}

            {/* Security Tab */}
            {activeTab === 'security' && (
               <div className="bg-white rounded-[32px] border border-slate-200 p-8 shadow-sm animate-in fade-in zoom-in-95 duration-300">
                  <h3 className="text-lg font-black text-slate-800 mb-6 flex items-center gap-2">
                     <Shield className="text-emerald-500" size={20} />
                     Security & Constraints
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                     <ConfigField label="Max Extraction Size (MB)" value="500" type="number" />
                     <ConfigField label="Max File Nesting Depth" value="10" type="number" />
                     <ConfigField label="Checksum Algorithm" value="SHA256" />
                     <ConfigField label="Audit Log Retention" value="90 Days" />
                  </div>
               </div>
            )}

            {/* AI Tab */}
            {activeTab === 'ai' && (
               <div className="bg-white rounded-[32px] border border-slate-200 p-8 shadow-sm animate-in fade-in zoom-in-95 duration-300">
                  <h3 className="text-lg font-black text-slate-800 mb-6 flex items-center gap-2">
                     <Cpu className="text-purple-500" size={20} />
                     AI Decision Engine
                  </h3>
                  
                  {/* Interactive Slider Widget */}
                  <div className="bg-slate-900 rounded-[24px] p-6 text-white mb-6 relative overflow-hidden">
                     <div className="absolute top-0 right-0 p-8 opacity-10"><Cpu size={120} /></div>
                     <div className="relative z-10">
                        <div className="flex justify-between items-end mb-4">
                           <div>
                              <div className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-1">Confidence Threshold</div>
                              <div className="text-4xl font-black">{aiConfidence}%</div>
                           </div>
                           <div className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${aiConfidence > 90 ? 'bg-red-500' : aiConfidence > 75 ? 'bg-green-500' : 'bg-amber-500'}`}>
                              {aiConfidence > 90 ? 'Strict' : aiConfidence > 75 ? 'Balanced' : 'Permissive'}
                           </div>
                        </div>
                        
                        <input 
                           type="range" 
                           min="50" 
                           max="99" 
                           value={aiConfidence} 
                           onChange={(e) => setAiConfidence(parseInt(e.target.value))}
                           className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
                        />
                        <div className="flex justify-between text-[10px] text-slate-500 font-bold mt-2 uppercase tracking-widest">
                           <span>Permissive (50%)</span>
                           <span>Strict (99%)</span>
                        </div>
                     </div>
                  </div>

                  <p className="text-slate-500 text-xs leading-relaxed p-4 bg-slate-50 rounded-2xl border border-slate-100">
                    The Decision Engine uses a cascaded approach (Magic Bytes → Signatures → Extensions) to resolve file type conflicts. 
                    Higher thresholds reduce false positives but may increase 'Ambiguous' exceptions.
                  </p>
               </div>
            )}
         </div>
      </div>
    </div>
  );
};

const ConfigField: React.FC<{ label: string; value: string; icon?: any; desc?: string; type?: string }> = ({ label, value, icon: Icon, desc, type = 'text' }) => (
  <div className="space-y-2">
    <div className="flex justify-between">
      <label className="text-xs font-bold text-slate-600 uppercase tracking-wide">{label}</label>
    </div>
    <div className="relative group">
       <input 
         type={type} 
         defaultValue={value}
         className="w-full pl-4 pr-10 py-3.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-bold text-slate-700 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-400 outline-none transition-all group-hover:bg-white"
       />
       {Icon && <Icon className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />}
    </div>
    {desc && <p className="text-[10px] text-slate-400 font-medium ml-1">{desc}</p>}
  </div>
);

const ToggleSwitch = ({ checked }: { checked: boolean }) => (
   checked ? <ToggleRight size={32} className="text-blue-500 cursor-pointer" /> : <ToggleLeft size={32} className="text-slate-300 cursor-pointer" />
);

export default Settings;
