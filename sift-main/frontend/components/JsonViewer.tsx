/**
 * JsonViewer Component
 * Displays JSON with syntax highlighting
 */
import React from "react";

interface JsonViewerProps {
  data: any;
  onCopy?: () => void;
  showCopyButton?: boolean;
}

export const JsonViewer: React.FC<JsonViewerProps> = ({
  data,
  onCopy,
  showCopyButton = true,
}) => {
  const jsonString = JSON.stringify(data, null, 2);

  return (
    <div className="relative">
      {showCopyButton && onCopy && (
        <button
          onClick={onCopy}
          className="absolute top-4 right-4 px-3 py-1 bg-blue-500 text-white rounded text-sm font-medium hover:bg-blue-600 transition-colors"
        >
          Copy JSON
        </button>
      )}

      <pre className="bg-gray-900 text-gray-100 p-6 rounded-lg overflow-auto max-h-96 text-sm font-mono">
        <code>{jsonString}</code>
      </pre>
    </div>
  );
};
