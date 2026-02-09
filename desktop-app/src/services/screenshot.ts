import { desktopCapturer, screen } from 'electron';

export interface ScreenshotResult {
  imageBase64: string;
  timestamp: string;
}

const MAX_WIDTH = 1920;
const MAX_HEIGHT = 1080;

export async function captureScreenshot(): Promise<ScreenshotResult> {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.size;

  const sources = await desktopCapturer.getSources({
    types: ['screen'],
    thumbnailSize: { width, height },
  });

  if (sources.length === 0) {
    throw new Error('No screen source available for capture.');
  }

  let image = sources[0].thumbnail;

  // Downscale to avoid OOM on high-DPI displays (issue 6b)
  const imgSize = image.getSize();
  if (imgSize.width > MAX_WIDTH || imgSize.height > MAX_HEIGHT) {
    const scale = Math.min(MAX_WIDTH / imgSize.width, MAX_HEIGHT / imgSize.height);
    const newWidth = Math.round(imgSize.width * scale);
    const newHeight = Math.round(imgSize.height * scale);
    image = image.resize({ width: newWidth, height: newHeight, quality: 'good' });
  }

  const imageBase64 = image.toPNG().toString('base64');

  return {
    imageBase64,
    timestamp: new Date().toISOString(),
  };
}
