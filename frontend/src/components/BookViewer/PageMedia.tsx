import React from "react";
import PageShadowOverlay from "./PageShadowOverlay";
import { useMediaUrl } from "../../hooks/useMediaUrl";

interface PageMediaProps {
  bookId: string;
  pageId: string;
  imageUrl?: string;
  expiresAt?: string;
  isShared: boolean;
}

const PageMedia = React.memo(
  ({ bookId, pageId, imageUrl, expiresAt, isShared }: PageMediaProps) => {
    const { urls, refreshUrls } = useMediaUrl({
      bookId,
      pageId,
      initialUrls: { video_url: imageUrl },
      expiresAt,
      isShared,
    });

    const handleError = async () => {
      if (!isShared) {
        console.warn("Background video failed to load, attempting refresh...");
        try {
          await refreshUrls();
        } catch (err) {
          console.error("Failed to recover video:", err);
        }
      }
    };

    return (
      <div className="relative w-full h-full bg-white flex flex-col justify-center items-center p-5">
        <video
          key={urls.video_url}
          muted
          autoPlay
          loop
          onError={handleError} // ← 추가
          className="h-full w-full object-cover"
        >
          <source src={urls.video_url} type="video/mp4" />
        </video>

        <PageShadowOverlay position="right" opacity="normal" />
        <PageShadowOverlay position="left" opacity="light" />
      </div>
    );
  }
);

PageMedia.displayName = "PageMedia";

export default PageMedia;
