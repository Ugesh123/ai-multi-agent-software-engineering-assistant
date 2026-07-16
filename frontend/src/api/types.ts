// Mirrors app.api.schemas on the backend. Kept as a single source of
// truth for the wire format so components never guess at shape.

export type RunStatus =
  | "pending"
  | "planning"
  | "designing"
  | "coding"
  | "reviewing"
  | "testing"
  | "documenting"
  | "completed"
  | "failed";

export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface PlanItem {
  id: string;
  title: string;
  description: string;
  order: number;
  depends_on: string[];
}

export interface ArchitectureComponent {
  name: string;
  responsibility: string;
  interfaces: string[];
  dependencies: string[];
}

export interface Architecture {
  summary: string;
  components: ArchitectureComponent[];
  tech_choices: Record<string, string>;
  file_layout: string[];
}

export interface GeneratedFile {
  path: string;
  content: string;
  change_type: "create" | "update" | "delete";
  language: string;
}

export interface ReviewFinding {
  file_path: string;
  severity: "blocker" | "major" | "minor" | "nit";
  message: string;
  line: number | null;
}

export interface Review {
  verdict: "approved" | "changes_requested";
  findings: ReviewFinding[];
  summary: string;
}

export interface TestCaseResult {
  name: string;
  passed: boolean;
  output: string;
}

export interface TestReport {
  verdict: "passed" | "failed";
  cases: TestCaseResult[];
  summary: string;
}

export interface AgentRun {
  id: string;
  project_id: string;
  request: string;
  status: RunStatus;
  parent_run_id: string | null;
  version: number;
  commit_message: string;
  model: string | null;
  plan: PlanItem[];
  architecture: Architecture | null;
  files: GeneratedFile[];
  review: Review | null;
  test_report: TestReport | null;
  documentation: string;
  review_iterations: number;
  test_iterations: number;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentMessage {
  id: string;
  role: string;
  content: string;
  created_at: string;
  metadata: Record<string, string>;
}

export interface StreamEvent {
  run_id: string;
  status: RunStatus;
  latest_message: AgentMessage | null;
  review_iterations: number;
  test_iterations: number;
  error?: string;
}

export interface ModifiedFileDiff {
  path: string;
  unified_diff: string;
  added_lines: number;
  removed_lines: number;
}

export interface ProjectDiff {
  added: string[];
  deleted: string[];
  modified: ModifiedFileDiff[];
  unchanged: string[];
}

export interface ReferenceDocument {
  id: string;
  project_id: string;
  filename: string;
  content_type: string;
  created_at: string;
  preview: string;
}

export interface RetrievedChunk {
  source_type: "generated_file" | "reference_doc";
  source_label: string;
  content: string;
  score: number;
}

export interface ModelInfo {
  name: string;
  provider: string;
}

export interface ModelListResponse {
  models: ModelInfo[];
  current_default: string;
}

export interface GitCommit {
  hash: string;
  author: string;
  date: string;
  message: string;
}

export interface ApiError {
  error: string;
  details: Record<string, unknown>;
}
