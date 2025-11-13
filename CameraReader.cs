using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;

/// <summary>
/// Đọc raw BGR frames từ gst-launch bằng fdsink fd=1.
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

        // Pipeline tối ưu cho JetBot 2GB AI Kit
        // Sử dụng framerate thấp hơn (15fps) và format BGRx (4-byte aligned)
        // Thêm videoconvert để đảm bảo stride đúng (no padding)
        string pipeline =
            $"nvarguscamerasrc sensor-mode=0 ! " +
            $"video/x-raw(memory:NVMM),width={width},height={height},framerate=15/1,format=NV12 ! " +
            $"nvvidconv ! video/x-raw,format=BGRx ! " +
            $"videoconvert ! video/x-raw,format=RGBA,width={width},height={height} ! " +
            $"fdsink sync=false fd=1";

        gstProcess = new Process();
        gstProcess.StartInfo.FileName = "gst-launch-1.0";
        gstProcess.StartInfo.Arguments = pipeline;
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

        Console.WriteLine($"CameraReader started: {width}x{height} @ 15fps, format=RGBA");
        Console.WriteLine($"Expected frame size: {width * height * 4} bytes");

        running = true;
        readThread = new Thread(ReadLoop) { IsBackground = true };
        readThread.Start();
    }

    private void ReadLoop()
    {
        try
        {
            int frameSize = width * height * 4; // RGBA: 4 bytes per pixel, no padding
            var buffer = new byte[frameSize];
            Stream stream = gstProcess!.StandardOutput.BaseStream;

            while (running && !stream.CanRead)
                Thread.Sleep(10);

            while (running)
            {
                int totalRead = 0;
                while (totalRead < frameSize && running)
                {
                    int read = stream.Read(buffer, totalRead, frameSize - totalRead);
                    if (read <= 0)
                    {
                        // nếu read = 0, gst-process có thể kết thúc; dừng vòng lặp
                        Thread.Sleep(10);
                        continue;
                    }
                    totalRead += read;
                }

                if (!running) break;
                if (totalRead < frameSize) continue;

                // Debug: Log first frame info
                static int frameCount = 0;
                if (frameCount == 0)
                {
                    Console.WriteLine($"First frame received: {totalRead} bytes");
                    Console.WriteLine($"Expected: {frameSize} bytes ({width}x{height}x4)");
                    Console.WriteLine($"Match: {totalRead == frameSize}");
                }
                frameCount++;

                // convert RGBA -> Image<Rgba32> với tối ưu cho JetBot
                // videoconvert đảm bảo stride = width * 4 (no padding)
                var img = new Image<Rgba32>(width, height);

                unsafe
                {
                    img.ProcessPixelRows(accessor =>
                    {
                        int srcStride = width * 4; // RGBA packed, no padding
                        for (int y = 0; y < height; y++)
                        {
                            var dstRow = accessor.GetRowSpan(y);
                            int srcOffset = y * srcStride;

                            for (int x = 0; x < width; x++)
                            {
                                int i = srcOffset + (x * 4);
                                byte r = buffer[i + 0];
                                byte g = buffer[i + 1];
                                byte b = buffer[i + 2];
                                byte a = buffer[i + 3];
                                dstRow[x] = new Rgba32(r, g, b, a);
                            }
                        }
                    });
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

