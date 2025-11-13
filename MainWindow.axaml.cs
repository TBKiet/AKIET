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
            cam = new CameraReader(320, 240); // Giảm độ phân giải để tăng FPS
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

            // Debug log first frame
            if (frameCounter == 2)
            {
                System.Console.WriteLine($"[MainWindow] Image size: {annotated.Width}x{annotated.Height}");
                var p0 = annotated[0, 0];
                var p1 = annotated[10, 0];
                var p2 = annotated[0, 10];
                System.Console.WriteLine($"[MainWindow] Pixel (0,0): R={p0.R}, G={p0.G}, B={p0.B}");
                System.Console.WriteLine($"[MainWindow] Pixel (10,0): R={p1.R}, G={p1.G}, B={p1.B}");
                System.Console.WriteLine($"[MainWindow] Pixel (0,10): R={p2.R}, G={p2.G}, B={p2.B}");
            }

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
                        int stride = fb.RowBytes; // ✅ Lấy stride thực tế của WriteableBitmap

                        // Debug log first frame
                        if (frameCounter == 2)
                        {
                            System.Console.WriteLine($"[MainWindow] Bitmap stride: {stride} bytes (width={w}, expected={w*4})");
                        }

                        for (int y = 0; y < h; y++)
                        {
                            int rowStart = y * stride; // Offset đầu mỗi row
                            for (int x = 0; x < w; x++)
                            {
                                var p = annotated[x, y];
                                int i = rowStart + x * 4; // ✅ Tính đúng với stride thực tế
                                dst[i + 0] = p.B;
                                dst[i + 1] = p.G;
                                dst[i + 2] = p.R;
                                dst[i + 3] = 255;
                            }
                        }

                        // Debug: verify first few pixels in bitmap
                        if (frameCounter == 2)
                        {
                            System.Console.WriteLine($"[MainWindow] Bitmap[0]: B={dst[0]}, G={dst[1]}, R={dst[2]}");
                            System.Console.WriteLine($"[MainWindow] Bitmap[40]: B={dst[40]}, G={dst[41]}, R={dst[42]}");
                        }
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

