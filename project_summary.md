# JetsonVisionApp Project Summary

This document provides a summary of the JetsonVisionApp project, a C# .NET 8 application for real-time computer vision on Jetson devices.

## 1. Project Purpose

The JetsonVisionApp captures video from a camera connected to a Jetson device, performs real-time blob detection on the video frames, and displays the annotated video feed in a graphical user interface.

## 2. Architecture and Flow

The application follows a simple pipeline architecture:

1.  **UI (Avalonia Framework)**: The user interface consists of a single window with a "Start" button and an image view for displaying the video feed. The UI is built with the cross-platform Avalonia framework.

2.  **Camera Capture (`CameraReader.cs`)**: Clicking the "Start" button initiates the `CameraReader`. This class spawns a `gst-launch-1.0` process to create a GStreamer pipeline. The pipeline leverages NVIDIA's hardware acceleration (`nvarguscamerasrc`, `nvvidconv`) to capture raw BGRx video frames and pipe them to its standard output. The `CameraReader` reads these frames from the process's stdout in a separate thread.

3.  **Image Conversion & Eventing**: Each raw frame buffer is converted into an `Image<Rgba32>` object using the `SixLabors.ImageSharp` library. A `FrameReady` event is then fired, carrying the processed image.

4.  **Image Processing (`ImageProcessing.cs`)**: The main window listens for the `FrameReady` event. The received image is passed to the `ImageProcessing.ProcessFrame` static method, which executes the core computer vision logic:
    *   Convert the image to grayscale.
    *   Apply a Sobel filter for edge detection.
    *   Threshold the result to create a binary image.
    *   Perform a connected-components analysis (`FindBlobs`) to identify objects.
    *   Draw bounding boxes and centroids for the detected blobs onto the original color image.

5.  **Display**: The final annotated image is converted into an Avalonia `WriteableBitmap` for display. This is done on the UI thread to ensure thread safety and involves performance-conscious `unsafe` code for direct memory manipulation. The bitmap is then rendered in the main window's image view.

## 3. Key Components & Libraries

*   **UI Framework**: [Avalonia](https://avaloniaui.net/)
*   **Image Processing**: [SixLabors.ImageSharp](https://sixlabors.com/products/imagesharp/)
*   **Camera Interfacing**: GStreamer (via a `gst-launch-1.0` command-line process)
*   **Target Platform**: .NET 8 on `linux-arm64` (Jetson)

## 4. How to Build and Run

### Prerequisites

*   .NET 8 SDK for `linux-arm64`
*   GStreamer and its plugins installed on the Jetson device.
*   A camera compatible with `nvarguscamerasrc`.

### Build

```bash
dotnet build -c Release
```

### Run

The application must be run from a graphical environment (e.g., the Jetson's desktop environment) to display the UI.

```bash
./bin/Release/net8.0/linux-arm64/JetsonVisionApp
```

## 5. Noteworthy Points

*   **Unused GStreamer Bindings**: The project includes a dependency on `gstreamer-sharp-netcore` and a file `GstCameraCapture.cs` which uses these bindings. However, the current implementation favors the `CameraReader` approach, which parses the output of a CLI process. This was likely done for simplicity or to overcome a specific issue with the bindings.
*   **Performance Optimizations**: The code uses `unsafe` blocks and direct memory copying for image format conversion (RGBA to BGRA) between `ImageSharp` and Avalonia's `WriteableBitmap`. This is a clear optimization to improve throughput and reduce CPU overhead on the embedded device.
