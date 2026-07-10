---
title: "Bài 8: Memory & GC trong .NET — Stack vs Heap, Generations, Memory Leak & IDisposable"
description: "Hiểu sâu về quản lý bộ nhớ .NET dành cho senior .NET backend engineer: phân biệt Stack và Heap, cơ chế GC Generations (Gen0/1/2), Large Object Heap, memory leak thường gặp, và cách implement IDisposable đúng chuẩn."
tags: [dotnet, memory-management, garbage-collection, stack, heap, performance, idisposable, memory-leak]
keywords: [.NET memory, garbage collection, stack vs heap, GC generations, LOH, memory leak, IDisposable, .NET performance, quản lý bộ nhớ .NET, dọn rác .NET, memory optimization]
---

# Bài 8: Memory & GC trong .NET — Stack vs Heap, Generations, Memory Leak

> Dành cho: kỹ sư backend .NET 🔧
> Ngày: 2026-07-10
> Chủ đề: Stack, Heap, GC Generations (Gen0/1/2), LOH, memory leak, IDisposable
> Ẩn dụ xuyên suốt: 🗑️ **Bãi đậu xe + đội dọn vệ sinh**
> Thời gian đọc: ~20 phút

---

## 🎯 Tổng quan — "Bộ nhớ không phải là vô hạn"

Bạn viết code, tạo object, rồi... quên nó. Nếu không có ai dọn, bộ nhớ sẽ đầy và ứng dụng crash.

**.NET có GC (Garbage Collector) tự động dọn** — nhưng nếu bạn không hiểu GC hoạt động thế nào, bạn sẽ:
- Tạo ra object không cần thiết → GC chạy liên tục → CPU tốn, app chậm.
- Giữ reference không giải phóng → memory leak → app chết sau vài ngày.
- Lưu object lớn vào sai chỗ → LOH fragmentation → app crash vì OutOfMemory.

> **Mục tiêu bài này:** Hiểu cách bộ nhớ .NET hoạt động để viết code **ít tạo garbage**, **tránh memory leak**, và **debug được memory issue** khi nó xảy ra.

---

## 🏗️ 1. Stack vs Heap — Hai khu vực bộ nhớ

Hãy tưởng tượng bộ nhớ là một **khu đất**:

### Stack (Ngăn xếp) — Tủ đồ cá nhân

```
┌─────────────────────┐
│     Stack           │
├─────────────────────┤
│ Main()              │ ← method đang chạy
│   ├─ int x = 5      │
│   └─ int y = 10     │
├─────────────────────┤
│ ProcessOrder()      │
│   ├─ int orderId    │
│   └─ long amount    │
├─────────────────────┤
│ Validate()           │
│   ├─ bool isValid   │
│   └─ string str     │ ← đây là REFERENCE, giá trị ở Heap
└─────────────────────┘
```

**Đặc điểm Stack:**
- Mỗi thread có **1 Stack riêng**.
- Dữ liệu được push/pop theo LIFO (Last In First Out).
- **Tự động dọn** khi method kết thúc — không cần GC.
- Kích thước nhỏ: mặc định ~1MB/thread (.NET).
- Chỉ chứa: **value types** (`int`, `long`, `bool`, `struct`, `enum`) và **references** (con trỏ đến object ở Heap).

### Heap (Đống) — Bãi đậu xe công cộng

```
Heap
┌──────────────────────────────────────┐
│ Gen0: xe đỗ tạm thời (object mới)    │
│   ├─ Order{Id=1, Amount=500000}      │
│   ├─ string "hello"                  │
│   └─ List<int>(capacity=4)           │
├──────────────────────────────────────┤
│ Gen1: xe đỗ lâu hơn                  │
│   └─ DbConnection pool               │
├──────────────────────────────────────┤
│ Gen2: xe đỗ vĩnh viễn                │
│   ├─ Static config                   │
│   └─ Singleton services              │
├──────────────────────────────────────┤
│ LOH (Large Object Heap): xe tải      │
│   └─ byte[85000]                     │
└──────────────────────────────────────┘
```

**Đặc điểm Heap:**
- **Tất cả thread chia sẻ** 1 Heap.
- Chứa: **reference types** (`class`, `string`, `array`, `delegate`, `List<T>`...).
- Không tự động dọn — **GC phải chạy** để dọn.
- Kích thước lớn (có thể GB).
- Tốn kém hơn Stack: allocation + GC collection.

### Quy tắc vàng:

| Loại | Lưu ở đâu? | Ai dọn? |
|---|---|---|
| `int`, `long`, `bool`, `struct`, `enum` | **Stack** (hoặc inline trong object nếu là field của class) | Tự động khi ra khỏi scope |
| `class`, `string`, `array`, `delegate`, `interface` | **Heap** | **GC** |
| `record` | **Heap** (dù có vẻ như value type) | **GC** |

> ⚠️ **Nhiều dev mới hiểu sai:** `struct` luôn ở stack? **Không hẳn.** Nếu struct là field của 1 `class`, thì struct đó nằm **trong Heap** (vì nó là 1 phần của object trên Heap).

---

## ♻️ 2. GC — Garbage Collector hoạt động thế nào?

GC không phải chạy liên tục. Nó chỉ chạy khi:
1. **Gen0 đầy** (thường ~256KB-4MB tuỳ mode).
2. **Hệ thống báo memory pressure** (sắp hết RAM, Windows gửi signal).
3. Bạn gọi **`GC.Collect()`** — nhưng **đừng làm vậy trừ khi bạn thực sự hiểu**.

### 2.1. 3 Generations — Phân loại rác

Ý tưởng thiên tài của GC: **Object trẻ chết nhanh, object già sống lâu.**

> **Weak Generational Hypothesis:** 80-90% object mới tạo ra sẽ không còn được dùng đến sau vài mili giây.

Dựa trên đó, GC chia Heap làm 3 "thế hệ":

| Gen | Ai ở đó? | Kích thước | Tần suất GC |
|---|---|---|---|
| **Gen0** | Object mới tạo | Nhỏ (~256KB-2MB) | **Rất thường xuyên** (cứ vài trăm ms) |
| **Gen1** | Object sống sót sau 1 lần GC | Trung bình | Thường |
| **Gen2** | Object sống sót sau 2+ lần GC | Lớn nhất | **Rất hiếm** (có thể vài phút) |
| **LOH** | Object >= 85KB | Tuỳ ý | Khi cần (không theo Gen) |

### 2.2. GC diễn ra thế nào?

```
Before GC:
Gen0: [A][B][C][D][E][F] ← Gen0 đầy
Gen1: [X][Y] 
Gen2: [StaticConfig][SingletonService]

GC diễn ra (Gen0 collection):
1. Duyệt từ ROOT (static, stack, register) → tìm object còn được tham chiếu.
2. C: không ai dùng → BỎ (rác).
3. E: được dùng → MOVE lên Gen1.
4. F: không ai dùng → BỎ.
5. Nén (compact) Gen0 để không còn lỗ hổng.

After GC (Gen0 collection):
Gen0: [] ← trống
Gen1: [X][Y][E]
Gen2: [StaticConfig][SingletonService]
```

### 2.3. GC Collection types

| Type | Dọn Gen nào? | Tốc độ | Ảnh hưởng |
|---|---|---|---|
| **Gen0** | Gen0 | Nhanh (~1ms) | Hầu như không ảnh hưởng |
| **Gen1** | Gen0 + Gen1 | Trung bình (~5-10ms) | Có thể thấy latency nhỏ |
| **Gen2** | Gen0 + Gen1 + Gen2 | **Chậm (~50-200ms)** | **App bị "đứng" (pause)** |
| **Full** | Gen0 + Gen1 + Gen2 + LOH | **Rất chậm (~100-500ms)** | **Thảm hoạ cho real-time** |

### 2.4. GC Mode — Workstation vs Server

| Mode | Workstation (mặc định) | Server |
|---|---|---|
| Dùng cho | Desktop app, service nhỏ | **Backend API, service lớn** |
| Thread GC | 1 thread | 1 thread/core |
| Priority | Bình thường | Cao |
| Phù hợp | UI-responsive | **Throughput cao** |

```xml
<!-- .csproj — bật Server GC -->
<PropertyGroup>
  <ServerGarbageCollection>true</ServerGarbageCollection>
</PropertyGroup>
```

Hoặc trong `runtimeconfig.json`:
```json
{
  "runtimeOptions": {
    "configProperties": {
      "System.GC.Server": true
    }
  }
}
```

> **Khuyến nghị:** API backend .NET LUÔN bật Server GC. Workstation GC chỉ nên cho desktop app.

---

## 📦 3. LOH (Large Object Heap) — Object lớn là vấn đề đặc biệt

Object >= **85KB** được đặt vào **LOH** thay vì Gen0/1/2.

**Tại sao có LOH riêng?** Vì compact (nén) object lớn rất tốn kém — phải copy cả đống bytes.

**Hậu quả:** LOH **không được compact** (mặc định). Sau một thời gian:

```
LOH: [byte[100KB]][   free   ][byte[50KB]][   free   ][byte[200KB]]
```

Các lỗ hổng (free) nhỏ lẻ → không đủ chỗ cho object lớn mới → **OutOfMemory ngay cả khi tổng RAM còn nhiều**.

Đây gọi là **LOH fragmentation**.

### Cách tránh LOH fragmentation:

1. **Dùng mảng có kích thước cố định** (pooling).
2. **ArrayPool<T>** — tái sử dụng mảng lớn thay vì tạo mới.

```csharp
// ❌ Xấu: tạo mới mỗi lần, gây LOH fragmentation
byte[] buffer = new byte[100_000];
// xử lý...
// Quên không dùng nữa → object rác trên LOH

// ✅ Tốt: dùng ArrayPool, tái sử dụng
byte[] buffer = ArrayPool<byte>.Shared.Rent(100_000);
try
{
    // xử lý...
}
finally
{
    ArrayPool<byte>.Shared.Return(buffer);
}
```

3. **Bật LOH compaction** (từ .NET 5+):

```json
{
  "runtimeOptions": {
    "configProperties": {
      "System.GC.LargeObjectHeapCompactionMode": 1
    }
  }
}
```

⚠️ LOH compaction chậm. Chỉ bật nếu bạn thực sự bị fragmentation.

---

## 💧 4. Memory Leak trong .NET — "Rò rỉ" thế nào khi đã có GC?

Nhiều người nghĩ: ".NET có GC tự động → không thể memory leak". **SAI TO.**

GC chỉ dọn object **không còn được tham chiếu** (unreachable). Nếu bạn **vô tình giữ reference** đến object, GC không bao giờ dọn nó.

Đây là **memory leak .NET** — không leak theo kiểu C/C++ (quên free), mà leak bằng cách **giữ object sống mãi**.

### 4.1. Static event — Kẻ giết người thầm lặng NHẤT

```csharp
// ❌ Memory leak kinh điển!
public class OrderService
{
    public void Subscribe()
    {
        // Static event! OrderEventEmitter sống mãi → subscriber không bao giờ được GC
        OrderEventEmitter.OnOrderCreated += HandleOrderCreated;
    }
    
    private void HandleOrderCreated(object sender, OrderEventArgs e)
    {
        // xử lý...
    }
}

// OrderEventEmitter giữ reference đến OrderService.HandleOrderCreated
// → OrderService không bao giờ được GC → memory leak
```

**Giải pháp:**
```csharp
// ✅ Luôn unsubscribe khi không cần
public class OrderService : IDisposable
{
    public void Subscribe()
    {
        OrderEventEmitter.OnOrderCreated += HandleOrderCreated;
    }
    
    public void Dispose()
    {
        OrderEventEmitter.OnOrderCreated -= HandleOrderCreated;
    }
}
```

### 4.2. Captured variable trong Lambda/Closure

```csharp
// ❌ Closure giữ reference
public class ReportGenerator
{
    private byte[] _hugeReportData = new byte[100_000_000]; // 100MB

    public Func<string> GetReportSummary()
    {
        // Lambda capture _hugeReportData → nó không bao giờ được GC
        return () => $"Report size: {_hugeReportData.Length} bytes";
    }
}
```

**Giải pháp:** Capture đúng cái cần, đừng capture cả object.

```csharp
public Func<string> GetReportSummary()
{
    var size = _hugeReportData.Length; // capture int, không capture cả object
    return () => $"Report size: {size} bytes";
}
```

### 4.3. Thread local storage / AsyncLocal

```csharp
// ❌ AsyncLocal có thể leak nếu không clear
private static AsyncLocal<byte[]> _context = new();

public async Task ProcessAsync()
{
    _context.Value = new byte[100_000_000]; // 100MB
    // ... await ...
    // Quên không clear → _context giữ reference đến 100MB mãi mãi
}
```

**Giải pháp:** Luôn `Dispose` hoặc clear sau khi dùng.

### 4.4. Collection tăng vô hạn (ConcurrentDictionary, List static)

```csharp
// ❌ ConcurrentDictionary không có cơ chế cleanup
private static ConcurrentDictionary<int, byte[]> _cache = new();

public void AddToCache(int id, byte[] data)
{
    _cache[id] = data; // Không bao giờ remove → memory tăng mãi
}
```

**Giải pháp:** Dùng `MemoryCache` có eviction policy, hoặc tự cleanup định kỳ.

### 4.5. Debugging memory leak — Công cụ

| Công cụ | Dùng để |
|---|---|
| **dotnet-counters** | Monitor memory real-time |
| **dotnet-dump** | Lấy dump process |
| **dotnet-gcdump** | Lấy GC dump riêng |
| **Visual Studio Diagnostic Tools** | Heap view, snapshot comparison |
| **Rider Memory Profiler** | .NET memory profiler |

**Các bước debug memory leak:**

```bash
# 1. Monitor memory real-time
dotnet-counters monitor --process-id 1234 System.Runtime

# Output:
# System.Runtime
#     % Time in GC since last GC (%)          0.3
#     Allocation Rate (B / 1 sec)             1,234,567
#     GC Heap Size (MB)                       850       ← đang tăng dần?
#     Gen 0 Size (B)                          2,000,000
#     Gen 1 Size (B)                          5,000,000
#     Gen 2 Size (B)                          800,000,000  ← Gen2 lớn bất thường

# 2. Lấy GC dump
dotnet-gcdump collect --process-id 1234 -o memory.gcdump

# 3. Phân tích: mở trong Visual Studio hoặc dotnet-gcdump analyze
```

---

## ⏱️ 5. GC Pause — Kẻ thù của latency

GC cần **dừng tất cả managed thread** (pause) để dọn rác — càng lâu càng ảnh hưởng latency.

### 5.1. Khi nào GC gây đau?

- Gen2 collection: có thể **50-200ms** — API của bạn không phản hồi trong thời gian đó.
- Nếu có **1000 request/giây**, mỗi request latency bị +200ms do GC → trung bình tăng lên.
- Trong thời gian GC: thread bị freeze → request queue dài ra → thêm timeout.

### 5.2. Background GC — Giải pháp cho .NET Server

Từ .NET 4.5+, có **Background GC** (mặc định khi Server GC được bật):

```
Background GC: GC chạy song song với managed thread
- Dọn Gen0/Gen1 liên tục (concurrent)
- Gen2 vẫn phải pause, nhưng ngắn hơn
```

**Kết quả:** Gen2 collection không còn "đứng hình" lâu nữa, latency ổn định hơn.

### 5.3. Giảm GC pressure — Code sạch = GC nhẹ

```csharp
// ❌ Tạo nhiều garbage
public string GetFullAddress(User user)
{
    return user.City + ", " + user.District + ", " + user.Ward; 
    // 3 string → 3 allocation → GC có việc làm
}

// ✅ Dùng StringBuilder hoặc string interpolation (1 allocation)
public string GetFullAddress(User user)
{
    return $"{user.City}, {user.District}, {user.Ward}";
}

// ❌ LINQ tạo nhiều object tạm
var result = orders.Where(o => o.Amount > 1000).ToList();
// Where tạo iterator object, List tạo array → GC

// ✅ Nếu performance-critical, dùng for loop
var result = new List<Order>();
for (int i = 0; i < orders.Count; i++)
{
    if (orders[i].Amount > 1000)
        result.Add(orders[i]);
}
```

### 5.4. Struct vs Class — Khi nào dùng struct để giảm GC?

```csharp
// ❌ Class: luôn ở Heap → GC phải dọn
public class PointClass
{
    public int X { get; set; }
    public int Y { get; set; }
}

// ✅ Struct: có thể ở Heap tuỳ nơi dùng
public struct PointStruct
{
    public int X;
    public int Y;
}
```

**Khi nào dùng struct (value type)?**
- Object nhỏ (< 16 bytes).
- Immutable hoặc gần immutable.
- Không cần inheritance.
- Được dùng trong array/list lớn (mảng struct contiguous → cache friendly).

**Khi nào KHÔNG dùng struct?**
- Object lớn (> 16 bytes) — copy struct tốn kém hơn copy reference.
- Cần inheritance/polymorphism.
- Được pass qua nhiều method (mỗi lần pass là 1 copy).

---

## 🔧 Tổng kết — Cẩm nang sinh tồn

### Nguyên tắc vàng:
1. **Không gọi GC.Collect()** — để GC tự quyết định.
2. **Bật Server GC** cho API backend.
3. **Unsubscribe event** khi không cần.
4. **Dùng ArrayPool<T> cho buffer lớn** (>= 85KB).
5. **Dùng MemoryCache** thay vì ConcurrentDictionary vô hạn.
6. **Dùng StringBuilder** cho string concatenation nhiều lần.
7. **Monitor:** GC Heap Size, % Time in GC, LOH size.

### Dấu hiệu nhận biết memory issue:

| Triệu chứng | Nguyên nhân có thể |
|---|---|
| RAM tăng đều, không giảm | Memory leak (static event, cache vô hạn) |
| API chậm dần theo thời gian, restart là hết | Gen2 collection lâu, memory fragmentation |
| OutOfMemoryException dù còn RAM | LOH fragmentation |
| % Time in GC > 5% | Tạo quá nhiều garbage, cần tối ưu |
| Gen0 size không reset sau collection | Object bị "pin" bởi P/Invoke, unsafe code |

---

## ✅ Active Recall Quiz

<details>
<summary><b>Câu 1:</b> Stack và Heap khác nhau thế nào? Mỗi cái chứa gì?</summary>

**Stack:** mỗi thread 1 stack riêng, LIFO, tự động dọn, chứa value types + references.

**Heap:** tất cả thread chung, chứa reference types, GC phải dọn.
</details>

<details>
<summary><b>Câu 2:</b> 3 Generations trong GC là gì? Tại sao có 3 Gen?</summary>

**Gen0:** object mới (chết nhanh), **Gen1:** sống sót 1 lần GC, **Gen2:** sống lâu.

Lý do: **Weak Generational Hypothesis** — 80-90% object mới chết ngay. Phân gen để GC không phải duyệt toàn bộ Heap mỗi lần.
</details>

<details>
<summary><b>Câu 3:</b> LOH là gì? Tại sao gây OutOfMemory?</summary>

**LOH (Large Object Heap):** chứa object >= 85KB.

LOH **không compact** mặc định → fragmentation: RAM còn nhiều nhưng không có vùng liên tục đủ lớn cho object mới → OutOfMemory.
</details>

<details>
<summary><b>Câu 4:</b> Kể 3 nguyên nhân memory leak trong .NET và cách fix?</summary>

1. **Static event không unsubscribe** → Fix: unsubscribe trong Dispose
2. **Lambda capture cả object** → Fix: chỉ capture giá trị cần
3. **Collection tăng vô hạn (ConcurrentDictionary)** → Fix: dùng MemoryCache có eviction
</details>

<details>
<summary><b>Câu 5:</b> Server GC vs Workstation GC khác nhau thế nào? Nên dùng cái nào cho API?</summary>

**Server GC:** 1 thread/core, high priority, throughput cao. Phù hợp backend/API.
**Workstation GC:** 1 thread, normal priority. Phù hợp desktop UI.

**API backend LUÔN dùng Server GC.**
</details>

<details>
<summary><b>Câu 6:</b> Tại sao không nên gọi GC.Collect()?</summary>

GC tự biết khi nào cần chạy dựa trên kích thước Gen và memory pressure.

Gọi `GC.Collect()` thủ công:
- Gây Gen2 collection không cần thiết → app đứng.
- Làm object trẻ bị promote lên Gen1/Gen2 sớm → Gen2 phình to.
- Không giải quyết root cause của memory issue.

**Ngoại lệ duy nhất:** Khi bạn biết chính xác mình vừa giải phóng 1 lượng lớn memory (ví dụ load xong 1GB file, không dùng nữa) và muốn trả RAM về OS ngay.
</details>

---

> 💬 *"GC không phải ma thuật. Nó chỉ dọn được object không ai dùng. Giữ reference vô tình = memory leak dù có GC."*

---

*Đây là bài cuối trong lộ trình 8 bài về kỹ thuật backend .NET chuyên sâu. 🎉*
