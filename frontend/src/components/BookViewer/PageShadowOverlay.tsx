import React from "react";

interface PageShadowOverlayProps {
  position: "left" | "right";
  opacity?: "normal" | "light";
}

const PageShadowOverlay = React.memo(
  ({ position, opacity = "normal" }: PageShadowOverlayProps) => {
    const width = position === "right" ? "10%" : "15%";
    const positionClass = position === "right" ? "right-0" : "left-0";

    const gradient =
      position === "right"
        ? opacity === "light"
          ? "linear-gradient(to left, rgba(0,0,0,0.1) 20%, transparent 100%)"
          : "linear-gradient(to left, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.4) 20%, rgba(0,0,0,0.1) 60%, transparent 100%)"
        : opacity === "light"
          ? "linear-gradient(to right, rgba(0,0,0,0.1) 20%, transparent 100%)"
          : "linear-gradient(to right, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.4) 20%, rgba(0,0,0,0.1) 60%, transparent 100%)";

    return (
      <div
        className={`pointer-events-none absolute inset-y-0 ${positionClass}`}
        style={{
          width,
          background: gradient,
        }}
      />
    );
  }
);

PageShadowOverlay.displayName = "PageShadowOverlay";

export default PageShadowOverlay;
