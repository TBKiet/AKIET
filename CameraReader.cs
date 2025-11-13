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

        // Pipeline: xuất raw BGR tới stdout (fd=1)
        // nvvidconv convert trực tiếp sang BGR, bỏ videoconvert để tránh stride alignment issues
        string pipeline =
            $"nvarguscamerasrc ! video/x-raw(memory:NVMM),width={width},height={height},framerate=30/1 ! " +
            $"nvvidconv ! video/x-raw,format=BGR ! fdsink fd=1 sync=false";

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

        running = true;
        readThread = new Thread(ReadLoop) { IsBackground = true };
        readThread.Start();
    }

    private void ReadLoop()
    {
        try
        {
            int frameSize = width * height * 3; // BGR 8-bit
            var buffer = new byte[frameSize];
            Stream stream = gstProcess!.StandardOutput.BaseStream;

            Console.WriteLine($"[CameraReader] Expected frame size: {frameSize} bytes ({width}x{height} BGR)");

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

                // convert BGR -> Image<Rgba32>
                var img = new Image<Rgba32>(width, height);
                int stride = width * 3;
                for (int y = 0; y < height; y++)
                {
                    int baseIdx = y * stride;
                    for (int x = 0; x < width; x++)
                    {
                        byte b = buffer[baseIdx + x * 3 + 0];
                        byte g = buffer[baseIdx + x * 3 + 1];
                        byte r = buffer[baseIdx + x * 3 + 2];
                        img[x, y] = new Rgba32(r, g, b, 255);
                    }
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

