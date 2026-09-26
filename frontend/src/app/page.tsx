"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import confetti from "canvas-confetti";
import { consumeSSEStream, startAnalysis } from "@/lib/api";
import type { AnalysisResult, JobStatus, SSEPayload } from "@/types/resume";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  AlertCircle,
  BarChart3,
  CheckCircle2,
  ExternalLink,
  Loader2,
  Search,
  Sparkles,
  TrendingUp,
  Zap,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Types nội bộ
// ---------------------------------------------------------------------------

interface AnalysisState {
  jobId: string | null;
  status: JobStatus | null;
  progress: number;
  message: string;
  result: AnalysisResult | null;
  error: string | null;
}

const INITIAL_STATE: AnalysisState = {
  jobId: null,
  status: null,
  progress: 0,
  message: "",
  result: null,
  error: null,
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ProgressCard({
  progress,
  message,
  status,
}: {
  progress: number;
  message: string;
  status: JobStatus | null;
}) {
  const isFailed = status === "failed";
  const isCompleted = status === "completed";

  return (
    <Card className="bg-slate-900/80 border-slate-800/80 backdrop-blur-md">
      <CardContent className="pt-6 pb-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isFailed ? (
              <AlertCircle className="h-4 w-4 text-rose-400" />
            ) : isCompleted ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            ) : (
              <Loader2 className="h-4 w-4 text-indigo-400 animate-spin" />
            )}
            <span
              className={`text-sm font-medium ${
                isFailed
                  ? "text-rose-400"
                  : isCompleted
                  ? "text-emerald-400"
                  : "text-slate-200"
              }`}
            >
              {message || "Đang xử lý..."}
            </span>
          </div>
          <span
            className={`text-sm font-bold tabular-nums ${
              isFailed ? "text-rose-400" : "text-indigo-400"
            }`}
          >
            {progress}%
          </span>
        </div>
        <Progress
          value={progress}
          className={`h-2 ${isFailed ? "[&>div]:bg-rose-500" : "[&>div]:bg-indigo-500"}`}
        />
      </CardContent>
    </Card>
  );
}

function InsightsGrid({ result }: { result: AnalysisResult }) {
  const { insights } = result;

  return (
    <div className="space-y-4">
      {/* Summary */}
      <Card className="bg-slate-900/80 border-slate-800/80">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-indigo-400" />
            Tổng quan
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-300 leading-relaxed">{insights.summary}</p>
          {insights.market_size_estimate && (
            <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs">
              <TrendingUp className="h-3 w-3" />
              {insights.market_size_estimate}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Grid: Trends + Opportunities + Risks + Players */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <InsightsList
          title="Xu hướng chính"
          items={insights.key_trends}
          color="indigo"
          icon="📈"
        />
        <InsightsList
          title="Cơ hội"
          items={insights.opportunities}
          color="emerald"
          icon="✅"
        />
        <InsightsList
          title="Rủi ro"
          items={insights.risks}
          color="rose"
          icon="⚠️"
        />
        <InsightsList
          title="Tác nhân chính"
          items={insights.key_players}
          color="violet"
          icon="🏢"
        />
      </div>
    </div>
  );
}

function InsightsList({
  title,
  items,
  color,
  icon,
}: {
  title: string;
  items: string[];
  color: "indigo" | "emerald" | "rose" | "violet";
  icon: string;
}) {
  const colorMap = {
    indigo: "border-indigo-500/20 bg-indigo-500/5",
    emerald: "border-emerald-500/20 bg-emerald-500/5",
    rose: "border-rose-500/20 bg-rose-500/5",
    violet: "border-violet-500/20 bg-violet-500/5",
  };
  const dotMap = {
    indigo: "bg-indigo-500",
    emerald: "bg-emerald-500",
    rose: "bg-rose-500",
    violet: "bg-violet-500",
  };

  if (!items || items.length === 0) return null;

  return (
    <Card className={`border ${colorMap[color]}`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold text-slate-200">
          {icon} {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
              <span
                className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${dotMap[color]}`}
              />
              {item}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function SourcesList({ sources }: { sources: AnalysisResult["sources"] }) {
  if (!sources || sources.length === 0) return null;

  return (
    <Card className="bg-slate-900/80 border-slate-800/80">
      <CardHeader>
        <CardTitle className="text-sm font-semibold text-slate-200">
          🔗 Nguồn tham khảo ({sources.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {sources.map((source, i) => (
            <div key={i} className="group">
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-2 hover:opacity-80 transition-opacity"
              >
                <ExternalLink className="h-3.5 w-3.5 text-indigo-400 shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <p className="text-xs font-medium text-indigo-300 truncate group-hover:underline">
                    {source.title || source.url}
                  </p>
                  {source.snippet && (
                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">
                      {source.snippet}
                    </p>
                  )}
                </div>
              </a>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ReportSection({ markdown }: { markdown: string }) {
  const [expanded, setExpanded] = useState(false);

  if (!markdown) return null;

  return (
    <Card className="bg-slate-900/80 border-slate-800/80">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-slate-200">
            📄 Báo cáo chi tiết
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-slate-400 hover:text-slate-200"
          >
            {expanded ? "Thu gọn" : "Xem đầy đủ"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div
          className={`overflow-hidden transition-all duration-300 ${
            expanded ? "max-h-none" : "max-h-80"
          } relative`}
        >
          <div className="prose prose-invert prose-sm max-w-none prose-headings:text-slate-200 prose-p:text-slate-400 prose-li:text-slate-400 prose-a:text-indigo-400 prose-strong:text-slate-300">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {markdown}
            </ReactMarkdown>
          </div>
          {!expanded && (
            <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-slate-900/80 to-transparent" />
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function Home() {
  const [query, setQuery] = useState("");
  const [maxResults, setMaxResults] = useState(5);
  const [analysis, setAnalysis] = useState<AnalysisState>(INITIAL_STATE);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // AbortController để hủy SSE khi cần (tránh memory leak khi unmount)
  const abortRef = useRef<AbortController | null>(null);

  // Cleanup khi unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const handleSSEUpdate = useCallback((payload: SSEPayload) => {
    setAnalysis((prev) => ({
      ...prev,
      status: payload.status,
      progress: payload.progress,
      message: payload.message,
      result: payload.result,
      error: payload.error,
    }));

    // Trigger confetti khi hoàn tất
    if (payload.status === "completed") {
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
        colors: ["#6366f1", "#8b5cf6", "#06b6d4"],
      });
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery || isSubmitting) return;

    // Hủy SSE stream cũ nếu có
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setIsSubmitting(true);
    setAnalysis({
      ...INITIAL_STATE,
      status: "pending",
      message: "Đang tạo job...",
    });

    try {
      // 1. POST /api/analyze — lấy job_id
      const analyzeResp = await startAnalysis({
        query: trimmedQuery,
        max_results: maxResults,
      });

      setAnalysis((prev) => ({
        ...prev,
        jobId: analyzeResp.job_id,
        status: "pending",
        message: "Đã tạo job. Đang kết nối stream...",
      }));

      // 2. Kết nối SSE stream — fetch + ReadableStream (KHÔNG dùng Axios)
      await consumeSSEStream(
        analyzeResp.job_id,
        handleSSEUpdate,
        abortRef.current.signal
      );
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        // Bị hủy chủ động (component unmount hoặc re-submit)
        return;
      }
      const message =
        err instanceof Error ? err.message : "Đã xảy ra lỗi không xác định.";
      setAnalysis((prev) => ({
        ...prev,
        status: "failed",
        progress: 0,
        message: `❌ ${message}`,
        error: message,
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const isLoading =
    isSubmitting ||
    analysis.status === "pending" ||
    analysis.status === "running";

  const isCompleted = analysis.status === "completed";
  const isFailed = analysis.status === "failed";
  const hasProgress = analysis.status !== null && !isCompleted;

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[400px] bg-gradient-to-b from-indigo-600/12 via-violet-600/8 to-transparent blur-3xl pointer-events-none" />

      <div className="relative max-w-4xl mx-auto px-4 py-10 md:py-14 space-y-8">
        {/* Header */}
        <header className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/20 bg-indigo-500/10 text-indigo-300 text-xs font-medium">
            <Sparkles className="h-3.5 w-3.5" />
            AMA-System Market Intelligence
          </div>
          <div className="flex items-center justify-center gap-3">
            <div className="bg-gradient-to-tr from-indigo-600 to-violet-500 p-2.5 rounded-2xl shadow-lg shadow-indigo-500/25">
              <TrendingUp className="h-6 w-6 text-white" />
            </div>
            <h1 className="text-2xl md:text-3xl font-black tracking-tight">
              Phân Tích Thị Trường AI
            </h1>
          </div>
          <p className="text-sm text-slate-400 max-w-xl mx-auto">
            Nhập chủ đề cần phân tích — hệ thống sẽ tự động cào dữ liệu web
            (Tavily) và phân tích chuyên sâu bằng Gemini 2.0 Flash.
          </p>
        </header>

        {/* Search form */}
        <Card className="bg-slate-900/80 border-slate-800/80 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Search className="h-4 w-4 text-indigo-400" />
              Nhập chủ đề phân tích
            </CardTitle>
            <CardDescription className="text-slate-400">
              Ví dụ: &quot;AI chip market 2024&quot;, &quot;thị trường EV Việt Nam&quot;, &quot;fintech
              Southeast Asia trends&quot;
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="flex gap-3">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="VD: AI chip market 2024..."
                  disabled={isLoading}
                  className="flex-1 bg-slate-950/60 border-slate-700 text-slate-100 placeholder:text-slate-500 focus-visible:ring-indigo-500/50"
                  maxLength={500}
                />
                <Button
                  type="submit"
                  disabled={!query.trim() || isLoading}
                  className="shrink-0 h-10 px-5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold gap-2"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Đang phân tích
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4" />
                      Phân tích
                    </>
                  )}
                </Button>
              </div>

              {/* Max results slider */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-500 shrink-0">
                  Số nguồn web:
                </span>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={maxResults}
                  onChange={(e) => setMaxResults(Number(e.target.value))}
                  disabled={isLoading}
                  className="flex-1 accent-indigo-500 disabled:opacity-50"
                />
                <Badge
                  variant="outline"
                  className="border-indigo-500/30 text-indigo-300 tabular-nums w-8 justify-center"
                >
                  {maxResults}
                </Badge>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Progress card — hiển thị khi đang chạy hoặc bị lỗi */}
        {hasProgress && (
          <ProgressCard
            progress={analysis.progress}
            message={analysis.message}
            status={analysis.status}
          />
        )}

        {/* Error state */}
        {isFailed && analysis.error && (
          <Card className="bg-rose-950/20 border-rose-900/40">
            <CardContent className="pt-4 pb-4">
              <p className="text-sm text-rose-400 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {analysis.error}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Results */}
        {isCompleted && analysis.result && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Success header */}
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
              <div>
                <h2 className="text-lg font-bold text-slate-100">
                  Phân tích hoàn tất
                </h2>
                <p className="text-xs text-slate-500">
                  Query: &quot;{analysis.result.query}&quot; · {analysis.result.sources_count}{" "}
                  nguồn
                </p>
              </div>
            </div>

            {/* Insights grid */}
            <InsightsGrid result={analysis.result} />

            {/* Markdown report */}
            <ReportSection markdown={analysis.result.report_markdown} />

            {/* Sources */}
            <SourcesList sources={analysis.result.sources} />
          </div>
        )}
      </div>
    </main>
  );
}
