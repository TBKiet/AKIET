using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;

/// <summary>
/// Đọc raw RGBA frames từ gst-launch bằng fdsink fd=1.
/// RGBA format: 4 bytes/pixel (R, G, B, A) - output của nvvidconv.
/// </summary>
public class CameraReader : IDisposable
{
    private Process? gstProcess;
    private Thread? readThread;
    private volatile bool running = false;
    private readonly int width;
    private readonly int height;
    public event Action<Image<Rgba32>>? FrameReady;

    public CameraReader(int width = 640, int height = 480)
    {
        this.width = width;
        this.height = height;
    }

    public void Start()
    {
        if (running) return;

        // Pipeline: RGBA format với silent mode
        // RGBA = 4 bytes/pixel (R,G,B,A)
        // silent=true để ngăn GStreamer debug messages leak vào stdout
        string pipeline =
            $"nvarguscamerasrc silent=true ! video/x-raw(memory:NVMM),width={width},height={height},framerate=30/1 ! " +
            $"nvvidconv silent=true ! video/x-raw,format=RGBA ! fdsink fd=1 sync=false silent=true";

        gstProcess = new Process();
        gstProcess.StartInfo.FileName = "gst-launch-1.0";
	gstProcess.StartInfo.Arguments = "-q " + pipeline; // -q = quiet mode, no messages to stdout
        gstProcess.StartInfo.RedirectStandardOutput = true;
        gstProcess.StartInfo.RedirectStandardError = true; // hữu ích để debug
        gstProcess.StartInfo.UseShellExecute = false;
        gstProcess.StartInfo.CreateNoWindow = true;

        gstProcess.ErrorDataReceived += (s, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
                Console.Error.WriteLine("GStreamer: " + e.Data);
        };

        gstProcess.Start();
        gstProcess.BeginErrorReadLine();

        running = true;
        readThread = new Thread(ReadLoop) { IsBackground = true };
        readThread.Start();
    }

    private void ReadLoop()
    {
        try
        {
            int frameSize = width * height * 4; // RGBA = 4 bytes/pixel (R,G,B,A)
            var buffer = new byte[frameSize];
            Stream stream = gstProcess!.StandardOutput.BaseStream;

            Console.WriteLine($"[CameraReader] Expected frame size: {frameSize} bytes ({width}x{height} RGBA)");

            while (running && !stream.CanRead)
                Thread.Sleep(5);

            int frameCount = 0;
            while (running)
            {
                int totalRead = 0;
                while (totalRead < frameSize && running)
                {
                    int read = stream.Read(buffer, totalRead, frameSize - totalRead);
                    if (read <= 0)
                    {
                        // nếu read = 0, gst-process có thể kết thúc; dừng vòng lặp
                        Thread.Sleep(5);
                        continue;
                    }
                    totalRead += read;
                }

                if (!running) break;
                if (totalRead < frameSize) continue;

                // Log first few frames để verify
                frameCount++;
                if (frameCount <= 3)
                {
                    Console.WriteLine($"[CameraReader] Frame {frameCount}: Read {totalRead} bytes (expected {frameSize})");
                }

                // Skip frame 1 nếu chứa text (GStreamer messages leak)
                // Check xem có phải ASCII text không
                if (frameCount == 1)
                {
                    bool isText = true;
                    for (int i = 0; i < Math.Min(20, buffer.Length); i++)
                    {
                        if (buffer[i] > 127 || (buffer[i] < 32 && buffer[i] != 10 && buffer[i] != 13))
                        {
                            isText = false;
                            break;
                        }
                    }
                    if (isText)
                    {
                        Console.WriteLine("[CameraReader] Frame 1 contains text, skipping...");
                        continue; // Skip frame này
                    }
                }

                // convert RGBA -> Image<Rgba32>
                // RGBA format: mỗi pixel 4 bytes [R, G, B, A]
                var img = new Image<Rgba32>(width, height);

                // Sử dụng ProcessPixelRows để có direct memory access và tránh stride issues
                img.ProcessPixelRows(accessor =>
                {
                    int srcStride = width * 4; // RGBA stride
                    for (int y = 0; y < height; y++)
                    {
                        Span<Rgba32> pixelRow = accessor.GetRowSpan(y);
                        int srcRowStart = y * srcStride;

                        for (int x = 0; x < width; x++)
                        {
                            int srcIdx = srcRowStart + x * 4;
                            byte r = buffer[srcIdx + 0];  // RGBA: R ở byte 0
                            byte g = buffer[srcIdx + 1];  // G ở byte 1
                            byte b = buffer[srcIdx + 2];  // B ở byte 2
                            byte a = buffer[srcIdx + 3];  // A ở byte 3 (có thể bỏ qua)
                            pixelRow[x] = new Rgba32(r, g, b, 255); // Force alpha = 255
                        }
                    }
                });

                // Debug: verify raw buffer và pixel đầu tiên của VALID frame đầu tiên
                if (frameCount <= 2) // Log cả frame 1 và 2 để compare
                {
                    // Dump first 50 bytes của buffer
                    Console.Write($"[CameraReader] Frame {frameCount} - Raw buffer first 50 bytes: ");
                    for (int i = 0; i < 50; i++)
                    {
                        Console.Write($"{buffer[i]:X2} ");
                    }
                    Console.WriteLine();

                    // Verify pixels đã convert
                    var p0 = img[0, 0];
                    var p1 = img[10, 0];
                    Console.WriteLine($"[CameraReader] Frame {frameCount} - First pixel (0,0): R={p0.R}, G={p0.G}, B={p0.B}");
                    Console.WriteLine($"[CameraReader] Frame {frameCount} - Pixel (10,0): R={p1.R}, G={p1.G}, B={p1.B}");

                    // Verify buffer position cho pixel (10,0)
                    int idx10 = 10 * 4; // pixel 10 ở row 0
                    Console.WriteLine($"[CameraReader] Frame {frameCount} - Buffer at pixel (10,0): [{idx10}]={buffer[idx10]:X2}, [{idx10+1}]={buffer[idx10+1]:X2}, [{idx10+2}]={buffer[idx10+2]:X2}, [{idx10+3}]={buffer[idx10+3]:X2}");
                }

                FrameReady?.Invoke(img);
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("CameraReader.ReadLoop error: " + ex);
        }
    }

    public void Stop()
    {
        running = false;
        try
        {
            if (gstProcess != null && !gstProcess.HasExited)
            {
                gstProcess.Kill();
                gstProcess.WaitForExit(1000);
            }
        }
        catch { }
    }

    public void Dispose() => Stop();
}
