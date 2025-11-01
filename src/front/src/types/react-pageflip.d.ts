declare module "react-pageflip" {
  import React from "react";

  export interface IProps {
    width: number;
    height: number;
    size?: "fixed" | "stretch";
    minWidth?: number;
    maxWidth?: number;
    minHeight?: number;
    maxHeight?: number;
    showCover?: boolean;
    useMouseEvents?: boolean;
    maxShadowOpacity?: number;
    startPage?: number;
    style?: React.CSSProperties;
    className?: string;
    drawShadow?: boolean;
    showPageCorners?: boolean;
    flippingTime?: number;
    usePortrait?: boolean;
    disableFlipByClick?: boolean;
    swipeDistance?: number;
    mobileScrollSupport?: boolean;
    clickEventForward?: boolean;
    autoSize?: boolean;
    startZIndex?: number;
    onFlip?: (pageIndex: number) => void;
    onChangeOrientation?: (orientation: "portrait" | "landscape") => void;
    onChangeState?: (state: string) => void;
    children: React.ReactNode;
  }

  const HTMLFlipBook: React.ForwardRefExoticComponent<
    IProps & React.RefAttributes<any>
  >;

  export default HTMLFlipBook;
}
