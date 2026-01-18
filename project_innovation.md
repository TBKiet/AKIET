# Project Innovation Plan

## 1. Mục tiêu & Định hướng

Mục tiêu của đồ án là xây dựng **một hệ thống thị giác máy tính mang tính học thuật cao**, chạy trên **NVIDIA Jetson với chỉ 1 camera**, có khả năng:

* Nhận diện vật thể hình tròn (đĩa)
* Phân loại kích thước (Small / Medium / Large)
* Hiểu cấu trúc không gian (chồng đĩa, vị trí)
* Mô phỏng quá trình lập kế hoạch đường đi của robot

Đồ án **không hướng tới hoàn thiện robot vật lý**, mà tập trung vào:

> *Perception – Measurement – Planning – Visualization*

---

## 2. Giả thuyết & Thiết lập hệ thống (System Hypothesis)

### 2.1 Cấu hình Eye-to-Hand

* Camera **gắn cố định**, quan sát toàn bộ bàn làm việc
* Camera đóng vai trò là **sensor duy nhất**
* Robot (cánh tay) được **mô phỏng bằng hình ảnh và thuật toán**

### 2.2 Góc nhìn Camera

* **Top-down view (khuyến nghị)**

  * Giảm sai số phối cảnh
  * Dễ đo kích thước thực
  * Đơn giản hóa chuyển đổi tọa độ

> Lý do chọn Eye-to-Hand:
>
> * Hệ tọa độ thế giới ổn định
> * Không cần ước lượng pose camera liên tục
> * Phù hợp với đồ án quy mô nhỏ, 1 camera

---

## 3. Kiến trúc hệ thống (System Architecture)

```
Camera
  ↓
Image Acquisition
  ↓
Preprocessing & Calibration
  ↓
Object Detection (Circle / Disc)
  ↓
Size Measurement & Classification
  ↓
Spatial Reasoning (Stack / Position)
  ↓
Path Planning (Simulation)
  ↓
Visualization & UI
```

---

## 4. Công nghệ sử dụng (Tech Stack)

### 4.1 Ngôn ngữ & Môi trường

* Python 3.8+
* NVIDIA Jetson (Nano / Xavier / Orin)

### 4.2 Vision & AI

* **OpenCV**: xử lý ảnh, calibration, Hough Transform
* **YOLOv8 Nano (tùy chọn nâng cao)**:

  * So sánh với phương pháp CV cổ điển
  * Chứng minh khả năng áp dụng Deep Learning hiện đại

### 4.3 Tăng tốc phần cứng

* TensorRT (convert YOLO model sang `.engine`)
* Demo inference tốc độ cao trên Jetson

### 4.4 UI & Visualization

* PyQt6 (khuyến nghị)
* OpenCV overlay (circle, path, text)

---

## 5. Thuật toán chi tiết (Algorithms)

### 5.1 Camera Calibration & Đo lường

**Mục tiêu:** chuyển từ pixel → đơn vị thực (mm)

Các bước:

1. Calibration bằng checkerboard (OpenCV)
2. Undistort ảnh
3. Xác định Pixel-to-Metric ratio bằng vật chuẩn

Kết quả:

* Cho phép đo chính xác đường kính đĩa
* Tránh sai lệch do khoảng cách camera

---

### 5.2 Phát hiện đĩa (Baseline – CV cổ điển)

* Grayscale → Gaussian Blur
* **Hough Circle Transform**

Output:

* Tâm (x, y)
* Bán kính (pixel)

---

### 5.3 Phân loại kích thước (Size Classification)

Chuyển bán kính sang mm:

```
radius_mm = radius_pixel × scale
```

Logic phân loại:

* Small: radius < 30 mm
* Medium: 30–50 mm
* Large: > 50 mm

> Ưu điểm: rõ ràng, dễ giải thích, có tính đo lường thực

---

### 5.4 Phát hiện nâng cao bằng Deep Learning (Extension)

* Sử dụng YOLOv8 Nano
* Train class: `disc`
* Output: Bounding Box + confidence

Mục đích:

* So sánh với Hough Transform
* Đánh giá độ robust với ánh sáng, nền phức tạp

---

### 5.5 Nhận diện cấu trúc chồng đĩa (Spatial Reasoning)

* Xác định tâm chung của các đĩa
* Ước lượng tầng dựa trên vị trí tương đối

> Phần này được xem là **conceptual demonstration**, không yêu cầu chính xác tuyệt đối

---

### 5.6 Lập kế hoạch đường đi (Robot Path Planning – Simulation)

Giả lập robot di chuyển trong mặt phẳng 2D:

* Start: Camera / Robot base
* Goal: Tâm đĩa mục tiêu

Thuật toán:

* Bézier Curve / Parabolic trajectory
* Trapezoidal Velocity Profile

Ý nghĩa:

* Mô phỏng chuyển động mượt của robot
* Tránh va chạm, tránh chuyển động giật cục

---

## 6. Giao diện & Demo (Visualization)

### 6.1 Màn hình trái – Camera View

* Live camera stream
* Vẽ circle / bounding box
* Hiển thị thông số:

  * Diameter (mm)
  * Class (S/M/L)

### 6.2 Màn hình phải – Simulation View

* Không gian 2D nhìn từ trên xuống
* Đĩa được biểu diễn bằng các điểm tròn
* Đường đi robot được vẽ bằng đường cong mượt

---

## 7. Kịch bản Demo (Demo Storytelling)

1. Bật hệ thống
2. Camera nhận diện các đĩa thật
3. Hiển thị kích thước & phân loại
4. Chọn một đĩa mục tiêu
5. Nhấn nút "Sort"
6. Robot ảo di chuyển theo đường cong đến đĩa

> Với giới hạn 1 camera, demo tập trung vào kiểm chứng thuật toán và tư duy hệ thống

---

## 8. Giá trị học thuật & Đóng góp

* Kết hợp **Computer Vision cổ điển + Deep Learning hiện đại**
* Có calibration & đo lường thực
* Có lập kế hoạch chuyển động
* Có mô phỏng trực quan
* Phù hợp phần cứng giới hạn

---

## 9. Hướng mở rộng

* Gắn camera lên robot thật (Eye-in-Hand)
* Thêm inverse kinematics
* 3D simulation (RoboDK)
* Multi-object sorting

---

## 10. Kết luận

Đồ án không chỉ là một demo thị giác máy tính, mà là **một hệ thống nhận thức – ra quyết định – mô phỏng chuyển động** hoàn chỉnh ở quy mô nhỏ. Với giả thuyết hợp lý và lựa chọn thuật toán phù hợp, hệ thống đủ tính học thuật để trình bày trước giảng viên và có khả năng mở rộng trong tương lai.
