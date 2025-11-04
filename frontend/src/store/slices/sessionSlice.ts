import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import apiService, { Session, AgentMessage, SupplementaryUserInput, ClarifyingQuestion } from '../../services/apiService';

// Re-export types from API service
export { Session, AgentMessage, SupplementaryUserInput, ClarifyingQuestion };

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
  async (userInput: string, { rejectWithValue }) => {
    try {
      const response = await apiService.createSession({
        user_input: userInput,
        max_iterations: 5,
        max_interventions: 3
      });
      return response.session;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to create session');
    }
  }
);

export const fetchSession = createAsyncThunk(
  'session/fetchSession',
  async (sessionId: string, { rejectWithValue }) => {
    try {
      const session = await apiService.getSession(sessionId);
      return session;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to fetch session');
    }
  }
);

export const fetchSessions = createAsyncThunk(
  'session/fetchSessions',
  async (params?: { page?: number; size?: number; status?: string; search?: string }, { rejectWithValue }) => {
    try {
      const response = await apiService.getSessions(params);
      return response;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to fetch sessions');
    }
  }
);

export const fetchSessionMessages = createAsyncThunk(
  'session/fetchSessionMessages',
  async (sessionId: string, { rejectWithValue }) => {
    try {
      const messages = await apiService.getSessionMessages(sessionId);
      return messages;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to fetch session messages');
    }
  }
);

export const addSupplementaryInput = createAsyncThunk(
  'session/addSupplementaryInput',
  async ({ sessionId, input }: { sessionId: string; input: string }, { rejectWithValue }) => {
    try {
      const response = await apiService.addSupplementaryInput(sessionId, {
        input_content: input,
        input_type: 'supplementary'
      });
      return { sessionId, response };
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to add supplementary input');
    }
  }
);

export const fetchClarifyingQuestions = createAsyncThunk(
  'session/fetchClarifyingQuestions',
  async (sessionId: string, { rejectWithValue }) => {
    try {
      const questions = await apiService.getClarifyingQuestions(sessionId);
      return { sessionId, questions };
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to fetch clarifying questions');
    }
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