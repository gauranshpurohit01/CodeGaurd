import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, ShieldAlert, FileCode2, Layers } from 'lucide-react';
import { MatchReport } from '../types';

interface ReportViewProps {
  reports: MatchReport[];
  querySource: string;
}

export const ReportView: React.FC<ReportViewProps> = ({ reports, querySource }) => {
  const [selectedMatchIndex, setSelectedMatchIndex] = useState(0);

  if (!reports || reports.length === 0) {
    return (
      <div className="flex-1 max-w-7xl mx-auto w-full p-8 flex flex-col items-center justify-center text-center">
        <div className="h-16 w-16 bg-slate-800 rounded-full flex items-center justify-center mb-4 text-slate-500">
          <ShieldAlert className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-200">No Plagiarism Report Available</h2>
        <p className="text-sm text-slate-400 mt-2 max-w-md">
          Open the Editor tab and click <span className="text-rose-400 font-semibold">"Check Plagiarism"</span> to analyze code against stored submissions.
        </p>
      </div>
    );
  }

  const match = reports[selectedMatchIndex] || reports[0];

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case 'likely copied':
        return (
          <div className="flex items-center space-x-1.5 bg-rose-500/10 border border-rose-500/30 text-rose-400 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
            <ShieldAlert className="h-4 w-4" />
            <span>Likely Copied</span>
          </div>
        );
      case 'suspicious':
        return (
          <div className="flex items-center space-x-1.5 bg-amber-500/10 border border-amber-500/30 text-amber-400 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
            <AlertCircle className="h-4 w-4" />
            <span>Suspicious</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center space-x-1.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
            <CheckCircle2 className="h-4 w-4" />
            <span>Low Similarity</span>
          </div>
        );
    }
  };

  return (
    <div className="flex-1 max-w-7xl mx-auto w-full p-4 flex flex-col gap-6">
      {/* Top Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Overall Score */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Overall Match</span>
            {getVerdictBadge(match.verdict)}
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-4xl font-extrabold text-slate-100">
              {Math.round(match.overall_similarity * 100)}%
            </span>
            <span className="text-xs text-slate-400">weighted confidence</span>
          </div>
          <div className="w-full bg-slate-950 h-2 rounded-full mt-3 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                match.overall_similarity >= 0.75
                  ? 'bg-rose-500'
                  : match.overall_similarity >= 0.5
                  ? 'bg-amber-500'
                  : 'bg-emerald-500'
              }`}
              style={{ width: `${Math.round(match.overall_similarity * 100)}%` }}
            />
          </div>
        </div>

        {/* Token Similarity */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Token Level</span>
            <span className="text-xs text-cyan-400 font-mono">Winnowing (K=5, W=4)</span>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-4xl font-extrabold text-cyan-400">
              {Math.round(match.token_similarity * 100)}%
            </span>
            <span className="text-xs text-slate-400">Jaccard index</span>
          </div>
          <div className="w-full bg-slate-950 h-2 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-cyan-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.round(match.token_similarity * 100)}%` }}
            />
          </div>
        </div>

        {/* Logic Similarity */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Logic Level</span>
            <span className="text-xs text-indigo-400 font-mono">AST Tree Alignment</span>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-4xl font-extrabold text-indigo-400">
              {Math.round(match.logic_similarity * 100)}%
            </span>
            <span className="text-xs text-slate-400">canonical structure</span>
          </div>
          <div className="w-full bg-slate-950 h-2 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-indigo-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.round(match.logic_similarity * 100)}%` }}
            />
          </div>
        </div>

        {/* Matched Subtrees Count */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Merkle Subtrees</span>
            <Layers className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-4xl font-extrabold text-emerald-400">
              {match.matched_subtrees.length}
            </span>
            <span className="text-xs text-slate-400">subtrees (size ≥ 3)</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-3 truncate">
            Target: Submission #{match.submission_id ?? 'Direct'} ({match.title || 'Source B'})
          </p>
        </div>
      </div>

      {/* Candidate Selector Tabs */}
      {reports.length > 1 && (
        <div className="flex items-center space-x-2 overflow-x-auto pb-1">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-2">Top Matches:</span>
          {reports.map((r, i) => (
            <button
              key={i}
              onClick={() => setSelectedMatchIndex(i)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                selectedMatchIndex === i
                  ? 'bg-slate-800 border-emerald-500 text-emerald-400 shadow-sm'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              #{r.submission_id || i + 1} {r.title || 'Target'} ({Math.round(r.overall_similarity * 100)}%)
            </button>
          ))}
        </div>
      )}

      {/* Side-by-Side Highlighted Code View */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Query Code */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col shadow-sm">
          <div className="bg-slate-950 px-4 py-2 border-b border-slate-800 flex justify-between items-center text-xs font-mono">
            <span className="text-slate-300 font-semibold flex items-center gap-1.5">
              <FileCode2 className="h-3.5 w-3.5 text-cyan-400" /> Query Submission (A)
            </span>
            <span className="text-slate-500">{match.matched_ranges_a.length} matched region(s)</span>
          </div>
          <div className="p-3 bg-slate-950 font-mono text-xs overflow-auto max-h-[380px] leading-relaxed">
            {querySource.split('\n').map((line, idx) => {
              const lineNum = idx + 1;
              const isMatched = match.matched_ranges_a.some(([s, e]) => lineNum >= s && lineNum <= e);
              return (
                <div
                  key={idx}
                  className={`flex ${
                    isMatched ? 'bg-rose-950/40 border-l-2 border-rose-500 text-rose-200' : 'text-slate-400'
                  }`}
                >
                  <span className="w-10 select-none text-slate-600 text-right pr-3">{lineNum}</span>
                  <span className="whitespace-pre">{line || ' '}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Matched Target Code */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col shadow-sm">
          <div className="bg-slate-950 px-4 py-2 border-b border-slate-800 flex justify-between items-center text-xs font-mono">
            <span className="text-slate-300 font-semibold flex items-center gap-1.5">
              <FileCode2 className="h-3.5 w-3.5 text-emerald-400" /> Compared Submission (B): {match.title}
            </span>
            <span className="text-slate-500">{match.matched_ranges_b.length} matched region(s)</span>
          </div>
          <div className="p-3 bg-slate-950 font-mono text-xs overflow-auto max-h-[380px] leading-relaxed">
            {/* Render matched subtree list or lines */}
            {match.matched_subtrees.length > 0 ? (
              <div className="space-y-2">
                <div className="text-slate-400 text-[11px] mb-2">Identified Maximal Subtree Matches (Merkle Hashes):</div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-[11px]">
                    <thead>
                      <tr className="text-slate-500 border-b border-slate-800">
                        <th className="pb-1.5">Construct Kind</th>
                        <th className="pb-1.5">Subtree Size</th>
                        <th className="pb-1.5">Query Line (A)</th>
                        <th className="pb-1.5">Target Line (B)</th>
                        <th className="pb-1.5">Merkle Hash</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {match.matched_subtrees.map((st, i) => (
                        <tr key={i} className="hover:bg-slate-900/60 text-slate-300">
                          <td className="py-1 text-indigo-400 font-bold">{st.kind}</td>
                          <td className="py-1">{st.size} nodes</td>
                          <td className="py-1 text-cyan-300">Line {st.line_a}</td>
                          <td className="py-1 text-emerald-300">Line {st.line_b}</td>
                          <td className="py-1 text-slate-500 text-[10px]">{st.hash_val.toString(16)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="text-slate-500 italic p-4 text-center">No maximal subtrees &ge; 3 nodes matched.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
