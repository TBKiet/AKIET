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
        int[] dx = { -1, 0, 1, -1, 1, -1, 0, 1 };
        int[] dy = { -1, -1, -1, 0, 0, 1, 1, 1 };

        for (int y = 0; y < h; y++)
        {
            for (int x = 0; x < w; x++)
            {
                if (bin[y, x] == 0) continue;
                int label = 0;
                for (int k = 0; k < 8; k++)
                {
                    int nx = x + dx[k], ny = y + dy[k];
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h && labels[ny, nx] != 0)
                    {
                        label = labels[ny, nx];
                        break;
                    }
                }
                if (label == 0)
                {
                    label = nextLabel++;
                    blobs[label] = new Blob(x, y);
                }
                else
                {
                    blobs[label].Add(x, y);
                }
                labels[y, x] = label;
            }
        }
        return blobs.Values.Where(b => b.Area >= minArea).ToList();
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

            for (int x = x0; x <= x1; x++)
            {
                if (y0 >= 0 && y0 < h) dst[x, y0] = color;
                if (y1 >= 0 && y1 < h) dst[x, y1] = color;
            }
            for (int y = y0; y <= y1; y++)
            {
                if (x0 >= 0 && x0 < w) dst[x0, y] = color;
                if (x1 >= 0 && x1 < w) dst[x1, y] = color;
            }

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

