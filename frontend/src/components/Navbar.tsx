import React from 'react';
import { ShieldCheck, Code2, GitCompare, Eye, History } from 'lucide-react';

interface NavbarProps {
  activeTab: 'editor' | 'report' | 'pipeline' | 'submissions';
  setActiveTab: (tab: 'editor' | 'report' | 'pipeline' | 'submissions') => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('editor')}>
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <ShieldCheck className="h-6 w-6 text-slate-950 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="font-bold text-lg bg-gradient-to-r from-slate-100 to-slate-400 bg-clip-text text-transparent">
              CodeGuard
            </h1>
            <p className="text-xs text-slate-400 font-mono">Compiler & Plagiarism Platform</p>
          </div>
        </div>

        <nav className="flex space-x-1 bg-slate-950/60 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('editor')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'editor'
                ? 'bg-slate-800 text-emerald-400 shadow-sm border border-slate-700/60'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Code2 className="h-4 w-4" />
            <span>Editor & Sandbox</span>
          </button>

          <button
            onClick={() => setActiveTab('pipeline')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'pipeline'
                ? 'bg-slate-800 text-cyan-400 shadow-sm border border-slate-700/60'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Eye className="h-4 w-4" />
            <span>Compiler Pipeline</span>
          </button>

          <button
            onClick={() => setActiveTab('report')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'report'
                ? 'bg-slate-800 text-rose-400 shadow-sm border border-slate-700/60'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <GitCompare className="h-4 w-4" />
            <span>Plagiarism Report</span>
          </button>

          <button
            onClick={() => setActiveTab('submissions')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'submissions'
                ? 'bg-slate-800 text-indigo-400 shadow-sm border border-slate-700/60'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <History className="h-4 w-4" />
            <span>Submissions</span>
          </button>
        </nav>
      </div>
    </header>
  );
};
