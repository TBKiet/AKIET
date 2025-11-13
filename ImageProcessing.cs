using System;
using System.Collections.Generic;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using System.Linq;

public static class ImageProcessing
{
    public static byte[,] ToGray(Image<Rgba32> src)
    {
        int w = src.Width, h = src.Height;
        var gray = new byte[h, w];
        for (int y = 0; y < h; y++)
        {
            for (int x = 0; x < w; x++)
            {
                var p = src[x, y];
                gray[y, x] = (byte)((0.299f * p.R) + (0.587f * p.G) + (0.114f * p.B));
            }
        }
        return gray;
    }

    public static float[,] SobelMagnitude(byte[,] gray)
    {
        int h = gray.GetLength(0), w = gray.GetLength(1);
        var mag = new float[h, w];

        int[,] gx = { { -1, 0, 1 }, { -2, 0, 2 }, { -1, 0, 1 } };
        int[,] gy = { { -1, -2, -1 }, { 0, 0, 0 }, { 1, 2, 1 } };

        for (int y = 1; y < h - 1; y++)
        {
            for (int x = 1; x < w - 1; x++)
            {
                int sx = 0, sy = 0;
                for (int ky = -1; ky <= 1; ky++)
                for (int kx = -1; kx <= 1; kx++)
                {
                    int val = gray[y + ky, x + kx];
                    sx += gx[ky + 1, kx + 1] * val;
                    sy += gy[ky + 1, kx + 1] * val;
                }
                mag[y, x] = MathF.Sqrt(sx * sx + sy * sy);
            }
        }
        return mag;
    }

    public static byte[,] ThresholdEdges(float[,] mag, float thresh)
    {
        int h = mag.GetLength(0), w = mag.GetLength(1);
        var bin = new byte[h, w];
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
                bin[y, x] = (mag[y, x] >= thresh) ? (byte)255 : (byte)0;
        return bin;
    }

    public class Blob
    {
        public int MinX, MinY, MaxX, MaxY, Area;
        public Blob(int x, int y) { MinX = MaxX = x; MinY = MaxY = y; Area = 1; }
        public void Add(int x, int y)
        {
            Area++;
            if (x < MinX) MinX = x;
            if (x > MaxX) MaxX = x;
            if (y < MinY) MinY = y;
            if (y > MaxY) MaxY = y;
        }
        public (int cx, int cy) Centroid() => ((MinX + MaxX) / 2, (MinY + MaxY) / 2);
    }

    public static List<Blob> FindBlobs(byte[,] bin, int minArea = 50)
    {
        int h = bin.GetLength(0), w = bin.GetLength(1);
        var labels = new int[h, w];
        int nextLabel = 1;
        var blobs = new Dictionary<int, Blob>();
        var parent = new Dictionary<int, int>(); // Union-Find parent

        // Helper: Find root label (Union-Find)
        int FindRoot(int label)
        {
            while (parent.ContainsKey(label) && parent[label] != label)
                label = parent[label];
            return label;
        }

        // Helper: Merge two labels
        void Union(int label1, int label2)
        {
            int root1 = FindRoot(label1);
            int root2 = FindRoot(label2);
            if (root1 != root2)
                parent[root2] = root1; // Merge root2 vào root1
        }

        // First pass: label pixels và track equivalences
        int[] dx = { -1, 0, 1, -1 }; // Chỉ check 4 neighbors trên/trái (đã scan)
        int[] dy = { -1, -1, -1, 0 };

        for (int y = 0; y < h; y++)
        {
            for (int x = 0; x < w; x++)
            {
                if (bin[y, x] == 0) continue;

                List<int> neighborLabels = new List<int>();
                for (int k = 0; k < 4; k++)
                {
                    int nx = x + dx[k], ny = y + dy[k];
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h && labels[ny, nx] != 0)
                    {
                        int rootLabel = FindRoot(labels[ny, nx]);
                        if (!neighborLabels.Contains(rootLabel))
                            neighborLabels.Add(rootLabel);
                    }
                }

                if (neighborLabels.Count == 0)
                {
                    // Pixel mới, tạo label mới
                    int label = nextLabel++;
                    labels[y, x] = label;
                    parent[label] = label;
                    blobs[label] = new Blob(x, y);
                }
                else
                {
                    // Dùng label nhỏ nhất, merge các labels khác
                    int minLabel = neighborLabels.Min();
                    labels[y, x] = minLabel;
                    blobs[minLabel].Add(x, y);

                    // Merge tất cả neighbor labels
                    foreach (var lbl in neighborLabels)
                    {
                        if (lbl != minLabel)
                            Union(minLabel, lbl);
                    }
                }
            }
        }

        // Second pass: merge blobs theo equivalences
        var finalBlobs = new Dictionary<int, Blob>();
        foreach (var kvp in blobs)
        {
            int root = FindRoot(kvp.Key);
            if (!finalBlobs.ContainsKey(root))
                finalBlobs[root] = new Blob(kvp.Value.MinX, kvp.Value.MinY);

            // Merge blob data
            var srcBlob = kvp.Value;
            var dstBlob = finalBlobs[root];
            if (srcBlob.MinX < dstBlob.MinX) dstBlob.MinX = srcBlob.MinX;
            if (srcBlob.MinY < dstBlob.MinY) dstBlob.MinY = srcBlob.MinY;
            if (srcBlob.MaxX > dstBlob.MaxX) dstBlob.MaxX = srcBlob.MaxX;
            if (srcBlob.MaxY > dstBlob.MaxY) dstBlob.MaxY = srcBlob.MaxY;
            dstBlob.Area += srcBlob.Area;
        }

        return finalBlobs.Values.Where(b => b.Area >= minArea).ToList();
    }

    public static void DrawOverlay(Image<Rgba32> dst, List<Blob> blobs, Rgba32 color)
    {
        int w = dst.Width, h = dst.Height;
        foreach (var b in blobs)
        {
            int x0 = Math.Clamp(b.MinX, 0, w - 1);
            int y0 = Math.Clamp(b.MinY, 0, h - 1);
            int x1 = Math.Clamp(b.MaxX, 0, w - 1);
            int y1 = Math.Clamp(b.MaxY, 0, h - 1);
            var c = b.Centroid();

            // Vẽ bounding box (4 cạnh)
            for (int x = x0; x <= x1; x++)
            {
                dst[x, y0] = color; // Cạnh trên
                dst[x, y1] = color; // Cạnh dưới
            }
            for (int y = y0; y <= y1; y++)
            {
                dst[x0, y] = color; // Cạnh trái
                dst[x1, y] = color; // Cạnh phải
            }

            // Vẽ centroid (dấu thập đỏ)
            int cx = Math.Clamp(c.cx, 0, w - 1);
            int cy = Math.Clamp(c.cy, 0, h - 1);
            for (int dx = -4; dx <= 4; dx++)
            {
                int xx = cx + dx;
                if (xx >= 0 && xx < w) dst[xx, cy] = new Rgba32(255, 0, 0);
            }
            for (int dy = -4; dy <= 4; dy++)
            {
                int yy = cy + dy;
                if (yy >= 0 && yy < h) dst[cx, yy] = new Rgba32(255, 0, 0);
            }
        }
    }

    public static (Image<Rgba32> annotated, byte[,] binary) ProcessFrame(Image<Rgba32> frame,
        float edgeThresh = 80f, int minBlobArea = 80)
    {
        var color = frame;
        var gray = ToGray(color);
        var mag = SobelMagnitude(gray); // bỏ GaussianBlur để tăng tốc
        var bin = ThresholdEdges(mag, edgeThresh);
        var blobs = FindBlobs(bin, minBlobArea);
        DrawOverlay(color, blobs, new Rgba32(0, 255, 0));
        return (color, bin);
    }
}

