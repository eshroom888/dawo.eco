/**
 * ScreenshotPreview component.
 *
 * Story 6-9, Task 8.7: Image component that loads screenshot from API,
 * supports click-to-zoom, and shows loading skeleton.
 */

import { useState, useCallback } from "react";

interface ScreenshotPreviewProps {
  evidenceId: string;
  alt?: string;
  className?: string;
}

export function ScreenshotPreview({
  evidenceId,
  alt = "Evidence screenshot",
  className = "",
}: ScreenshotPreviewProps) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const [zoomed, setZoomed] = useState(false);

  const src = `/api/evidence/${evidenceId}/screenshot`;

  const handleLoad = useCallback(() => setLoaded(true), []);
  const handleError = useCallback(() => {
    setError(true);
    setLoaded(true);
  }, []);
  const toggleZoom = useCallback(() => setZoomed((prev) => !prev), []);

  return (
    <>
      {/* Inline preview */}
      <div className={`relative ${className}`}>
        {!loaded && (
          <div className="absolute inset-0 bg-gray-200 rounded animate-pulse" />
        )}
        {error ? (
          <div className="flex items-center justify-center h-full bg-gray-100 rounded text-gray-400 text-sm">
            Screenshot unavailable
          </div>
        ) : (
          <img
            src={src}
            alt={alt}
            className="w-full h-full object-cover rounded cursor-zoom-in"
            onLoad={handleLoad}
            onError={handleError}
            onClick={toggleZoom}
            loading="lazy"
          />
        )}
      </div>

      {/* Zoom overlay */}
      {zoomed && !error && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
          onClick={toggleZoom}
        >
          <img
            src={src}
            alt={alt}
            className="max-w-[90vw] max-h-[90vh] object-contain rounded shadow-2xl"
          />
        </div>
      )}
    </>
  );
}

export default ScreenshotPreview;
