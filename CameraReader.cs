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

        // Pipeline tối ưu cho JetBot 2GB AI Kit với stride cố định
        // Sử dụng videoscale để force stride alignment
        string pipeline =
            $"nvarguscamerasrc sensor-mode=0 ! " +
            $"video/x-raw(memory:NVMM),width={width},height={height},framerate=15/1,format=NV12 ! " +
            $"nvvidconv ! video/x-raw,format=RGBA ! " +
            $"videoscale ! video/x-raw,format=RGBA,width={width},height={height},pixel-aspect-ratio=1/1 ! " +
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
            // Đọc buffer lớn hơn expected để catch padding
            int expectedFrameSize = width * height * 4; // RGBA packed
            int maxFrameSize = width * height * 4 + (height * 256); // thêm buffer cho padding
            var buffer = new byte[maxFrameSize];
            Stream stream = gstProcess!.StandardOutput.BaseStream;

            while (running && !stream.CanRead)
                Thread.Sleep(10);

            // Detect actual stride từ first frame
            int actualStride = width * 4; // default
            bool strideDetected = false;

            while (running)
            {
                // Đọc 1 chunk lớn để detect stride
                int chunkSize = strideDetected ? (actualStride * height) : maxFrameSize;
                int totalRead = 0;

                while (totalRead < chunkSize && running)
                {
                    int read = stream.Read(buffer, totalRead, chunkSize - totalRead);
                    if (read <= 0)
                    {
                        Thread.Sleep(10);
                        continue;
                    }
                    totalRead += read;

                    // Stop early nếu đã đọc đủ 1 frame minimal
                    if (!strideDetected && totalRead >= expectedFrameSize)
                    {
                        // Đợi thêm 100ms để xem có data padding không
                        Thread.Sleep(100);
                        if (stream.DataAvailable)
                            continue; // Có thêm data, đọc tiếp
                        else
                            break; // Hết data, đây là 1 frame hoàn chỉnh
                    }
                }

                if (!running) break;
                if (totalRead < expectedFrameSize) continue;

                // Detect stride from first frame
                if (!strideDetected)
                {
                    actualStride = totalRead / height;
                    strideDetected = true;

                    Console.WriteLine($"Stride detection:");
                    Console.WriteLine($"  Total bytes received: {totalRead}");
                    Console.WriteLine($"  Expected (packed): {expectedFrameSize} bytes");
                    Console.WriteLine($"  Detected stride: {actualStride} bytes/row");
                    Console.WriteLine($"  Expected stride: {width * 4} bytes/row");
                    Console.WriteLine($"  Padding per row: {actualStride - (width * 4)} bytes");
                }

                // convert RGBA -> Image<Rgba32>
                var img = new Image<Rgba32>(width, height);

                unsafe
                {
                    img.ProcessPixelRows(accessor =>
                    {
                        for (int y = 0; y < height; y++)
                        {
                            var dstRow = accessor.GetRowSpan(y);
                            int srcOffset = y * actualStride; // Dùng actual stride!

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

