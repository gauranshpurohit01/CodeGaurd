import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, ShieldAlert, FileCode2, Layers, GitCompare, ArrowRightLeft, Sparkles } from 'lucide-react';
import { MatchReport, SupportedLanguage } from '../types';

interface ReportViewProps {
  reports: MatchReport[];
  querySource: string;
  onCustomCompare?: (rep: MatchReport, codeA: string) => void;
}

export const ReportView: React.FC<ReportViewProps> = ({ reports, querySource, onCustomCompare }) => {
  const [selectedMatchIndex, setSelectedMatchIndex] = useState(0);
  const [showDirectCompare, setShowDirectCompare] = useState(reports.length === 0);

  // Direct compare form states
  const [customCodeA, setCustomCodeA] = useState(querySource || `// Code A (e.g. C)
#include <stdio.h>

int factorial(int n) {
    int res = 1;
    for (int i = 1; i <= n; i++) {
        res = res * i;
    }
    return res;
}

int main(void) {
    printf("%d\\n", factorial(5));
    return 0;
}`);
  const [customLangA, setCustomLangA] = useState<SupportedLanguage>('c');

  const [customCodeB, setCustomCodeB] = useState(`// Code B (e.g. Python or C while loop)
def factorial(n: int) -> int:
    ans = 1
    i = 1
    while i <= n:
        ans = ans * i
        i = i + 1
    return ans

def main() -> int:
    print(factorial(5))
    return 0`);
  const [customLangB, setCustomLangB] = useState<SupportedLanguage>('python');
  const [isComparing, setIsComparing] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  const [activeReports, setActiveReports] = useState<MatchReport[]>(reports);
  const [activeQuerySource, setActiveQuerySource] = useState<string>(querySource);

  // Sync with prop updates if they change
  React.useEffect(() => {
    setActiveReports(reports);
    setActiveQuerySource(querySource);
    if (reports.length > 0) {
      setShowDirectCompare(false);
    }
  }, [reports, querySource]);

  const handleRunDirectCompare = async () => {
    setIsComparing(true);
    setCompareError(null);
    try {
      const resp = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_a: customCodeA,
          language_a: customLangA,
          source_b: customCodeB,
          language_b: customLangB,
        }),
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || 'Comparison request failed');
      }
      const data: MatchReport = await resp.json();
      data.title = `Custom Code B (${customLangB.toUpperCase()})`;
      data.target_source = customCodeB;
      setActiveReports([data]);
      setActiveQuerySource(customCodeA);
      setSelectedMatchIndex(0);
      setShowDirectCompare(false);
      if (onCustomCompare) {
        onCustomCompare(data, customCodeA);
      }
    } catch (err: any) {
      setCompareError(err.message || 'Comparison failed');
    } finally {
      setIsComparing(false);
    }
  };

  const match = activeReports[selectedMatchIndex] || activeReports[0];

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
      {/* Top Controls Bar */}
      <div className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-xl p-3 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg flex items-center justify-center">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100">Semantic & Token Plagiarism Inspection</h2>
            <p className="text-xs text-slate-400">Two-tier detection: Winnowing (token-level) & Canonical AST alignment (logic-level)</p>
          </div>
        </div>

        <button
          onClick={() => setShowDirectCompare(!showDirectCompare)}
          className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
        >
          <GitCompare className="h-3.5 w-3.5 text-cyan-400" />
          <span>{showDirectCompare ? 'Hide Custom Compare' : 'Direct Compare 2 Custom Snippets'}</span>
        </button>
      </div>

      {/* Direct Compare Input Form (Collapsible / Default if no reports) */}
      {showDirectCompare && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2 text-sm font-bold text-slate-200">
              <Sparkles className="h-4 w-4 text-emerald-400" />
              <span>Direct Comparison: Paste Any Two Code Snippets</span>
            </div>
            <span className="text-xs text-slate-400">Cross-language supported (C, C++, Python, Java)</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Snippet A */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300 uppercase">Code A (Query):</label>
                <select
                  value={customLangA}
                  onChange={(e) => setCustomLangA(e.target.value as SupportedLanguage)}
                  className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded px-2 py-1 font-medium"
                >
                  <option value="c">C</option>
                  <option value="cpp">C++</option>
                  <option value="python">Python</option>
                  <option value="java">Java</option>
                </select>
              </div>
              <textarea
                value={customCodeA}
                onChange={(e) => setCustomCodeA(e.target.value)}
                rows={10}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-200 focus:outline-none focus:border-cyan-500 leading-relaxed"
                placeholder="Paste code snippet A here..."
              />
            </div>

            {/* Snippet B */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300 uppercase">Code B (Target):</label>
                <select
                  value={customLangB}
                  onChange={(e) => setCustomLangB(e.target.value as SupportedLanguage)}
                  className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded px-2 py-1 font-medium"
                >
                  <option value="c">C</option>
                  <option value="cpp">C++</option>
                  <option value="python">Python</option>
                  <option value="java">Java</option>
                </select>
              </div>
              <textarea
                value={customCodeB}
                onChange={(e) => setCustomCodeB(e.target.value)}
                rows={10}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-200 focus:outline-none focus:border-emerald-500 leading-relaxed"
                placeholder="Paste code snippet B here..."
              />
            </div>
          </div>

          {compareError && (
            <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-lg text-xs text-rose-300 font-mono">
              // Error: {compareError}
            </div>
          )}

          <div className="flex justify-end">
            <button
              onClick={handleRunDirectCompare}
              disabled={isComparing || !customCodeA.trim() || !customCodeB.trim()}
              className="flex items-center space-x-2 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-slate-950 font-bold px-5 py-2 rounded-lg text-xs transition-all shadow-md shadow-emerald-500/20 disabled:opacity-50"
            >
              <ArrowRightLeft className="h-4 w-4 stroke-[2.5]" />
              <span>{isComparing ? 'Analyzing Plagiarism...' : 'Run Direct Plagiarism Comparison'}</span>
            </button>
          </div>
        </div>
      )}

      {/* No Reports Fallback */}
      {(!activeReports || activeReports.length === 0) && !showDirectCompare && (
        <div className="flex-1 max-w-7xl mx-auto w-full p-8 flex flex-col items-center justify-center text-center">
          <div className="h-16 w-16 bg-slate-800 rounded-full flex items-center justify-center mb-4 text-slate-500">
            <ShieldAlert className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-bold text-slate-200">No Plagiarism Report Loaded</h2>
          <p className="text-sm text-slate-400 mt-2 max-w-md">
            Click <span className="text-cyan-400 font-semibold">"Direct Compare 2 Custom Snippets"</span> above or go to the Editor tab to check code against the database.
          </p>
        </div>
      )}

      {/* Report Dashboard */}
      {activeReports && activeReports.length > 0 && match && (
        <>
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
                Target: {match.title || `Submission #${match.submission_id ?? 'Direct'}`}
              </p>
            </div>
          </div>

          {/* Candidate Selector Tabs */}
          {activeReports.length > 1 && (
            <div className="flex items-center space-x-2 overflow-x-auto pb-1">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-2">Top Matches:</span>
              {activeReports.map((r, i) => (
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
              <div className="p-3 bg-slate-950 font-mono text-xs overflow-auto max-h-[420px] leading-relaxed">
                {(activeQuerySource || '').split('\n').map((line, idx) => {
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
              <div className="p-3 bg-slate-950 font-mono text-xs overflow-auto max-h-[420px] leading-relaxed">
                {match.target_source ? (
                  match.target_source.split('\n').map((line, idx) => {
                    const lineNum = idx + 1;
                    const isMatched = match.matched_ranges_b.some(([s, e]) => lineNum >= s && lineNum <= e);
                    return (
                      <div
                        key={idx}
                        className={`flex ${
                          isMatched ? 'bg-emerald-950/40 border-l-2 border-emerald-500 text-emerald-200' : 'text-slate-400'
                        }`}
                      >
                        <span className="w-10 select-none text-slate-600 text-right pr-3">{lineNum}</span>
                        <span className="whitespace-pre">{line || ' '}</span>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-slate-500 italic p-4 text-center">
                    Original target source not stored. Review matched subtrees below.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Bottom Table: Maximal Subtree Matches (Merkle Hashes) */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="bg-slate-950 px-4 py-2.5 border-b border-slate-800 flex justify-between items-center text-xs font-mono">
              <span className="text-slate-300 font-semibold flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-indigo-400" /> Identified Maximal Subtree Matches (Merkle Hashes)
              </span>
              <span className="text-slate-500">{match.matched_subtrees.length} subtree clone(s)</span>
            </div>
            <div className="p-3 overflow-x-auto">
              {match.matched_subtrees.length > 0 ? (
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-800 pb-2">
                      <th className="py-2 px-3">Construct Kind</th>
                      <th className="py-2 px-3">Subtree Size</th>
                      <th className="py-2 px-3">Query Line (A)</th>
                      <th className="py-2 px-3">Target Line (B)</th>
                      <th className="py-2 px-3">Merkle Hash</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {match.matched_subtrees.map((st, i) => (
                      <tr key={i} className="hover:bg-slate-950/60 transition-colors">
                        <td className="py-2 px-3 text-indigo-400 font-bold">{st.kind}</td>
                        <td className="py-2 px-3 text-slate-300">{st.size} nodes</td>
                        <td className="py-2 px-3 text-cyan-300 font-semibold">Line {st.line_a}</td>
                        <td className="py-2 px-3 text-emerald-300 font-semibold">Line {st.line_b}</td>
                        <td className="py-2 px-3 text-slate-500 text-[11px] font-mono">{st.hash_val.toString(16)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="text-slate-500 italic p-4 text-center text-xs">
                  No maximal subtrees &ge; 3 nodes matched. Structural similarity computed via recursive tree alignment.
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
