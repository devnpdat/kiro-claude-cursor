# 🧠 Bài 1: CPU-bound vs I/O-bound — Hiểu để không "đứng chờ nồi sôi"

> **Dành cho:** anh Đạt — thợ code có thâm niên  
> **Ngày:** 2026-07-10  
> **Chủ đề:** Concurrency fundamentals  
> **Thời gian đọc:** ~10 phút

---

## 📌 TL;DR — Tóm gọn 1 câu

> **CPU-bound** = tay bận liên tục (thái rau, băm thịt).  
> **I/O-bound** = đứng chờ, không làm gì (chờ trứng luộc, chờ lò nướng).  
> **90% backend API** của mình là **I/O-bound** — và đó là lý do async/await quan trọng vãi.

---

## 🍳 Ẩn dụ đầu bếp (Chef Metaphor)

Tưởng tượng anh là một **đầu bếp** trong bếp nhà hàng. Anh có nhiều món cần nấu cùng lúc.

### Hai loại công việc trong bếp:

| | 🔪 CPU-bound | ⏳ I/O-bound |
|---|---|---|
| **Là gì?** | Tay anh **bận liên tục** | Anh **đứng chờ**, tay rảnh |
| **Ví dụ bếp** | Thái rau, băm thịt, nặn há cảo | Luộc trứng, chờ lò nướng, chờ nước sôi |
| **CPU làm gì?** | Chạy hết công suất 100% | Ngồi chơi 5-10%, chờ kết quả từ bên ngoài |
| **Bottleneck** | Tốc độ tay (CPU speed) | Thời gian chờ (network, disk, DB) |
| **Giải pháp** | Thêm tay (more threads/cores) | Làm việc khác trong lúc chờ (async) |

### 🧑‍🍳 Đầu bếp thông minh vs Đầu bếp "ngáo"

```
Đầu bếp "ngáo" (blocking/synchronous):
┌─────────────────────────────────────────────────┐
│ Bỏ trứng vô nồi → ĐỨNG NHÌN NỒI 10 PHÚT →    │
│ Trứng chín → Mới bắt đầu thái rau → ...        │
│                                                  │
│ ⏱️ Tổng: 10 + 5 + 8 = 23 phút                  │
└─────────────────────────────────────────────────┘

Đầu bếp thông minh (async):
┌─────────────────────────────────────────────────┐
│ Bỏ trứng vô nồi → TRONG LÚC CHỜ → thái rau → │
│ TRONG LÚC CHỜ → băm thịt → Trứng chín! →      │
│ Xong hết!                                        │
│                                                  │
│ ⏱️ Tổng: ~10 phút (chạy song song)              │
└─────────────────────────────────────────────────┘
```

**Moral of the story:** Anh không cần thêm đầu bếp (thread) để luộc trứng nhanh hơn. Anh chỉ cần **đừng đứng nhìn nồi** — đi làm việc khác trong lúc chờ.

---

## 🔍 Ví dụ cụ thể trong code

### CPU-bound — "Tay bận liên tục"

```python
# 🔪 Image processing — CPU phải tính toán từng pixel
from PIL import Image
img = Image.open("photo.jpg")
img = img.resize((1920, 1080))  # CPU chạy hết tốc lực
img.save("resized.jpg")

# 🔪 Encryption — CPU phải mã hóa từng block
import hashlib
hashlib.pbkdf2_hmac('sha256', password, salt, 100000)  # CPU quay vù vù

# 🔪 Data compression
import gzip
gzip.compress(huge_data)  # CPU nén từng byte

# 🔪 Complex calculations
result = sum(x**2 for x in range(10_000_000))  # CPU: "mệt quá trời"
```

### I/O-bound — "Đứng chờ, tay rảnh"

```python
# ⏳ Database query — CPU gửi query rồi... ngồi chờ
cursor.execute("SELECT * FROM orders WHERE status = 'pending'")
# CPU: "Ê DB, trả kết quả đi..." *ngáp*

# ⏳ HTTP call — gọi service khác rồi chờ
response = requests.get("https://api.payment.com/verify")
# CPU: "Hello? Ai đó? Trả response đi..." *lướt FB*

# ⏳ File I/O — đọc/ghi file
with open("big_file.csv") as f:
    data = f.read()  # CPU chờ disk đọc xong

# ⏳ Sending email
smtp.send_message(email)  # CPU chờ SMTP server respond
```

---

## 📊 Bảng phân loại nhanh

| Task | Loại | Tại sao? |
|------|------|----------|
| Query database (SELECT, INSERT...) | ⏳ **I/O-bound** | CPU gửi query rồi chờ DB trả |
| Gọi REST API bên ngoài | ⏳ **I/O-bound** | Chờ network round-trip |
| Đọc/ghi file | ⏳ **I/O-bound** | Chờ disk |
| Gửi email/SMS | ⏳ **I/O-bound** | Chờ SMTP/SMS gateway |
| Resize ảnh, generate thumbnail | 🔪 **CPU-bound** | CPU xử lý từng pixel |
| Encrypt/decrypt data | 🔪 **CPU-bound** | CPU tính toán crypto |
| Nén/giải nén file (zip, gzip) | 🔪 **CPU-bound** | CPU nén từng block |
| Parse JSON/XML cực lớn | 🔪 **CPU-bound** | CPU parse từng token |
| Sort 10 triệu records in-memory | 🔪 **CPU-bound** | CPU so sánh liên tục |
| Machine learning inference | 🔪 **CPU-bound** | CPU/GPU tính toán ma trận |

---

## 💡 Key Insight — Cái này quan trọng nè

### 90% backend API work là I/O-bound

```
Typical API request lifecycle:
                                                    
  Request → Validate input → Query DB → Call service → Format response → Return
              (CPU: 1ms)     (I/O: 50ms)  (I/O: 100ms)   (CPU: 1ms)
                  │                                          │
                  └──── CPU làm việc: ~2ms ──────────────────┘
                         I/O chờ đợi: ~150ms
                         
  👉 CPU chỉ làm việc 1.3% thời gian. 98.7% là ĐỨNG CHỜ.
```

**Sai lầm phổ biến:** Nhiều dev nghĩ API chậm → cần CPU mạnh hơn → scale up server.  
**Sự thật:** API chậm vì **chờ I/O** → cần **async/await** hoặc **concurrent requests** → không cần server khỏe hơn.

### Công thức đơn giản:

| Triệu chứng | Chẩn đoán | Thuốc |
|---|---|---|
| CPU luôn **100%**, app chậm | 🔪 CPU-bound | Thêm CPU cores, dùng multiprocessing, optimize algorithm |
| CPU chỉ **5-10%**, app VẪN chậm | ⏳ I/O-bound | Dùng async/await, connection pooling, caching, concurrent I/O |

---

## 🔧 Giải pháp cho từng loại

### Với I/O-bound (phổ biến nhất):

```python
# ❌ SAI — Đầu bếp "ngáo": chờ từng món một
user = db.get_user(user_id)          # chờ 50ms
orders = db.get_orders(user_id)      # chờ 50ms  
notifications = db.get_notifs(user_id) # chờ 50ms
# Tổng: 150ms 😴

# ✅ ĐÚNG — Đầu bếp thông minh: chờ tất cả cùng lúc
user, orders, notifications = await asyncio.gather(
    db.get_user(user_id),              # ─┐
    db.get_orders(user_id),            # ─┼─ chạy song song
    db.get_notifs(user_id),            # ─┘
)
# Tổng: ~50ms 🚀 (chỉ chờ cái lâu nhất)
```

```csharp
// C# version — Task.WhenAll
var userTask = db.GetUserAsync(userId);
var ordersTask = db.GetOrdersAsync(userId);
var notifsTask = db.GetNotifsAsync(userId);

await Task.WhenAll(userTask, ordersTask, notifsTask);
// 3 queries chạy song song, chỉ tốn time = max(3 cái)
```

### Với CPU-bound:

```python
# Cần nhiều tay hơn → multiprocessing
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as executor:
    # 4 "đầu bếp" cùng thái rau
    results = list(executor.map(process_image, images))
```

---

## 🧪 Cách nhận biết trong thực tế

### Bước 1: Check CPU usage

```bash
# Linux/Mac
top -p <pid>

# Hoặc dùng htop cho đẹp
htop
```

### Bước 2: Đọc kết quả

```
Kịch bản 1: CPU = 95-100%
→ CPU-bound. App đang "thái rau" liên tục.
→ Giải pháp: optimize algorithm, thêm cores.

Kịch bản 2: CPU = 3-10% nhưng response time = 2 giây  
→ I/O-bound. App đang "đứng chờ nồi sôi".
→ Giải pháp: async, caching, optimize queries.
```

### Bước 3: Profile code (nếu cần)

```python
# Đo thời gian từng phần
import time

start = time.time()
data = db.query("SELECT ...")  # Nếu cái này chiếm 95% time → I/O-bound
print(f"DB query: {time.time() - start:.3f}s")

start = time.time()  
result = heavy_computation(data)  # Nếu cái này chiếm 95% time → CPU-bound
print(f"Computation: {time.time() - start:.3f}s")
```

---

## 🎯 Active Recall — Tự kiểm tra

*Che đáp án lại, trả lời trước rồi mới mở nhé!*

### Câu 1: Database query là CPU-bound hay I/O-bound?

<details>
<summary>👉 Xem đáp án</summary>

**I/O-bound** ⏳  
CPU gửi query đến database server rồi **đứng chờ** kết quả trả về qua network. Giống như anh đầu bếp order nguyên liệu rồi chờ shipper giao — tay anh rảnh, chỉ chờ thôi.

</details>

### Câu 2: Nén file zip là loại nào?

<details>
<summary>👉 Xem đáp án</summary>

**CPU-bound** 🔪  
CPU phải đọc từng byte, tìm pattern, tính toán compression algorithm liên tục. Giống thái rau — tay bận không ngừng.

</details>

### Câu 3: API gọi service bên ngoài rồi chờ response là loại nào?

<details>
<summary>👉 Xem đáp án</summary>

**I/O-bound** ⏳  
CPU gửi HTTP request rồi **ngồi chờ** response. Network latency là bottleneck, không phải CPU. Giống gọi điện order đồ — anh chỉ chờ người ta giao.

</details>

### Câu 4: Khi CPU chỉ 5% mà app vẫn chậm, bottleneck ở đâu?

<details>
<summary>👉 Xem đáp án</summary>

**Bottleneck ở I/O** — database chậm, network latency cao, disk I/O chậm, hoặc đang chờ external service respond.

CPU rảnh (5%) = CPU **muốn** làm nhưng **không có gì để làm** vì đang chờ data từ bên ngoài. Giải pháp: **async/await**, caching, optimize queries, connection pooling — KHÔNG phải upgrade CPU.

</details>

### Câu 5 (Bonus): Anh có 1 API endpoint mà:
- Nhận ảnh upload từ user
- Lưu vào S3
- Resize thành 3 kích thước
- Lưu metadata vào DB
- Trả response

**Phần nào CPU-bound? Phần nào I/O-bound?**

<details>
<summary>👉 Xem đáp án</summary>

| Bước | Loại | Giải thích |
|------|------|------------|
| Upload ảnh từ user | ⏳ I/O | Chờ network nhận data |
| Lưu vào S3 | ⏳ I/O | Chờ S3 API respond |
| **Resize 3 kích thước** | 🔪 **CPU** | **CPU xử lý pixel — đây là phần CPU-bound duy nhất!** |
| Lưu metadata vào DB | ⏳ I/O | Chờ DB write |
| Trả response | ⏳ I/O | Gửi qua network |

👉 4/5 bước là I/O-bound. Chỉ resize ảnh là CPU-bound.  
👉 Nên dùng async cho I/O steps, và có thể offload resize sang background worker.

</details>

---

## 🗺️ Sơ đồ tổng kết

```
                    App chậm?
                       │
            ┌──────────┴──────────┐
            │                     │
       CPU = 100%?          CPU = 5-10%?
            │                     │
      🔪 CPU-bound          ⏳ I/O-bound
            │                     │
    ┌───────┴───────┐    ┌───────┴───────┐
    │               │    │               │
 Optimize      Add more  Use async/   Caching
 algorithm     cores     await         
                         │               
                    Connection        
                    pooling           
```

---

## 📚 Bài tiếp theo

→ **Bài 2: async/await — Cơ chế "đầu bếp thông minh" hoạt động thế nào?**

Sẽ đi sâu vào event loop, coroutine, và tại sao `await` không block thread.

---

> 💬 *"Biết được task của mình là CPU-bound hay I/O-bound là bước đầu tiên để optimize đúng chỗ. Đừng mua dao mới (upgrade CPU) khi vấn đề là anh đang đứng nhìn nồi nước sôi."*
