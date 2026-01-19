import cv2

# Thử mở camera:
# Nếu là USB Camera: dùng số 0 hoặc 1
# Nếu là Jetson CSI Camera: Cần chuỗi GStreamer (xem bên dưới)
def get_jetson_gstreamer_source(capture_width=1280, capture_height=720, framerate=30, flip_method=0):
    return (
        f'nvarguscamerasrc ! '
        f'video/x-raw(memory:NVMM), width={capture_width}, height={capture_height}, format=NV12, framerate={framerate}/1 ! '
        f'nvvidconv ! '
        f'video/x-raw, format=BGRx ! '
        f'videoconvert ! '
        f'video/x-raw, format=BGR ! appsink'
    )

# Chọn 1 trong 2 dòng dưới đây để test:
# cap = cv2.VideoCapture(0) # Cho USB Camera
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
