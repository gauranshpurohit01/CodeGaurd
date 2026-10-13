import React, { useState, useEffect } from 'react';
import { History, GitCompare, RefreshCw, FileCode2 } from 'lucide-react';
import { Submission, MatchReport } from '../types';

interface SubmissionsViewProps {
  onCompareResult: (reports: MatchReport[], queryCode: string) => void;
}

export const SubmissionsView: React.FC<SubmissionsViewProps> = ({ onCompareResult }) => {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedA, setSelectedA] = useState<number | null>(null);
  const [selectedB, setSelectedB] = useState<number | null>(null);
  const [comparing, setComparing] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const fetchSubmissions = async () => {
    setLoading(true);
    try {
      const resp = await fetch('/api/submissions');
      if (resp.ok) {
        const data: Submission[] = await resp.json();
        setSubmissions(data);
      }
    } catch (err: any) {
      setStatus(`Failed to fetch submissions: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubmissions();
  }, []);

  const handleCompareTwo = async () => {
    if (!selectedA || !selectedB || selectedA === selectedB) {
      setStatus('Please select two distinct submissions to compare.');
      return;
    }

    const subA = submissions.find((s) => s.id === selectedA);
    const subB = submissions.find((s) => s.id === selectedB);
    if (!subA || !subB) return;

    setComparing(true);
    setStatus('Computing cross-submission plagiarism comparison...');
    try {
      const resp = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_a: subA.original_source,
          language_a: subA.language,
          source_b: subB.original_source,
          language_b: subB.language,
        }),
      });
      if (resp.ok) {
        const rep: MatchReport = await resp.json();
        rep.title = `${subB.title} (#${subB.id})`;
        rep.submission_id = subB.id;
        onCompareResult([rep], subA.original_source);
      }
    } catch (err: any) {
      setStatus(`Comparison failed: ${err.message}`);
    } finally {
      setComparing(false);
    }
  };

  return (
    <div className="flex-1 max-w-7xl mx-auto w-full p-4 flex flex-col gap-6">
      {/* Top Header & Compare Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-lg flex items-center justify-center">
            <History className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100">Submission History & Database</h2>
            <p className="text-xs text-slate-400">Indexed submissions for plagiarism comparison</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {submissions.length >= 2 && (
            <div className="flex items-center space-x-2 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
              <span className="text-slate-400 pl-2">Compare:</span>
              <select
                value={selectedA ?? ''}
                onChange={(e) => setSelectedA(Number(e.target.value))}
                className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
              >
                <option value="">Select #A</option>
                {submissions.map((s) => (
                  <option key={s.id} value={s.id}>
                    #{s.id} {s.title}
                  </option>
                ))}
              </select>

              <span className="text-slate-500">vs</span>

              <select
                value={selectedB ?? ''}
                onChange={(e) => setSelectedB(Number(e.target.value))}
                className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
              >
                <option value="">Select #B</option>
                {submissions.map((s) => (
                  <option key={s.id} value={s.id}>
                    #{s.id} {s.title}
                  </option>
                ))}
              </select>

              <button
                onClick={handleCompareTwo}
                disabled={comparing || !selectedA || !selectedB}
                className="flex items-center space-x-1.5 bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1 rounded font-medium disabled:opacity-50"
              >
                <GitCompare className="h-3.5 w-3.5" />
                <span>{comparing ? 'Comparing...' : 'Compare Pair'}</span>
              </button>
            </div>
          )}

          <button
            onClick={fetchSubmissions}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-lg"
            title="Refresh submissions"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>
      </div>

      {status && (
        <div className="bg-slate-900 border border-slate-800 p-3 rounded-lg text-xs text-slate-300 font-mono">
          // {status}
        </div>
      )}

      {/* Submissions Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        {submissions.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No submissions stored in database yet. Open the Editor and click "Store" to index submissions.
          </div>
        ) : (
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="bg-slate-950 border-b border-slate-800 text-slate-400">
                <th className="py-2.5 px-4">ID</th>
                <th className="py-2.5 px-4">Title</th>
                <th className="py-2.5 px-4">Language</th>
                <th className="py-2.5 px-4">Snippet</th>
                <th className="py-2.5 px-4">Date Added</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {submissions.map((sub) => (
                <tr key={sub.id} className="hover:bg-slate-950/60 transition-colors">
                  <td className="py-2.5 px-4 font-bold text-slate-400">#{sub.id}</td>
                  <td className="py-2.5 px-4 text-slate-200 font-bold">{sub.title}</td>
                  <td className="py-2.5 px-4">
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-cyan-400 uppercase">
                      {sub.language}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-slate-400 truncate max-w-xs font-mono text-[11px]">
                    {sub.original_source.replace(/\s+/g, ' ')}
                  </td>
                  <td className="py-2.5 px-4 text-slate-500 text-[11px]">
                    {sub.created_at ? new Date(sub.created_at).toLocaleTimeString() : 'Recent'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
