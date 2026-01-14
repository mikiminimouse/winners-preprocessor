
import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  Play, 
  Settings as SettingsIcon, 
  Database, 
  BarChart3, 
  Clock,
  History,
  Activity
} from 'lucide-react';
import Dashboard from './components/Dashboard';
import ProcessingControl from './components/ProcessingControl';
import UnitExplorer from './components/UnitExplorer';
import Statistics from './components/Statistics';
import Settings from './components/Settings';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'process' | 'units' | 'stats' | 'settings'>('dashboard');
  const [protocolDate, setProtocolDate] = useState('2025-03-20');

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col">
        <div className="p-6">
          <div className="flex items-center gap-3 text-white mb-8">
            <div className="bg-blue-600 p-2 rounded-lg">
              <Activity className="w-6 h-6" />
            </div>
            <span className="font-bold text-xl tracking-tight">DocPrep v2</span>
          </div>
          
          <nav className="space-y-1">
            <NavItem 
              active={activeTab === 'dashboard'} 
              onClick={() => setActiveTab('dashboard')} 
              icon={<LayoutDashboard size={20} />} 
              label="Dashboard" 
            />
            <NavItem 
              active={activeTab === 'process'} 
              onClick={() => setActiveTab('process')} 
              icon={<Play size={20} />} 
              label="Pipeline Run" 
            />
            <NavItem 
              active={activeTab === 'units'} 
              onClick={() => setActiveTab('units')} 
              icon={<Database size={20} />} 
              label="Unit Explorer" 
            />
            <NavItem 
              active={activeTab === 'stats'} 
              onClick={() => setActiveTab('stats')} 
              icon={<BarChart3 size={20} />} 
              label="Analytics" 
            />
            <div className="pt-4 mt-4 border-t border-slate-800">
              <NavItem 
                active={activeTab === 'settings'} 
                onClick={() => setActiveTab('settings')} 
                icon={<SettingsIcon size={20} />} 
                label="System Config" 
              />
            </div>
          </nav>
        </div>

        <div className="mt-auto p-6 bg-slate-800/50">
          <div className="flex items-center gap-3 text-xs mb-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span>Engine Connected</span>
          </div>
          <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">v2.1.0-STABLE</p>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
             <h2 className="text-lg font-semibold text-slate-800 capitalize">{activeTab}</h2>
             <span className="text-slate-300">|</span>
             <div className="flex items-center gap-2 text-sm text-slate-500">
                <Clock size={14} />
                <span>Working Protocol: {protocolDate}</span>
             </div>
          </div>
          <div className="flex items-center gap-3">
             <button className="px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-md transition-colors flex items-center gap-2">
                <History size={16} />
                Audit Logs
             </button>
             <button className="px-4 py-1.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md shadow-sm transition-all flex items-center gap-2">
                <Play size={16} />
                Fast Run
             </button>
          </div>
        </header>

        {/* Dynamic View */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
          {activeTab === 'dashboard' && <Dashboard protocolDate={protocolDate} />}
          {activeTab === 'process' && <ProcessingControl protocolDate={protocolDate} />}
          {activeTab === 'units' && <UnitExplorer />}
          {activeTab === 'stats' && <Statistics />}
          {activeTab === 'settings' && <Settings />}
        </div>
      </main>
    </div>
  );
};

interface NavItemProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}

const NavItem: React.FC<NavItemProps> = ({ active, onClick, icon, label }) => (
  <button
    onClick={onClick}
    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
      active 
        ? 'bg-blue-600/10 text-blue-400 ring-1 ring-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]' 
        : 'text-slate-400 hover:text-white hover:bg-slate-800'
    }`}
  >
    {icon}
    {label}
  </button>
);

export default App;