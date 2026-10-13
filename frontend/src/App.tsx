import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { EditorView } from './components/EditorView';
import { ReportView } from './components/ReportView';
import { PipelineView } from './components/PipelineView';
import { SubmissionsView } from './components/SubmissionsView';
import { SupportedLanguage, MatchReport } from './types';

const DEFAULT_CODE = `#include <stdio.h>

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
}`;

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'editor' | 'report' | 'pipeline' | 'submissions'>('editor');
  const [source, setSource] = useState(DEFAULT_CODE);
  const [language, setLanguage] = useState<SupportedLanguage>('c');
  const [plagiarismReports, setPlagiarismReports] = useState<MatchReport[]>([]);

  const handleCheckPlagiarism = (matches: MatchReport[]) => {
    setPlagiarismReports(matches);
    setActiveTab('report');
  };

  const handleCompareResult = (matches: MatchReport[], queryCode: string) => {
    setPlagiarismReports(matches);
    setSource(queryCode);
    setActiveTab('report');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 flex flex-col">
        {activeTab === 'editor' && (
          <EditorView
            source={source}
            setSource={setSource}
            language={language}
            setLanguage={setLanguage}
            onCheckPlagiarism={handleCheckPlagiarism}
            onOpenPipeline={() => setActiveTab('pipeline')}
          />
        )}

        {activeTab === 'report' && (
          <ReportView reports={plagiarismReports} querySource={source} />
        )}

        {activeTab === 'pipeline' && (
          <PipelineView source={source} language={language} />
        )}

        {activeTab === 'submissions' && (
          <SubmissionsView onCompareResult={handleCompareResult} />
        )}
      </main>

      <footer className="border-t border-slate-900 bg-slate-950 px-4 py-3 text-center text-xs text-slate-500 font-mono">
        CodeGuard • Compiler Construction Platform • Hand-written Lexers & Parsers (C, C++, Python, Java) • AST Canonicalization • Winnowing
      </footer>
    </div>
  );
};

export default App;
