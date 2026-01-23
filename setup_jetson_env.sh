#!/bin/bash

# ==============================================================================
# SCRIPT CÀI ĐẶT MÔI TRƯỜNG CHO PROJECT AKIET TRÊN NVIDIA JETSON (JEBOT)
# ==============================================================================
# Hướng dẫn sử dụng:
# 1. Copy script này vào Jetson Nano.
# 2. Cấp quyền thực thi: chmod +x setup_jetson_env.sh
# 3. Chạy: ./setup_jetson_env.sh
# ==============================================================================

set -e  # Dừng ngay nếu có lỗi

echo ">>> [1/6] BẮT ĐẦU CÀI ĐẶT MÔI TRƯỜNG CHO JETSON..."

# 1. Update hệ thống APT
echo "--- Cập nhật danh sách gói (apt update)..."
sudo apt-get update

# 2. Cài đặt các gói hệ thống cần thiết (System Dependencies)
echo ">>> [2/6] Cài đặt thư viện hệ thống & Multimedia..."
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-setuptools \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-tools \
    gstreamer1.0-x \
    gstreamer1.0-gl

# 3. Cài đặt OpenCV & PyQt5 từ kho NVIDIA/Ubuntu
# LƯU Ý: Trên Jetson, KHÔNG cài opencv-python qua pip vì nó mất hỗ trợ GStreamer (phần cứng).
# Hãy dùng bản python3-opencv có sẵn.
echo ">>> [3/6] Cài đặt OpenCV & PyQt5 (Phiên bản tối ưu cho Jetson)..."
sudo apt-get install -y python3-opencv python3-pyqt5

# 4. Cài đặt các thư viện Python bổ trợ (qua pip)
echo ">>> [4/6] Cài đặt Numpy, Scipy & Utils..."
# Numpy bản < 1.25 để tương thích tốt với code cũ và Numba (nếu dùng)
pip3 install "numpy<1.25.0" "scipy<1.11.0" --verbose

# 5. Cấu hình quyền truy cập Camera
echo ">>> [5/6] Cấp quyền truy cập Video cho user: $USER ..."
sudo usermod -a -G video "$USER"

# 6. Kiểm tra & Verify
echo ">>> [6/6] Kiểm tra môi trường..."

echo "--------------------------------------------------------"
python3 -c "
import cv2
import sys
print(f'Python Version: {sys.version.split()[0]}')
print(f'OpenCV Version: {cv2.__version__}')
info = cv2.getBuildInformation()
gst_status = 'YES' if 'GStreamer:                   YES' in info else 'NO'
print(f'OpenCV GStreamer Support: {gst_status}')
"
echo "--------------------------------------------------------"

echo ""
echo "=========================================================="
echo "✅ CÀI ĐẶT HOÀN TẤT!"
echo "=========================================================="
echo "LƯU Ý QUAN TRỌNG:"
echo "1. Nếu 'OpenCV GStreamer Support' là 'NO', camera CSI sẽ KHÔNG chạy được."
echo "   -> Hãy đảm bảo bạn dùng đúng bản python3-opencv của JetPack."
echo "2. Hãy khởi động lại Jetson (sudo reboot) để áp dụng quyền truy cập Camera."
echo "3. Để chạy chương trình:"
echo "   export DISPLAY=:0  # Nếu chạy qua SSH mà muốn hiển thị lên màn hình cắm vào Jetson"
echo "   python3 src/main.py"
echo "=========================================================="
