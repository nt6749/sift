/**
 * DrugInput Component
 * Text input for target drug name
 */
import React from "react";

interface DrugInputProps {
  value: string;
  onChange: (value: string) => void;
  onKeyPress?: (e: React.KeyboardEvent) => void;
  disabled?: boolean;
  placeholder?: string;
  error?: string;
}

export const DrugInput: React.FC<DrugInputProps> = ({
  value,
  onChange,
  onKeyPress,
  disabled = false,
  placeholder = "Enter target drug (e.g., Humira, Ozempic)",
  error,
}) => {
  return (
    <div className="w-full">
      <div className="mb-2 flex items-center justify-between">
        <label htmlFor="drug-input" className="block text-sm font-medium text-gray-700">
          Target Drug
        </label>
        {value && !error && (
          <span className="text-xs text-green-600 font-medium">✓ Valid</span>
        )}
      </div>

      <input
        id="drug-input"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyPress={onKeyPress}
        disabled={disabled}
        placeholder={placeholder}
        className={`
          w-full px-4 py-3 rounded-lg border-2 transition-all duration-200
          font-medium text-base
          ${
            error
              ? "border-red-300 bg-red-50 text-gray-900"
              : disabled
                ? "border-gray-200 bg-gray-50 text-gray-500 cursor-not-allowed"
                : value
                  ? "border-blue-400 bg-blue-50 text-gray-900"
                  : "border-gray-300 bg-white text-gray-900 placeholder-gray-500"
          }
        `}
      />

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
};
