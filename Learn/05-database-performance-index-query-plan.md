# Bài 5: Database Performance — Index, Query Plan, Connection Pool

> Dành cho: anh Đạt — thợ code có thâm niên 🔧
> Ngày: 2026-07-10
> Chủ đề: SQL Server index, đọc query plan, tối ưu connection pool
> Ẩn dụ xuyên suốt: 📚 **Thư viện sách**

---

## 🎯 Tổng quan — 80% chậm là do Database

Trong hệ thống .NET backend, **database thường là bottleneck số 1**. Code có nhanh cỡ nào, async có xịn cỡ nào, mà query database chậm thì tất cả đều vô nghĩa.

```
Request đến
    │
    ▼
┌─────────────┐     ┌──────────────────┐
│ Controller   │────►│ Business Logic   │────► Database
│ (nhanh)      │     │ (nhanh)          │     │
└─────────────┘     └──────────────────┘     │
                                              ▼
                                      ┌────────────────┐
                                      │ Query mất 2 giây│ ← Bottleneck thật sự
                                      └────────────────┘
```

3 vấn đề chính anh cần hiểu:
1. **Index** — Tra sách có mục lục hay không?
2. **Query Plan** — SQL Server thực sự chạy câu query thế nào?
3. **Connection Pool** — Bao nhiêu kết nối là đủ?

---

## 📐 1. Index — Mục lục của thư viện

### Clustered Index — Sách được sắp xếp

Tưởng tượng thư viện xếp sách **theo số ISBN** (tăng dần). Cần tìm sách ISBN=12345, anh đi thẳng đến kệ đó, lấy ngay.

```sql
-- Mặc định: PK = Clustered Index
CREATE TABLE Orders (
    OrderId INT IDENTITY PRIMARY KEY,  -- ← Tự động tạo Clustered Index
    CustomerId INT,
    TotalAmount DECIMAL(18,2),
    CreatedAt DATETIME
);
```

- Chỉ **1 clustered index / table** (vì chỉ xếp 1 kiểu được)
- Dữ liệu **vật lý** được sắp xếp theo clustered index
- Tìm theo clustered index = **nhanh nhất** (1 lần đọc)

### Non-Clustered Index — Mục lục riêng

Anh mua 1 cuốn "Mục lục tra cứu theo tên tác giả" — không phải sắp xếp lại sách, chỉ là 1 quyển sổ nhỏ ghi:

```
"Tác giả Nguyễn Nhật Ánh → Kệ số 3, hàng 5"
```

```sql
-- Tạo index để tìm nhanh theo CustomerId
CREATE NONCLUSTERED INDEX IX_Orders_CustomerId 
ON Orders (CustomerId);
```

- Có thể có **nhiều non-clustered index** / table
- Index là 1 cấu trúc riêng, **không thay đổi** cách lưu dữ liệu gốc
- Tìm theo non-clustered index → tìm trong index (nhanh) → **bookmark lookup** đến dữ liệu thật (có thể chậm nếu bảng lớn)

### Composite Index — Index nhiều cột

```sql
-- Index trên (CustomerId, CreatedAt)
CREATE NONCLUSTERED INDEX IX_Orders_CustomerId_CreatedAt 
ON Orders (CustomerId, CreatedAt);
```

Query sau sẽ dùng index này:

```sql
-- Dùng được index (CustomerId trước)
SELECT * FROM Orders 
WHERE CustomerId = 100 AND CreatedAt >= '2026-01-01';

-- Dùng được index (chỉ CustomerId thôi cũng được)
SELECT * FROM Orders 
WHERE CustomerId = 100;

-- ⚠️ KHÔNG dùng được index (CreatedAt đứng trước, nhưng CustomerId không có)
SELECT * FROM Orders 
WHERE CreatedAt >= '2026-01-01';
```

> ⚠️ **Rule**: Cột đầu tiên trong composite index phải xuất hiện trong WHERE.
> 
> Giống như tra mục lục sách: "Tìm theo Tên → Họ" được, nhưng "Tìm theo Họ" mà sách sắp theo Tên thì không.

### Covering Index — Index chứa đủ dữ liệu

Nếu query chỉ cần vài cột, index có thể "bao phủ" (cover) query — không cần đụng vào bảng chính:

```sql
-- Query này chỉ cần CustomerId và TotalAmount
SELECT CustomerId, TotalAmount FROM Orders WHERE CustomerId = 100;

-- → Nếu index có cả 2 cột, SQL Server chỉ đọc INDEX, không đọc TABLE
CREATE NONCLUSTERED INDEX IX_Orders_Covering 
ON Orders (CustomerId) 
INCLUDE (TotalAmount, Status);  -- INCLUDE = thêm vào leaf level, không ảnh hưởng sắp xếp
```

Covering index = **nhanh nhất** cho query cụ thể đó.

### Khi nào index gây hại?

Index **tăng tốc SELECT** nhưng **làm chậm INSERT/UPDATE/DELETE** vì SQL Server phải cập nhật cả index lẫn data.

| Nếu bảng | Nên có |
|---|---|
| Đọc nhiều, ghi ít (tra cứu, báo cáo) | Nhiều index |
| Ghi nhiều, đọc ít (log, audit) | Ít index, chỉ clustered PK |
| Cả đọc và ghi | Index hợp lý, monitor missing index |

---

## 🔍 2. Đọc Query Plan — SQL Server chạy query thế nào?

### Cách xem Query Plan

```sql
-- Trong SSMS: Bật "Include Actual Execution Plan" (Ctrl+M)
-- Hoặc:
SET STATISTICS IO ON;
SET STATISTICS TIME ON;

SELECT * FROM Orders WHERE CustomerId = 100;
```

### Các toán tử (operator) chính

| Operator | Ý nghĩa | Tốc độ |
|---|---|---|
| **Index Seek** | Dò index theo đường dẫn (B-tree) | ⚡ Cực nhanh |
| **Index Scan** | Quét toàn bộ index (vẫn chậm hơn Seek) | 🚶 Trung bình |
| **Table Scan** | Quét toàn bộ bảng | 🐢 Cực chậm |
| **Key Lookup** | Từ index → lấy dòng data trong clustered index | 🚶 Có thể chấp nhận |
| **RID Lookup** | Từ non-clustered → lấy dòng data trong heap table (không có clustered) | 🐢 Chậm |
| **Sort** | Sắp xếp | 🐢 Chậm nếu data lớn |
| **Hash Match** | Nối bảng bằng hash | 🚶 Tạm được |
| **Nested Loops** | Nối bảng bằng vòng lặp (1 bảng nhỏ, 1 bảng lớn) | ⚡ Nếu bảng trong nhỏ |

### Cách đọc — Đọc từ phải sang, từ trên xuống

```text
  SELECT (Cost: 0%)
  └── Nested Loops (Cost: 2%)
       ├── Index Seek (Cost: 48%)  ← Tốn nhất! Tối ưu chỗ này
       └── Key Lookup (Cost: 50%)  ← Có thể thêm INCLUDE để bỏ lookup
```

> ⚠️ **Cái bẫy**: Nhìn vào operator có cost cao nhất → đó là nơi cần tối ưu.

### Ví dụ thực tế — Tìm đơn hàng của khách

```sql
-- Query chậm
SELECT o.OrderId, o.TotalAmount, o.Status, c.CustomerName
FROM Orders o
JOIN Customers c ON o.CustomerId = c.CustomerId
WHERE o.CreatedAt >= '2026-01-01' AND o.TotalAmount > 1000000;
```

Nếu không có index trên `CreatedAt`:

```
|-- Hash Match (vì phải scan cả 2 bảng)
     |-- Table Scan (Orders)  ← Chậm! 1.5 triệu dòng
     |-- Table Scan (Customers)
```

Thêm index:

```sql
CREATE NONCLUSTERED INDEX IX_Orders_CreatedAt_Include
ON Orders (CreatedAt)
INCLUDE (CustomerId, TotalAmount, Status);
```

Query plan mới:

```
|-- Nested Loops
     |-- Index Seek (Orders)  ← Chỉ lấy 450 dòng phù hợp
     |-- Key Lookup (Customers) ← 450 lần, tạm chấp nhận
```

---

## 🔗 3. Index trong Entity Framework — Những điều cần biết

### EF Core tạo index tự động

```csharp
// Entity
public class Order
{
    public int Id { get; set; }
    public int CustomerId { get; set; }
    public DateTime CreatedAt { get; set; }
    
    // Navigation property → EF tự tạo FK index
    public Customer Customer { get; set; }
}
```

EF Core tự động tạo index cho foreign key `CustomerId` — tốt.

### Custom index bằng Data Annotation

```csharp
[Index(nameof(CreatedAt), nameof(Status))]
[Index(nameof(CustomerId), IsUnique = false)]
public class Order
{
    // ...
}
```

### Index trong Fluent API

```csharp
protected override void OnModelCreating(ModelBuilder modelBuilder)
{
    modelBuilder.Entity<Order>(entity =>
    {
        // Composite index
        entity.HasIndex(e => new { e.CustomerId, e.CreatedAt })
              .HasDatabaseName("IX_Orders_CustomerId_CreatedAt");
        
        // Filtered index (SQL Server)
        entity.HasIndex(e => e.Status)
              .HasFilter("[Status] = N'Pending'")
              .HasDatabaseName("IX_Orders_PendingStatus");
    });
}
```

> 🎯 Filtered index: chỉ index những dòng Pending → index siêu nhỏ → tìm siêu nhanh.

---

## 🌊 4. Connection Pool — "Bể bơi" kết nối

### Vấn đề

Mỗi lần mở kết nối SQL Server:
1. TCP handshake (3 bước)
2. SSL/TLS handshake
3. Authentication
4. Session setup

→ Mất **20-100ms** mỗi lần mở kết nối mới!

### Giải pháp: Connection Pool

ADO.NET tự động quản lý pool. Khi anh `.Open()` → nó lấy từ pool. Khi anh `.Close()` → nó trả về pool.

```text
┌─────────────────────────────────────────┐
│            Connection Pool              │
│                                         │
│  ┌──────┐ ┌──────┐ ┌──────┐           │
│  │Conn 1│ │Conn 2│ │Conn 3│  ...      │
│  └──────┘ └──────┘ └──────┘           │
│                                         │
└─────────────────────────────────────────┘
      ▲                          ▲
      │                          │
  .Open() ── request ──►    .Close() ── return ──►
```

### Cấu hình connection string

```yaml
# appsettings.json
"ConnectionStrings": {
  "DefaultConnection": "Server=db;Database=ReturnHome;Trusted_Connection=true;
    Min Pool Size=5;
    Max Pool Size=100;
    Connection Lifetime=300;
    Pooling=true"
}
```

| Tham số | Ý nghĩa | Khuyên anh |
|---|---|---|
| `Min Pool Size` | Luôn giữ ít nhất N kết nối sẵn | 5-10 (tránh cold start) |
| `Max Pool Size` | Không mở quá N kết nối | 100-200, tùy RAM server |
| `Connection Lifetime` | Đóng kết nối sau N giây | 300 (5 phút) — tránh connection leak từ network layer |
| `Pooling=true` | Bật pooling | Luôn bật |

### Pool Exhaustion — Cái bẫy kinh điển

```text
Request 1: .Open() → lấy conn
Request 2: .Open() → lấy conn
...
Request 101: .Open() → ⚠️ HẾT POOL! (max=100)
             Chờ... timeout sau 30s → Exception
```

**Nguyên nhân thường gặp:**
1. Quên `.Dispose()` / `.Close()`
2. Dùng synchronous `Task.Result` / `.Wait()` trên async database call
3. Transaction dài không commit/rollback
4. Không dùng `using`:

```csharp
// ❌ SAI — Quên dispose
var conn = new SqlConnection(connectionString);
conn.Open();
// ... làm gì đó
// KHÔNG close → conn ở lại pool đến khi timeout

// ✅ ĐÚNG — using
using var conn = new SqlConnection(connectionString);
await conn.OpenAsync();
// ... xong tự động trả pool

// ✅ CÁCH 2: try/finally
try { conn.Open(); }
finally { conn.Close(); }
```

### Entity Framework + Connection Pool

EF Core dùng connection pool của ADO.NET bên dưới. Nhưng có **bẫy**: mỗi `DbContext` mới mở 1 connection → cần dùng `DbContextFactory`:

```csharp
// ❌ SAI trong background job
using (var db = new AppDbContext())
{
    // ... mỗi lần tạo DbContext mới → new connection
}

// ✅ ĐÚNG
services.AddDbContextPool<AppDbContext>(options =>
    options.UseSqlServer(connectionString, 
        sqlOptions => sqlOptions.MaxBatchSize(100)));
```

---

## 🎯 5. N+1 Query — Kẻ giết hiệu năng thầm lặng

### Vấn đề

```csharp
// Lấy 100 đơn hàng
var orders = await _context.Orders.Take(100).ToListAsync();

foreach (var order in orders)
{
    // ❌ Mỗi lần loop = 1 query riêng!
    Console.WriteLine(order.Customer.Name);
}
```

→ 1 query đầu + 100 query sau = **101 queries**!

### Dùng Include (Eager Loading)

```csharp
// ✅ 1 query với JOIN
var orders = await _context.Orders
    .Include(o => o.Customer)
    .Take(100)
    .ToListAsync();
```

### Dùng Projection

```csharp
// ✅ 1 query, chỉ lấy đúng cột cần
var orderSummaries = await _context.Orders
    .Where(o => o.CreatedAt >= cutoff)
    .Select(o => new OrderSummary
    {
        OrderId = o.Id,
        CustomerName = o.Customer.Name,  // JOIN tự động
        TotalAmount = o.TotalAmount
    })
    .ToListAsync();
```

### Cách phát hiện N+1

Dùng SQL Server Profiler hoặc EF Core Logging:

```csharp
// appsettings.json
"Logging": {
  "LogLevel": {
    "Microsoft.EntityFrameworkCore.Database.Command": "Information"
  }
}
```

Nếu thấy 100 query `SELECT ... FROM Customers WHERE Id = ...` sau 1 query Orders → **N+1 alert!**

---

## ✅ Tổng kết — Checklist Database

| Việc | Nên làm |
|---|---|
| Index cho WHERE thường dùng | `CREATE INDEX IX_... ON Table (Column)` |
| Composite index | Cột hay dùng nhất đặt **đầu tiên** |
| Covering index | Dùng `INCLUDE` cho cột SELECT |
| Xem Query Plan trước | Bật Actual Execution Plan (Ctrl+M) |
| Connection Pool | `Min=5, Max=100, Lifetime=300` |
| Dispose connection | Luôn `using` hoặc try/finally |
| N+1 | Dùng `.Include()` hoặc `.Select()` |
| Filtered index | Index cho trạng thái Pending |
| EF Core batch insert | Dùng `AddRange()` + `SaveChanges()` 1 lần |
| Monitor | Xem `sys.dm_exec_query_stats` |

---

## 🧪 Active Recall — Kiểm tra trí nhớ

<details>
<summary><strong>1️⃣ Clustered vs Non-Clustered Index khác gì nhau?</strong></summary>

Clustered = sắp xếp **dữ liệu vật lý** (chỉ 1 cái/table). Non-clustered = mục lục riêng (nhiều cái được).
</details>

<details>
<summary><strong>2️⃣ Tại sao composite index (A, B) KHÔNG dùng được cho WHERE B = ?</strong></summary>

Vì index được sắp xếp theo A trước, chỉ khi có A mới tìm được B. Giống tra mục lục sách — tìm theo Tên/Họ được, nhưng chỉ có Họ thì không dùng được mục lục Tên/Họ.
</details>

<details>
<summary><strong>3️⃣ Index Seek vs Index Scan khác gì?</strong></summary>

Index Seek = dò theo B-tree, chỉ lấy đúng dòng cần (nhanh). Index Scan = quét toàn bộ index (chậm). Seek tốt hơn Scan rất nhiều.
</details>

<details>
<summary><strong>4️⃣ Khi nào anh nên dùng covering index?</strong></summary>

Khi query SELECT chỉ cần vài cột và WHERE filter mạnh. Dùng INCLUDE để index chứa luôn dữ liệu, không cần lookup về table chính.
</details>

<details>
<summary><strong>5️⃣ Connection pool exhaustion là gì?</strong></summary>

Hết kết nối trong pool (vượt Max Pool Size). Request mới phải chờ → timeout. Nguyên nhân: quên dispose connection, dùng sync blocking, transaction dài.
</details>

<details>
<summary><strong>6️⃣ Làm sao phát hiện N+1 query trong EF Core?</strong></summary>

Bật logging level `Information` cho `Microsoft.EntityFrameworkCore.Database.Command`. Nếu thấy nhiều query lặp lại trong 1 request → N+1.
</details>
