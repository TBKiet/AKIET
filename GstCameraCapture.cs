using System;
using Gst;
using Gst.App;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;

public class GstCameraCapture : IDisposable
{
    private readonly Pipeline pipeline;
    private readonly AppSink appsink;
    private readonly int width;
    private readonly int height;
    public event Action<Image<Rgba32>>? FrameReady;

    public GstCameraCapture(int width = 640, int height = 480)
    {
        this.width = width;
        this.height = height;
        Application.Init();

        pipeline = new Pipeline("camera-pipeline");

        var src = ElementFactory.Make("nvarguscamerasrc", "src");
        var conv1 = ElementFactory.Make("nvvidconv", "conv1");
        var conv2 = ElementFactory.Make("videoconvert", "conv2");
        var capsfilter = ElementFactory.Make("capsfilter", "filter");
        appsink = ElementFactory.Make("appsink", "mysink") as AppSink 
                  ?? throw new Exception("Không tạo được appsink!");

        if (src == null || conv1 == null || conv2 == null)
            throw new Exception("Không tạo được 1 trong các phần tử GStreamer!");

        // cấu hình định dạng cho conv1 → conv2
        var caps = Caps.FromString($"video/x-raw,width={width},height={height},format=BGR");
        capsfilter["caps"] = caps;

        // cấu hình appsink
        appsink.EmitSignals = true;
        appsink.Drop = true;
        appsink.MaxBuffers = 1;
        appsink.NewSample += OnNewSample;

        // thêm các phần tử vào pipeline
        pipeline.Add(src, conv1, conv2, capsfilter, appsink);

        // link từng đoạn
        if (!src.Link(conv1))
            throw new Exception("Không link được src → conv1");
        if (!conv1.Link(conv2))
            throw new Exception("Không link được conv1 → conv2");
        if (!conv2.Link(capsfilter))
            throw new Exception("Không link được conv2 → capsfilter");
        if (!capsfilter.Link(appsink))
            throw new Exception("Không link được capsfilter → appsink");
    }

    private void OnNewSample(object sender, GLib.SignalArgs args)
    {
        var sample = appsink.PullSample();
        if (sample == null) return;

        var buffer = sample.Buffer;
        buffer.Map(out MapInfo map, MapFlags.Read);
        byte[] raw = map.Data;
        if (raw == null)
        {
            buffer.Unmap(map);
            sample.Dispose();
            return;
        }

        int stride = width * 3;
        var img = new Image<Rgba32>(width, height);
        for (int y = 0; y < height; y++)
        {
            int offset = y * stride;
            for (int x = 0; x < width; x++)
            {
                byte b = raw[offset + x * 3 + 0];
                byte g = raw[offset + x * 3 + 1];
                byte r = raw[offset + x * 3 + 2];
                img[x, y] = new Rgba32(r, g, b, 255);
            }
        }

        buffer.Unmap(map);
        sample.Dispose();
        FrameReady?.Invoke(img);
    }

    public void Start() => pipeline.SetState(State.Playing);
    public void Stop() => pipeline.SetState(State.Null);
    public void Dispose() => Stop();
}

