export interface DehazeResponse {
  blobUrl: string;
  processingTimeMs: number;
  originalWidth: number;
  originalHeight: number;
  processedWidth: number;
  processedHeight: number;
}

export class ApiError extends Error {
  constructor(public message: string, public status?: number) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Sends an image to the dehazing API.
 * Uses the /api proxy in development to avoid CORS issues.
 */
export async function dehazeImage(file: File): Promise<DehazeResponse> {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('algorithm', 'dark_channel_prior');

  try {
    const response = await fetch('/api/dehaze', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = 'An error occurred during processing.';
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = errorData.detail;
        }
      } catch (e) {
        // Fallback to status text if JSON parsing fails
        errorMessage = response.statusText || errorMessage;
      }
      throw new ApiError(errorMessage, response.status);
    }

    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);

    const processingTimeMs = parseInt(response.headers.get('x-processing-time-ms') || '0', 10);
    const originalWidth = parseInt(response.headers.get('x-original-width') || '0', 10);
    const originalHeight = parseInt(response.headers.get('x-original-height') || '0', 10);
    const processedWidth = parseInt(response.headers.get('x-processed-width') || '0', 10);
    const processedHeight = parseInt(response.headers.get('x-processed-height') || '0', 10);

    return {
      blobUrl,
      processingTimeMs,
      originalWidth,
      originalHeight,
      processedWidth,
      processedHeight
    };
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network errors or other fetch failures
    throw new ApiError(error instanceof Error ? error.message : 'Network error or API is unavailable');
  }
}
