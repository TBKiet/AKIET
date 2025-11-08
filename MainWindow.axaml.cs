using Avalonia.Controls;
using Avalonia.Media.Imaging;
using Avalonia.Threading;
using System.IO;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;

namespace JetsonVisionApp
{
    public partial class MainWindow : Window
    {
        private CameraReader? cam;
        private int frameCounter = 0;

        public MainWindow()
        {
            InitializeComponent();
            BtnStart.Click += BtnStart_Click;
        }

        private void BtnStart_Click(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            // Tối ưu cho JetBot 2GB: 320x240 @ 15fps

            // VERSION 1: Auto stride detection (dùng nếu version 2 không work)
            // cam = new CameraReader_v2(320, 240);

            // VERSION 2: Force stride với videoscale (default)
            cam = new CameraReader(320, 240);

            cam.FrameReady += OnFrame;
            cam.Start();
            BtnStart.IsEnabled = false;
        }

        private async void OnFrame(Image<Rgba32> img)
        {
            frameCounter++;
            if (frameCounter % 2 != 0) return; // xử lý mỗi 2 frame

            var (annotated, binary) = ImageProcessing.ProcessFrame(img,
                edgeThresh: 80f, minBlobArea: 60);

            await Dispatcher.UIThread.InvokeAsync(() =>
            {
                int w = annotated.Width, h = annotated.Height;

                // Kiểm tra xem kích thước bitmap đã đúng chưa, nếu chưa thì tạo lại
                var bmp = Preview.Source as WriteableBitmap;
                if (bmp == null || bmp.PixelSize.Width != w || bmp.PixelSize.Height != h)
                {
                    bmp = new WriteableBitmap(
                        new Avalonia.PixelSize(w, h),
                        new Avalonia.Vector(96, 96),
                        Avalonia.Platform.PixelFormat.Bgra8888,
                        Avalonia.Platform.AlphaFormat.Opaque);
                    Preview.Source = bmp;
                }

                using (var fb = bmp.Lock())
                {
                    unsafe
                    {
                        byte* dstBase = (byte*)fb.Address;

                        // LẤY STRIDE THỰC TẾ TỪ FRAMEBUFFER
                        int destStride = fb.RowBytes;

                        for (int y = 0; y < h; y++)
                        {
                            // Lấy con trỏ đến đầu hàng ĐÍCH (destination)
                            byte* pDestRow = dstBase + (y * destStride);

                            // Lấy tham chiếu đến hàng NGUỒN (source) để tăng tốc
                            var srcSpan = annotated.GetPixelRowSpan(y);

                            for (int x = 0; x < w; x++)
                            {
                                // Lấy pixel nguồn
                                var p = srcSpan[x];

                                // Tính toán offset trong hàng đích
                                int destOffset = x * 4;

                                pDestRow[destOffset + 0] = p.B;
                                pDestRow[destOffset + 1] = p.G;
                                pDestRow[destOffset + 2] = p.R;
                                pDestRow[destOffset + 3] = 255;
                            }
                        }
                    }
                }

                // Không cần gán lại Preview.Source = bmp; vì WriteableBitmap tự cập nhật
                // (chỉ cần đảm bảo nó được tạo 1 lần và gán ban đầu)
            });
        }

        protected override void OnClosed(System.EventArgs e)
        {
            cam?.Stop();
            base.OnClosed(e);
        }
    }
}

