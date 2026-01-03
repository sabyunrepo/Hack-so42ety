import { useState, useEffect, useRef } from "react";
import { refreshMediaUrls } from "../api";
import type { DialogueAudio } from "../types/book";

export interface MediaUrls {
  video_url?: string;
  image_url?: string;
  audios?: DialogueAudio[];
}

interface UseMediaUrlOptions {
  bookId: string;
  pageId: string;
  initialUrls: MediaUrls;
  expiresAt?: string; // ISO 8601 datetime (백엔드 응답에서 제공)
  isShared: boolean;
}

export function useMediaUrl({
  bookId,
  pageId,
  initialUrls,
  expiresAt,
  isShared,
}: UseMediaUrlOptions) {
  const [urls, setUrls] = useState<MediaUrls>(initialUrls);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const refreshTimerRef = useRef<number | null>(null);

  const refreshUrls = async () => {
    if (isShared) {
      console.warn("Public content does not require URL refresh");
      return;
    }

    try {
      setIsRefreshing(true);
      const response = await refreshMediaUrls(bookId, pageId);

      // audios 배열을 DialogueAudio 형식으로 변환
      const transformedAudios: DialogueAudio[] =
        response.urls.audios?.map((audio) => ({
          language_code: audio.language_code,
          voice_id: "", // API 응답에 없으므로 빈 문자열
          audio_url: audio.audio_url,
        })) || [];

      setUrls({
        video_url: response.urls.video_url,
        image_url: response.urls.image_url,
        audios: transformedAudios,
      });

      // 다음 갱신 타이머 설정 (만료 30분 전)
      scheduleNextRefresh(response.expires_at);
    } catch (error) {
      console.error("Failed to refresh media URLs:", error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const scheduleNextRefresh = (expiresAtStr: string) => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }

    const expirationTime = new Date(expiresAtStr).getTime();
    const now = Date.now();
    const thirtyMinutesBeforeExpiry = expirationTime - 30 * 60 * 1000; // 30분 전
    const delay = thirtyMinutesBeforeExpiry - now;

    if (delay > 0) {
      console.log(
        `Next URL refresh scheduled in ${Math.round(delay / 1000 / 60)} minutes`
      );
      refreshTimerRef.current = setTimeout(() => {
        console.log("Auto-refreshing URLs before expiration...");
        refreshUrls();
      }, delay);
    } else {
      // 이미 만료 30분 전을 지났으면 즉시 갱신
      console.warn("URLs are close to expiration, refreshing immediately...");
      refreshUrls();
    }
  };

  useEffect(() => {
    if (expiresAt && !isShared) {
      scheduleNextRefresh(expiresAt);
    }

    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expiresAt, isShared]);

  return { urls, refreshUrls, isRefreshing };
}
