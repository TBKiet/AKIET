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
        var capsfilter1 = ElementFactory.Make("capsfilter", "filter1");
        var conv1 = ElementFactory.Make("nvvidconv", "conv1");
        var conv2 = ElementFactory.Make("videoconvert", "conv2");
        var capsfilter2 = ElementFactory.Make("capsfilter", "filter2");
        appsink = ElementFactory.Make("appsink", "mysink") as AppSink
                  ?? throw new Exception("Không tạo được appsink!");

        if (src == null || conv1 == null || conv2 == null || capsfilter1 == null || capsfilter2 == null)
            throw new Exception("Không tạo được 1 trong các phần tử GStreamer!");

        // cấu hình caps cho camera source
        var caps1 = Caps.FromString($"video/x-raw(memory:NVMM),width={width},height={height},framerate=30/1");
        capsfilter1["caps"] = caps1;

        // cấu hình định dạng BGR cho output
        var caps2 = Caps.FromString($"video/x-raw,width={width},height={height},format=BGR");
        capsfilter2["caps"] = caps2;

        // cấu hình appsink
        appsink.EmitSignals = true;
        appsink.Drop = true;
        appsink.MaxBuffers = 1;
        appsink.NewSample += OnNewSample;

        // thêm các phần tử vào pipeline
        pipeline.Add(src, capsfilter1, conv1, conv2, capsfilter2, appsink);

        // link từng đoạn: src → capsfilter1 → conv1 → conv2 → capsfilter2 → appsink
        if (!src.Link(capsfilter1))
            throw new Exception("Không link được src → capsfilter1");
        if (!capsfilter1.Link(conv1))
            throw new Exception("Không link được capsfilter1 → conv1");
        if (!conv1.Link(conv2))
            throw new Exception("Không link được conv1 → conv2");
        if (!conv2.Link(capsfilter2))
            throw new Exception("Không link được conv2 → capsfilter2");
        if (!capsfilter2.Link(appsink))
            throw new Exception("Không link được capsfilter2 → appsink");
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

