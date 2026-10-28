import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, ShieldAlert, FileCode2, Layers, GitCompare, ArrowRightLeft, Sparkles, Globe, ExternalLink, Database } from 'lucide-react';
import { MatchReport, SupportedLanguage, WebPlagiarismResult } from '../types';

interface ReportViewProps {
  reports: MatchReport[];
  querySource: string;
  webPlagiarism?: WebPlagiarismResult;
  onCustomCompare?: (rep: MatchReport, codeA: string) => void;
}

type ActiveSourceTab = 'web' | 'local' | 'custom';

export const ReportView: React.FC<ReportViewProps> = ({ reports, querySource, webPlagiarism, onCustomCompare }) => {
  // Check if web plagiarism returned matches
  const hasWebMatches = !!(webPlagiarism && webPlagiarism.matches && webPlagiarism.matches.length > 0);

  // Default to 'web' (Internet / GitHub) as the primary plagiarism check
  const [activeSourceTab, setActiveSourceTab] = useState<ActiveSourceTab>('web');

  const [selectedWebMatchIndex, setSelectedWebMatchIndex] = useState(0);
  const [selectedLocalMatchIndex, setSelectedLocalMatchIndex] = useState(0);

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
  const [customMatch, setCustomMatch] = useState<MatchReport | null>(null);

  const [activeQuerySource, setActiveQuerySource] = useState<string>(querySource);

  // Automatically select 'web' tab whenever internet plagiarism checking was performed
  React.useEffect(() => {
    if (webPlagiarism && webPlagiarism.checked) {
      setActiveSourceTab('web');
      if (webPlagiarism.matches && webPlagiarism.matches.length > 0) {
        setSelectedWebMatchIndex(0);
      }
    } else if (webPlagiarism === undefined && reports.length > 0) {
      // Only switch to local when web check was not run (e.g. Submissions view compare)
      setActiveSourceTab('local');
      setSelectedLocalMatchIndex(0);
    }
    setActiveQuerySource(querySource);
  }, [reports, querySource, webPlagiarism]);

  // Convert web matches into normalized MatchReport structures
  const webReports: MatchReport[] = (webPlagiarism?.matches || []).map((m) => {
    const tokSim = m.token_similarity_num != null
      ? m.token_similarity_num
      : parseFloat(m.token_similarity || '0') / 100;
    const compScore = m.composite_score_num != null
      ? m.composite_score_num
      : parseFloat(m.composite_score || '0') / 100;
    const logSim = m.logic_similarity_num != null
      ? m.logic_similarity_num
      : parseFloat(m.logic_similarity || '0') / 100;

    return {
      submission_id: undefined,
      title: m.repository,
      source_url: m.source_url,
      overall_similarity: compScore,
      token_similarity: tokSim,
      token_containment_a: tokSim,
      token_containment_b: tokSim,
      logic_similarity: logSim,
      matched_ranges_a: m.matched_ranges_a || [],
      matched_ranges_b: m.matched_ranges_b || [],
      matched_subtrees: m.matched_subtrees || [],
      verdict: m.verdict || (compScore >= 0.70 ? 'likely copied' : compScore >= 0.40 ? 'suspicious' : 'low'),
      target_source: m.target_source || `// Candidate source from ${m.source_url}\n// (Full source fetched via GitHub API)`,
    };
  });

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
      setCustomMatch(data);
      setActiveQuerySource(customCodeA);
      setActiveSourceTab('custom');
      if (onCustomCompare) {
        onCustomCompare(data, customCodeA);
      }
    } catch (err: any) {
      setCompareError(err.message || 'Comparison failed');
    } finally {
      setIsComparing(false);
    }
  };

  // Determine currently active match depending on active tab
  let currentReports: MatchReport[] = [];
  let currentIndex = 0;
  let onSelectIndex = (idx: number) => {};

  if (activeSourceTab === 'web') {
    currentReports = webReports;
    currentIndex = selectedWebMatchIndex;
    onSelectIndex = setSelectedWebMatchIndex;
  } else if (activeSourceTab === 'local') {
    currentReports = reports;
    currentIndex = selectedLocalMatchIndex;
    onSelectIndex = setSelectedLocalMatchIndex;
  } else if (activeSourceTab === 'custom') {
    currentReports = customMatch ? [customMatch] : [];
    currentIndex = 0;
    onSelectIndex = () => {};
  }

  const match = currentReports[currentIndex] || currentReports[0];

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
      {/* Top Source Switcher Navigation Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900 border border-slate-800 rounded-xl p-3.5 shadow-sm">
        {/* Toggle Mode Buttons */}
        <div className="flex flex-wrap items-center gap-1.5 bg-slate-950 p-1.5 rounded-lg border border-slate-800">
          <button
            onClick={() => setActiveSourceTab('web')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all ${
              activeSourceTab === 'web'
                ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md shadow-cyan-500/25 ring-1 ring-cyan-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Globe className="h-4 w-4 text-cyan-300" />
            <span>🌐 Internet & GitHub Plagiarism</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[11px] font-mono font-bold ${
                activeSourceTab === 'web' ? 'bg-cyan-950 text-cyan-200 border border-cyan-400/40' : 'bg-slate-800 text-slate-300'
              }`}
            >
              {webReports.length}
            </span>
          </button>

          <button
            onClick={() => setActiveSourceTab('local')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all ${
              activeSourceTab === 'local'
                ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-md shadow-emerald-500/25 ring-1 ring-emerald-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Database className="h-4 w-4 text-emerald-300" />
            <span>📁 Classroom Submissions (Optional)</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[11px] font-mono font-bold ${
                activeSourceTab === 'local' ? 'bg-emerald-950 text-emerald-200 border border-emerald-400/40' : 'bg-slate-800 text-slate-300'
              }`}
            >
              {reports.length}
            </span>
          </button>

          <button
            onClick={() => setActiveSourceTab('custom')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all ${
              activeSourceTab === 'custom'
                ? 'bg-slate-800 text-cyan-300 border border-cyan-500/60 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <GitCompare className="h-4 w-4" />
            <span>⚡ Direct 2-Snippet Compare</span>
          </button>
        </div>

        {/* Mode Description Tag */}
        <div className="flex items-center space-x-2">
          {activeSourceTab === 'web' && (
            <span className="text-xs font-mono text-cyan-300 bg-cyan-950/70 border border-cyan-800/80 px-3 py-1.5 rounded-lg flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
              <span>Target: Public GitHub Code Search & TheAlgorithms / GeeksforGeeks Archive</span>
            </span>
          )}
          {activeSourceTab === 'local' && (
            <span className="text-xs font-mono text-emerald-300 bg-emerald-950/70 border border-emerald-800/80 px-3 py-1.5 rounded-lg flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              <span>Target: Classroom Assignment SQLite Database Submissions</span>
            </span>
          )}
          {activeSourceTab === 'custom' && (
            <span className="text-xs font-mono text-amber-300 bg-amber-950/70 border border-amber-800/80 px-3 py-1.5 rounded-lg">
              Direct Two-Source Cross-Language Inspection
            </span>
          )}
        </div>
      </div>

      {/* WEB MODE HEADER: Signatures & Search Status */}
      {activeSourceTab === 'web' && webPlagiarism && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2.5">
              <div className="h-9 w-9 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 rounded-lg flex items-center justify-center">
                <Globe className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <span>Live Internet (GitHub) Plagiarism Search</span>
                  <span className="text-[11px] bg-cyan-950 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded-full font-mono">
                    {webReports.length} candidate{webReports.length === 1 ? '' : 's'} identified
                  </span>
                </h3>
                <p className="text-xs text-slate-400">
                  {webPlagiarism.status_message || 'Analyzed distinctive high-entropy signatures against public open-source repositories.'}
                </p>
              </div>
            </div>

            {webPlagiarism.search_queries_used && webPlagiarism.search_queries_used.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-400">
                <span className="font-semibold text-slate-500 uppercase tracking-wider text-[10px]">Queried Signatures:</span>
                {webPlagiarism.search_queries_used.map((q, idx) => (
                  <span key={idx} className="bg-slate-950 border border-slate-800 text-cyan-300 font-mono text-xs px-2.5 py-1 rounded">
                    {q}
                  </span>
                ))}
              </div>
            )}
          </div>

          {webReports.length === 0 && (
            <div className="text-xs text-slate-400 italic py-2">
              No matching open-source candidate files met or exceeded the 20% similarity threshold. You can also view the local database submissions using the tabs above.
            </div>
          )}
        </div>
      )}

      {/* DIRECT COMPARE FORM (Visible when in custom mode) */}
      {activeSourceTab === 'custom' && (
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

      {/* NO MATCHES FALLBACK FOR ACTIVE MODE */}
      {currentReports.length === 0 && activeSourceTab !== 'custom' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 flex flex-col items-center justify-center text-center shadow-sm">
          <div className="h-14 w-14 bg-emerald-500/10 border border-emerald-500/30 rounded-full flex items-center justify-center mb-3 text-emerald-400">
            {activeSourceTab === 'web' ? <CheckCircle2 className="h-7 w-7 text-emerald-400" /> : <ShieldAlert className="h-7 w-7 text-emerald-400" />}
          </div>
          <h3 className="text-base font-bold text-slate-200">
            {activeSourceTab === 'web' ? 'Internet & GitHub Plagiarism Search Completed' : 'No Local Database Submissions'}
          </h3>
          <p className="text-xs text-slate-400 mt-2 max-w-lg leading-relaxed">
            {activeSourceTab === 'web'
              ? 'CodeGuard queried GitHub and public internet repositories using your code signatures. No open-source candidates exceeded similarity thresholds — your code appears to be original and clean of public plagiarism!'
              : 'The local submissions database does not contain any records for comparison.'}
          </p>
          {activeSourceTab === 'web' && reports.length > 0 && (
            <button
              onClick={() => setActiveSourceTab('local')}
              className="mt-4 flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-slate-700 px-4 py-2 rounded-lg text-xs font-semibold transition-all shadow-sm"
            >
              <Database className="h-4 w-4 text-emerald-400" />
              <span>Inspect Local Database Matches ({reports.length} Submissions)</span>
            </button>
          )}
        </div>
      )}

      {/* DASHBOARD: OVERVIEW CARDS & CANDIDATE SELECTOR & DIFF VIEWER */}
      {currentReports.length > 0 && match && (
        <>
          {/* Top Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Overall Score */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between shadow-sm">
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
                    match.overall_similarity >= 0.70
                      ? 'bg-rose-500'
                      : match.overall_similarity >= 0.40
                      ? 'bg-amber-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: `${Math.round(match.overall_similarity * 100)}%` }}
                />
              </div>
            </div>

            {/* Token Similarity */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between shadow-sm">
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
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between shadow-sm">
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

            {/* Target Source Info Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between shadow-sm">
              <div className="flex justify-between items-start">
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Compared Source</span>
                {match.source_url ? (
                  <a
                    href={match.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center space-x-1 text-cyan-400 hover:text-cyan-300 text-xs font-semibold"
                  >
                    <span>GitHub</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                ) : (
                  <Layers className="h-4 w-4 text-emerald-400" />
                )}
              </div>
              <div className="mt-2">
                <span className="text-sm font-bold text-slate-100 block truncate" title={match.title}>
                  {match.title || `Submission #${match.submission_id ?? 'Direct'}`}
                </span>
                <span className="text-xs text-slate-400 block mt-0.5">
                  {match.matched_subtrees?.length || 0} Merkle subtree clones identified
                </span>
              </div>
              {match.source_url ? (
                <a
                  href={match.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 flex items-center justify-center space-x-1.5 bg-slate-950 hover:bg-slate-800 text-cyan-300 border border-slate-800 hover:border-cyan-500/50 py-1 px-2 rounded text-[11px] font-mono transition-all"
                >
                  <ExternalLink className="h-3 w-3" />
                  <span className="truncate">View Public Repo</span>
                </a>
              ) : (
                <p className="text-[11px] text-slate-500 mt-2 truncate">
                  Database ID: #{match.submission_id ?? 'Direct'}
                </p>
              )}
            </div>
          </div>

          {/* Candidate Selector Tabs */}
          {currentReports.length > 1 && (
            <div className="flex items-center space-x-2 overflow-x-auto pb-1">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-2 shrink-0">
                {activeSourceTab === 'web' ? 'Internet Candidates:' : 'Database Matches:'}
              </span>
              {currentReports.map((r, i) => (
                <button
                  key={i}
                  onClick={() => onSelectIndex(i)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 shrink-0 ${
                    currentIndex === i
                      ? activeSourceTab === 'web'
                        ? 'bg-slate-800 border-cyan-500 text-cyan-300 shadow-sm'
                        : 'bg-slate-800 border-emerald-500 text-emerald-400 shadow-sm'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {activeSourceTab === 'web' && <Globe className="h-3 w-3 shrink-0" />}
                  <span className="truncate max-w-[200px]">
                    #{i + 1} {r.title || 'Target'}
                  </span>
                  <span className="font-bold">({Math.round(r.overall_similarity * 100)}%)</span>
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
                  <FileCode2 className="h-3.5 w-3.5 text-cyan-400" /> Query Submission (Your Code)
                </span>
                <span className="text-slate-500">{match.matched_ranges_a?.length || 0} matched region(s)</span>
              </div>
              <div className="p-3 bg-slate-950 font-mono text-xs overflow-auto max-h-[440px] leading-relaxed">
                {(activeQuerySource || '').split('\n').map((line, idx) => {
                  const lineNum = idx + 1;
                  const isMatched = (match.matched_ranges_a || []).some(([s, e]) => lineNum >= s && lineNum <= e);
                  return (
                    <div
                      key={idx}
                      className={`flex ${
                        isMatched ? 'bg-rose-950/40 border-l-2 border-rose-500 text-rose-200 font-medium' : 'text-slate-400'
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
                <span className="text-slate-300 font-semibold flex items-center gap-1.5 truncate max-w-[70%]">
                  {activeSourceTab === 'web' ? (
                    <Globe className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                  ) : (
                    <FileCode2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                  )}
                  <span className="truncate">
                    {activeSourceTab === 'web' ? `GitHub Candidate: ${match.title}` : `Target: ${match.title}`}
                  </span>
                </span>
                <div className="flex items-center space-x-2">
                  {match.source_url && (
                    <a
                      href={match.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 text-[11px]"
                    >
                      <span>Open Link</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                  <span className="text-slate-500">{match.matched_ranges_b?.length || 0} match(es)</span>
                </div>
              </div>
              <div className="p-3 bg-slate-950 font-mono text-xs overflow-auto max-h-[440px] leading-relaxed">
                {match.target_source ? (
                  match.target_source.split('\n').map((line, idx) => {
                    const lineNum = idx + 1;
                    const isMatched = (match.matched_ranges_b || []).some(([s, e]) => lineNum >= s && lineNum <= e);
                    return (
                      <div
                        key={idx}
                        className={`flex ${
                          isMatched ? 'bg-emerald-950/40 border-l-2 border-emerald-500 text-emerald-200 font-medium' : 'text-slate-400'
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
              <span className="text-slate-500">{match.matched_subtrees?.length || 0} subtree clone(s)</span>
            </div>
            <div className="p-3 overflow-x-auto">
              {match.matched_subtrees && match.matched_subtrees.length > 0 ? (
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
                  No maximal subtrees &ge; 3 nodes matched. Structural similarity computed via recursive AST alignment.
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
