# Bài 3: Scale — Nâng cấp máy hay thêm máy? K8s bao nhiêu pod?

> Dành cho: anh Đạt — thợ code có thâm niên  
> Ngày: 2026-07-10  
> Chủ đề: Vertical vs Horizontal Scaling, K8s Pod Sizing, HPA  
> Ẩn dụ xuyên suốt: 🍜 **Quán Phở Anh Đạt**

---

## 🎯 Tổng quan — Bài toán kinh điển

Quán phở anh mở đông khách quá. Giờ có 2 lựa chọn:

```
╔══════════════════════════════════════════════════════════════════╗
║                    QUÁN PHỞ ANH ĐẠT                            ║
║                                                                  ║
║   Khách xếp hàng dài ngoài cửa... làm sao đây?                ║
║                                                                  ║
║   Option A: Nâng cấp quán hiện tại                              ║
║             (bếp to hơn, đầu bếp giỏi hơn, thêm bàn)          ║
║                                                                  ║
║   Option B: Mở thêm chi nhánh                                   ║
║             (quán 2, quán 3... cùng công thức)                  ║
╚══════════════════════════════════════════════════════════════════╝
```

Đây chính là **Vertical vs Horizontal Scaling** — câu hỏi mà bất kỳ thợ code nào cũng sẽ gặp khi hệ thống bắt đầu "đông khách".

---

## 📐 Vertical Scaling (Scale UP) = Nâng cấp quán hiện tại

### Ý tưởng

Quán phở hiện tại bé quá → **sửa quán to hơn, mua bếp xịn hơn, thuê đầu bếp pro hơn**.

Trong tech = **thêm RAM, thêm CPU, ổ SSD nhanh hơn** cho CÙNG 1 server.

```
┌──────────────────────────────────────────────────────┐
│              VERTICAL SCALING (Scale UP)              │
│                                                       │
│   TRƯỚC:                    SAU:                      │
│   ┌─────────┐              ┌─────────────────┐       │
│   │ 4 CPU   │              │ 16 CPU          │       │
│   │ 8GB RAM │    ═══►      │ 64GB RAM        │       │
│   │ HDD     │              │ NVMe SSD        │       │
│   │ 🍜 x20  │              │ 🍜 x100         │       │
│   └─────────┘              └─────────────────┘       │
│                                                       │
│   Quán nhỏ                  Quán to bự                │
│   20 khách/h                100 khách/h               │
└──────────────────────────────────────────────────────┘
```

### Ưu điểm

| Ưu điểm | Giải thích bằng quán phở |
|----------|--------------------------|
| **Đơn giản** | Không cần đổi code. Cứ upgrade server thôi. Như mua bếp mới, không cần đổi công thức phở |
| **Không cần load balancer** | Chỉ có 1 quán, khỏi cần người điều phối khách |
| **Dễ debug** | 1 server = 1 chỗ xem log. Dễ tìm bug hơn |

### Nhược điểm — Cái trần nhà

| Nhược điểm | Giải thích |
|-------------|-----------|
| **Có trần (ceiling)** | Server khủng nhất thế giới vẫn có giới hạn. Quán to cỡ nào cũng chỉ chứa X khách |
| **Chi phí tăng theo cấp số nhân** | 16→32GB RAM = x2 giá. Nhưng 128→256GB = x5 đến x10 giá 💸 |
| **Downtime khi upgrade** | Phải đóng quán để sửa. Server phải restart để thêm RAM |
| **Single point of failure** | 1 quán cháy = mất hết. 1 server die = toàn bộ hệ thống sập |

```
💸 Chi phí Vertical Scaling — Đường cong kinh hoàng:

Chi phí ($)
    │                                          ╱
    │                                        ╱
    │                                      ╱
    │                                   ╱
    │                                ╱
    │                            ╱
    │                        ╱
    │                   ╱╱
    │              ╱╱
    │         ╱╱
    │     ╱╱
    │  ╱╱
    │╱
    └────────────────────────────────────────── Tài nguyên
     4GB   8GB   16GB   32GB   64GB   128GB   256GB

    → Càng lên cao, càng đắt kinh khủng!
```

---

## 📐 Horizontal Scaling (Scale OUT) = Mở thêm chi nhánh

### Ý tưởng

Thay vì sửa 1 quán to hơn → **mở thêm chi nhánh**, mỗi quán cùng nấu 1 công thức phở.

Trong tech = **thêm pod/instance/server chạy cùng 1 code**.

```
┌──────────────────────────────────────────────────────────┐
│             HORIZONTAL SCALING (Scale OUT)                │
│                                                           │
│   TRƯỚC:                SAU:                              │
│   ┌─────────┐          ┌─────────┐  ┌─────────┐         │
│   │ Quán 1  │          │ Quán 1  │  │ Quán 2  │         │
│   │ 🍜 x20  │  ═══►   │ 🍜 x20  │  │ 🍜 x20  │         │
│   └─────────┘          └─────────┘  └─────────┘         │
│                         ┌─────────┐  ┌─────────┐         │
│                         │ Quán 3  │  │ Quán 4  │         │
│                         │ 🍜 x20  │  │ 🍜 x20  │         │
│                         └─────────┘  └─────────┘         │
│                                                           │
│   20 khách/h            80 khách/h (4 quán x 20)         │
│                                                           │
│   + Cần: 🧑‍💼 Người điều phối khách (Load Balancer)       │
│   + Cần: 📋 Công thức phở giống nhau (Stateless Code)    │
└──────────────────────────────────────────────────────────┘
```

### Ưu điểm

| Ưu điểm | Giải thích bằng quán phở |
|----------|--------------------------|
| **Không có trần** | Cần thêm? Mở thêm chi nhánh. Lý thuyết: vô hạn |
| **Fault tolerant** | Quán 1 cháy? Còn quán 2, 3, 4 phục vụ. Khách không bị đói |
| **Chi phí tuyến tính** | Gấp đôi khách = gấp đôi quán = gấp đôi chi phí. Công bằng! |
| **Scale linh hoạt** | Giờ cao điểm mở thêm, giờ vắng đóng bớt (K8s HPA!) |

### Nhược điểm — Nhưng khó hơn!

| Nhược điểm | Giải thích |
|-------------|-----------|
| **Cần Load Balancer** | Phải có người điều phối: "Anh đi quán 2, chị đi quán 3" |
| **Code phải stateless** | Phở phải giống nhau mọi quán! Không được kiểu "quán 1 nhớ anh thích thêm hành" mà quán 2 không biết |
| **Phức tạp hơn** | Session, cache, file upload... phải share giữa các quán (Redis, S3...) |
| **Thêm pod ≠ giải quyết mọi vấn đề** | Nếu 1 tô nấu 5 phút, 10 quán nấu vẫn 5 phút/tô |

---

## ⚖️ Golden Rule — Khi nào dùng cái nào?

```
╔════════════════════════════════════════════════════════════════════╗
║                     🏆 QUY TẮC VÀNG                               ║
║                                                                    ║
║  ❓ 1 request chậm?                                               ║
║  → VERTICAL / FIX CODE                                            ║
║  → Mở chi nhánh không giúp gì — 1 tô phở vẫn nấu chậm!         ║
║                                                                    ║
║  ❓ Nhiều request đổ về cùng lúc, server quá tải?                 ║
║  → HORIZONTAL                                                      ║
║  → Chia khách ra nhiều quán!                                       ║
╚════════════════════════════════════════════════════════════════════╝
```

### Bảng quyết định nhanh

| Triệu chứng | Giải pháp | Ẩn dụ phở |
|-------------|-----------|-----------|
| 1 API call mất 5s | Fix code / vertical | Đầu bếp nấu chậm → dạy nấu nhanh hơn, KHÔNG mở thêm quán |
| 100 user đồng thời, server 100% CPU | Horizontal | Quán full bàn → mở chi nhánh |
| Query DB mất 3s | Fix query (index!) | Tìm nguyên liệu trong kho lộn xộn → sắp xếp kho |
| Upload file 1GB chậm | Vertical (RAM/bandwidth) | Cửa quán bé → mở cửa to hơn |
| 10K request/s | Horizontal + cache | 10K khách → chuỗi quán + phở đóng gói sẵn (cache) |

---

## 🐳 K8s Pod Sizing — Quán phở trong Kubernetes

### Khái niệm cơ bản

```
┌──────────────────────────────────────────────────────────────┐
│                    K8s = ÔNG CHỦ CHUỖI                       │
│                                                               │
│   Pod = 1 chi nhánh quán phở                                 │
│   Node = 1 khu phố (có nhiều mặt bằng cho quán)             │
│   Cluster = cả thành phố                                     │
│   Deployment = bản thiết kế quán (bao nhiêu quán, spec gì)  │
│   Service = bảng chỉ đường cho khách                         │
│   HPA = ông chủ xem camera, quyết định mở/đóng chi nhánh   │
│                                                               │
│   ┌─── Node (Khu phố) ───────────────────────┐              │
│   │                                            │              │
│   │  ┌─Pod 1──┐  ┌─Pod 2──┐  ┌─Pod 3──┐     │              │
│   │  │ 🍜     │  │ 🍜     │  │ 🍜     │     │              │
│   │  │0.5 CPU │  │0.5 CPU │  │0.5 CPU │     │              │
│   │  │512MB   │  │512MB   │  │512MB   │     │              │
│   │  └────────┘  └────────┘  └────────┘     │              │
│   │                                            │              │
│   │  Node total: 4 CPU, 8GB RAM               │              │
│   └────────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────────┘
```

### resources.requests vs resources.limits

Đây là phần HAY NHẦM nhất. Hãy nghĩ thế này:

```
resources.requests = Diện tích MẶT BẰNG TỐI THIỂU anh thuê (20m²)
                     → K8s đảm bảo quán anh LUÔN CÓ ít nhất 20m²
                     → Dùng để K8s quyết định xếp pod vào node nào

resources.limits   = Diện tích TỐI ĐA được phép dùng (40m²)
                     → Quán anh mà bày bàn ghế tràn ra quá 40m²?
                     → BỊ ĐUỔI! (OOMKilled / CPU throttled)
```

### YAML mẫu — .NET API điển hình (I/O-bound)

```yaml
# deployment.yaml - Quán Phở API
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pho-api
  labels:
    app: pho-api
spec:
  replicas: 2                    # Mở 2 quán ban đầu (HA)
  selector:
    matchLabels:
      app: pho-api
  template:
    metadata:
      labels:
        app: pho-api
    spec:
      containers:
      - name: pho-api
        image: pho-api:latest
        ports:
        - containerPort: 8080
        resources:
          requests:               # 🏠 Mặt bằng tối thiểu
            cpu: "250m"           # 0.25 core — đủ cho I/O-bound
            memory: "256Mi"       # 256MB — .NET API thường dùng tầm này
          limits:                 # 🚧 Giới hạn tối đa
            cpu: "500m"           # 0.5 core — cho phép burst gấp đôi
            memory: "512Mi"       # 512MB — vượt = OOMKilled 💀
        readinessProbe:           # Kiểm tra quán đã sẵn sàng chưa
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:            # Kiểm tra quán còn hoạt động không
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 20
```

### Giải thích CPU units

```
1 CPU    = 1000m (millicores)
0.5 CPU  = 500m
0.25 CPU = 250m

Ví dụ thực tế:
┌─────────────────────────────────────────────────────┐
│  Loại workload         │  CPU request │  CPU limit  │
├────────────────────────┼──────────────┼─────────────┤
│  .NET I/O-bound API    │  250m        │  500m       │
│  .NET CPU-heavy (calc) │  500m-1000m  │  1000-2000m │
│  Background worker     │  100m        │  250m       │
│  Redis sidecar         │  50m         │  100m       │
└─────────────────────────────────────────────────────┘
```

> 💡 **Mẹo của thợ code có thâm niên**: Với .NET API chủ yếu gọi DB, gọi Redis, gọi API khác (I/O-bound) → **0.25-0.5 core, 256-512MB là đủ**. Đừng phí 2 core 2GB cho cái mà 90% thời gian nó ngồi chờ I/O.

---

## 📈 HPA — Horizontal Pod Autoscaler

### HPA = Ông chủ chuỗi ngồi xem camera

```
┌──────────────────────────────────────────────────────────────┐
│                 HPA — AUTO SCALING                            │
│                                                               │
│   👨‍💼 Ông chủ (HPA) ngồi xem camera:                        │
│                                                               │
│   📹 "Quán 1 đông quá! CPU > 70%"                           │
│       → "Mở thêm quán 2!"                                    │
│                                                               │
│   📹 "Quán 2 cũng đông! CPU > 70%"                          │
│       → "Mở thêm quán 3!"                                    │
│                                                               │
│   📹 "Giờ trưa qua rồi, quán 2,3 vắng hoe..."              │
│       → "Đóng quán 3, giữ quán 1,2"                         │
│                                                               │
│   Timeline:                                                   │
│   ────────────────────────────────────────────────            │
│   06:00  2 pods  ██                                           │
│   11:00  5 pods  █████          (giờ cao điểm trưa)          │
│   14:00  3 pods  ███                                          │
│   17:00  6 pods  ██████         (giờ cao điểm chiều)         │
│   22:00  2 pods  ██             (vắng, scale down)           │
│   ────────────────────────────────────────────────            │
└──────────────────────────────────────────────────────────────┘
```

### YAML mẫu — HPA config

```yaml
# hpa.yaml - Ông chủ tự động mở/đóng chi nhánh
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: pho-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: pho-api
  minReplicas: 2              # 🔒 Luôn giữ ít nhất 2 quán (HA)
                               #    1 quán chết → quán kia vẫn phục vụ
  maxReplicas: 8              # 🚫 Tối đa 8 quán
                               #    Vì DB chỉ chịu được ~80 connections
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70   # 📊 CPU > 70% → scale up
                                  #    Tại sao 70% không phải 90%?
                                  #    → Cần headroom cho burst traffic
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80   # 📊 Memory > 80% → scale up
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60    # Chờ 1 phút trước khi scale up
                                         # (tránh scale vì spike tạm thời)
      policies:
      - type: Pods
        value: 2                         # Tối đa thêm 2 pod mỗi lần
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300   # Chờ 5 phút trước khi scale down
                                         # (tránh "đóng quán" rồi lại phải "mở lại")
      policies:
      - type: Pods
        value: 1                         # Tối đa giảm 1 pod mỗi lần
        periodSeconds: 120              # Mỗi 2 phút mới giảm thêm
```

### Giải thích các con số

```
minReplicas: 2
├── Tại sao KHÔNG PHẢI 1?
│   → 1 pod chết = DOWNTIME. Khách đến quán thấy đóng cửa!
│   → 2 pod = High Availability. 1 pod restart, pod kia vẫn phục vụ
│
maxReplicas: 8
├── Tại sao KHÔNG PHẢI 100?
│   → Mỗi pod mở ~10 DB connections
│   → 100 pods = 1000 connections → DB chết ngay!  💀
│   → Tính: DB max connections / connections per pod = max pods
│   → Ví dụ: 100 DB connections / 10 per pod = max 10 pods
│
averageUtilization: 70 (CPU)
├── Tại sao 70% không phải 90%?
│   → 90% = quá sát giới hạn
│   → Burst traffic đến → CPU 100% → pod chậm/crash TRƯỚC KHI kịp scale
│   → 70% = đủ headroom, HPA có thời gian mở thêm quán
```

---

## 🔢 Công thức tính Pod

### Công thức cơ bản

```
┌──────────────────────────────────────────────────────────────┐
│                    CÔNG THỨC TÍNH POD                         │
│                                                               │
│   Pods cần = Peak RPS ÷ RPS mỗi pod                         │
│                                                               │
│   Sau đó: × 1.3 đến 1.5 (buffer 30-50%)                    │
│                                                               │
│   ──────────────────────────────────────                      │
│   Ví dụ thực tế:                                             │
│                                                               │
│   📊 Peak traffic: 200 req/s (giờ cao điểm)                 │
│   📊 1 pod xử lý: 50 req/s (đo bằng load test)             │
│                                                               │
│   Pods cần = 200 ÷ 50 = 4 pods                              │
│   + Buffer 30% = 4 × 1.3 = 5.2 ≈ 6 pods                    │
│                                                               │
│   → HPA config: min=2, max=8                                 │
│     (min=2 cho HA, max=8 cho peak + thêm buffer)            │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Bảng tham khảo nhanh — .NET API (I/O-bound)

| Pod spec | RPS ước tính | Ghi chú |
|----------|-------------|---------|
| 0.25 core, 256MB | 30-50 req/s | API đơn giản, query nhẹ |
| 0.5 core, 512MB | 50-100 req/s | API trung bình, có cache |
| 1 core, 1GB | 100-200 req/s | API phức tạp, nhiều logic |

> ⚠️ **Cảnh báo**: Nếu pod 0.5 core mà **dưới 30 req/s** → **CHECK CODE TRƯỚC!** Đừng vội thêm pod. Như kiểu đầu bếp nấu 1 tô mất 10 phút — thêm bếp không giúp gì, phải dạy đầu bếp nấu nhanh hơn!

### Ví dụ tính toán đầy đủ

```
🏪 Hệ thống quán phở Online:

Dữ kiện:
- Peak traffic: 500 req/s (11h-13h trưa)
- Off-peak: 50 req/s (22h-6h)
- Load test: 1 pod (0.5 core, 512MB) xử lý ~80 req/s
- DB PostgreSQL: max_connections = 100
- Mỗi pod dùng connection pool size = 10

Tính toán:
1. Pods cho peak   = 500 ÷ 80 = 6.25 → 7 pods
2. + Buffer 30%    = 7 × 1.3 = 9.1 → 10 pods
3. Check DB limit  = 100 ÷ 10 = 10 pods max ← 😬 SÁT LIMIT!
4. Giảm pool size  = 100 ÷ 5 = 20 pods max ← OK, nhưng pool nhỏ quá
5. Hoặc thêm cache → giảm DB calls → mỗi pod cần ít connections hơn ✅

Kết luận:
- minReplicas: 2 (off-peak + HA)
- maxReplicas: 10 (peak + buffer, nhưng phải monitor DB connections!)
- Thêm Redis cache → giảm 60% DB calls → thực tế chỉ cần 4-6 pods
```

---

## 🪤 Classic Trap — Cái bẫy kinh điển

### Death Spiral — Vòng xoáy chết

Đây là cái bẫy mà nhiều team dính phải. Đọc kỹ nha:

```
            💀 THE DEATH SPIRAL 💀

   More pods ──────────────────────────────►
       │                                     │
       │  ┌──────────────────────────────┐  │
       │  │ Pods nhiều hơn               │  │
       │  │     ↓                        │  │
       │  │ DB connections tăng          │  │
       │  │     ↓                        │  │
       │  │ DB quá tải, query chậm       │  │
       │  │     ↓                        │  │
       │  │ Tất cả pods chậm theo        │  │
       │  │     ↓                        │  │
       │  │ CPU tăng vì request pending  │  │
       │  │     ↓                        │  │
       │  │ HPA thấy CPU cao            │  │
       │  │     ↓                        │  │
       │  │ HPA thêm NHIỀU pods hơn!    │  │
       │  │     ↓                        │  │
       │  │ DB connections tăng NỮA      │  │
       │  │     ↓                        │  │
       │  │ 💀 DB CHẾT → TẤT CẢ CHẾT   │  │
       │  └──────────────────────────────┘  │
       │                                     │
       ◄─────────────────────────────────────┘
              Repeat until 💀💀💀
```

### Ẩn dụ quán phở

> Quán phở đông quá → mở thêm chi nhánh → tất cả chi nhánh đều gọi nguyên liệu từ **1 kho duy nhất** → kho quá tải → tất cả quán đều thiếu nguyên liệu → khách chờ lâu → mở thêm chi nhánh NỮA → kho **SẬP** → tất cả quán **ĐÓNG CỬA** 💀

### Giải pháp — CHECK TRƯỚC KHI SCALE

```
🔍 Trước khi thêm pod, PHẢI check theo thứ tự:

1. DB Connection Pool
   → Tổng connections = pods × pool_size
   → PHẢI < DB max_connections (để headroom)
   
2. Redis Cache
   → Cache các query hay dùng
   → Giảm 50-80% DB calls
   
3. Async đúng cách
   → await Task.WhenAll() thay vì await từng cái
   → Không block thread pool
   
4. Query optimization
   → Index đã đúng?
   → N+1 query?
   → SELECT * hay SELECT cần gì lấy đó?
```

---

## ✅ Checklist trước khi Scale

Mỗi lần muốn thêm pod, chạy qua checklist này:

```
┌──────────────────────────────────────────────────────────────┐
│           📋 CHECKLIST TRƯỚC KHI SCALE                       │
│                                                               │
│   □ 1. Code async/await đúng chưa?                          │
│        → ConfigureAwait(false) cho library code              │
│        → Không .Result hay .Wait() (sync over async)         │
│        → Task.WhenAll cho parallel calls                     │
│                                                               │
│   □ 2. Database queries tối ưu chưa?                        │
│        → Có index cho WHERE/JOIN columns?                    │
│        → Có bị N+1 query không? (Include/Join)              │
│        → SELECT chỉ columns cần thiết?                      │
│        → Connection pool size hợp lý?                       │
│                                                               │
│   □ 3. Cache những gì cần cache chưa?                       │
│        → Redis cho hot data?                                 │
│        → In-memory cache cho static data?                    │
│        → Response caching cho GET endpoints?                 │
│                                                               │
│   □ 4. Bottleneck ở đâu — CPU hay I/O?                     │
│        → CPU cao + I/O thấp = CPU-bound → có thể vertical   │
│        → CPU thấp + I/O chờ lâu = I/O-bound → fix query/    │
│          cache trước, horizontal SAU                          │
│        → CPU cao + I/O cao = quá tải thật → horizontal OK   │
│                                                               │
│   □ 5. TẤT CẢ trên OK → Scale horizontal!                  │
│        → Tính pods cần bao nhiêu                             │
│        → Check DB connection limits                          │
│        → Set HPA min/max hợp lý                             │
│                                                               │
│   ⚠️  SKIP checklist = mời Death Spiral vào nhà             │
└──────────────────────────────────────────────────────────────┘
```

---

## ❌ Bảng sai lầm phổ biến

| Sai lầm | Tại sao sai? | Đúng ra là |
|---------|-------------|-----------|
| **API chậm → thêm pod** | 1 request vẫn chậm trên 10 pods. 10 quán nấu, 1 tô vẫn 5 phút! | Fix code/query TRƯỚC |
| **Mỗi pod 2 core 2GB** | Phí phạm cho I/O-bound API. Như thuê mặt bằng 200m² để bán phở take-away | 0.25-0.5 core, 256-512MB |
| **minReplicas: 1** | Pod chết = downtime. 1 quán = không có backup | Min 2 cho HA |
| **maxReplicas: 100** | 100 pods × 10 connections = 1000 → DB chết! | Tính dựa trên DB connection limit |
| **Không set limits** | Pod ăn hết RAM của node → node crash → tất cả pod trên node chết | **LUÔN** set limits |
| **Chỉ scale CPU, quên memory** | Memory leak → OOM → pod restart liên tục | Monitor cả CPU lẫn memory |
| **Scale trước, optimize sau** | Tốn tiền gấp 5 cho vấn đề giải quyết bằng 1 dòng index | Optimize TRƯỚC, scale SAU |

---

## 🧩 Bài tập so sánh nhanh

```
┌────────────────────────────────────────────────────────────────┐
│                VERTICAL vs HORIZONTAL                          │
│                                                                │
│              Vertical          │       Horizontal               │
│  ──────────────────────────────┼──────────────────────────────  │
│  Nâng cấp quán                │  Mở thêm chi nhánh             │
│  Thêm RAM/CPU                 │  Thêm pod/instance              │
│  Có trần (ceiling)            │  Không trần (lý thuyết)         │
│  Đơn giản, không đổi code     │  Cần stateless, load balancer   │
│  Chi phí exponential          │  Chi phí linear                 │
│  Single point of failure      │  Fault tolerant                 │
│  Downtime khi upgrade         │  Zero downtime (rolling update) │
│  Fix 1 request chậm           │  Fix nhiều request đồng thời    │
│  Dễ debug (1 server)          │  Khó hơn (distributed)          │
│  Phù hợp: dev, staging        │  Phù hợp: production            │
└────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Active Recall — Tự kiểm tra

Che đáp án bên dưới, trả lời trước rồi mới check!

### Câu hỏi

1. **API mỗi request mất 5 giây, nên thêm pod hay fix code?**

2. **Vertical scaling giống gì trong ẩn dụ quán phở?**

3. **Tại sao maxReplicas: 100 có thể giết DB?**

4. **200 req/s peak, 50 req/s per pod → mấy pod (cả buffer)?**

5. **Trước khi scale pod, check 4 thứ gì?**

---

### Đáp án

<details>
<summary>1. Fix code hay thêm pod?</summary>

**FIX CODE!** 1 request mất 5 giây thì 10 pods vẫn mất 5 giây cho request đó. Thêm pod chỉ giúp khi NHIỀU request đến cùng lúc, không giúp khi 1 request chậm. Như mở thêm quán phở nhưng đầu bếp vẫn nấu 5 phút/tô — thêm quán không giúp khách nhận phở nhanh hơn.

</details>

<details>
<summary>2. Vertical scaling = ?</summary>

**Nâng cấp quán hiện tại** — bếp to hơn, đầu bếp giỏi hơn, thêm bàn ghế trong CÙNG 1 quán. Tương đương thêm RAM, CPU, SSD cho cùng 1 server.

</details>

<details>
<summary>3. Tại sao maxReplicas: 100 nguy hiểm?</summary>

Mỗi pod mở connection pool đến DB (ví dụ 10 connections/pod). 100 pods = 1000 DB connections. Hầu hết DB (PostgreSQL, MySQL) có giới hạn max_connections (thường 100-500). Vượt quá → DB từ chối connections → TẤT CẢ pods fail → **Death Spiral**: HPA thấy CPU cao → thêm pods → thêm connections → DB chết nhanh hơn 💀

</details>

<details>
<summary>4. Tính pods?</summary>

```
Pods cần = 200 ÷ 50 = 4 pods
+ Buffer 30% = 4 × 1.3 = 5.2 ≈ 6 pods

HPA config: min=2, max=8
(min=2 cho HA, max=8 cho peak + thêm buffer)
```

</details>

<details>
<summary>5. Checklist 4 thứ trước khi scale?</summary>

1. **Async/await** đúng chưa? (không sync-over-async, dùng Task.WhenAll)
2. **Database queries** tối ưu chưa? (index, N+1, connection pool)
3. **Cache** những gì cần cache chưa? (Redis, in-memory)
4. **Bottleneck** ở đâu? CPU-bound hay I/O-bound?

Tất cả OK rồi → MỚI scale horizontal!

</details>

---

## 🔑 Takeaway — Ghi nhớ cuối bài

```
╔══════════════════════════════════════════════════════════════╗
║  1. 1 request chậm → FIX CODE, đừng thêm pod               ║
║  2. Nhiều request quá tải → HORIZONTAL (thêm pod)           ║
║  3. Pod .NET I/O-bound: 0.25-0.5 core, 256-512MB là đủ     ║
║  4. LUÔN set resources.requests AND limits                   ║
║  5. minReplicas ≥ 2 cho HA                                   ║
║  6. maxReplicas tính theo DB connection limit                ║
║  7. HPA target CPU 70% (chừa headroom)                      ║
║  8. OPTIMIZE CODE TRƯỚC → SCALE SAU                         ║
║  9. Coi chừng Death Spiral: pods ↑ → DB connections ↑ → 💀  ║
╚══════════════════════════════════════════════════════════════╝
```

> 💬 *"Quán phở ngon không phải vì có 100 chi nhánh, mà vì 1 tô phở nấu đã ngon sẵn. Scale code cũng vậy — optimize trước, scale sau."*
> — Thợ code có thâm niên

---

*Bài tiếp theo: Bài 4 — Caching Strategy: Redis, In-Memory, và khi nào dùng cái gì?*
