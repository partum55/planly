import { desktopCapturer, screen } from 'electron';

export interface ScreenshotResult {
  imageBase64: string;
  timestamp: string;
}

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

  const image = sources[0].thumbnail;
  const imageBase64 = image.toPNG().toString('base64');

  return {
    imageBase64,
    timestamp: new Date().toISOString(),
  };
}
