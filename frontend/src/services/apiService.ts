import axios, { AxiosInstance, AxiosResponse } from 'axios';

// API Base Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Types
export interface CreateSessionRequest {
  user_input: string;
  max_iterations?: number;
  max_interventions?: number;
}

export interface Session {
  id: string;
  user_input: string;
  status: 'active' | 'waiting_for_user' | 'processing' | 'completed' | 'failed' | 'timeout';
  final_prompt: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  iteration_count: number;
  user_intervention_count: number;
  max_interventions: number;
  waiting_for_user_since: string | null;
  current_question_id: string | null;
  session_metadata: any;
}

export interface AgentMessage {
  id: string;
  session_id: string;
  agent_type: 'product_manager' | 'technical_developer' | 'team_lead';
  message_content: string;
  message_type: 'requirement' | 'solution' | 'review' | 'approval' | 'rejection';
  sequence_number: number;
  parent_message_id: string | null;
  created_at: string;
  processing_time_ms: number | null;
  message_metadata: any;
}

export interface SupplementaryUserInput {
  id: string;
  session_id: string;
  input_content: string;
  input_type: 'supplementary' | 'clarification_response';
  provided_at: string;
  processing_status: 'pending' | 'processed' | 'failed';
  incorporated_into_requirements: boolean;
  sequence_number: number;
  input_metadata: any;
}

export interface ClarifyingQuestion {
  id: string;
  session_id: string;
  question_text: string;
  question_type: 'ambiguity' | 'clarification' | 'confirmation';
  priority: number;
  asked_at: string;
  response_deadline: string | null;
  status: 'pending' | 'answered' | 'expired' | 'cancelled';
  response_text: string | null;
  responded_at: string | null;
  agent_type: 'product_manager';
  sequence_number: number;
  question_metadata: any;
}

export interface CreateSessionResponse {
  session: Session;
  message: string;
}

export interface SessionHistoryResponse {
  sessions: Session[];
  total: number;
  page: number;
  size: number;
}

export interface UserInputRequest {
  input_content: string;
  input_type: 'supplementary' | 'clarification_response';
}

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        console.error('API Response Error:', error.response?.data || error.message);

        // Handle common error cases
        if (error.response?.status === 404) {
          error.message = 'Resource not found';
        } else if (error.response?.status === 500) {
          error.message = 'Server error. Please try again later.';
        } else if (error.code === 'ECONNABORTED') {
          error.message = 'Request timeout. Please check your connection.';
        }

        return Promise.reject(error);
      }
    );
  }

  // Session Management
  async createSession(request: CreateSessionRequest): Promise<CreateSessionResponse> {
    const response: AxiosResponse<CreateSessionResponse> = await this.client.post('/v1/sessions', request);
    return response.data;
  }

  async getSession(sessionId: string): Promise<Session> {
    const response: AxiosResponse<Session> = await this.client.get(`/v1/sessions/${sessionId}`);
    return response.data;
  }

  async getSessions(params?: {
    page?: number;
    size?: number;
    status?: string;
    search?: string;
  }): Promise<SessionHistoryResponse> {
    const response: AxiosResponse<SessionHistoryResponse> = await this.client.get('/v1/sessions', { params });
    return response.data;
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.client.delete(`/v1/sessions/${sessionId}`);
  }

  // Message Management
  async getSessionMessages(sessionId: string): Promise<AgentMessage[]> {
    const response: AxiosResponse<AgentMessage[]> = await this.client.get(`/v1/sessions/${sessionId}/messages`);
    return response.data;
  }

  async addSupplementaryInput(sessionId: string, input: UserInputRequest): Promise<any> {
    const response = await this.client.post(`/v1/sessions/${sessionId}/input`, input);
    return response.data;
  }

  async getSupplementaryInputs(sessionId: string): Promise<SupplementaryUserInput[]> {
    const response: AxiosResponse<SupplementaryUserInput[]> = await this.client.get(`/v1/sessions/${sessionId}/input`);
    return response.data;
  }

  // Clarifying Questions
  async getClarifyingQuestions(sessionId: string): Promise<ClarifyingQuestion[]> {
    const response: AxiosResponse<ClarifyingQuestion[]> = await this.client.get(`/v1/sessions/${sessionId}/questions`);
    return response.data;
  }

  async answerClarifyingQuestion(sessionId: string, questionId: string, answer: string): Promise<any> {
    const response = await this.client.post(`/v1/sessions/${sessionId}/questions/${questionId}/answer`, {
      response_text: answer
    });
    return response.data;
  }

  // Health Check
  async healthCheck(): Promise<any> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Utility Methods
  getApiUrl(): string {
    return API_BASE_URL;
  }

  isHealthy(): Promise<boolean> {
    return this.healthCheck()
      .then(() => true)
      .catch(() => false);
  }
}

// Export singleton instance
export const apiService = new ApiService();

// Export types for use in components
export default apiService;