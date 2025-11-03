import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

// Types
export interface Session {
  id: string;
  user_input: string;
  status: 'active' | 'waiting_for_user' | 'processing' | 'completed' | 'failed' | 'timeout';
  final_prompt: string | null;
  created_at: string;
  updated_at: string;
  iteration_count: number;
  user_intervention_count: number;
  waiting_for_user_since: string | null;
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
}

export interface SupplementaryUserInput {
  id: string;
  session_id: string;
  input_content: string;
  input_type: 'supplementary' | 'clarification_response';
  provided_at: string;
  processing_status: 'pending' | 'processed' | 'failed';
  sequence_number: number;
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
}

interface SessionState {
  sessions: Session[];
  currentSession: Session | null;
  messages: AgentMessage[];
  supplementaryInputs: SupplementaryUserInput[];
  clarifyingQuestions: ClarifyingQuestion[];
  loading: boolean;
  error: string | null;
}

const initialState: SessionState = {
  sessions: [],
  currentSession: null,
  messages: [],
  supplementaryInputs: [],
  clarifyingQuestions: [],
  loading: false,
  error: null,
};

// Async thunks
export const createSession = createAsyncThunk(
  'session/createSession',
  async (userInput: string) => {
    // TODO: Implement API call
    const response = await fetch('/v1/sessions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_input: userInput }),
    });
    const data = await response.json();
    return data;
  }
);

export const fetchSession = createAsyncThunk(
  'session/fetchSession',
  async (sessionId: string) => {
    // TODO: Implement API call
    const response = await fetch(`/v1/sessions/${sessionId}`);
    const data = await response.json();
    return data;
  }
);

export const fetchSessionMessages = createAsyncThunk(
  'session/fetchSessionMessages',
  async (sessionId: string) => {
    // TODO: Implement API call
    const response = await fetch(`/v1/sessions/${sessionId}/messages`);
    const data = await response.json();
    return data.messages;
  }
);

const sessionSlice = createSlice({
  name: 'session',
  initialState,
  reducers: {
    setCurrentSession: (state, action: PayloadAction<Session | null>) => {
      state.currentSession = action.payload;
    },
    addMessage: (state, action: PayloadAction<AgentMessage>) => {
      state.messages.push(action.payload);
    },
    updateSessionStatus: (state, action: PayloadAction<{ id: string; status: Session['status'] }>) => {
      const { id, status } = action.payload;
      const session = state.sessions.find(s => s.id === id);
      if (session) {
        session.status = status;
      }
      if (state.currentSession && state.currentSession.id === id) {
        state.currentSession.status = status;
      }
    },
    clearError: (state) => {
      state.error = null;
    },
    clearCurrentSession: (state) => {
      state.currentSession = null;
      state.messages = [];
      state.supplementaryInputs = [];
      state.clarifyingQuestions = [];
    },
  },
  extraReducers: (builder) => {
    builder
      // Create session
      .addCase(createSession.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createSession.fulfilled, (state, action) => {
        state.loading = false;
        state.sessions.push(action.payload);
        state.currentSession = action.payload;
      })
      .addCase(createSession.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to create session';
      })
      // Fetch session
      .addCase(fetchSession.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSession.fulfilled, (state, action) => {
        state.loading = false;
        state.currentSession = action.payload;
      })
      .addCase(fetchSession.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch session';
      })
      // Fetch messages
      .addCase(fetchSessionMessages.fulfilled, (state, action) => {
        state.messages = action.payload;
      });
  },
});

export const {
  setCurrentSession,
  addMessage,
  updateSessionStatus,
  clearError,
  clearCurrentSession,
} = sessionSlice.actions;

export default sessionSlice.reducer;