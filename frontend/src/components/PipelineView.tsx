import React, { useState, useEffect } from 'react';
import { Eye, Code2, GitFork, Wand2, RefreshCw } from 'lucide-react';
import { ASTViewResponse, SupportedLanguage } from '../types';

interface PipelineViewProps {
  source: string;
  language: SupportedLanguage;
}

export const PipelineView: React.FC<PipelineViewProps> = ({ source, language }) => {
  const [pipelineData, setPipelineData] = useState<ASTViewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeStage, setActiveStage] = useState<'tokens' | 'raw_ast' | 'canonical_ast' | 'generated_c'>('raw_ast');

  const fetchPipeline = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch('/api/ast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language, source }),
      });
      if (!resp.ok) {
        throw new Error(`Failed to load compiler pipeline: ${resp.statusText}`);
      }
      const data: ASTViewResponse = await resp.json();
      setPipelineData(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipeline();
  }, [source, language]);

  return (
    <div className="flex-1 max-w-7xl mx-auto w-full p-4 flex flex-col gap-4">
      {/* Stage Tabs Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-2.5 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setActiveStage('tokens')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeStage === 'tokens'
                ? 'bg-slate-800 text-cyan-400 border border-slate-700/80'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Code2 className="h-3.5 w-3.5" />
            <span>1. Lexer Tokens ({pipelineData?.tokens.length || 0})</span>
          </button>

          <button
            onClick={() => setActiveStage('raw_ast')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeStage === 'raw_ast'
                ? 'bg-slate-800 text-indigo-400 border border-slate-700/80'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <GitFork className="h-3.5 w-3.5" />
            <span>2. Parser Shared AST</span>
          </button>

          <button
            onClick={() => setActiveStage('canonical_ast')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeStage === 'canonical_ast'
                ? 'bg-slate-800 text-emerald-400 border border-slate-700/80'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Wand2 className="h-3.5 w-3.5" />
            <span>3. Canonicalized AST</span>
          </button>

          <button
            onClick={() => setActiveStage('generated_c')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeStage === 'generated_c'
                ? 'bg-slate-800 text-amber-400 border border-slate-700/80'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Eye className="h-3.5 w-3.5" />
            <span>4. C Codegen Output</span>
          </button>
        </div>

        <button
          onClick={fetchPipeline}
          disabled={loading}
          className="flex items-center space-x-1 text-xs text-slate-400 hover:text-slate-200 px-2 py-1 rounded bg-slate-800/80"
          title="Refresh Pipeline Stages"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-emerald-400' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Main Content Area */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex-1 min-h-[480px] p-4 flex flex-col shadow-sm">
        {loading && (
          <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">
            <RefreshCw className="h-5 w-5 animate-spin mr-2 text-cyan-400" />
            Decomposing compiler pipeline phases...
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-950/40 border border-rose-800 text-rose-300 rounded-lg text-xs font-mono">
            {error}
          </div>
        )}

        {!loading && pipelineData && (
          <div className="flex-1 flex flex-col">
            {/* Stage 1: Tokens Table */}
            {activeStage === 'tokens' && (
              <div className="flex-1 overflow-auto max-h-[580px]">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="py-2 px-3">#</th>
                      <th className="py-2 px-3">Token Kind</th>
                      <th className="py-2 px-3">Normalized Value</th>
                      <th className="py-2 px-3">Raw Source Text</th>
                      <th className="py-2 px-3">Position</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {pipelineData.tokens.map((tok, i) => (
                      <tr key={i} className="hover:bg-slate-950/60 transition-colors">
                        <td className="py-1.5 px-3 text-slate-600">{i + 1}</td>
                        <td className="py-1.5 px-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                              tok.kind === 'KEYWORD'
                                ? 'bg-cyan-950 text-cyan-400'
                                : tok.kind === 'IDENTIFIER'
                                ? 'bg-indigo-950 text-indigo-400'
                                : tok.kind === 'NUMBER'
                                ? 'bg-emerald-950 text-emerald-400'
                                : tok.kind === 'OPERATOR'
                                ? 'bg-amber-950 text-amber-400'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            {tok.kind}
                          </span>
                        </td>
                        <td className="py-1.5 px-3 text-slate-200 font-bold">{tok.value}</td>
                        <td className="py-1.5 px-3 text-slate-400">{tok.raw}</td>
                        <td className="py-1.5 px-3 text-slate-500 text-[11px]">
                          L{tok.line}:C{tok.col}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Stage 2: Raw AST */}
            {activeStage === 'raw_ast' && (
              <div className="flex-1 flex flex-col">
                <div className="text-xs text-slate-400 mb-2">
                  Shared Node IR produced by hand-written recursive-descent parser before canonicalization:
                </div>
                <pre className="flex-1 bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-indigo-300 overflow-auto max-h-[580px] leading-relaxed">
                  {JSON.stringify(pipelineData.raw_ast, null, 2)}
                </pre>
              </div>
            )}

            {/* Stage 3: Canonical AST */}
            {activeStage === 'canonical_ast' && (
              <div className="flex-1 flex flex-col">
                <div className="text-xs text-slate-400 mb-2">
                  Normalized AST post-canonicalization (for/while unified to Loop, ternary collapsed, commutative ops sorted):
                </div>
                <pre className="flex-1 bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-emerald-300 overflow-auto max-h-[580px] leading-relaxed">
                  {JSON.stringify(pipelineData.canonical_ast, null, 2)}
                </pre>
              </div>
            )}

            {/* Stage 4: Generated C Source */}
            {activeStage === 'generated_c' && (
              <div className="flex-1 flex flex-col">
                <div className="text-xs text-slate-400 mb-2">
                  Compilable C code emitted by <code className="text-amber-400">c_codegen.py</code> from the shared IR:
                </div>
                <pre className="flex-1 bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-amber-200 overflow-auto max-h-[580px] leading-relaxed">
                  {pipelineData.generated_c}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
