using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;

/// <summary>
/// Alternative implementation: Đọc với stride detection tự động
/// </summary>
public class CameraReader_v2 : IDisposable
{
    private Process? gstProcess;
    private Thread? readThread;
    private volatile bool running = false;
    private readonly int width;
    private readonly int height;
    public event Action<Image<Rgba32>>? FrameReady;

    public CameraReader_v2(int width = 640, int height = 480)
    {
        this.width = width;
        this.height = height;
    }

    public void Start()
    {
        if (running) return;

        // Pipeline đơn giản: chỉ output BGRx raw
        // Không force stride, để GStreamer tự quyết định
        string pipeline =
            $"nvarguscamerasrc sensor-mode=0 ! " +
            $"video/x-raw(memory:NVMM),width={width},height={height},framerate=15/1 ! " +
            $"nvvidconv ! video/x-raw,format=BGRx ! " +
            $"fdsink sync=false fd=1";

        gstProcess = new Process();
        gstProcess.StartInfo.FileName = "gst-launch-1.0";
        gstProcess.StartInfo.Arguments = pipeline;
        gstProcess.StartInfo.RedirectStandardOutput = true;
        gstProcess.StartInfo.RedirectStandardError = true;
        gstProcess.StartInfo.UseShellExecute = false;
        gstProcess.StartInfo.CreateNoWindow = true;

        gstProcess.ErrorDataReceived += (s, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
                Console.Error.WriteLine("GStreamer: " + e.Data);
        };

        gstProcess.Start();
        gstProcess.BeginErrorReadLine();

        Console.WriteLine($"CameraReader_v2 started: {width}x{height} @ 15fps, format=BGRx");

        running = true;
        readThread = new Thread(ReadLoop) { IsBackground = true };
        readThread.Start();
    }

    private void ReadLoop()
    {
        try
        {
            Stream stream = gstProcess!.StandardOutput.BaseStream;

            // Tính toán các stride có thể có (aligned to 64, 128, 256 bytes)
            int minStride = width * 4;
            int[] possibleStrides = {
                minStride,
                AlignTo(minStride, 64),
                AlignTo(minStride, 128),
                AlignTo(minStride, 256)
            };

            Console.WriteLine($"Possible strides: {string.Join(", ", possibleStrides)}");

            while (running && !stream.CanRead)
                Thread.Sleep(10);

            // Đọc first frame để detect stride
            int detectedStride = DetectStride(stream, possibleStrides);
            if (detectedStride == 0)
            {
                Console.Error.WriteLine("Failed to detect stride!");
                return;
            }

            Console.WriteLine($"✓ Detected stride: {detectedStride} bytes/row");
            Console.WriteLine($"  Padding per row: {detectedStride - minStride} bytes");

            int frameSize = detectedStride * height;
            var buffer = new byte[frameSize];

            while (running)
            {
                int totalRead = 0;
                while (totalRead < frameSize && running)
                {
                    int read = stream.Read(buffer, totalRead, frameSize - totalRead);
                    if (read <= 0)
                    {
                        Thread.Sleep(10);
                        continue;
                    }
                    totalRead += read;
                }

                if (!running) break;
                if (totalRead < frameSize) continue;

                // Convert BGRx -> Image<Rgba32>
                var img = new Image<Rgba32>(width, height);

                unsafe
                {
                    img.ProcessPixelRows(accessor =>
                    {
                        for (int y = 0; y < height; y++)
                        {
                            var dstRow = accessor.GetRowSpan(y);
                            int srcOffset = y * detectedStride;

                            for (int x = 0; x < width; x++)
                            {
                                int i = srcOffset + (x * 4);
                                byte b = buffer[i + 0];
                                byte g = buffer[i + 1];
                                byte r = buffer[i + 2];
                                // byte padding = buffer[i + 3]; // X channel, ignore
                                dstRow[x] = new Rgba32(r, g, b, 255);
                            }
                        }
                    });
                }

                FrameReady?.Invoke(img);
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("CameraReader_v2.ReadLoop error: " + ex);
        }
    }

    private int DetectStride(Stream stream, int[] possibleStrides)
    {
        // Đọc nhiều data để phân tích pattern
        int maxSize = possibleStrides[^1] * (height + 10);
        var testBuffer = new byte[maxSize];

        int totalRead = 0;
        var timeout = DateTime.Now.AddSeconds(5);

        while (totalRead < maxSize && DateTime.Now < timeout)
        {
            int read = stream.Read(testBuffer, totalRead, maxSize - totalRead);
            if (read > 0)
                totalRead += read;
            else
                Thread.Sleep(50);
        }

        Console.WriteLine($"Read {totalRead} bytes for stride detection");

        // Test mỗi stride có thể
        foreach (int stride in possibleStrides)
        {
            int expectedFrameSize = stride * height;
            if (totalRead >= expectedFrameSize && totalRead < expectedFrameSize + stride)
            {
                // Data size match với stride này
                Console.WriteLine($"Stride {stride} matches (frame size: {expectedFrameSize})");
                return stride;
            }
        }

        // Fallback: tính từ total read
        int calculatedStride = totalRead / height;
        Console.WriteLine($"Calculated stride from data: {calculatedStride}");
        return calculatedStride;
    }

    private static int AlignTo(int value, int alignment)
    {
        return ((value + alignment - 1) / alignment) * alignment;
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
