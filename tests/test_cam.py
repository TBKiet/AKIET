import cv2

# Thử mở camera:
# Nếu là USB Camera: dùng số 0 hoặc 1
# In gia thong tin build de xem co ho tro GStreamer khong
print("OpenCV Build Info (Check for GSTREAMER):")
print(cv2.getBuildInformation())

def get_jetson_gstreamer_source():
    # Pipeline GStreamer (Giong het src/camera.py - verified on Jetson Nano)
    return (
        "nvarguscamerasrc sensor-id=0 ! "
        "video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1 ! "
        "nvvidconv ! "
        "video/x-raw, format=BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! "
        "appsink drop=1"
    )

# cap = cv2.VideoCapture(0) # Cho USB Camera
print("Attempting to open camera with GStreamer pipeline...")
cap = cv2.VideoCapture(get_jetson_gstreamer_source(), cv2.CAP_GSTREAMER) # Cho Jetson CSI Camera

if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        cv2.imwrite("test_image.jpg", frame)
        print("Scuccess! Ảnh đã được lưu tại test_image.jpg")
    else:
        print("Camera mở được nhưng không đọc được frame nào.")
    cap.release()
else:
    print("Không thể mở camera.")
