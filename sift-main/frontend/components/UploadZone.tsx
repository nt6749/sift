/**
 * UploadZone Component
 * Drag-and-drop file upload with visual feedback
 */
import React, { useRef, useState } from "react";

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
  isLoading?: boolean;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFileSelect,
  disabled = false,
  isLoading = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled) return;

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type === "application/pdf") {
        onFileSelect(file);
      } else {
        alert("Only PDF files are supported");
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelect(e.target.files[0]);
    }
  };

  const handleClick = () => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  };

  return (
    <div
      onClick={handleClick}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`
        relative w-full max-w-md mx-auto px-8 py-12 border-2 border-dashed rounded-xl
        transition-all duration-200 cursor-pointer
        ${isDragging && !disabled ? "border-blue-400 bg-blue-50" : "border-gray-300"}
        ${disabled ? "opacity-50 cursor-not-allowed" : "hover:border-gray-400 hover:bg-gray-50"}
        ${isLoading ? "opacity-75" : ""}
      `}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileSelect}
        disabled={disabled || isLoading}
        className="hidden"
        aria-label="Upload PDF file"
      />

      <div className="text-center">
        {isLoading ? (
          <>
            <div className="mb-4 flex justify-center">
              <div className="h-12 w-12 border-4 border-gray-200 border-t-blue-500 rounded-full animate-spin" />
            </div>
            <p className="text-gray-600 font-medium">Uploading...</p>
          </>
        ) : (
          <>
            <svg
              className="mx-auto h-12 w-12 text-gray-400 mb-2"
              stroke="currentColor"
              fill="none"
              viewBox="0 0 48 48"
            >
              <path
                d="M28 8H12a4 4 0 00-4 4v28a4 4 0 004 4h24a4 4 0 004-4V20m-8-12v12m0 0l-4-4m4 4l4-4"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <p className="text-gray-700 font-semibold">Drag and drop your PDF</p>
            <p className="text-gray-500 text-sm mt-1">or click to browse</p>
            <p className="text-gray-400 text-xs mt-2">Maximum 50MB</p>
          </>
        )}
      </div>
    </div>
  );
};
