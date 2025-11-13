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
            cam = new CameraReader(320, 240);
            cam.FrameReady += OnFrame;
            cam.Start();
            BtnStart.IsEnabled = false;
        }

        private async void OnFrame(Image<Rgba32> img)
        {
            frameCounter++;
            // JetBot 2GB: xử lý mỗi frame (framerate đã giảm xuống 15fps)
            // Nếu vẫn lag, có thể skip: if (frameCounter % 2 != 0) return;

            var (annotated, binary) = ImageProcessing.ProcessFrame(img,
                edgeThresh: 100f, minBlobArea: 40); // Tăng threshold để giảm số blob

            await Dispatcher.UIThread.InvokeAsync(() =>
            {
                var bmp = new WriteableBitmap(
                    new Avalonia.PixelSize(annotated.Width, annotated.Height),
                    new Avalonia.Vector(96, 96),
                    Avalonia.Platform.PixelFormat.Bgra8888,
                    Avalonia.Platform.AlphaFormat.Opaque);

                using (var fb = bmp.Lock())
                {
                    unsafe
                    {
                        byte* dst = (byte*)fb.Address;
                        int w = annotated.Width, h = annotated.Height;
                        int dstStride = fb.RowBytes;

                        // Sử dụng ProcessPixelRows để đọc từ ImageSharp một cách chính xác
                        annotated.ProcessPixelRows(accessor =>
                        {
                            for (int y = 0; y < h; y++)
                            {
                                var srcRow = accessor.GetRowSpan(y);
                                byte* dstRow = dst + (y * dstStride);

                                for (int x = 0; x < w; x++)
                                {
                                    var p = srcRow[x];
                                    int offset = x * 4;
                                    dstRow[offset + 0] = p.B; // Blue
                                    dstRow[offset + 1] = p.G; // Green
                                    dstRow[offset + 2] = p.R; // Red
                                    dstRow[offset + 3] = 255; // Alpha
                                }
                            }
                        });
                    }
                }
                Preview.Source = bmp;
            });
        }

        protected override void OnClosed(System.EventArgs e)
        {
            cam?.Stop();
            base.OnClosed(e);
        }
    }
}

