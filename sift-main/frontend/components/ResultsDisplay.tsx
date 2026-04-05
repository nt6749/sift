/**
 * ResultsDisplay Component
 * Displays extracted structured data in organized sections
 */
import React, { useState } from "react";
import { PolicyData } from "@/lib/api";

interface ResultsDisplayProps {
  data: PolicyData;
  targetDrug: string;
}

const renderValue = (value: any): React.ReactNode => {
  if (value === null || value === undefined) {
    return <span className="text-gray-400 italic">Not available</span>;
  }

  if (value === "unknown") {
    return <span className="text-gray-500 italic">Unknown</span>;
  }

  if (typeof value === "boolean") {
    return (
      <span
        className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
          value
            ? "bg-red-100 text-red-800"
            : "bg-green-100 text-green-800"
        }`}
      >
        {value ? "Yes" : "No"}
      </span>
    );
  }

  if (typeof value === "string") {
    return <span className="text-gray-700">{value}</span>;
  }

  return <span className="text-gray-700">{String(value)}</span>;
};

const Card: React.FC<{
  title: string;
  children: React.ReactNode;
  empty?: boolean;
  isExpanded?: boolean;
  onToggle?: () => void;
}> = ({ title, children, empty = false, isExpanded = true, onToggle }) => (
  <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:border-gray-300 transition-colors">
    <button
      onClick={onToggle}
      className="w-full px-6 py-4 bg-gray-50 border-b border-gray-200 flex justify-between items-center hover:bg-gray-100 transition-colors text-left"
    >
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      <span className={`text-gray-500 transform transition-transform ${isExpanded ? "rotate-180" : ""}`}>
        ▼
      </span>
    </button>
    {isExpanded && (
      <div className="px-6 py-4">
        {empty ? (
          <div className="text-center text-gray-500 italic">
            No data available
          </div>
        ) : (
          children
        )}
      </div>
    )}
  </div>
);

const KeyValueRow: React.FC<{
  label: string;
  value: any;
  highlight?: boolean;
}> = ({ label, value, highlight = false }) => (
  <div
    className={`flex justify-between items-start gap-4 py-3 ${
      highlight ? "bg-blue-50 px-4 -mx-4 py-3" : ""
    } ${highlight ? "rounded" : ""}`}
  >
    <span className="font-medium text-gray-700">{label}</span>
    <div className="text-right">{renderValue(value)}</div>
  </div>
);

export const ResultsDisplay: React.FC<ResultsDisplayProps> = ({
  data,
  targetDrug,
}) => {
  // Initialize all sections as expanded by default
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set([
      "payer_information",
      "drug_name",
      "access_status",
      "coverage",
      "prior_authorization",
      "step_therapy",
      "site_of_care",
      "dosing_and_quantity_limits",
      "policy_metadata",
    ])
  );

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const isExpanded = (section: string) => expandedSections.has(section);

  return (
    <div className="space-y-4 animate-slideUp">
      {/* Payer Information */}
      <Card
        title="Payer Information"
        isExpanded={isExpanded("payer_information")}
        onToggle={() => toggleSection("payer_information")}
      >
        <KeyValueRow label="Payer Name" value={data.payer_name} />
      </Card>

      {/* Drug Information */}
      <Card
        title="Drug Information"
        empty={
          !data.drug_name.brand &&
          !data.drug_name.generic &&
          !data.drug_category
        }
        isExpanded={isExpanded("drug_name")}
        onToggle={() => toggleSection("drug_name")}
      >
        <div className="space-y-2">
          <KeyValueRow label="Brand Name" value={data.drug_name.brand} />
          <KeyValueRow label="Generic Name" value={data.drug_name.generic} />
          <KeyValueRow label="Drug Category" value={data.drug_category} />
        </div>
      </Card>

      {/* Access Status */}
      <Card
        title="Access Status"
        empty={data.access_status.status === "unknown" && !data.access_status.notes}
        isExpanded={isExpanded("access_status")}
        onToggle={() => toggleSection("access_status")}
      >
        <div className="space-y-2">
          <KeyValueRow
            label="Status"
            value={data.access_status.status}
            highlight={true}
          />
          <KeyValueRow
            label="Preferred Count in Category"
            value={data.access_status.preferred_count_in_category}
          />
          <KeyValueRow label="Notes" value={data.access_status.notes} />
        </div>
      </Card>

      {/* Coverage */}
      <Card
        title="Coverage"
        empty={
          data.coverage.covered === "unknown" &&
          data.coverage.covered_indications.length === 0
        }
        isExpanded={isExpanded("coverage")}
        onToggle={() => toggleSection("coverage")}
      >
        <div className="space-y-4">
          <KeyValueRow
            label="Drug Covered"
            value={data.coverage.covered}
            highlight={true}
          />

          {data.coverage.covered_indications.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">
                Covered Indications:
              </h4>
              <ul className="space-y-2">
                {data.coverage.covered_indications.map((indication, idx) => (
                  <li
                    key={idx}
                    className="border-l-4 border-green-400 pl-3 py-1"
                  >
                    <p className="font-medium text-gray-800">
                      {indication.condition}
                    </p>
                    {indication.criteria && (
                      <p className="text-sm text-gray-600 mt-1">
                        {indication.criteria}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </Card>

      {/* Prior Authorization */}
      <Card
        title="Prior Authorization"
        empty={
          data.prior_authorization.required === "unknown" &&
          data.prior_authorization.criteria.length === 0
        }
        isExpanded={isExpanded("prior_authorization")}
        onToggle={() => toggleSection("prior_authorization")}
      >
        <div className="space-y-3">
          <KeyValueRow
            label="Required"
            value={data.prior_authorization.required}
            highlight={data.prior_authorization.required === true}
          />

          {data.prior_authorization.criteria.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">Criteria:</h4>
              <ul className="space-y-2">
                {data.prior_authorization.criteria.map((criteria, idx) => (
                  <li
                    key={idx}
                    className="flex gap-2 text-sm text-gray-700"
                  >
                    <span className="text-orange-500 font-bold">•</span>
                    <span>{criteria}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </Card>

      {/* Step Therapy */}
      <Card
        title="Step Therapy"
        empty={
          data.step_therapy.required === "unknown" &&
          data.step_therapy.steps.length === 0
        }
        isExpanded={isExpanded("step_therapy")}
        onToggle={() => toggleSection("step_therapy")}
      >
        <div className="space-y-3">
          <KeyValueRow
            label="Required"
            value={data.step_therapy.required}
            highlight={data.step_therapy.required === true}
          />

          {data.step_therapy.steps.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-3">Steps:</h4>
              <div className="space-y-3">
                {data.step_therapy.steps.map((step, idx) => (
                  <div
                    key={idx}
                    className="bg-gray-50 rounded-lg p-3 border border-gray-200"
                  >
                    <div className="flex items-start gap-3">
                      <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-blue-500 text-white text-xs font-bold flex-shrink-0">
                        {step.step_number}
                      </span>
                      <div className="flex-1">
                        <p className="font-medium text-gray-800">
                          {step.required_drug_or_class}
                        </p>
                        {step.notes && (
                          <p className="text-sm text-gray-600 mt-1">
                            {step.notes}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Site of Care */}
      <Card
        title="Site of Care"
        empty={
          data.site_of_care.restrictions.length === 0 &&
          !data.site_of_care.notes
        }
        isExpanded={isExpanded("site_of_care")}
        onToggle={() => toggleSection("site_of_care")}
      >
        <div className="space-y-3">
          {data.site_of_care.restrictions.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">
                Restrictions:
              </h4>
              <ul className="space-y-2">
                {data.site_of_care.restrictions.map((restriction, idx) => (
                  <li
                    key={idx}
                    className="flex gap-2 text-sm text-gray-700"
                  >
                    <span className="text-red-500 font-bold">✓</span>
                    <span>{restriction}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <KeyValueRow label="Notes" value={data.site_of_care.notes} />
        </div>
      </Card>

      {/* Dosing & Quantity Limits */}
      <Card
        title="Dosing & Quantity Limits"
        empty={data.dosing_and_quantity_limits.limits.length === 0}
        isExpanded={isExpanded("dosing_and_quantity_limits")}
        onToggle={() => toggleSection("dosing_and_quantity_limits")}
      >
        <div className="space-y-3">
          {data.dosing_and_quantity_limits.limits.map((limit, idx) => (
            <div key={idx} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
              <div className="flex justify-between items-start gap-2 mb-1">
                <span className="text-xs font-semibold text-blue-600 uppercase">
                  {limit.type}
                </span>
              </div>
              <p className="font-medium text-gray-800">{limit.value}</p>
              {limit.notes && (
                <p className="text-sm text-gray-600 mt-1">{limit.notes}</p>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};
