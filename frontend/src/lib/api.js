const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

class ApiClient {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.getToken = null;
  }

  setTokenGetter(tokenGetter) {
    this.getToken = tokenGetter;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    if (this.getToken) {
      const token = await this.getToken();
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
    }

    const config = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        let errorData = { detail: "An error occurred" };
        try {
          errorData = await response.json();
        } catch (e) {
          errorData.detail = `Server returned ${response.status} without valid JSON.`;
        }
        throw new Error(errorData.detail || errorData.message || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("API request failed:", error);
      if (error instanceof TypeError && error.message === "Failed to fetch") {
        throw new Error("Network error or CORS issue: The server might be down, or the endpoint crashed without returning CORS headers.");
      }
      throw error;
    }
  }

  async get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: "GET" });
  }

  async post(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async put(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async patch(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: "DELETE" });
  }
}

export const apiClient = new ApiClient();

// Auth endpoints
export const authApi = {
  getMe: async () => {
    const response = await apiClient.get("/auth/me");
    return response.data; // Unwrap the DataResponse wrapper
  },
  updateRole: (data) => apiClient.put("/auth/me/role", data),
};

// Station endpoints
export const stationsApi = {
  getAll: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiClient.get(`/stations${queryString ? `?${queryString}` : ""}`);
    return response.data;
  },
  getById: async (id) => {
    const response = await apiClient.get(`/stations/${id}`);
    return response.data;
  },
};

// Session endpoints
export const sessionsApi = {
  create: async (data) => {
    const response = await apiClient.post("/sessions", data);
    return response.data;
  },
  getById: async (id) => {
    const response = await apiClient.get(`/sessions/${id}`);
    return response.data;
  },
  getSchedule: async (id) => {
    const response = await apiClient.get(`/sessions/${id}/schedule`);
    return response.data;
  },
  recalculate: async (id) => {
    const response = await apiClient.post(`/sessions/${id}/recalculate`);
    return response.data;
  },
  cancel: async (id) => {
    const response = await apiClient.post(`/sessions/${id}/cancel`);
    return response.data;
  },
  getMySessions: async () => {
    const response = await apiClient.get("/sessions"); // Wait, is the endpoint /sessions? Let's check router.
    return response.data;
  },
};

// Operator endpoints
export const operatorApi = {
  getDashboard: async () => {
    const response = await apiClient.get("/operator/dashboard");
    return response.data;
  },
};

// Grid operator endpoints
export const gridOperatorApi = {
  getRegions: async () => {
    const response = await apiClient.get("/grid/regions");
    return response.data;
  },
  getDashboard: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiClient.get(`/grid-operator/dashboard${queryString ? `?${queryString}` : ""}`);
    return response.data;
  },
  getGridStatus: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiClient.get(`/grid/status${queryString ? `?${queryString}` : ""}`);
    return response.data;
  },
  getRenewableStatus: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiClient.get(`/renewable/status${queryString ? `?${queryString}` : ""}`);
    return response.data;
  },
  getCurrentPricing: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiClient.get(`/pricing/current${queryString ? `?${queryString}` : ""}`);
    return response.data;
  },
  getAlerts: async () => {
    const response = await apiClient.get("/grid/alerts");
    return response.data;
  },
  createGridEvent: async (data) => {
    const payload = {
      region: data.region,
      type: data.event_type || data.type || "GRID_STRESS",
      event_type: data.event_type || data.type || "GRID_STRESS",
      severity: data.severity || "HIGH",
      message: data.message || "Grid stress event triggered for testing",
    };
    const response = await apiClient.post("/grid/events", payload);
    return response.data;
  },
};
