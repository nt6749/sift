/**
 * Main Policy Extraction Application
 * Choose between uploading PDF, searching online, or searching local database
 */
import React, { useState, useCallback, useEffect } from "react";
import Head from "next/head";
import {
  UploadZone,
  DrugInput,
  ResultsDisplay,
  JsonViewer,
  SkeletonLoader,
} from "@/components";
import { apiClient, PolicyData, ApiError, Drug, LocalSearchResult } from "@/lib/api";

type UploadMethod = "upload" | "search" | "local-db" | null;
type AppState =
  | "method-selection"
  | "uploading"
  | "classifying"
  | "drug-input"
  | "searching"
  | "extracting"
  | "results"
  | "local-db-input"
  | "local-db-searching"
  | "local-db-results";

interface AppData {
  uploadMethod: UploadMethod;
  uploadedFile: {
    file_id: string;
    file_path: string;
    original_name: string;
    pages: number;
  } | null;
  classification: "single_drug" | "multi_drug" | null;
  targetDrug: string;
  extractedData: PolicyData | null;
  sourceUrl: string | null;
  viewMode: "formatted" | "raw";
  error: string | null;
  progressMessages: string[];
  availableDrugs: Drug[];
  selectedDrugFromLocal: string | null;
  localSearchResults: LocalSearchResult[];
  drugsLoading: boolean;
  onlineSearchResults: LocalSearchResult[];
  isAddingToDatabase: boolean;
  lastSearchedDrug: string | null;
}

export default function Home() {
  const [state, setState] = useState<AppState>("method-selection");
  const [data, setData] = useState<AppData>({
    uploadMethod: null,
    uploadedFile: null,
    classification: null,
    targetDrug: "",
    extractedData: null,
    sourceUrl: null,
    viewMode: "formatted",
    error: null,
    progressMessages: [],
    availableDrugs: [],
    selectedDrugFromLocal: null,
    localSearchResults: [],
    drugsLoading: false,
    onlineSearchResults: [],
    isAddingToDatabase: false,
    lastSearchedDrug: null,
  });

  // Load available drugs on component mount
  useEffect(() => {
    const loadDrugs = async () => {
      try {
        setData((prev) => ({ ...prev, drugsLoading: true }));
        const response = await apiClient.getAllDrugs();
        setData((prev) => ({
          ...prev,
          availableDrugs: response.drugs,
          drugsLoading: false,
        }));
      } catch (error) {
        console.error("Failed to load drugs:", error);
        setData((prev) => ({ ...prev, drugsLoading: false }));
      }
    };

    loadDrugs();
  }, []);

  // Handle adding result to database (opt-in for verified results)
  const handleAddToDatabase = useCallback(async () => {
    if (!data.extractedData) {
      setData((prev) => ({ ...prev, error: "No policy data to save." }));
      return;
    }

    setData((prev) => ({ ...prev, isAddingToDatabase: true }));

    try {
      const response = await apiClient.addToDatabase(
        data.extractedData,
        data.sourceUrl || "",
        data.lastSearchedDrug || data.targetDrug
      );

      setData((prev) => ({
        ...prev,
        error: null,
        isAddingToDatabase: false,
      }));

      alert(
        `✅ Success! Policy for ${response.payer} has been added to the database.`
      );
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "Failed to add policy to database. Please try again.";
      setData((prev) => ({
        ...prev,
        error: message,
        isAddingToDatabase: false,
      }));
    }
  }, [data.extractedData, data.sourceUrl, data.lastSearchedDrug, data.targetDrug]);

  // Handle local database search
  const handleSearchLocal = useCallback(async () => {
    if (!data.selectedDrugFromLocal) {
      setData((prev) => ({
        ...prev,
        error: "Please select a drug from the database.",
      }));
      return;
    }

    setState("local-db-searching");
    setData((prev) => ({ ...prev, error: null }));

    try {
      const response = await apiClient.searchLocalDatabase(
        data.selectedDrugFromLocal
      );
      setData((prev) => ({
        ...prev,
        localSearchResults: response.payers,
        extractedData: response.policies[0] || null,
        error: null,
      }));
      setState("local-db-results");
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "Local database search failed. Please try again.";
      setData((prev) => ({ ...prev, error: message }));
      setState("local-db-input");
    }
  }, [data.selectedDrugFromLocal]);

  // Handle file upload
  const handleFileUpload = useCallback(async (file: File) => {
    setState("uploading");
    setData((prev) => ({ ...prev, error: null }));

    try {
      const response = await apiClient.uploadFile(file);
      setData((prev) => ({
        ...prev,
        uploadedFile: {
          file_id: response.file_id,
          file_path: response.file_path,
          original_name: response.original_name,
          pages: response.pages,
        },
        error: null,
      }));

      // Auto-classify
      setState("classifying");
      const classifyResponse = await apiClient.classifyPdf(response.file_path);
      setData((prev) => ({
        ...prev,
        classification: classifyResponse.classification,
      }));

      // Move to drug input
      setState("drug-input");
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "Failed to upload file. Please try again.";
      setData((prev) => ({ ...prev, error: message }));
      setState("method-selection");
    }
  }, []);

  // Handle search online
  const handleSearchOnline = useCallback(async () => {
    if (!data.targetDrug.trim()) {
      setData((prev) => ({
        ...prev,
        error: "Please enter a drug name to search.",
      }));
      return;
    }

    setState("searching");
    setData((prev) => ({ ...prev, error: null, progressMessages: [] }));

    try {
      const response = await apiClient.searchOnline(data.targetDrug);

      // Check if policy was found and has valid data
      if (response.found && response.data) {
        // Convert single result into comparison format (single row in table)
        const comparisonResult: LocalSearchResult = {
          payer: response.data?.payer_name || "Online Source",
          coverage: "unknown",
          policy: response.data,
        };

        setData((prev) => ({
          ...prev,
          extractedData: response.data,
          classification: response.classification,
          sourceUrl: response.source_url,
          onlineSearchResults: [comparisonResult],
          lastSearchedDrug: data.targetDrug,
          error: null,
          progressMessages: response.progress || [],
        }));
        setState("results");
      } else {
        // No valid policy found
        setData((prev) => ({
          ...prev,
          extractedData: null,
          error: response.error || "No valid policies found",
          progressMessages: response.progress || [],
        }));
        setState("results");
      }
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "Search failed. Please try again.";
      setData((prev) => ({ ...prev, error: message }));
      setState("drug-input");
    }
  }, [data.targetDrug]);

  // Handle extraction from uploaded PDF
  const handleExtract = useCallback(async () => {
    if (!data.uploadedFile || !data.targetDrug.trim()) {
      setData((prev) => ({
        ...prev,
        error: "Please upload a file and enter a target drug.",
      }));
      return;
    }

    setState("extracting");
    setData((prev) => ({ ...prev, error: null }));

    try {
      const response = await apiClient.extractData(
        data.uploadedFile.file_path,
        data.targetDrug,
      );
      setData((prev) => ({
        ...prev,
        extractedData: response.data,
        error: null,
      }));
      setState("results");
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "Extraction failed. Please try again.";
      setData((prev) => ({ ...prev, error: message }));
      setState("drug-input");
    }
  }, [data.uploadedFile, data.targetDrug]);

  // Handle drug input change
  const handleDrugChange = useCallback((value: string) => {
    setData((prev) => ({ ...prev, targetDrug: value }));
  }, []);

  // Handle copy to clipboard
  const handleCopyJson = useCallback(async () => {
    if (!data.extractedData) return;
    try {
      await navigator.clipboard.writeText(
        JSON.stringify(data.extractedData, null, 2),
      );
      alert("JSON copied to clipboard!");
    } catch {
      alert("Failed to copy to clipboard");
    }
  }, [data.extractedData]);

  // Handle reset
  const handleReset = useCallback(async () => {
    if (data.uploadedFile) {
      try {
        await apiClient.deleteFile(data.uploadedFile.file_id);
      } catch {
        // Ignore cleanup errors
      }
    }
    setData({
      uploadMethod: null,
      uploadedFile: null,
      classification: null,
      targetDrug: "",
      extractedData: null,
      sourceUrl: null,
      viewMode: "formatted",
      error: null,
      progressMessages: [],
      availableDrugs: data.availableDrugs,
      selectedDrugFromLocal: null,
      localSearchResults: [],
      drugsLoading: false,
      onlineSearchResults: [],
      isAddingToDatabase: false,
      lastSearchedDrug: null,
    });
    setState("method-selection");
  }, [data.uploadedFile, data.availableDrugs]);

  const handleSearchKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && data.uploadMethod === "search") {
      handleSearchOnline();
    }
  };

  const handleExtractKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && data.uploadMethod === "upload") {
      handleExtract();
    }
  };

  const handleLocalDbKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && data.uploadMethod === "local-db") {
      handleSearchLocal();
    }
  };

  const isExtractDisabled =
    !data.uploadedFile || !data.targetDrug.trim();
  const isSearchDisabled = !data.targetDrug.trim();
  const isLocalDbSearchDisabled =
    !data.selectedDrugFromLocal || data.drugsLoading;

  return (
    <>
      <Head>
        <title>SIFT Medical Policy Analyzer</title>
        <meta
          name="description"
          content="Extract structured data from medical policies or search online"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <main className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-12">
          {/* Header */}
          <div className="mb-12 text-center">
            <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight mb-3">
              SIFT Medical Policy Analyzer
            </h1>
            <p className="text-gray-500 text-lg max-w-2xl mx-auto">
              Extract structured drug policy data or search online
            </p>
          </div>

          {/* Error Alert */}
          {data.error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg animate-slideUp">
              <p className="text-red-800 font-medium">{data.error}</p>
              {state === "method-selection" && (
                <button
                  onClick={() =>
                    setData((prev) => ({ ...prev, error: null }))
                  }
                  className="mt-2 text-sm text-red-700 underline hover:text-red-800"
                >
                  Dismiss
                </button>
              )}
            </div>
          )}

          {/* Method Selection */}
          {state === "method-selection" && (
            <div className="space-y-6 animate-slideUp">
              <div>
                <h2 className="text-xl font-semibold text-gray-900 mb-6">
                  Choose Your Method
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Upload Option (Hidden per request) */}
                  {/* 
                  <button
                    onClick={() => {
                      setData((prev) => ({
                        ...prev,
                        uploadMethod: "upload",
                        targetDrug: "",
                      }));
                      setState("uploading");
                    }}
                    className="p-6 border-2 border-gray-200 rounded-xl hover:border-blue-500 hover:bg-blue-50 transition-all text-left group"
                  >
                    <div className="text-3xl mb-3 group-hover:scale-110 transition-transform">
                      📄
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Upload PDF
                    </h3>
                    <p className="text-gray-600 text-sm">
                      Have a medical policy PDF? Upload it for instant extraction.
                    </p>
                  </button>
                  */}

                  {/* Search Online Option */}
                  <button
                    onClick={() => {
                      setData((prev) => ({
                        ...prev,
                        uploadMethod: "search",
                        targetDrug: "",
                      }));
                      setState("drug-input");
                    }}
                    className="relative p-6 bg-white border border-gray-200 rounded-2xl shadow-sm hover:shadow-md hover:border-purple-500 hover:-translate-y-1 transition-all duration-200 text-left group"
                  >
                    <div className="text-3xl mb-4 group-hover:scale-110 transition-transform origin-left">
                      🔍
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Search Online
                    </h3>
                    <p className="text-gray-500 text-sm leading-relaxed">
                      Don&apos;t have a PDF? We&apos;ll search online for policies.
                    </p>
                  </button>

                  {/* Local Database Option */}
                  <button
                    onClick={() => {
                      setData((prev) => ({
                        ...prev,
                        uploadMethod: "local-db",
                      }));
                      setState("local-db-input");
                    }}
                    className="relative p-6 bg-white border border-gray-200 rounded-2xl shadow-sm hover:shadow-md hover:border-green-500 hover:-translate-y-1 transition-all duration-200 text-left group"
                  >
                    <div className="text-3xl mb-4 group-hover:scale-110 transition-transform origin-left">
                      💾
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Local Database
                    </h3>
                    <p className="text-gray-500 text-sm leading-relaxed">
                      Search our cached policy database for quick results.
                    </p>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Upload Flow */}
          {data.uploadMethod === "upload" &&
            (state === "uploading" ||
              state === "classifying" ||
              state === "drug-input" ||
              state === "extracting" ||
              state === "results") && (
              <div className="space-y-6 animate-slideUp">
                {/* Upload Zone */}
                {state === "uploading" || state === "classifying" ? (
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900 mb-4">
                      Upload Policy PDF
                    </h2>
                    <UploadZone
                      onFileSelect={handleFileUpload}
                      isLoading={state === "uploading"}
                      disabled={state === "classifying"}
                    />
                    {state === "classifying" && (
                      <div className="text-center mt-4">
                        <p className="text-gray-600 flex items-center justify-center gap-2">
                          <span className="inline-block h-4 w-4 border-2 border-gray-400 border-t-blue-500 rounded-full animate-spin" />
                          Analyzing document...
                        </p>
                      </div>
                    )}
                  </div>
                ) : null}

                {/* File Info & Drug Input */}
                {(state === "drug-input" ||
                  state === "extracting" ||
                  state === "results") &&
                  data.uploadedFile && (
                    <div className="space-y-6 animate-slideUp">
                      <div>
                        <h2 className="text-lg font-semibold text-gray-900 mb-3">
                          File Information
                        </h2>
                        <div className="bg-white p-4 rounded-xl border border-gray-200">
                          <p className="text-sm text-gray-600 mb-2">
                            File Name
                          </p>
                          <p className="font-medium text-gray-900 mb-3">
                            {data.uploadedFile.original_name}
                          </p>
                          <p className="text-sm text-gray-600 mb-2">
                            Pages
                          </p>
                          <p className="font-medium text-gray-900">
                            {data.uploadedFile.pages} pages
                          </p>
                        </div>
                      </div>

                      <div>
                        <h2 className="text-lg font-semibold text-gray-900 mb-3">
                          Target Drug
                        </h2>
                        <div className="bg-white p-6 rounded-xl border border-gray-200">
                          <DrugInput
                            value={data.targetDrug}
                            onChange={handleDrugChange}
                            onKeyPress={handleExtractKeyPress}
                            disabled={state === "extracting"}
                            error={
                              state !== "extracting" &&
                              data.targetDrug === "" &&
                              state !== "drug-input"
                                ? "Please enter a drug name"
                                : undefined
                            }
                          />
                        </div>
                      </div>
                    </div>
                  )}

                {/* Extract & Reset Buttons */}
                {(state === "drug-input" ||
                  state === "extracting" ||
                  state === "results") && (
                  <div className="flex gap-3">
                    <button
                      onClick={handleExtract}
                      disabled={isExtractDisabled || state === "extracting"}
                      className={`flex-1 px-6 py-3 rounded-lg font-semibold text-white transition-all duration-200 ${
                        isExtractDisabled || state === "extracting"
                          ? "bg-gray-400 cursor-not-allowed"
                          : "bg-blue-600 hover:bg-blue-700 active:scale-95"
                      }`}
                    >
                      {state === "extracting" ? (
                        <span className="flex items-center justify-center gap-2">
                          <span className="inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          Extracting...
                        </span>
                      ) : (
                        "Step 3: Extract Structured Data"
                      )}
                    </button>
                    <button
                      onClick={handleReset}
                      className="px-6 py-3 rounded-lg font-semibold text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-all duration-200 active:scale-95"
                    >
                      ← Back
                    </button>
                  </div>
                )}
              </div>
            )}

          {/* Search Flow */}
          {data.uploadMethod === "search" &&
            (state === "drug-input" ||
              state === "searching" ||
              state === "results") && (
              <div className="space-y-6 animate-slideUp">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 mb-3">
                    Enter Drug Name
                  </h2>
                  <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <DrugInput
                      value={data.targetDrug}
                      onChange={handleDrugChange}
                      onKeyPress={handleSearchKeyPress}
                      disabled={state === "searching"}
                      placeholder="e.g., Ozempic, Humira, Metformin"
                      error={
                        state !== "searching" &&
                        data.targetDrug === "" &&
                        state !== "drug-input"
                          ? "Please enter a drug name"
                          : undefined
                      }
                    />
                  </div>
                </div>

                {/* Search Button */}
                <div className="flex gap-3">
                  <button
                    onClick={handleSearchOnline}
                    disabled={isSearchDisabled || state === "searching"}
                    className={`flex-1 px-6 py-3 rounded-xl font-medium text-white shadow-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                      isSearchDisabled || state === "searching"
                        ? "bg-gray-400 cursor-not-allowed"
                        : "bg-purple-600 hover:bg-purple-700 focus:ring-purple-500 active:scale-95"
                    }`}
                  >
                    {state === "searching" ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Searching Online...
                      </span>
                    ) : (
                      "Search Online"
                    )}
                  </button>
                  <button
                    onClick={handleReset}
                    className="px-6 py-3 rounded-xl font-medium text-gray-700 bg-white border border-gray-300 shadow-sm hover:bg-gray-50 hover:text-gray-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-200 active:scale-95"
                  >
                    ← Back
                  </button>
                </div>

                {/* Found Source */}
                {state === "results" && data.sourceUrl && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-sm text-blue-800">
                      <span className="font-semibold">Source:</span>{" "}
                      <a
                        href={data.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline hover:text-blue-900 break-all"
                      >
                        {data.sourceUrl}
                      </a>
                    </p>
                  </div>
                )}
              </div>
            )}

          {/* Local Database Flow */}
          {data.uploadMethod === "local-db" &&
            (state === "local-db-input" ||
              state === "local-db-searching" ||
              state === "local-db-results") && (
              <div className="space-y-6 animate-slideUp">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 mb-3">
                    Select a Drug
                  </h2>
                  <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <select
                      value={data.selectedDrugFromLocal || ""}
                      onChange={(e) =>
                        setData((prev) => ({
                          ...prev,
                          selectedDrugFromLocal: e.target.value || null,
                        }))
                      }
                      disabled={
                        state === "local-db-searching" || data.drugsLoading
                      }
                      className="w-full px-4 py-3 bg-gray-50 border border-gray-300 rounded-xl text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed transition-colors"
                    >
                      <option value="">
                        {data.drugsLoading
                          ? "Loading available drugs..."
                          : "Select a drug from database..."}
                      </option>
                      {data.availableDrugs.map((drug) => (
                        <option key={drug.name} value={drug.name}>
                          {drug.brand_name || drug.name} ({drug.generic_name})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Search Button */}
                <div className="flex gap-3">
                  <button
                    onClick={handleSearchLocal}
                    disabled={
                      isLocalDbSearchDisabled || state === "local-db-searching"
                    }
                    className={`flex-1 px-6 py-3 rounded-xl font-medium text-white shadow-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                      isLocalDbSearchDisabled || state === "local-db-searching"
                        ? "bg-gray-400 cursor-not-allowed"
                        : "bg-green-600 hover:bg-green-700 focus:ring-green-500 active:scale-95"
                    }`}
                  >
                    {state === "local-db-searching" ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Searching Database...
                      </span>
                    ) : (
                      "Search Database"
                    )}
                  </button>
                  <button
                    onClick={handleReset}
                    className="px-6 py-3 rounded-xl font-medium text-gray-700 bg-white border border-gray-300 shadow-sm hover:bg-gray-50 hover:text-gray-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-200 active:scale-95"
                  >
                    ← Back
                  </button>
                </div>
              </div>
            )}

          {/* Local Database Results - Comparison View */}
          {state === "local-db-results" && data.localSearchResults.length > 0 && (
            <div className="space-y-6 animate-slideUp">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Insurance Company Coverage Comparison
                </h2>
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Insurance Company
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Coverage Status
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Action
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.localSearchResults.map((result, idx) => (
                        <tr
                          key={idx}
                          className="border-b border-gray-200 hover:bg-gray-50 transition-colors"
                        >
                          <td className="px-6 py-4 text-sm font-medium text-gray-900">
                            {result.payer}
                          </td>
                          <td className="px-6 py-4 text-sm">
                            {result.coverage === true ? (
                              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-green-100 text-green-800 font-medium">
                                ✓ Covered
                              </span>
                            ) : result.coverage === false ? (
                              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-100 text-red-800 font-medium">
                                ✗ Not Covered
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gray-100 text-gray-800 font-medium">
                                ? Unknown
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-sm">
                            <button
                              onClick={() => {
                                if (result.policy) {
                                  setData((prev) => ({
                                    ...prev,
                                    extractedData: result.policy,
                                  }));
                                }
                              }}
                              className="text-blue-600 hover:text-blue-800 font-medium underline"
                            >
                              View Policy
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Policy Details Section - Collapsible Fields Inside */}
              {data.extractedData && (
                <div className="space-y-4">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Policy Details
                  </h2>

                  <div className="flex items-center border border-gray-200 rounded-lg p-1 bg-gray-50 self-start w-fit">
                    <button
                      onClick={() =>
                        setData((prev) => ({
                          ...prev,
                          viewMode: "formatted",
                        }))
                      }
                      className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200 ${
                        data.viewMode === "formatted"
                          ? "bg-white text-gray-900 shadow-sm border border-gray-200"
                          : "text-gray-500 hover:text-gray-900"
                      }`}
                    >
                      Formatted
                    </button>
                    <button
                      onClick={() =>
                        setData((prev) => ({
                          ...prev,
                          viewMode: "raw",
                        }))
                      }
                      className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200 ${
                        data.viewMode === "raw"
                          ? "bg-white text-gray-900 shadow-sm border border-gray-200"
                          : "text-gray-500 hover:text-gray-900"
                      }`}
                    >
                      Raw JSON
                    </button>
                  </div>

                  {data.viewMode === "formatted" ? (
                    <ResultsDisplay
                      data={data.extractedData}
                      targetDrug={data.selectedDrugFromLocal || ""}
                    />
                  ) : (
                    <JsonViewer
                      data={data.extractedData}
                      onCopy={handleCopyJson}
                      showCopyButton={true}
                    />
                  )}
                </div>
              )}
            </div>
          )}

          {/* Upload/Search Results - No Policy Found */}
          {state === "results" &&
            !data.extractedData &&
            data.uploadMethod === "search" && (
              <div className="space-y-6 animate-slideUp">
                <div className="bg-red-50 border border-red-200 rounded-xl p-8">
                  <div className="text-center">
                    <div className="text-5xl mb-4">❌</div>
                    <h2 className="text-2xl font-semibold text-red-900 mb-2">
                      Unable to Find Policy
                    </h2>
                    <p className="text-red-700 mb-4">
                      We couldn&apos;t find a valid insurance policy for{" "}
                      <span className="font-semibold">{data.lastSearchedDrug}</span>.
                    </p>
                    <p className="text-sm text-red-600 mb-6">
                      This could mean the drug policy is not publicly available online
                      or the payer information couldn&apos;t be extracted.
                    </p>

                    {/* Show search progress */}
                    {data.progressMessages.length > 0 && (
                      <details className="text-left mt-6 bg-white border border-red-200 rounded-lg p-4">
                        <summary className="font-medium text-red-900 cursor-pointer hover:text-red-800">
                          📋 Search Details ({data.progressMessages.length} steps)
                        </summary>
                        <div className="mt-4 space-y-2 text-sm">
                          {data.progressMessages.map((msg, idx) => (
                            <div key={idx} className="flex items-start gap-3 text-red-800">
                              <div className="flex-shrink-0 w-4 h-4 rounded-full bg-red-300 mt-0.5" />
                              <p>{msg}</p>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                </div>

                {/* Note - No Add to Database for not-found results (Hidden PDF tip) */}
                {/*
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    <span className="font-semibold">💡 Tip:</span> Try uploading a PDF
                    directly to extract policy information manually.
                  </p>
                </div>
                */}

                {/* Back Button */}
                <div className="flex gap-3">
                  <button
                    onClick={handleReset}
                    className="flex-1 px-6 py-3 rounded-xl font-medium text-gray-700 bg-white border border-gray-300 shadow-sm hover:bg-gray-50 hover:text-gray-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-200 active:scale-95"
                  >
                    Try Another Search
                  </button>
                </div>
              </div>
            )}

          {/* Upload/Search Results */}
          {state === "results" && data.extractedData && (
            <div className="space-y-6 animate-slideUp">
              {/* Online Search Results - Show Comparison + Add to Database */}
              {data.uploadMethod === "search" && data.onlineSearchResults.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">
                    Search Result
                  </h2>
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-gray-50 border-b border-gray-200">
                        <tr>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            Source
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            Action
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="border-b border-gray-200 hover:bg-gray-50 transition-colors">
                          <td className="px-6 py-4 text-sm font-medium text-gray-900">
                            {data.extractedData?.payer_name || data.sourceUrl || "Online Source"}
                          </td>
                          <td className="px-6 py-4 text-sm">
                            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100 text-blue-800 font-medium">
                              ✓ Found
                            </span>
                          </td>
                          <td className="px-6 py-4 text-sm">
                            <button
                              onClick={handleAddToDatabase}
                              disabled={data.isAddingToDatabase}
                              className={`font-medium underline ${
                                data.isAddingToDatabase
                                  ? "text-gray-400 cursor-not-allowed"
                                  : "text-green-600 hover:text-green-800"
                              }`}
                            >
                              {data.isAddingToDatabase ? "Adding..." : "Add to Database"}
                            </button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* Note about adding to database */}
                  <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-800">
                      <span className="font-semibold">💾 Human Verification:</span> Click "Add to Database" to save this verified policy to our local database for faster access in the future.
                    </p>
                  </div>
                </div>
              )}

              {/* Policy Details - Collapsible (Default Open) */}
              <details open className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                <summary className="cursor-pointer">
                  <h2 className="text-lg font-semibold text-gray-900 inline flex items-center gap-2">
                    {data.uploadMethod === "search" ? "Policy Details" : "Extraction Results"}
                  </h2>
                </summary>

                <div className="mt-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center border border-gray-200 rounded-lg p-1 bg-gray-50">
                      <button
                        onClick={() =>
                          setData((prev) => ({
                            ...prev,
                            viewMode: "formatted",
                          }))
                        }
                        className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200 ${
                          data.viewMode === "formatted"
                            ? "bg-white text-gray-900 shadow-sm border border-gray-200"
                            : "text-gray-500 hover:text-gray-900"
                        }`}
                      >
                        Formatted
                      </button>
                      <button
                        onClick={() =>
                          setData((prev) => ({
                            ...prev,
                            viewMode: "raw",
                          }))
                        }
                      className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200 ${
                          data.viewMode === "raw"
                          ? "bg-white text-gray-900 shadow-sm border border-gray-200"
                          : "text-gray-500 hover:text-gray-900"
                        }`}
                      >
                        Raw JSON
                      </button>
                    </div>
                  </div>

                  {/* Show search progress if available */}
                  {data.progressMessages.length > 0 && (
                    <div className="mb-6">
                      <details className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                        <summary className="font-medium text-blue-900 cursor-pointer hover:text-blue-800">
                          📋 Search Progress ({data.progressMessages.length} steps)
                        </summary>
                        <div className="mt-4 space-y-2 text-sm">
                          {data.progressMessages.map((msg, idx) => (
                            <div key={idx} className="flex items-start gap-3 text-blue-900">
                              <div className="flex-shrink-0 w-4 h-4 rounded-full bg-blue-400 mt-0.5" />
                              <p>{msg}</p>
                            </div>
                          ))}
                        </div>
                      </details>
                    </div>
                  )}

                  {data.viewMode === "formatted" ? (
                    <ResultsDisplay
                      data={data.extractedData}
                      targetDrug={data.targetDrug}
                    />
                  ) : (
                    <JsonViewer
                      data={data.extractedData}
                      onCopy={handleCopyJson}
                      showCopyButton={true}
                    />
                  )}
                </div>
              </details>

              {/* Bottom Buttons */}
              <div className="flex gap-3">
                {data.uploadMethod === "search" && (
                  <button
                    onClick={handleAddToDatabase}
                    disabled={data.isAddingToDatabase}
                    className={`flex-1 px-6 py-3 rounded-xl font-medium text-white shadow-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                      data.isAddingToDatabase
                        ? "bg-gray-400 cursor-not-allowed"
                        : "bg-green-600 hover:bg-green-700 focus:ring-green-500 active:scale-95"
                    }`}
                  >
                    {data.isAddingToDatabase
                      ? "Adding to Database..."
                      : "💾 Add to Database"}
                  </button>
                )}
                <button
                  onClick={handleReset}
                  className="flex-1 px-6 py-3 rounded-xl font-medium text-gray-700 bg-white border border-gray-300 shadow-sm hover:bg-gray-50 hover:text-gray-900 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-200 active:scale-95"
                >
                  Start Over
                </button>
              </div>
            </div>
          )}

          {/* Loading State */}
          {state === "extracting" && data.uploadMethod === "upload" && (
            <div className="space-y-6 animate-slideUp">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-3">
                  Extracting Data...
                </h2>
                <SkeletonLoader />
              </div>
            </div>
          )}

          {state === "searching" && data.uploadMethod === "search" && (
            <div className="space-y-6 animate-slideUp">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-3">
                  Searching Online & Extracting Data...
                </h2>
                <div className="bg-white p-6 rounded-xl border border-gray-200 space-y-3">
                  {data.progressMessages.length > 0 ? (
                    data.progressMessages.map((msg, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-3 text-sm text-gray-700"
                      >
                        <div className="flex-shrink-0 w-4 h-4 rounded-full bg-blue-500 mt-1" />
                        <p>{msg}</p>
                      </div>
                    ))
                  ) : (
                    <SkeletonLoader />
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="mt-12 py-8 text-center text-sm text-gray-500 border-t border-gray-200">
          <p>
            Sift Medical Policy Analyzer • Search Online or Local Database
          </p>
        </footer>
      </main>
    </>
  );
}
