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
  ({
    bookId,
    pageId,
    imageUrl,
    expiresAt,
    isShared,
  }: PageMediaProps) => {
    const { urls } = useMediaUrl({
      bookId,
      pageId,
      initialUrls: { video_url: imageUrl },
      expiresAt,
      isShared,
    });

    return (
      <div className="relative w-full h-full bg-white flex flex-col justify-center items-center p-5">
        <video
          key={urls.video_url}
          muted
          autoPlay
          loop
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
