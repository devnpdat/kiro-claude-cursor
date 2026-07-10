---
title: "Bài 7: Observability — Metrics, Logs, Traces trong .NET với OpenTelemetry & Grafana"
description: "Xây dựng hệ thống observability toàn diện cho .NET backend với OpenTelemetry, Prometheus và Grafana. Senior .NET backend engineer học cách triển khai structured logging, distributed tracing và metrics monitoring để debug và tối ưu hệ thống."
tags: [observability, opentelemetry, prometheus, grafana, logging, tracing, metrics, dotnet]
keywords: [OpenTelemetry, Prometheus, Grafana, distributed tracing, structured logging, .NET observability, metrics monitoring, application performance monitoring, observable, theo dõi hệ thống]
---

# Bài 7: Observability — Metrics, Logs, Traces trong .NET

> Dành cho: kỹ sư backend .NET 🔧
> Ngày: 2026-07-10
> Chủ đề: OpenTelemetry, Prometheus, Grafana, structured logging, distributed tracing
> Ẩn dụ xuyên suốt: 🏥 **Bảng điều khiển trung tâm của bệnh viện**
> Thời gian đọc: ~20 phút

---

## 🎯 Tổng quan — "Máy bay không có bảng điều khiển"
- Không biết tốc độ bao nhiêu.
- Không biết còn bao nhiêu nhiên liệu.
- Không biết động cơ bên trái đang nóng lên bất thường.
- Không biết đang bay ở độ cao nào.

Bạn chỉ biết... **máy bay không rơi**. Nhưng nếu nó sắp rơi thì bạn không có cách nào biết trước.

---

Hệ thống phần mềm của bạn (API .NET, Kafka, Redis, DB) cũng vậy. Nếu không có **Observability**, bạn chỉ biết nó **đang chạy** — nhưng không biết nó **chạy thế nào**, **có sắp chết không**, **chỗ nào đau**.

> **Observability = khả năng hiểu được trạng thái bên trong của hệ thống chỉ bằng cách nhìn vào dữ liệu đầu ra (logs, metrics, traces).**

Không phải là "có log là được". Observability là **chủ động**: hệ thống kể cho bạn nghe nó đang thế nào, không phải bạn phải SSH vào để hỏi.

### 🔑 Ba trụ cột: The Three Pillars

| Trụ cột | Ẩn dụ bệnh viện | Mô tả |
|---|---|---|
| **Metrics** | Máy đo nhịp tim, huyết áp | Số đo tổng quát theo thời gian: RPS, latency p50/p95/p99, CPU, memory |
| **Logs** | Nhật ký bác sĩ ghi chép | Sự kiện rời rạc có timestamp: "User X login failed", "DB connection timeout" |
| **Traces** | Phim chụp X-quang toàn thân | Hành trình của 1 request xuyên suốt các service: Gateway → API → DB → Redis |

Cả 3 cái đều cần. Thiếu 1 trong 3 → bạn mù 1 mặt.

---

## 📊 1. Metrics — Đo lường để biết hệ thống "khoẻ hay yếu"

Metrics là các **con số được thu thập định kỳ**. Không phải "sự kiện gì đã xảy ra" mà là "giá trị bao nhiêu tại thời điểm này".

### 1.1. Các loại metrics cốt lõi

#### a) RED Method (dành cho request-driven services)
**R** — Rate: bao nhiêu request/giây?
**E** — Errors: bao nhiêu request bị lỗi?
**D** — Duration: mất bao lâu?

Đây là 3 metrics tối thiểu cho **MỌI** API endpoint.

```csharp
// Ví dụ: đo metrics bằng .NET Meter (OpenTelemetry)
using System.Diagnostics.Metrics;

var meter = new Meter("MyApi", "1.0.0");
var requestCounter = meter.CreateCounter<long>("api.requests.total");
var errorCounter = meter.CreateCounter<long>("api.requests.errors");
var requestDuration = meter.CreateHistogram<double>("api.requests.duration_ms");

// Trong middleware
app.Use(async (context, next) =>
{
    var sw = Stopwatch.StartNew();
    try
    {
        await next();
        requestCounter.Add(1, new KeyValuePair<string, object>("method", context.Request.Method));
    }
    catch
    {
        errorCounter.Add(1);
        throw;
    }
    finally
    {
        requestDuration.Record(sw.ElapsedMilliseconds);
    }
});
```

#### b) USE Method (dành cho resource — CPU, RAM, Disk, Network)
**U** — Utilization: bao nhiêu % đang được dùng?
**S** — Saturation: mức độ chờ đợi (queue depth)?
**E** — Errors: có lỗi gì không?

| Resource | Utilization | Saturation | Errors |
|---|---|---|---|
| CPU | % CPU time | Run queue length (Linux load avg) | — |
| Memory | % RAM used | OOM score, swap usage | OOM kills |
| Disk | I/O % busy | I/O wait queue | I/O errors |
| Network | Bandwidth % | Drop packet rate | Interface errors |

### 1.2. Latency percentile — Tại sao "average latency" là lừa đảo?

Giả sử API trả về **trung bình 50ms**. Nhưng thực tế:
- 90% request: 10ms
- 9% request: 100ms
- 1% request: **4000ms** (4 giây!)

Trung bình = (10×0.9 + 100×0.09 + 4000×0.01) = 9 + 9 + 40 = **58ms**. Nhìn vào 58ms → tưởng ổn. Nhưng **1% khách hàng bị 4 giây** — đó là thảm hoạ.

**Giải pháp:** Luôn theo dõi percentile:
- **p50** (median): 50% request nhanh hơn mức này
- **p95**: 95% request nhanh hơn mức này
- **p99**: 99% request nhanh hơn mức này (quan trọng nhất!)

> Nếu p99 = 200ms mà p50 = 10ms → có 1% request rất chậm. Nguyên nhân có thể là GC, connection pool cạn, hoặc DB query bị blocking.

### 1.3. Prometheus — Kho chứa metrics phổ biến nhất

Prometheus là hệ thống **scrape-based**: nó gọi đến endpoint `/metrics` của ứng dụng để lấy dữ liệu định kỳ.

```
# HELP api_requests_duration_ms Histogram of request duration
# TYPE api_requests_duration_ms histogram
api_requests_duration_ms_bucket{method="GET",le="10"} 1234
api_requests_duration_ms_bucket{method="GET",le="50"} 5678
api_requests_duration_ms_bucket{method="GET",le="200"} 7890
api_requests_duration_ms_bucket{method="GET",le="+Inf"} 8000
api_requests_duration_ms_sum{method="GET"} 240000
api_requests_duration_ms_count{method="GET"} 8000
```

**.NET OpenTelemetry** tự động expose `/metrics` endpoint:

```csharp
// Program.cs — cấu hình OpenTelemetry Metrics
builder.Services.AddOpenTelemetry()
    .WithMetrics(metrics => metrics
        .AddAspNetCoreInstrumentation()  // tự động đo HTTP request
        .AddRuntimeInstrumentation()     // CPU, memory, GC
        .AddPrometheusExporter());       // expose /metrics

app.MapPrometheusScrapingEndpoint();     // /metrics endpoint
```

---

## 📝 2. Structured Logging — Log kiểu "máy đọc được"

Log truyền thống: chuỗi text thuần — con người đọc được, máy thì không.

```
2026-07-10 14:30:22 INFO User 12345 login success from IP 192.168.1.1
```

Structured log: JSON — **cả người và máy** đều đọc được, dễ query, dễ filter.

```json
{
  "timestamp": "2026-07-10T14:30:22.123Z",
  "level": "info",
  "message": "User login success",
  "userId": 12345,
  "ip": "192.168.1.1",
  "service": "auth-api",
  "duration_ms": 45,
  "correlationId": "abc-123-def"
}
```

### 2.1. Serilog + .NET — Cấu hình chuẩn

```csharp
// Program.cs
Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Information()
    .MinimumLevel.Override("Microsoft", LogEventLevel.Warning)
    .Enrich.WithCorrelationId()         // thêm correlationId
    .Enrich.WithMachineName()           // thêm tên máy
    .WriteTo.Console(new JsonFormatter()) // JSON ra console
    .WriteTo.Seq("http://seq:5341")     // gửi về Seq Server
    .CreateLogger();

builder.Host.UseSerilog();
```

### 2.2. Các mức log (level) — Dùng đúng level, đừng lạm dụng

| Level | Khi nào dùng | Tần suất |
|---|---|---|
| **Trace** | Debug cực kỳ chi tiết (từng dòng code) | Dev/QA, rất hiếm production |
| **Debug** | Thông tin dev cần để debug | Hầu như không dùng production |
| **Information** | Luồng chính: "User created order 789" | Vừa phải, có chọn lọc |
| **Warning** | Có vấn đề nhưng chưa fail: "Connection pool near limit (80%)" | Ít |
| **Error** | Exception, fail operation | Chỉ khi thực sự lỗi |
| **Fatal** | App sắp chết: OOM, unhandled exception | Cực kỳ hiếm |

> ⚠️ **Sai lầm kinh điển:** Log `Information` cho MỌI THỨ. Hậu quả: 10GB log/ngày, không ai đọc, cost cao, performance giảm vì I/O.

### 2.3. Correlation ID — Xâu chuỗi log lại với nhau

Một request có thể đi qua: API Gateway → Auth → API → DB → Queue. Nếu mỗi service log riêng rẽ, làm sao biết request của user A đã đi đâu?

**Correlation ID** = 1 UUID duy nhất cho 1 request, được truyền qua tất cả service:

```csharp
// Middleware tạo correlation ID
app.Use(async (context, next) =>
{
    var correlationId = context.Request.Headers["X-Correlation-ID"]
                        ?? Guid.NewGuid().ToString();
    
    using (LogContext.PushProperty("CorrelationId", correlationId))
    {
        context.Response.Headers["X-Correlation-ID"] = correlationId;
        await next();
    }
});
```

Khi có lỗi → search log theo `CorrelationId = "abc-123"` → thấy toàn bộ hành trình.

---

## 🔍 3. Distributed Tracing — X-quang cho request

Metrics cho biết "API chậm". Log cho biết "request nào bị lỗi". Nhưng **Tại sao API chậm?** — Đó là việc của **Tracing**.

Tracing ghi lại:
- Request đi qua những service nào.
- Mỗi service mất bao nhiêu thời gian.
- Có chỗ nào bị chậm bất thường không.

### 3.1. Span và Trace

```
Trace (một request)
├── Span: API Gateway → nhận request (2ms)
├── Span: Gọi Auth Service (15ms)
│   ├── Span: Query DB lấy user (12ms)
│   └── Span: Verify token (3ms)
├── Span: Gọi Order Service (120ms) ← chậm nhất!
│   ├── Span: Redis cache check (2ms)
│   ├── Span: SQL query (100ms) ← đây là thủ phạm!
│   └── Span: Format response (18ms)
└── Span: Trả response về client (1ms)
```

### 3.2. OpenTelemetry trong .NET

```csharp
// Program.cs — cấu hình Tracing
builder.Services.AddOpenTelemetry()
    .WithTracing(tracing => tracing
        .AddAspNetCoreInstrumentation()     // tự động trace HTTP request
        .AddSqlClientInstrumentation()      // trace SQL query
        .AddRedisInstrumentation()          // trace Redis calls
        .AddKafkaInstrumentation()          // trace producer/consumer
        .AddOtlpExporter(options =>         // gửi về Jaeger/Grafana Tempo
            options.Endpoint = new Uri("http://tempo:4317")));
```

### 3.3. Custom tracing với ActivitySource

Khi cần trace một đoạn code custom (ví dụ gọi external API):

```csharp
private static readonly ActivitySource ActivitySource = new("OrderService");

public async Task<Order> ProcessOrderAsync(int orderId)
{
    using var activity = ActivitySource.StartActivity("ProcessOrder");
    activity?.SetTag("order.id", orderId);
    
    // Đoạn code cần trace
    using (var validateActivity = ActivitySource.StartActivity("ValidateOrder"))
    {
        var isValid = await _validator.ValidateAsync(orderId);
        validateActivity?.SetTag("valid", isValid);
    }
    
    using (var persistActivity = ActivitySource.StartActivity("PersistOrder"))
    {
        await _db.Orders.AddAsync(order);
        persistActivity?.SetTag("db.rows_affected", 1);
    }
}
```

---

## 🏗️ 4. Kiến trúc Observability hoàn chỉnh

```
                    ┌──────────────┐
                    │   Grafana    │ ← Dashboard
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                   │
   ┌────▼────┐      ┌─────▼──────┐      ┌─────▼──────┐
   │Prometheus│      │    Loki    │      │   Tempo    │
   │(Metrics) │      │   (Logs)   │      │  (Traces)  │
   └────┬────┘      └─────┬──────┘      └─────┬──────┘
        │                  │                   │
        └──────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │ OtelCollector│
                    │ (xử lý data) │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   .NET App  │
                    │  metrics/   │
                    │  logs/      │
                    │  traces     │
                    └─────────────┘
```

**Công cụ cho từng trụ cột:**

| Trụ cột | Công cụ | Ghi chú |
|---|---|---|
| Metrics | Prometheus + Grafana | Tiêu chuẩn industry |
| Logs | Seq / Loki + Grafana | Seq dễ dùng, Loki rẻ |
| Traces | Jaeger / Grafana Tempo | Jaeger đơn giản, Tempo mạnh hơn |

---

## 🎯 5. Observability trong ứng dụng — Cấu hình thực tế

### 5.1. Checklist tối thiểu cho production

**Phải có ngay từ ngày 1:**
- [x] Health check endpoint (`/health`, `/ready`, `/live`)
- [x] Metrics: RPS, error rate, p50/p95/p99 latency (per endpoint)
- [x] Metrics: CPU, RAM, thread pool, connection pool
- [x] Log structured (JSON) với correlation ID
- [x] Log level: Info cho business event, Warning cho bất thường, Error cho fail
- [x] Alert khi error rate > 1% hoặc p99 > 1s

**Nên có khi scale:**
- [ ] Distributed tracing qua OpenTelemetry
- [ ] Database query tracing
- [ ] Kafka/Cache tracing
- [ ] Dashboard Grafana cho từng service
- [ ] SLA/SLO monitoring

### 5.2. Health check endpoint

```csharp
// Program.cs
builder.Services.AddHealthChecks()
    .AddDbContextCheck<AppDbContext>()           // DB có alive?
    .AddRedis(_config["Redis:Connection"])       // Redis có alive?
    .AddKafka(new ProducerConfig { ... });        // Kafka có alive?

app.MapHealthChecks("/health", new HealthCheckOptions
{
    ResponseWriter = async (ctx, report) =>
    {
        ctx.Response.ContentType = "application/json";
        var json = JsonSerializer.Serialize(new
        {
            status = report.Status.ToString(),
            checks = report.Entries.Select(e => new
            {
                name = e.Key,
                status = e.Value.Status.ToString(),
                duration = e.Value.Duration.TotalMilliseconds
            })
        });
        await ctx.Response.WriteAsync(json);
    }
});
```

### 5.3. Dashboard metrics quan trọng (Grafana)

**Row 1 — Tổng quan:**
- RPS (rate per endpoint)
- Error rate % (5xx / total)
- p50, p95, p99 latency (heatmap)

**Row 2 — Resource:**
- CPU usage (%)
- Memory working set (MB)
- Thread pool queue length
- GC pause time (ms)

**Row 3 — Dependency:**
- DB query duration p99
- Redis hit/miss rate
- Kafka consumer lag

---

## ⚠️ 6. Sai lầm thường gặp & Cách tránh

### ❌ "Có log là đủ"
Không có metrics → không biết xu hướng. Hệ thống chậm dần trong 3 tháng, đến khi sập mới biết.

### ❌ "Log tất cả mọi thứ level Information"
10GB log/ngày → ai đọc? → không ai đọc → có log cũng như không.

**Fix:** Đặt giới hạn (rate limit) cho log. Dùng sampling: 1% request trace, 100% error.

### ❌ "Average latency là đủ"
Như đã giải thích ở trên, average là lừa đảo. Luôn dùng p95/p99.

### ❌ "Không có correlation ID"
Khi user report lỗi, không biết tìm log ở đâu. Không thể nối request qua các service.

**Fix:** Luôn có correlation ID từ API Gateway xuyên suốt.

### ❌ "Quên alert"
Có metrics, có dashboard nhưng không ai ngồi nhìn 24/7. Khi có vấn đề, chỉ phát hiện khi user report.

**Fix:** Alert qua Slack/Telegram/PagerDuty khi metrics vượt ngưỡng:
```
Error rate > 1% trong 5 phút → 🔴 Alarm
p99 latency > 2s trong 10 phút → 🟡 Warning
```

---

## 🧠 Tổng kết — Bạn cần nhớ gì?

| Khái niệm | Bản chất | Ẩn dụ |
|---|---|---|
| **Metrics** | Số đo định kỳ | Máy đo nhịp tim |
| **Logs** | Sự kiện có timestamp | Nhật ký bác sĩ |
| **Traces** | Hành trình request | Phim X-quang |
| **Prometheus** | Kho chứa metrics | Bảng điểm sức khoẻ |
| **Grafana** | Dashboard trực quan | Màn hình ICU |
| **Correlation ID** | UUID xâu chuỗi | Số bệnh án |
| **p99** | 99% request nhanh hơn mức này | Không để 1% khách hàng chết |

---

## ✅ Active Recall Quiz

<details>
<summary><b>Câu 1:</b> 3 trụ cột của Observability là gì? Ẩn dụ bệnh viện tương ứng?</summary>

1. **Metrics** — Máy đo nhịp tim, huyết áp (số đo định kỳ)
2. **Logs** — Nhật ký bác sĩ (sự kiện rời rạc)
3. **Traces** — Phim X-quang (hành trình request xuyên service)
</details>

<details>
<summary><b>Câu 2:</b> RED method và USE method khác nhau thế nào?</summary>

**RED:** Rate, Errors, Duration — dùng cho request-driven services (API).
**USE:** Utilization, Saturation, Errors — dùng cho resource (CPU, RAM, Disk, Network).
</details>

<details>
<summary><b>Câu 3:</b> Tại sao "average latency" là lừa đảo? Nên dùng gì thay thế?</summary>

Average bị skew bởi outlier. 99% request 10ms + 1% request 4000ms → average = ~50ms. Nhìn vào tưởng ổn.

Thay thế bằng **percentile**: p50, p95, p99 (đặc biệt p99).
</details>

<details>
<summary><b>Câu 4:</b> Correlation ID dùng để làm gì?</summary>

Là UUID duy nhất gắn vào mỗi request, truyền qua các service. Giúp xâu chuỗi log/trace lại với nhau để debug request từ đầu đến cuối.
</details>

<details>
<summary><b>Câu 5:</b> Bộ công cụ Observability phổ biến nhất hiện nay (open source) là gì?</summary>

**Prometheus** (metrics) + **Loki** (logs) + **Tempo/Jaeger** (traces) + **Grafana** (dashboard) + **OpenTelemetry** (instrumentation — agent thu thập dữ liệu).
</details>

<details>
<summary><b>Câu 6:</b> Khi cấu hình log, sai lầm lớn nhất là gì?</summary>

Log **Information** cho mọi thứ → 10GB log/ngày, không ai đọc, cost cao, chậm I/O.

**Fix:** Chỉ log business event ở Info. Warning cho bất thường. Error cho thực sự lỗi. Dùng structured log (JSON) + rate limit + sampling.
</details>

---

> 💬 *"Observability không phải là 'có log là được'. Mù 1 trong 3 trụ cột cũng như lái máy bay không có bảng điều khiển — vẫn bay được, nhưng không biết khi nào rơi."*

---

*Bài tiếp theo: Bài 8 — Memory & GC .NET: Stack vs Heap, Generations, Memory Leak*
