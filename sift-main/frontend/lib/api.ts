/**
 * API client service for communicating with the backend.
 * Handles all HTTP requests and error handling.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

interface UploadResponse {
  file_id: string;
  file_path: string;
  original_name: string;
  size: number;
  pages: number;
}

interface ClassifyResponse {
  classification: "single_drug" | "multi_drug";
  file_path: string;
}

interface ExtractResponse {
  data: PolicyData;
  file_path: string;
  target_drug: string;
  classification: string;
}

interface SearchResponse {
  data: PolicyData;
  source_url: string;
  target_drug: string;
  classification: string;
  found: true;
  progress?: string[];
}

export interface Drug {
  name: string;
  brand_name: string;
  generic_name: string;
  payers: string[];
}

interface GetDrugsResponse {
  drugs: Drug[];
}

export interface LocalSearchResult {
  payer: string;
  coverage: boolean | "unknown" | null;
  policy?: PolicyData | null;
}

interface SearchLocalResponse {
  target_drug: string;
  found: true;
  total_payers: number;
  payers: LocalSearchResult[];
  policies: PolicyData[];
}

interface AddToDatabaseResponse {
  success: boolean;
  message: string;
  payer: string;
}

export interface PolicyData {
  payer_name: string | null;
  drug_name: {
    brand: string | null;
    generic: string | null;
  };
  drug_category: string | null;
  access_status: {
    status: "preferred" | "non-preferred" | "restricted" | "unknown";
    preferred_count_in_category: number | null;
    notes: string | null;
  };
  coverage: {
    covered: boolean | "unknown";
    covered_indications: Array<{
      condition: string;
      criteria: string | null;
    }>;
  };
  prior_authorization: {
    required: boolean | "unknown";
    criteria: string[];
  };
  step_therapy: {
    required: boolean | "unknown";
    steps: Array<{
      step_number: number;
      required_drug_or_class: string;
      notes: string | null;
    }>;
  };
  site_of_care: {
    restrictions: string[];
    notes: string | null;
  };
  dosing_and_quantity_limits: {
    limits: Array<{
      type: "dose" | "frequency" | "quantity";
      value: string;
      notes: string | null;
    }>;
  };
  policy_metadata: {
    effective_date: string | null;
    policy_name: string | null;
    policy_id: string | null;
    source_file: string | null;
  };
}

class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  const data = await response.json();

  if (!response.ok) {
    throw new ApiError(
      response.status,
      data.error || `HTTP ${response.status}: ${response.statusText}`,
    );
  }

  return data;
}

export const apiClient = {
  /**
   * Upload a PDF file to the backend
   */
  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_URL}/api/upload`, {
      method: "POST",
      body: formData,
    });

    return handleResponse<UploadResponse>(response);
  },

  /**
   * Classify a PDF as single_drug or multi_drug
   */
  async classifyPdf(filePath: string): Promise<ClassifyResponse> {
    const response = await fetch(`${API_URL}/api/classify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ file_path: filePath }),
    });

    return handleResponse<ClassifyResponse>(response);
  },

  /**
   * Extract structured data from a PDF
   */
  async extractData(
    filePath: string,
    targetDrug: string,
    drugKeywords?: string[],
  ): Promise<ExtractResponse> {
    const response = await fetch(`${API_URL}/api/extract`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        file_path: filePath,
        target_drug: targetDrug,
        drug_keywords: drugKeywords || [targetDrug],
      }),
    });

    return handleResponse<ExtractResponse>(response);
  },

  /**
   * Delete an uploaded file
   */
  async deleteFile(fileId: string): Promise<void> {
    const response = await fetch(`${API_URL}/api/files/${fileId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const data = await response.json();
      throw new ApiError(
        response.status,
        data.error || `Failed to delete file`,
      );
    }
  },

  /**
   * Search online for drug policies
   */
  async searchOnline(
    targetDrug: string,
    drugKeywords?: string[],
  ): Promise<SearchResponse> {
    const response = await fetch(`${API_URL}/api/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        target_drug: targetDrug,
        drug_keywords: drugKeywords || [targetDrug],
      }),
    });

    return handleResponse<SearchResponse>(response);
  },

  /**
   * Get all available drugs from the local database
   */
  async getAllDrugs(): Promise<GetDrugsResponse> {
    const response = await fetch(`${API_URL}/api/drugs`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    return handleResponse<GetDrugsResponse>(response);
  },

  /**
   * Search the local database for a drug and get all payer policies
   */
  async searchLocalDatabase(targetDrug: string): Promise<SearchLocalResponse> {
    const response = await fetch(`${API_URL}/api/search-local`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        target_drug: targetDrug,
      }),
    });

    return handleResponse<SearchLocalResponse>(response);
  },

  /**
   * Add a policy result to the local database (opt-in for verified results)
   */
  async addToDatabase(
    policyData: PolicyData,
    sourceUrl: string,
    targetDrug: string,
  ): Promise<AddToDatabaseResponse> {
    const response = await fetch(`${API_URL}/api/add-to-database`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        policy_data: policyData,
        source_url: sourceUrl,
        target_drug: targetDrug,
      }),
    });

    return handleResponse<AddToDatabaseResponse>(response);
  },
};

export { ApiError };
