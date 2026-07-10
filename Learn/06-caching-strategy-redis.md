---
title: "Bài 6: Caching Strategy — Redis Patterns, Cache Invalidation & Chống Stampede"
description: "Các chiến lược caching với Redis dành cho senior .NET backend engineer: cache-aside, read-through, write-through, write-behind. Phân tích cache invalidation, TTL, và giải pháp chống cache stampede để hệ thống .NET luôn nhanh và ổn định."
tags: [redis, caching, cache-patterns, cache-invalidation, performance, dotnet, distributed-cache]
keywords: [Redis caching, cache-aside, cache invalidation, cache stampede, distributed cache, .NET Redis, caching strategy, TTL, Redis patterns, cache trong .NET]
---

# Bài 6: Caching Strategy — Redis patterns, Invalidation, Stampede

> Dành cho: kỹ sư backend .NET 🔧
> Ngày: 2026-07-10
> Chủ đề: Cache-aside, read-through, write-through, cache invalidation, stampede
> Ẩn dụ xuyên suốt: 🧊 **Tủ đông của quán phở**

---

## 🎯 Tổng quan — Tại sao phải cache?

Quán phở của bạn đông khách. Mỗi lần có khách hỏi "Còn phở không?", bạn chạy vào bếp, mở nồi xem, chạy ra báo. Làm vậy 500 lần/ngày → mệt, chậm.

**Giải pháp**: Chuẩn bị sẵn 1 **tờ giấy ghi số lượng phở còn lại**, treo ở quầy. Khách hỏi → nhìn tờ giấy 1 cái là xong.

```text
KHÔNG CACHE:
Khách ──► Hỏi còn phở? ──► Vào bếp xem ──► Báo ──► 5 giây
                              ▲
                              └── Database call (chậm)

CÓ CACHE:
Khách ──► Hỏi còn phở? ──► Xem tờ giấy ──► Báo ──► 0.1 giây
                              ▲
                              └── Redis get (nhanh)
```

Cache = lưu **kết quả đã tính toán** để lần sau lấy nhanh hơn.

### Khi nào nên cache?

| Nên cache | Không nên cache |
|---|---|
| Dữ liệu đọc nhiều, ghi ít (danh mục, config) | Dữ liệu thay đổi từng giây (giá cổ phiếu) |
| Dữ liệu tốn cost để tính (report, dashboard) | Dữ liệu nhạy cảm (mật khẩu, token) |
| Kết quả aggregation (count, sum, avg) | Dữ liệu user-specific cá nhân (trừ khi có session cache) |
| API response chậm hơn 200ms | Dữ liệu realtime cần chính xác tuyệt đối |

### Lợi ích mang lại

```
Database:          500 req/s  → 100ms/req → 100% CPU
Với cache (80% hit): 100 req/s DB + 400 req/s Redis
                      → 20ms DB + 1ms Redis → 20% CPU
```

---

## 🧊 1. Cache-Aside — Pattern cơ bản nhất

### Cách hoạt động

```text
1. Đọc: Check cache → miss → đọc DB → ghi cache → trả về
2. Ghi: Ghi DB → xoá cache (hoặc cập nhật)
```

```
                     ┌──────────┐
                ┌───►│  Redis   │◄───┐
                │    └──────────┘    │
           (1) GET      ▲      (3) SET
                │       │           │
                ▼       │           │
            ┌───────────────┐       │
            │ Application   ├───────┘
            └───────────────┘
                    │  ▲
            (2) DB  │  │ (4) Trả về
                    ▼  │
               ┌──────────┐
               │  SQL DB  │
               └──────────┘
```

### Code .NET — Cache-Aside

```csharp
public async Task<OrderDto> GetOrderAsync(int orderId)
{
    var cacheKey = $"order:{orderId}";
    
    // 1. Thử cache trước
    var cached = await _cache.GetStringAsync(cacheKey);
    if (cached != null)
    {
        _logger.LogInformation("Cache HIT for {Key}", cacheKey);
        return JsonSerializer.Deserialize<OrderDto>(cached);
    }
    
    _logger.LogInformation("Cache MISS for {Key}", cacheKey);
    
    // 2. Cache miss → query DB
    var order = await _dbContext.Orders
        .Include(o => o.Items)
        .FirstOrDefaultAsync(o => o.Id == orderId);
    
    if (order == null) return null;
    
    // 3. Ghi cache (TTL = 5 phút)
    var serialized = JsonSerializer.Serialize(MapToDto(order));
    await _cache.SetStringAsync(cacheKey, serialized, new TimeSpan(0, 5, 0));
    
    // 4. Trả về
    return MapToDto(order);
}
```

### Khi ghi dữ liệu — Xoá cache chứ không Update

```csharp
// Khi update order
public async Task UpdateOrderAsync(Order order)
{
    // 1. Ghi DB trước
    _dbContext.Orders.Update(order);
    await _dbContext.SaveChangesAsync();
    
    // 2. Xoá cache — để lần đọc sau tự refresh
    var cacheKey = $"order:{order.Id}";
    await _cache.RemoveAsync(cacheKey);
    
    // ⚠️ KHÔNG update cache ở đây
    // Vì update phải serialize đúng DTO → phức tạp, dễ sai
    // Xoá đi → lần đọc sau tự lấy mới → đơn giản, an toàn
}
```

> 🎯 **Rule of thumb**: Ghi DB trước, xoá cache sau — không update cache trực tiếp.

---

## 🔄 2. Cache Invalidation — Khi nào xoá cache?

### Vấn đề: Stale Data

Dữ liệu trong cache **cũ hơn** dữ liệu trong DB → khách thấy thông tin sai.

### 3 cách invalidation

| Cách | Cơ chế | Độ trễ dữ liệu | Độ phức tạp |
|---|---|---|---|
| **TTL (time-to-live)** | Tự động hết hạn sau N phút | Có thể cũ đến N phút | Thấp |
| **Write-through** | Ghi DB + ghi cache cùng lúc | Gần như realtime | Trung bình |
| **Event-driven** | DB change → publish event → xoá cache | Realtime (vài ms) | Cao |

### a) TTL — Đơn giản nhất

```csharp
// Cache 5 phút → sau 5 phút tự xoá
await _cache.SetStringAsync(key, value, TimeSpan.FromMinutes(5));
```

> Chọn TTL dựa trên: dữ liệu có thể cũ bao lâu?
> - Danh mục tỉnh/thành: 1 ngày
> - Tồn kho: 1 phút
> - Config: 5 phút

### b) Write-Through — Ghi DB + cache

```csharp
public async Task UpdateInventoryAsync(int productId, int newQuantity)
{
    // 1. Ghi DB
    var product = await _dbContext.Products.FindAsync(productId);
    product.StockQuantity = newQuantity;
    await _dbContext.SaveChangesAsync();
    
    // 2. Ghi cache — CẬP NHẬT luôn (không xoá)
    var cacheKey = $"product:stock:{productId}";
    await _cache.SetStringAsync(cacheKey, newQuantity.ToString(), 
        TimeSpan.FromMinutes(5));
}
```

**Nhược điểm**: Nếu DB ghi thành công, cache ghi thất bại → stale data.

### c) Event-Driven — Khi có nhiều service

```text
Service A (ghi DB) ──► Kafka ──► Service B (xoá cache)
                                ──► Service C (xoá cache local)
```

Phù hợp microservices, nhiều service cùng dùng 1 cache.

---

## 🚨 3. Cache Stampede — Đàn voi dẫm đạp

### Vấn đề

Cache key `order:123` hết hạn. 50 request cùng hỏi order 123 cùng lúc:

```text
Request 1: Cache MISS → Query DB → Ghi cache → OK (mất 2 giây)
Request 2: Cache MISS → Query DB → Ghi cache → OK (mất 2 giây)  ← Dư thừa!
Request 3: Cache MISS → Query DB → Ghi cache → OK (mất 2 giây)  ← Dư thừa!
...
Request 50: Cache MISS → Query DB → Ghi cache → OK (mất 2 giây) ← Dư thừa!
```

→ **50 query DB giống nhau**, trong khi chỉ cần 1 lần. DB quá tải, có thể sập.

### Giải pháp 1: Lock (Mutex)

```csharp
private static readonly SemaphoreSlim _lock = new(1, 1);

public async Task<OrderDto> GetOrderWithLockAsync(int orderId)
{
    var cacheKey = $"order:{orderId}";
    
    // 1. Check cache (nhanh, không lock)
    var cached = await _cache.GetStringAsync(cacheKey);
    if (cached != null) return Deserialize<OrderDto>(cached);
    
    // 2. Cache miss → lock để chỉ 1 request query DB
    await _lock.WaitAsync();
    try
    {
        // Double-check: có thể request khác đã ghi cache rồi
        cached = await _cache.GetStringAsync(cacheKey);
        if (cached != null) return Deserialize<OrderDto>(cached);
        
        // Thực sự miss → query DB
        var order = await _dbContext.Orders.FindAsync(orderId);
        await _cache.SetStringAsync(cacheKey, Serialize(MapToDto(order)),
            TimeSpan.FromMinutes(5));
        
        return MapToDto(order);
    }
    finally
    {
        _lock.Release();
    }
}
```

### Giải pháp 2: Early Expiry + Background Refresh

Set TTL = 5 phút, nhưng refresh ở phút thứ 4:

```csharp
public async Task<OrderDto> GetOrderSmartAsync(int orderId)
{
    var cacheKey = $"order:{orderId}";
    
    var cached = await _cache.GetStringAsync(cacheKey);
    if (cached == null)
    {
        // Miss → load từ DB
        return await LoadAndCacheOrderAsync(orderId);
    }
    
    // Parse metadata từ cache value
    var entry = JsonSerializer.Deserialize<CacheEntry<OrderDto>>(cached);
    
    // Nếu cache sắp hết hạn (< 20% TTL còn lại) → refresh background
    if (entry.RemainingLifePercent < 0.2)
    {
        _ = Task.Run(() => RefreshOrderCacheAsync(orderId));
        // Trả về entry cũ, khách không phải chờ
    }
    
    return entry.Data;
}

private async Task RefreshOrderCacheAsync(int orderId)
{
    try
    {
        var order = await _dbContext.Orders.FindAsync(orderId);
        await _cache.SetStringAsync($"order:{orderId}",
            Serialize(MapToDto(order)), TimeSpan.FromMinutes(5));
    }
    catch (Exception ex)
    {
        _logger.LogWarning(ex, "Background refresh failed for order {Id}", orderId);
        // Cache cũ vẫn còn, TTL chưa hết → không sao
    }
}
```

### Giải pháp 3: Set TTL ngẫu nhiên

Thay vì tất cả key cùng hết hạn lúc 5 phút → thêm random:

```csharp
var ttl = TimeSpan.FromMinutes(5) + TimeSpan.FromSeconds(Random.Shared.Next(60));
await _cache.SetStringAsync(key, value, ttl);
```

---

## 🏗️ 4. Redis Data Structures — Dùng cái nào?

### String — Cache đơn giản

```bash
SET order:123 "{...}" EX 300
GET order:123
```

Dùng cho: cache object, session, counters.

### Hash — Object có field

```bash
HSET user:456 name "Anh Đạt" role "TechLead" team "ReturnHome"
HGET user:456 name
HGETALL user:456
```

Dùng cho: lư/tra cứu field riêng lẻ của 1 object.

### List — Queue / Timeline

```bash
LPUSH notifications:789 "Đơn hàng mới" "Thanh toán thành công"
LRANGE notifications:789 0 -1  # Lấy tất cả
```

Dùng cho: hàng đợi tạm, feed gần đây.

### Set — Danh sách không trùng

```bash
SADD active_users "user1" "user2" "user3"
SISMEMBER active_users "user1"  # → 1 (có)
SMEMBERS active_users
```

Dùng cho: online users, tags, permission sets.

### Sorted Set — Leaderboard / Priority

```bash
ZADD leaderboard 100 "user1" 85 "user2"   # score = điểm
ZREVRANGE leaderboard 0 2                  # Top 3
```

Dùng cho: xếp hạng, rate limiting (timestamp làm score).

---

## 🎯 5. Cache trong ứng dụng — Áp dụng thế nào?

### Cache danh mục (ít thay đổi)

```csharp
// Cache danh sách sản phẩm — TTL 1 giờ
public async Task<List<ProductDto>> GetProductsAsync()
{
    const string cacheKey = "products:all";
    
    var cached = await _cache.GetStringAsync(cacheKey);
    if (cached != null)
        return JsonSerializer.Deserialize<List<ProductDto>>(cached);
    
    var products = await _dbContext.Products
        .Select(p => new ProductDto { ... })
        .ToListAsync();
    
    await _cache.SetStringAsync(cacheKey, 
        JsonSerializer.Serialize(products),
        TimeSpan.FromHours(1));
    
    return products;
}
```

### Cache lookup value (tiền, loại hàng)

```csharp
// Cache từng product riêng lẻ
public async Task<ProductDto> GetProductAsync(int productId)
{
    var cacheKey = $"product:{productId}";
    
    var cached = await _cache.GetStringAsync(cacheKey);
    if (cached != null)
        return JsonSerializer.Deserialize<ProductDto>(cached);
    
    var product = await _dbContext.Products.FindAsync(productId);
    if (product == null) return null;
    
    // TTL ngắn cho dữ liệu có thể thay đổi (giá, tồn kho)
    await _cache.SetStringAsync(cacheKey, 
        JsonSerializer.Serialize(MapToDto(product)),
        TimeSpan.FromMinutes(5));
    
    return MapToDto(product);
}
```

### Xoá cache khi có thay đổi

```csharp
public async Task UpdateProductAsync(Product product)
{
    _dbContext.Products.Update(product);
    await _dbContext.SaveChangesAsync();
    
    // Xoá cache của product này + cache danh sách
    await _cache.RemoveAsync($"product:{product.Id}");
    await _cache.RemoveAsync("products:all");  // Danh sách cũng cần xoá
}
```

---

## 📊 6. Monitoring Cache

| Metric | Ý nghĩa | Tốt | Xấu |
|---|---|---|---|
| **Cache Hit Ratio** | % request được serve từ cache | > 80% | < 50% |
| **Cache Miss Ratio** | % request phải query DB | < 20% | > 50% |
| **Evicted Keys** | Số key bị đá ra do đầy memory | 0 | > 0 |
| **Expired Keys** | Key hết hạn tự nhiên | Bình thường | Bất thường |

**Cách xem trên Redis:**

```bash
redis-cli INFO stats
# cache_hits: 45000
# cache_misses: 5000
# Hit ratio = 45000 / (45000 + 5000) = 90% ✅

redis-cli INFO memory
# used_memory_human: 256MB
# evicted_keys: 0  ← Nếu > 0 là đang thiếu RAM cho Redis
```

---

## ✅ Tổng kết — Checklist Cache

| Việc | Nên làm |
|---|---|
| Cache-Aside | Pattern cơ bản — thử cache → miss → DB |
| TTL | Luôn set TTL — không có cache vĩnh viễn |
| Xoá cache khi ghi DB | Remove key → lần đọc sau tự refresh |
| Cache Stampede | Dùng lock hoặc early refresh |
| Hit ratio | Monitor, > 80% là tốt |
| Set TTL ngẫu nhiên | Tránh tất cả key hết hạn cùng lúc |
| Redis memory | Set `maxmemory` + `allkeys-lru` policy |
| Không cache sensitive data | Password, token, PII |

---

## 🧪 Active Recall — Kiểm tra trí nhớ

<details>
<summary><strong>1️⃣ Cache-Aside hoạt động thế nào?</strong></summary>

1. Check cache. 2. Nếu HIT → trả về. 3. Nếu MISS → query DB → ghi cache → trả về. Khi ghi DB → xoá cache.
</details>

<details>
<summary><strong>2️⃣ Khi update DB, nên update cache hay xoá cache?</strong></summary>

**Xoá cache**. Vì update cache phải đúng format DTO, sync giữa DB và cache dễ fail. Xoá đi → lần đọc sau tự lấy lại → đơn giản, an toàn.
</details>

<details>
<summary><strong>3️⃣ Cache Stampede là gì?</strong></summary>

Nhiều request cùng hit cache MISS → cùng query DB → DB quá tải. Xảy ra khi cache key vừa hết hạn.
</details>

<details>
<summary><strong>4️⃣ 3 cách chống Cache Stampede?</strong></summary>

1. Lock (chỉ 1 request query DB, các request khác chờ). 2. Early expiry (refresh cache trước khi hết hạn). 3. Random TTL (tránh key cùng lúc hết hạn).
</details>

<details>
<summary><strong>5️⃣ Khi nào dùng Redis Hash thay vì String?</strong></summary>

Khi cần đọc/ghi field riêng lẻ của object (VD: chỉ update 1 field của user profile). Dùng Hash → tiết kiệm bandwidth hơn String vì không cần get/set cả object.
</details>

<details>
<summary><strong>6️⃣ Cache hit ratio 30% có nghĩa gì?</strong></summary>

70% request vào thẳng DB → cache không hiệu quả. Cần xem lại: TTL quá ngắn? Key không đúng? Data ít được đọc lại?
</details>
