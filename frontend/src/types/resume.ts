// Types cho phân hệ Market Intelligence Analysis
// ---------------------------------------------------------------------------

export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface MarketInsight {
  summary: string;
  key_trends: string[];
  opportunities: string[];
  risks: string[];
  key_players: string[];
  market_size_estimate: string | null;
}

export interface AnalysisSource {
  title: string;
  url: string;
  snippet: string;
}

export interface AnalysisResult {
  query: string;
  sources_count: number;
  insights: MarketInsight;
  report_markdown: string;
  sources: AnalysisSource[];
}

export interface AnalyzeRequest {
  query: string;
  max_results?: number;
}

export interface AnalyzeResponse {
  job_id: string;
  status: JobStatus;
  message: string;
  stream_url: string;
}

/** Payload của mỗi SSE event */
export interface SSEPayload {
  status: JobStatus;
  progress: number;
  message: string;
  result: AnalysisResult | null;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Legacy Resume types (giữ nguyên)
// ---------------------------------------------------------------------------

export interface ResumeMetadata {
  filename: string;
  file_type: "pdf" | "docx";
  file_size_bytes: number;
  page_count: number | null;
  character_count: number;
  word_count: number;
}

export interface ResumeExtractResponse {
  success: boolean;
  message: string;
  metadata: ResumeMetadata;
  extracted_text: string;
}

export interface ApiErrorDetail {
  detail?: string | { msg: string }[];
}
