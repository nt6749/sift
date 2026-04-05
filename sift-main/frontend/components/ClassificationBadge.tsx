/**
 * ClassificationBadge Component
 * Displays classification result with appropriate styling
 */
import React from "react";

interface ClassificationBadgeProps {
  classification: "single_drug" | "multi_drug" | null;
  isLoading?: boolean;
}

export const ClassificationBadge: React.FC<ClassificationBadgeProps> = ({
  classification,
  isLoading = false,
}) => {
  if (!classification && !isLoading) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg rounded-xl animate-pulse">
        <div className="h-2 w-2 bg-gray-400 rounded-full" />
        <span className="text-gray-600 text-sm font-medium">Classifying...</span>
      </div>
    );
  }

  const isSingleDrug = classification === "single_drug";

  return (
    <div className="animate-slideUp">
      <div
        className={`
          inline-flex items-center gap-2 px-4 py-2 rounded-lg rounded-xl font-medium text-sm
          ${
            isSingleDrug
              ? "bg-green-100 text-green-800"
              : "bg-purple-100 text-purple-800"
          }
        `}
      >
        <span className={`h-2 w-2 rounded-full ${isSingleDrug ? "bg-green-600" : "bg-purple-600"}`} />
        {isSingleDrug ? "Single Drug Policy" : "Multi-Drug Formulary"}
      </div>
    </div>
  );
};
