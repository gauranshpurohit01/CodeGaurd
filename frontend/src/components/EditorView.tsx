import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Play, ArrowRightLeft, ShieldAlert, Save, Terminal, Clock, Cpu, CheckCircle2, AlertTriangle, Globe, ExternalLink, ShieldCheck } from 'lucide-react';
import { SupportedLanguage, RunResponse, ConvertResponse, MatchReport, WebPlagiarismResult } from '../types';

interface EditorViewProps {
  source: string;
  setSource: (s: string) => void;
  language: SupportedLanguage;
  setLanguage: (l: SupportedLanguage) => void;
  onCheckPlagiarism: (report: MatchReport[], webResult?: WebPlagiarismResult) => void;
  onOpenPipeline: () => void;
}

const TEMPLATES: Record<string, { lang: SupportedLanguage; code: string }> = {
  'Factorial (For)': {
    lang: 'c',
    code: `#include <stdio.h>\n\nint factorial(int n) {\n    int res = 1;\n    for (int i = 1; i <= n; i++) {\n        res = res * i;\n    }\n    return res;\n}\n\nint main(void) {\n    printf("%d\\n", factorial(5));\n    return 0;\n}`,
  },
  'Factorial (While)': {
    lang: 'c',
    code: `#include <stdio.h>\n\nint factorial_while(int num) {\n    int ans = 1;\n    int j = 1;\n    while (j <= num) {\n        ans = ans * j;\n        j = j + 1;\n    }\n    return ans;\n}\n\nint main(void) {\n    printf("%d\\n", factorial_while(5));\n    return 0;\n}`,
  },
  'Python Factorial': {
    lang: 'python',
    code: `def factorial(n: int) -> int:\n    res = 1\n    for i in range(1, n + 1):\n        res = res * i\n    return res\n\ndef main() -> int:\n    print(factorial(5))\n    return 0`,
  },
  'Java Factorial': {
    lang: 'java',
    code: `public class Factorial {\n    public static int calc(int n) {\n        int res = 1;\n        for (int i = 1; i <= n; i++) {\n            res *= i;\n        }\n        return res;\n    }\n\n    public static void main(String[] args) {\n        System.out.println(calc(5));\n    }\n}`,
  },
  'Fibonacci (C)': {
    lang: 'c',
    code: `#include <stdio.h>\n\nint fib(int n) {\n    if (n <= 1) return n;\n    return fib(n - 1) + fib(n - 2);\n}\n\nint main(void) {\n    printf("%d\\n", fib(7));\n    return 0;\n}`,
  },
};

export const EditorView: React.FC<EditorViewProps> = ({
  source,
  setSource,
  language,
  setLanguage,
  onCheckPlagiarism,
  onOpenPipeline,
}) => {
  const [stdin, setStdin] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [checkWeb, setCheckWeb] = useState(true);
  const [runResult, setRunResult] = useState<RunResponse | null>(null);
  const [convertResult, setConvertResult] = useState<ConvertResponse | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [submissionTitle, setSubmissionTitle] = useState('My Submission');

  const handleRun = async () => {
    setIsRunning(true);
    setStatusMessage('Compiling and executing in sandbox (with real-time plagiarism check)...');
    try {
      const resp = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language, source, stdin, check_plagiarism: true, check_web: checkWeb }),
      });
      const data: RunResponse = await resp.json();
      setRunResult(data);
      if (data.compile_ok) {
        let msg = 'Execution completed.';
        if (data.web_plagiarism?.matches && data.web_plagiarism.matches.length > 0) {
          msg += ` Found ${data.web_plagiarism.matches.length} matching repositories on GitHub!`;
        }
        setStatusMessage(msg);
      } else {
        setStatusMessage('Compilation failed.');
      }
    } catch (err: any) {
      setStatusMessage(`Error executing code: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleConvert = async () => {
    setIsConverting(true);
    setStatusMessage('Translating source to C IR...');
    try {
      const resp = await fetch('/api/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language, source }),
      });
      const data: ConvertResponse = await resp.json();
      setConvertResult(data);
      if (data.success) {
        setStatusMessage('Successfully converted to compilable C.');
      } else {
        setStatusMessage('Conversion diagnostics generated.');
      }
    } catch (err: any) {
      setStatusMessage(`Conversion error: ${err.message}`);
    } finally {
      setIsConverting(false);
    }
  };

  const handleCheckPlagiarism = async () => {
    setIsChecking(true);
    setStatusMessage('Analyzing token winnowing, AST alignment & live GitHub candidates...');
    try {
      const resp = await fetch('/api/plagiarism/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language, source, compare_with: 'database', check_web: checkWeb }),
      });
      const data = await resp.json();
      onCheckPlagiarism(data.matches, data.web_plagiarism);
    } catch (err: any) {
      setStatusMessage(`Plagiarism check error: ${err.message}`);
    } finally {
      setIsChecking(false);
    }
  };

  const handleSaveSubmission = async () => {
    try {
      const resp = await fetch('/api/submissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: submissionTitle, language, source }),
      });
      const data = await resp.json();
      setStatusMessage(`Saved submission #${data.id} ("${data.title}") to database.`);
    } catch (err: any) {
      setStatusMessage(`Failed to save: ${err.message}`);
    }
  };

  return (
    <div className="flex-1 flex flex-col p-4 gap-4 max-w-7xl mx-auto w-full">
      {/* Top Toolbar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 shadow-sm">
        <div className="flex items-center space-x-3">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Language:</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
            className="bg-slate-950 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-emerald-500 font-medium"
          >
            <option value="c">C (Subset)</option>
            <option value="cpp">C++ (Tolerance)</option>
            <option value="python">Python (Typed Subset)</option>
            <option value="java">Java (Subset)</option>
          </select>

          <div className="h-5 w-[1px] bg-slate-800" />

          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Templates:</label>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(TEMPLATES).map(([name, t]) => (
              <button
                key={name}
                onClick={() => {
                  setLanguage(t.lang);
                  setSource(t.code);
                }}
                className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-md transition-colors"
              >
                {name}
              </button>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="flex items-center space-x-1.5 bg-emerald-600 hover:bg-emerald-500 text-slate-950 px-3.5 py-1.5 rounded-lg text-sm font-semibold transition-all shadow-md shadow-emerald-600/20 disabled:opacity-50"
          >
            <Play className="h-4 w-4 fill-slate-950" />
            <span>{isRunning ? 'Running...' : 'Run'}</span>
          </button>

          {language !== 'c' && language !== 'cpp' && (
            <button
              onClick={handleConvert}
              disabled={isConverting}
              className="flex items-center space-x-1.5 bg-cyan-600 hover:bg-cyan-500 text-white px-3.5 py-1.5 rounded-lg text-sm font-semibold transition-all shadow-md shadow-cyan-600/20 disabled:opacity-50"
            >
              <ArrowRightLeft className="h-4 w-4" />
              <span>{isConverting ? 'Converting...' : 'Convert to C'}</span>
            </button>
          )}

          <button
            onClick={handleCheckPlagiarism}
            disabled={isChecking}
            className="flex items-center space-x-1.5 bg-rose-600 hover:bg-rose-500 text-white px-3.5 py-1.5 rounded-lg text-sm font-semibold transition-all shadow-md shadow-rose-600/20 disabled:opacity-50"
          >
            <ShieldAlert className="h-4 w-4" />
            <span>{isChecking ? 'Checking...' : 'Check Plagiarism'}</span>
          </button>

          <label className="flex items-center space-x-1.5 cursor-pointer bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800 text-xs text-slate-300 hover:border-slate-700 select-none">
            <input
              type="checkbox"
              checked={checkWeb}
              onChange={(e) => setCheckWeb(e.target.checked)}
              className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0"
            />
            <Globe className="h-3.5 w-3.5 text-cyan-400" />
            <span>Live GitHub</span>
          </label>

          <button
            onClick={onOpenPipeline}
            className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg text-sm font-medium border border-slate-700"
          >
            <span>Pipeline View</span>
          </button>

          <button
            onClick={handleSaveSubmission}
            className="flex items-center space-x-1.5 bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg text-sm font-medium"
            title="Save into Plagiarism Database"
          >
            <Save className="h-4 w-4" />
            <span>Store</span>
          </button>
        </div>
      </div>

      {/* Editor & Console Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-[520px]">
        {/* Monaco Editor Container */}
        <div className="lg:col-span-8 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col shadow-sm">
          <div className="bg-slate-950 px-4 py-2 border-b border-slate-800 text-xs font-mono text-slate-400 flex justify-between items-center">
            <span>Source Code ({language.toUpperCase()})</span>
            <span className="text-[10px] text-slate-500">Monaco Editor • UTF-8</span>
          </div>
          <div className="flex-1 min-h-[480px]">
            <Editor
              height="100%"
              language={language === 'c' || language === 'cpp' ? 'c' : language}
              value={source}
              onChange={(val) => setSource(val || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                fontFamily: 'JetBrains Mono, Menlo, monospace',
                padding: { top: 12 },
              }}
            />
          </div>
        </div>

        {/* Right Pane: Stdin + Terminal / Output */}
        <div className="lg:col-span-4 flex flex-col gap-4">
          {/* Stdin Panel */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-col">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Standard Input (stdin):</label>
            <textarea
              value={stdin}
              onChange={(e) => setStdin(e.target.value)}
              placeholder="Arguments or inputs for scanf / input()..."
              rows={3}
              className="bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
            />
          </div>

          {/* Terminal Output */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl flex-1 flex flex-col overflow-hidden">
            <div className="bg-slate-950 px-3.5 py-2 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center space-x-2 text-xs font-mono text-slate-300">
                <Terminal className="h-3.5 w-3.5 text-emerald-400" />
                <span>Execution Output</span>
              </div>
              {runResult && (
                <div className="flex items-center space-x-3 text-[11px] text-slate-400 font-mono">
                  <span className="flex items-center space-x-1">
                    <Clock className="h-3 w-3 text-cyan-400" />
                    <span>{runResult.time_ms} ms</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <Cpu className="h-3 w-3 text-indigo-400" />
                    <span>{runResult.memory_kb} KB</span>
                  </span>
                </div>
              )}
            </div>

            <div className="p-3.5 flex-1 font-mono text-xs overflow-auto bg-slate-950 text-slate-200">
              {statusMessage && (
                <div className="text-slate-400 italic mb-2">// {statusMessage}</div>
              )}

              {runResult && (
                <div>
                  {!runResult.compile_ok ? (
                    <div className="text-rose-400 whitespace-pre-wrap">
                      <div className="font-bold flex items-center gap-1 text-rose-300 mb-1">
                        <AlertTriangle className="h-3.5 w-3.5" /> Compilation Error:
                      </div>
                      {runResult.compiler_messages}
                    </div>
                  ) : (
                    <div>
                      {runResult.stdout ? (
                        <div className="text-emerald-300 whitespace-pre-wrap leading-relaxed">
                          {runResult.stdout}
                        </div>
                      ) : (
                        <div className="text-slate-500 italic">(Program exited without output)</div>
                      )}

                      {runResult.stderr && (
                        <div className="text-amber-400 whitespace-pre-wrap mt-2">
                          stderr:\n{runResult.stderr}
                        </div>
                      )}

                      <div className="mt-3 pt-2 border-t border-slate-800/80 text-[11px] text-slate-400">
                        Process finished with exit code {runResult.exit_code}
                        {runResult.timed_out && ' (TIMED OUT)'}
                      </div>

                      {/* Real-Time Web & GitHub Plagiarism Matches */}
                      {runResult.web_plagiarism && runResult.web_plagiarism.checked && (
                        <div className="mt-3 pt-3 border-t border-slate-800">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-semibold text-cyan-400 flex items-center gap-1.5 text-xs">
                              <Globe className="h-3.5 w-3.5" /> Live GitHub Plagiarism Matches:
                            </span>
                            {runResult.web_plagiarism.search_queries_used.length > 0 && (
                              <span className="text-[10px] text-slate-500 font-mono">
                                Queries: {runResult.web_plagiarism.search_queries_used.slice(0, 2).join(', ')}
                              </span>
                            )}
                          </div>

                          {runResult.web_plagiarism.matches.length > 0 ? (
                            <div className="space-y-1.5">
                              {runResult.web_plagiarism.matches.map((m, i) => (
                                <div key={i} className="bg-slate-900 border border-slate-800 rounded-lg p-2.5 flex items-center justify-between text-xs">
                                  <div className="flex items-center space-x-2 truncate">
                                    <a
                                      href={m.source_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-cyan-400 hover:underline flex items-center gap-1 font-semibold truncate"
                                      title={m.source_url}
                                    >
                                      <span>{m.repository}</span>
                                      <ExternalLink className="h-3 w-3 shrink-0" />
                                    </a>
                                  </div>
                                  <div className="flex items-center space-x-2.5 shrink-0 text-[11px]">
                                    <span className="text-slate-400">Token: <strong className="text-slate-200">{m.token_similarity}</strong></span>
                                    <span className="text-slate-400">Logic: <strong className="text-slate-200">{m.logic_similarity}</strong></span>
                                    <span className="px-2 py-0.5 rounded font-bold text-slate-950 bg-rose-400">
                                      {m.composite_score}
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-slate-500 text-[11px] italic">
                              {runResult.web_plagiarism.status_message || 'No live open-source matches exceeded 35% threshold.'}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {convertResult && (
                <div className="mt-4 pt-3 border-t border-slate-800">
                  <div className="font-semibold text-cyan-400 mb-1 flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Generated C Source:
                  </div>
                  <pre className="text-slate-300 bg-slate-900 p-2.5 rounded-lg border border-slate-800 text-[11px] overflow-auto max-h-48">
                    {convertResult.c_source}
                  </pre>
                  {convertResult.diagnostics.length > 0 && (
                    <div className="mt-2 text-rose-400 text-[11px]">
                      {convertResult.diagnostics.map((d, i) => (
                        <div key={i}>• {d}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
