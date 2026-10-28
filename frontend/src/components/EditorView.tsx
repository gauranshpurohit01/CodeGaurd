import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Play, ArrowRightLeft, ShieldAlert, Save, Terminal, Clock, Cpu, CheckCircle2, AlertTriangle, Globe, ExternalLink, ShieldCheck, ListChecks, Plus, Trash2, XCircle, Sparkles } from 'lucide-react';
import { SupportedLanguage, RunResponse, ConvertResponse, MatchReport, WebPlagiarismResult } from '../types';

interface TestCaseItem {
  id: string;
  input: string;
  expected: string;
}

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
  const [inputMode, setInputMode] = useState<'tests' | 'stdin'>('tests');
  const [testCases, setTestCases] = useState<TestCaseItem[]>([
    { id: '1', input: '', expected: '120' },
    { id: '2', input: '5', expected: '120' },
    { id: '3', input: '3', expected: '6' },
  ]);
  const [activeTestCaseIndex, setActiveTestCaseIndex] = useState(0);

  const [isRunning, setIsRunning] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [checkWeb, setCheckWeb] = useState(true);
  const [runResult, setRunResult] = useState<RunResponse | null>(null);
  const [convertResult, setConvertResult] = useState<ConvertResponse | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [submissionTitle, setSubmissionTitle] = useState('My Submission');

  const handleAddTestCase = () => {
    const newId = String(Date.now());
    const newCase: TestCaseItem = { id: newId, input: '', expected: '' };
    setTestCases((prev) => [...prev, newCase]);
    setActiveTestCaseIndex(testCases.length);
  };

  const handleRemoveTestCase = (indexToRemove: number) => {
    if (testCases.length <= 1) return;
    const updated = testCases.filter((_, i) => i !== indexToRemove);
    setTestCases(updated);
    if (activeTestCaseIndex >= updated.length) {
      setActiveTestCaseIndex(updated.length - 1);
    }
  };

  const handleUpdateTestCase = (field: 'input' | 'expected', value: string) => {
    setTestCases((prev) => {
      const copy = [...prev];
      if (copy[activeTestCaseIndex]) {
        copy[activeTestCaseIndex] = {
          ...copy[activeTestCaseIndex],
          [field]: value,
        };
      }
      return copy;
    });
  };

  const parseApiResponse = async <T,>(resp: Response): Promise<T> => {
    if (!resp.ok) {
      let detail = '';
      try {
        const errJson = await resp.json();
        detail = errJson.detail || '';
      } catch {
        detail = await resp.text().catch(() => '');
      }
      if (resp.status === 502 || resp.status === 503 || resp.status === 504) {
        throw new Error("Backend server is not running on http://localhost:8000. Please start it using 'make run-backend' in your terminal.");
      }
      throw new Error(detail || `Server error (${resp.status} ${resp.statusText})`);
    }
    try {
      return (await resp.json()) as T;
    } catch {
      throw new Error("Backend returned empty response. Please verify backend is running on port 8000 ('make run-backend').");
    }
  };

  const handleRun = async () => {
    setIsRunning(true);
    setStatusMessage(
      inputMode === 'tests'
        ? `Compiling & running batch test suite (${testCases.length} test cases)...`
        : 'Compiling and executing in sandbox (with real-time plagiarism check)...'
    );
    try {
      const testsPayload =
        inputMode === 'tests' && testCases.length > 0
          ? testCases.map((tc) => [tc.input, tc.expected])
          : undefined;

      const resp = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          language,
          source,
          stdin: inputMode === 'stdin' ? stdin : '',
          tests: testsPayload,
          check_plagiarism: true,
          check_web: checkWeb,
        }),
      });
      const data: RunResponse = await parseApiResponse<RunResponse>(resp);
      setRunResult(data);
      if (data.compile_ok) {
        let msg = 'Execution completed.';
        if (data.test_results && data.test_results.length > 0) {
          const passed = data.test_results.filter((r) => r.passed).length;
          msg = `Test Suite: ${passed}/${data.test_results.length} test cases passed.`;
        }
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
      const data: ConvertResponse = await parseApiResponse<ConvertResponse>(resp);
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
      const data: any = await parseApiResponse(resp);
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
            <span>{isRunning ? 'Running...' : inputMode === 'tests' ? `Run Test Suite (${testCases.length})` : 'Run & Execute'}</span>
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

      {/* Language Mismatch Warning Banner */}
      {((language === 'python' && (source.trim().startsWith('#include') || source.includes('int main') || source.includes('printf('))) ||
        (language === 'c' && (source.trim().startsWith('def ') || source.includes('print('))) ||
        (language === 'java' && (source.trim().startsWith('#include') || source.trim().startsWith('def ')))) && (
        <div className="bg-amber-950/60 border border-amber-600/50 rounded-xl p-3 flex flex-wrap items-center justify-between gap-2 text-xs text-amber-200 shadow-sm animate-pulse">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
            <span>
              {language === 'python' && source.trim().startsWith('#include')
                ? "Language Mismatch: You have C code in the editor, but the language dropdown is set to 'Python (Typed Subset)'."
                : "Language Mismatch: The code syntax does not match the selected language dropdown."}
            </span>
          </div>
          <button
            onClick={() => {
              if (source.trim().startsWith('#include') || source.includes('int main') || source.includes('printf(')) {
                setLanguage('c');
              } else if (source.trim().startsWith('def ')) {
                setLanguage('python');
              }
            }}
            className="bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-3 py-1 rounded-lg text-xs transition-colors shrink-0 shadow"
          >
            Switch Language to {source.trim().startsWith('#include') ? 'C' : 'Python'}
          </button>
        </div>
      )}

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
          {/* Input & Test Case Manager Panel */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-col gap-2.5 shadow-sm">
            {/* Header: Mode Switcher */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center space-x-1 bg-slate-950 p-0.5 rounded-lg border border-slate-800">
                <button
                  type="button"
                  onClick={() => setInputMode('tests')}
                  className={`flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                    inputMode === 'tests'
                      ? 'bg-slate-800 text-emerald-400 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <ListChecks className="h-3.5 w-3.5" />
                  <span>Test Suite ({testCases.length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => setInputMode('stdin')}
                  className={`flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                    inputMode === 'stdin'
                      ? 'bg-slate-800 text-cyan-400 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Terminal className="h-3.5 w-3.5" />
                  <span>Single Stdin</span>
                </button>
              </div>

              {inputMode === 'tests' && (
                <button
                  type="button"
                  onClick={handleAddTestCase}
                  className="flex items-center space-x-1 text-[11px] font-medium bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-1 rounded transition-colors"
                  title="Add another test case"
                >
                  <Plus className="h-3 w-3" />
                  <span>Add Case</span>
                </button>
              )}
            </div>

            {/* Mode 1: Single Stdin */}
            {inputMode === 'stdin' && (
              <div className="flex flex-col gap-1.5">
                <span className="text-[11px] text-slate-400 font-medium">Standard Input for scanf() / input():</span>
                <textarea
                  value={stdin}
                  onChange={(e) => setStdin(e.target.value)}
                  placeholder="Arguments or inputs for scanf / input()..."
                  rows={3}
                  className="bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
            )}

            {/* Mode 2: Multi-Test-Case Suite */}
            {inputMode === 'tests' && (
              <div className="flex flex-col gap-2">
                {/* Case Selector Tabs */}
                <div className="flex items-center space-x-1.5 overflow-x-auto pb-1">
                  {testCases.map((tc, idx) => {
                    const res = runResult?.test_results?.[idx];
                    return (
                      <button
                        key={tc.id || idx}
                        type="button"
                        onClick={() => setActiveTestCaseIndex(idx)}
                        className={`flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-mono transition-all shrink-0 ${
                          activeTestCaseIndex === idx
                            ? 'bg-slate-800 text-slate-100 border border-emerald-500/60 font-bold'
                            : 'bg-slate-950 text-slate-400 hover:text-slate-300 border border-slate-800'
                        }`}
                      >
                        {res ? (
                          res.passed ? (
                            <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                          ) : (
                            <XCircle className="h-3 w-3 text-rose-400" />
                          )
                        ) : (
                          <span className="h-1.5 w-1.5 rounded-full bg-slate-600" />
                        )}
                        <span>Case {idx + 1}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Active Case Editor */}
                {testCases[activeTestCaseIndex] && (
                  <div className="flex flex-col gap-2 bg-slate-950 border border-slate-800/80 rounded-lg p-2.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-slate-300 uppercase tracking-wider">
                        Configuring Case #{activeTestCaseIndex + 1}
                      </span>
                      {testCases.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveTestCase(activeTestCaseIndex)}
                          className="text-slate-500 hover:text-rose-400 transition-colors flex items-center gap-1 text-[10px]"
                          title="Delete this test case"
                        >
                          <Trash2 className="h-3 w-3" />
                          <span>Delete Case</span>
                        </button>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] text-slate-400 uppercase font-mono font-semibold">Input (stdin):</label>
                        <textarea
                          value={testCases[activeTestCaseIndex].input}
                          onChange={(e) => handleUpdateTestCase('input', e.target.value)}
                          placeholder="e.g. 5"
                          rows={2}
                          className="bg-slate-900 border border-slate-800 rounded p-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] text-slate-400 uppercase font-mono font-semibold">Expected Output:</label>
                        <textarea
                          value={testCases[activeTestCaseIndex].expected}
                          onChange={(e) => handleUpdateTestCase('expected', e.target.value)}
                          placeholder="e.g. 120"
                          rows={2}
                          className="bg-slate-900 border border-slate-800 rounded p-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
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
                      {/* Batch Test Case Results (if tests were executed) */}
                      {runResult.test_results && runResult.test_results.length > 0 ? (
                        <div className="space-y-3 mb-3">
                          {(() => {
                            const passedCount = runResult.test_results.filter((r) => r.passed).length;
                            const totalCount = runResult.test_results.length;
                            const allPassed = passedCount === totalCount;
                            return (
                              <div
                                className={`flex items-center justify-between p-3 rounded-xl border ${
                                  allPassed
                                    ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                                    : 'bg-rose-950/40 border-rose-500/30 text-rose-300'
                                }`}
                              >
                                <div className="flex items-center space-x-2.5">
                                  {allPassed ? (
                                    <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
                                  ) : (
                                    <XCircle className="h-5 w-5 text-rose-400 shrink-0" />
                                  )}
                                  <div>
                                    <div className="font-bold text-xs">
                                      {allPassed
                                        ? 'All Test Cases Passed!'
                                        : `${passedCount} of ${totalCount} Test Cases Passed`}
                                    </div>
                                    <div className="text-[10px] text-slate-400">
                                      Total execution time: {runResult.time_ms} ms
                                    </div>
                                  </div>
                                </div>
                                <span
                                  className={`text-xs font-mono font-bold px-2.5 py-1 rounded-full ${
                                    allPassed
                                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                      : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                  }`}
                                >
                                  {passedCount}/{totalCount} Passed
                                </span>
                              </div>
                            );
                          })()}

                          <div className="space-y-2">
                            {runResult.test_results.map((r, idx) => (
                              <div
                                key={idx}
                                className={`bg-slate-900 border rounded-lg p-2.5 flex flex-col gap-2 transition-all ${
                                  r.passed
                                    ? 'border-emerald-900/60 hover:border-emerald-700/60'
                                    : 'border-rose-900/80 hover:border-rose-700/80'
                                }`}
                              >
                                <div className="flex items-center justify-between text-xs">
                                  <div className="flex items-center space-x-2 font-bold font-mono">
                                    {r.passed ? (
                                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                                    ) : (
                                      <XCircle className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                                    )}
                                    <span className={r.passed ? 'text-emerald-300' : 'text-rose-300'}>
                                      Test Case #{idx + 1}: {r.passed ? 'PASSED' : 'FAILED'}
                                    </span>
                                  </div>
                                  <span className="text-[10px] font-mono text-slate-400">
                                    {r.time_ms} ms
                                  </span>
                                </div>

                                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                                  <div className="bg-slate-950 p-2 rounded border border-slate-800/80">
                                    <span className="text-slate-500 block text-[9px] uppercase font-bold">
                                      Input (stdin)
                                    </span>
                                    <span className="text-slate-300 whitespace-pre">
                                      {r.input ? r.input : <em className="text-slate-600">(empty)</em>}
                                    </span>
                                  </div>
                                  <div className="bg-slate-950 p-2 rounded border border-slate-800/80">
                                    <span className="text-slate-500 block text-[9px] uppercase font-bold">
                                      Expected Output
                                    </span>
                                    <span className="text-slate-300 whitespace-pre">
                                      {r.expected ? r.expected : <em className="text-slate-600">(empty)</em>}
                                    </span>
                                  </div>
                                </div>

                                <div className="bg-slate-950 p-2 rounded border border-slate-800/80 text-[11px] font-mono">
                                  <span className="text-slate-500 block text-[9px] uppercase font-bold">
                                    Actual Output
                                  </span>
                                  <span
                                    className={`whitespace-pre ${
                                      r.passed ? 'text-emerald-300' : 'text-rose-300 font-semibold'
                                    }`}
                                  >
                                    {r.actual ? r.actual : <em className="text-slate-600">(no output)</em>}
                                  </span>
                                  {!r.passed && (
                                    <div className="mt-1 pt-1 border-t border-rose-900/40 text-[10px] text-rose-400">
                                      Assertion mismatch: expected '{r.expected}' but received '{r.actual}'.
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
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
                        </div>
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
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="font-semibold text-cyan-400 flex items-center gap-1.5">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Generated C Source:
                    </div>
                    {convertResult.success && (
                      <button
                        onClick={() => {
                          setLanguage('c');
                          setSource(convertResult.c_source);
                          setStatusMessage('Loaded generated C code into the editor (Language switched to C).');
                        }}
                        className="text-[10px] font-bold bg-cyan-600 hover:bg-cyan-500 text-slate-950 px-2.5 py-1 rounded transition-all shadow"
                        title="Load this C code into the main editor"
                      >
                        Load C into Editor
                      </button>
                    )}
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
