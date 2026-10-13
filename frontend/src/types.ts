export type SupportedLanguage = 'c' | 'cpp' | 'python' | 'java';

export interface ConvertResponse {
  c_source: string;
  diagnostics: string[];
  success: boolean;
}

export interface TestCaseResult {
  input: string;
  expected: string;
  actual: string;
  passed: boolean;
  time_ms: number;
}

export interface RunResponse {
  compile_ok: boolean;
  compiler_messages: string;
  stdout: string;
  stderr: string;
  exit_code: number;
  time_ms: number;
  memory_kb: number;
  timed_out: boolean;
  killed_reason?: string;
  converted_c_source?: string;
  test_results: TestCaseResult[];
}

export interface MatchedSubtree {
  kind: string;
  size: number;
  line_a: number;
  line_b: number;
  hash_val: number;
}

export interface MatchReport {
  submission_id?: number;
  title?: string;
  language?: string;
  token_similarity: number;
  token_containment_a: number;
  token_containment_b: number;
  logic_similarity: number;
  overall_similarity: number;
  verdict: 'low' | 'suspicious' | 'likely copied';
  matched_ranges_a: [number, number][];
  matched_ranges_b: [number, number][];
  matched_subtrees: MatchedSubtree[];
}

export interface PlagiarismCheckResponse {
  query_language: string;
  matches: MatchReport[];
}

export interface Submission {
  id: number;
  title: string;
  language: string;
  original_source: string;
  generated_c_source: string;
  created_at?: string;
}

export interface TokenView {
  kind: string;
  value: string;
  raw: string;
  line: number;
  col: number;
}

export interface ASTNode {
  kind: string;
  value?: string | number | boolean;
  line: number;
  col: number;
  children?: ASTNode[];
}

export interface ASTViewResponse {
  tokens: TokenView[];
  raw_ast: ASTNode;
  canonical_ast: ASTNode;
  generated_c: string;
}
