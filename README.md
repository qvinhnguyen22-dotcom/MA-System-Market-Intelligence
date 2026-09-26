<div align="center">

# 🚀 AMA-System: AI-Powered Market Intelligence SaaS

<p align="center">
  <b>Nền tảng tình báo thị trường và phân tích chiến lược tự động hóa thế hệ mới</b><br>
  <i>Biến dữ liệu web thô thành báo cáo chiến lược kinh doanh toàn diện chỉ trong vài giây.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-v2.0-005571?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Next.js-15.2-black?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js">
  <img src="https://img.shields.io/badge/Gemini_2.0_Flash-AI-8E75B2?style=for-the-badge&logo=googleparade&logoColor=white" alt="Gemini AI">
  <img src="https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind CSS">
  <img src="https://img.shields.io/badge/TypeScript-Ready-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License">
</p>

</div>

---

## 🌟 Tổng Quan Về Dự Án

Trong kỷ nguyên số, việc nắm bắt xu hướng thị trường và phân tích đối thủ cạnh tranh quyết định sự sống còn của doanh nghiệp. **AMA-System** được xây dựng nhằm tự động hóa toàn bộ quy trình nghiên cứu thị trường tẻ nhạt. 

Hệ thống kết hợp sức mạnh của **Tavily API** để cào dữ liệu web thời gian thực và mô hình trí tuệ nhân tạo đỉnh cao **Gemini 2.0 Flash**, cho phép các nhà sáng lập, nhà quản lý và chuyên gia marketing tạo ra các báo cáo chiến lược sâu sắc, chân dung khách hàng chi tiết và **Ma trận SWOT** tiêu chuẩn ngay lập tức.

---

## 🏛️ Kiến Trúc Hệ Thống & Sơ Đồ Luồng (Pipeline)

Hệ thống vận hành theo mô hình bất đồng bộ (Asynchronous) hiệu năng cao, đảm bảo trải nghiệm người dùng mượt mà từ khâu yêu cầu đến khi trả kết quả:

```text
[ Giao diện Next.js ] ──( Gửi từ khóa )──► [ FastAPI Backend ]
                                                   │
         ┌─────────────────────────────────────────┘
         ▼
 1. 🔍 Tavily API (Thu thập dữ liệu web thời gian thực)
         │
         ▼
 2. 🤖 Gemini 2.0 Flash (Phân tích AI & Làm sạch Regex JSON)
         │
         ▼
 3. ⚡ SSE Stream (/api/stream/{job_id}) ──► [ Cập nhật tiến trình Real-time trên UI ]


  Các Tính Năng Đột Phá (Key Features)
🌐 Real-time Web Mining: Tự động cào lọc thông tin, xu hướng và dữ liệu giá cả từ hàng loạt nguồn internet tin cậy thông qua Tavily API.
🧠 AI Intelligence Engine: Sử dụng Gemini 2.0 Flash với các prompt kỹ thuật cao để tự động phân tích sâu, lập chiến lược và xuất báo cáo định dạng Markdown chuẩn chuyên gia[cite: 3].
📊 Automated SWOT Matrix: Tự động tổng hợp Điểm mạnh, Điểm yếu, Cơ hội và Thách thức một cách logic và sắc bén.
⚡ Real-time Streaming (SSE): Ứng dụng Server-Sent Events giúp client theo dõi từng bước tiến trình ngầm (0% -> 100%) trực quan mà không lo nghẽn mạng.   
🛡️ Resilient Backend: Tích hợp bộ lọc Regex thông minh giúp trích xuất và ép kiểu an toàn phản hồi từ AI, triệt tiêu hoàn toàn lỗi cú pháp JSON.
🛠️ Công Nghệ Sử Dụng (Tech Stack)
Backend (Core Engine)
Language & Framework: Python, FastAPI (v2), Pydantic v2 (Xác thực dữ liệu nghiêm ngặt).   
AI & Data: Google GenAI SDK (gemini-2.0-flash), Tavily Search API[cite: 3].
Realtime Communication: SSE (Server-Sent Events)[cite: 5].
Frontend (Client Experience)
Framework: Next.js 15.2+ (App Router).   
Styling & UI: Tailwind CSS v4, TypeScript.   

