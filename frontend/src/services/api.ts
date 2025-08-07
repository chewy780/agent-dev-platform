import axios, { AxiosInstance, AxiosResponse } from 'axios';

// API base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Types
export interface Agent {
  id: number;
  agent_id: string;
  name: string;
  description?: string;
  config: Record<string, any>;
  api_keys: Record<string, any>;
  tools: string[];
  permissions: Record<string, any>;
  is_active: boolean;
  is_running: boolean;
  created_at: string;
  updated_at: string;
  last_run?: string;
  owner_id: number;
}

export interface AgentCreate {
  agent_id: string;
  name: string;
  description?: string;
  config?: Record<string, any>;
  api_keys?: Record<string, any>;
  tools?: string[];
  permissions?: Record<string, any>;
}

export interface AgentUpdate {
  name?: string;
  description?: string;
  config?: Record<string, any>;
  api_keys?: Record<string, any>;
  tools?: string[];
  permissions?: Record<string, any>;
}

export interface ChatMessage {
  id: number;
  role: string;
  content: string;
  metadata?: Record<string, any>;
  timestamp: string;
  agent_id: number;
}

export interface LogEntry {
  id: number;
  level: string;
  message: string;
  metadata?: Record<string, any>;
  timestamp: string;
  agent_id: number;
}

export interface ToolInfo {
  id: string;
  name: string;
  description: string;
  category: string;
  permissions: string[];
  parameters: Record<string, any>;
}

// Auth API
export const authApi = {
  setToken: (token: string | null) => {
    if (token) {
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete apiClient.defaults.headers.common['Authorization'];
    }
  },

  login: async (username: string, password: string) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await apiClient.post('/api/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  register: async (username: string, email: string, password: string) => {
    const response = await apiClient.post('/api/auth/register', {
      username,
      email,
      password,
    });
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await apiClient.get('/api/auth/me');
    return response.data;
  },

  refreshToken: async () => {
    const response = await apiClient.post('/api/auth/refresh');
    return response.data;
  },

  logout: async () => {
    const response = await apiClient.post('/api/auth/logout');
    return response.data;
  },
};

// Agents API
export const agentsApi = {
  list: async (): Promise<Agent[]> => {
    const response = await apiClient.get('/api/agents');
    return response.data;
  },

  get: async (agentId: string): Promise<Agent> => {
    const response = await apiClient.get(`/api/agents/${agentId}`);
    return response.data;
  },

  create: async (agentData: AgentCreate): Promise<Agent> => {
    const response = await apiClient.post('/api/agents', agentData);
    return response.data;
  },

  update: async (agentId: string, agentData: AgentUpdate): Promise<Agent> => {
    const response = await apiClient.put(`/api/agents/${agentId}`, agentData);
    return response.data;
  },

  delete: async (agentId: string): Promise<void> => {
    await apiClient.delete(`/api/agents/${agentId}`);
  },

  start: async (agentId: string): Promise<void> => {
    await apiClient.post(`/api/agents/${agentId}/start`);
  },

  stop: async (agentId: string): Promise<void> => {
    await apiClient.post(`/api/agents/${agentId}/stop`);
  },

  restart: async (agentId: string): Promise<void> => {
    await apiClient.post(`/api/agents/${agentId}/restart`);
  },

  getLogs: async (agentId: string, params?: Record<string, any>): Promise<LogEntry[]> => {
    const response = await apiClient.get(`/api/agents/${agentId}/logs`, { params });
    return response.data;
  },

  getTasks: async (agentId: string, params?: Record<string, any>): Promise<any[]> => {
    const response = await apiClient.get(`/api/agents/${agentId}/tasks`, { params });
    return response.data;
  },

  exportConfig: async (agentId: string, format: string = 'json'): Promise<any> => {
    const response = await apiClient.get(`/api/agents/${agentId}/export`, {
      params: { format },
    });
    return response.data;
  },

  importConfig: async (agentId: string, configFile: string): Promise<void> => {
    await apiClient.post(`/api/agents/${agentId}/import`, { config_file: configFile });
  },
};

// Chat API
export const chatApi = {
  getMessages: async (agentId: string, params?: Record<string, any>): Promise<ChatMessage[]> => {
    const response = await apiClient.get(`/api/chat/${agentId}/messages`, { params });
    return response.data;
  },

  sendMessage: async (agentId: string, content: string, metadata?: Record<string, any>): Promise<ChatMessage> => {
    const response = await apiClient.post(`/api/chat/${agentId}/messages`, {
      content,
      metadata,
    });
    return response.data;
  },

  getSessions: async (agentId: string): Promise<any[]> => {
    const response = await apiClient.get(`/api/chat/${agentId}/sessions`);
    return response.data;
  },

  clearHistory: async (agentId: string): Promise<void> => {
    await apiClient.delete(`/api/chat/${agentId}/messages`);
  },
};

// Logs API
export const logsApi = {
  getLogs: async (agentId: string, params?: Record<string, any>): Promise<LogEntry[]> => {
    const response = await apiClient.get(`/api/logs/${agentId}`, { params });
    return response.data;
  },

  getStats: async (agentId: string, days: number = 7): Promise<any> => {
    const response = await apiClient.get(`/api/logs/${agentId}/stats`, {
      params: { days },
    });
    return response.data;
  },

  clearLogs: async (agentId: string, beforeDate?: string): Promise<void> => {
    await apiClient.delete(`/api/logs/${agentId}`, {
      params: { before_date: beforeDate },
    });
  },

  exportLogs: async (agentId: string, format: string = 'json', params?: Record<string, any>): Promise<any> => {
    const response = await apiClient.get(`/api/logs/${agentId}/export`, {
      params: { format, ...params },
    });
    return response.data;
  },
};

// Tools API
export const toolsApi = {
  list: async (category?: string): Promise<ToolInfo[]> => {
    const response = await apiClient.get('/api/tools', {
      params: { category },
    });
    return response.data;
  },

  getCategories: async (): Promise<any[]> => {
    const response = await apiClient.get('/api/tools/categories');
    return response.data;
  },

  getInfo: async (toolId: string): Promise<ToolInfo> => {
    const response = await apiClient.get(`/api/tools/${toolId}`);
    return response.data;
  },

  execute: async (toolId: string, action: string, parameters: Record<string, any>): Promise<any> => {
    const response = await apiClient.post(`/api/tools/${toolId}/execute`, {
      action,
      parameters,
    });
    return response.data;
  },

  getInstalledPlugins: async (): Promise<any[]> => {
    const response = await apiClient.get('/api/tools/plugins/installed');
    return response.data;
  },

  installPlugin: async (pluginUrl: string): Promise<any> => {
    const response = await apiClient.post('/api/tools/plugins/install', {
      plugin_url: pluginUrl,
    });
    return response.data;
  },
};

export default apiClient;
