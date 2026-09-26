/**
 * API client cho AMA-System Market Intelligence.
 *
 * Nguyên tắc SSE:
 *   - KHÔNG dùng Axios cho SSE (Axios không hỗ trợ ReadableStream native)
 *   - Dùng fetch() với ReadableStream decoder
 *   - EventSource native cũng hoạt động nhưng không cho phép custom headers
 *   - Chuẩn hóa CRLF / LF và ghép đa dòng data theo RFC 8895
 */

import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ApiErrorDetail,
  SSEPayload,
} from "@/types/resume";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function parseErrorMessage(payload: ApiErrorDetail, fallback: string): string {
  const { detail } = payload;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((item) => item.msg).join(", ");
  }
  return fallback;
}

// ---------------------------------------------------------------------------
// Market Intelligence API
// ---------------------------------------------------------------------------

/**
 * POST /api/analyze — Tạo analysis job.
 * Trả về job_id và stream_url để kết nối SSE.
 */
export async function startAnalysis(
  payload: AnalyzeRequest
): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = `Khởi tạo phân tích thất bại (${response.status})`;
    try {
      const errorPayload = (await response.json()) as ApiErrorDetail;
      message = parseErrorMessage(errorPayload, message);
    } catch {
      // Giữ message mặc định
    }
    throw new Error(message);
  }

  return response.json() as Promise<AnalyzeResponse>;
}

/**
 * Kết nối SSE stream bằng fetch + ReadableStream.
 *
 * Ưu điểm so với EventSource / Axios:
 *   - Không bị giới hạn phương thức hoặc thiếu custom headers như EventSource
 *   - Đọc stream liên tục non-blocking qua ReadableStream
 *   - Hỗ trợ AbortSignal chủ động đóng kết nối khi user hủy hoặc navigate
 *
 * @param jobId     - Job ID nhận được từ startAnalysis()
 * @param onUpdate  - Callback gọi mỗi khi nhận SSE payload mới
 * @param signal    - AbortSignal để ngắt kết nối
 */
export async function consumeSSEStream(
  jobId: string,
  onUpdate: (payload: SSEPayload) => void,
  signal?: AbortSignal
): Promise<void> {
  const url = `${API_BASE_URL}/api/stream/${jobId}`;

  const response = await fetch(url, {
    method: "GET",
    headers: {
      Accept: "text/event-stream",
      "Cache-Control": "no-cache",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Kết nối SSE thất bại: HTTP ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Máy chủ không hỗ trợ luồng dữ liệu (ReadableStream is null).");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // Decode UTF-8 với stream flag để bảo toàn byte qua các chunks
      buffer += decoder.decode(value, { stream: true });

      // Chuẩn hóa CRLF về LF để phân tách đúng trên mọi hệ điều hành
      buffer = buffer.replace(/\r\n/g, "\n");

      // SSE event kết thúc bằng 2 ký tự xuống dòng liên tiếp (\n\n)
      const parts = buffer.split("\n\n");
      // Phần cuối chưa hoàn chỉnh giữ lại trong buffer
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const trimmed = part.trim();
        if (!trimmed) continue;

        // Lấy tất cả dòng 'data:' và ghép lại
        const dataLines = trimmed
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trim());

        if (dataLines.length === 0) continue;
        const jsonStr = dataLines.join("\n");

        try {
          const payload = JSON.parse(jsonStr) as SSEPayload;
          onUpdate(payload);

          // Stream tự đóng khi job đạt trạng thái cuối
          if (payload.status === "completed" || payload.status === "failed") {
            return;
          }
        } catch (parseErr) {
          console.warn("[SSE Parser] Bỏ qua event không đúng định dạng JSON:", jsonStr, parseErr);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ---------------------------------------------------------------------------
// Legacy Resume API
// ---------------------------------------------------------------------------

export async function uploadResume(
  file: File
): Promise<import("@/types/resume").ResumeExtractResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/v1/resume/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let message = `Upload thất bại (${response.status})`;
    try {
      const errorPayload = (await response.json()) as ApiErrorDetail;
      message = parseErrorMessage(errorPayload, message);
    } catch {
      // Giữ message mặc định nếu body không phải JSON
    }
    throw new Error(message);
  }

  return response.json() as Promise<import("@/types/resume").ResumeExtractResponse>;
}
