export type JobStatus = "in_progress" | "completed" | "failed";

export type SwotMatrix = {
  strengths: string;
  weaknesses: string;
  opportunities: string;
  threats: string;
};

export type AnalysisResult = {
  target_audience?: string;
  trends?: string;
  swot?: SwotMatrix;
  full_report_markdown?: string;
  parse_fallback?: boolean;
};

export type StreamPayload = {
  status: JobStatus;
  progress?: number;
  message?: string;
  error?: string | null;
  result?: AnalysisResult | string | null;
};

export type AnalyzeAccepted = {
  job_id: string;
  status: string;
};
