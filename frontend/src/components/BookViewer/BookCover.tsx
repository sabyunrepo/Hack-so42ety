import React from "react";

interface BookCoverProps {
  type: "front" | "back";
  coverImage?: string;
  altText?: string;
  backCoverContent?: React.ReactNode;
}

const BookCover = React.memo(
  ({ type, coverImage, altText, backCoverContent }: BookCoverProps) => {
    if (type === "front") {
      return (
        <div className="w-full h-full bg-white shadow-2xl/30">
          <img
            src={coverImage}
            alt={altText || "Book cover"}
            className="w-full h-full object-cover"
            loading="eager"
          />
        </div>
      );
    }

    // Back cover
    return (
      <div className="w-full h-full bg-[#f2bf27] relative shadow-2xl/30">
        {backCoverContent}
      </div>
    );
  }
);

BookCover.displayName = "BookCover";

export default BookCover;
