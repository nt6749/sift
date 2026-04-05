/**
 * SkeletonLoader Component
 * Shows loading skeleton while data is being fetched
 */
import React from "react";

export const SkeletonLoader: React.FC = () => {
  return (
    <div className="space-y-4 animate-pulse">
      {[...Array(4)].map((_, i) => (
        <div
          key={i}
          className="bg-white rounded-xl border border-gray-200 overflow-hidden"
        >
          <div className="px-6 py-4 bg-gray-100 border-b border-gray-200">
            <div className="h-5 bg-gray-300 rounded w-1/3" />
          </div>
          <div className="px-6 py-4 space-y-3">
            {[...Array(3)].map((_, j) => (
              <div key={j} className="flex justify-between">
                <div className="h-4 bg-gray-200 rounded w-1/4" />
                <div className="h-4 bg-gray-200 rounded w-1/2" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};
