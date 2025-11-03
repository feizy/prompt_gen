import { createSlice, PayloadAction } from '@reduxjs/toolkit';

// Types
export interface Agent {
  type: 'product_manager' | 'technical_developer' | 'team_lead';
  status: 'idle' | 'thinking' | 'speaking' | 'error';
  lastActive: string | null;
  messageCount: number;
}

export interface AgentState {
  agents: Record<string, Agent>;
  currentSpeaker: string | null;
  isCollaborating: boolean;
}

const initialState: AgentState = {
  agents: {
    product_manager: {
      type: 'product_manager',
      status: 'idle',
      lastActive: null,
      messageCount: 0,
    },
    technical_developer: {
      type: 'technical_developer',
      status: 'idle',
      lastActive: null,
      messageCount: 0,
    },
    team_lead: {
      type: 'team_lead',
      status: 'idle',
      lastActive: null,
      messageCount: 0,
    },
  },
  currentSpeaker: null,
  isCollaborating: false,
};

const agentSlice = createSlice({
  name: 'agent',
  initialState,
  reducers: {
    setAgentStatus: (state, action: PayloadAction<{ agentType: string; status: Agent['status'] }>) => {
      const { agentType, status } = action.payload;
      if (state.agents[agentType]) {
        state.agents[agentType].status = status;
        if (status === 'speaking') {
          state.currentSpeaker = agentType;
          state.agents[agentType].lastActive = new Date().toISOString();
          state.agents[agentType].messageCount += 1;
        } else if (state.currentSpeaker === agentType && status === 'idle') {
          state.currentSpeaker = null;
        }
      }
    },
    startCollaboration: (state) => {
      state.isCollaborating = true;
      // Reset all agents to idle
      Object.keys(state.agents).forEach(agentType => {
        state.agents[agentType].status = 'idle';
        state.agents[agentType].messageCount = 0;
        state.agents[agentType].lastActive = null;
      });
    },
    stopCollaboration: (state) => {
      state.isCollaborating = false;
      state.currentSpeaker = null;
      // Set all agents to idle
      Object.keys(state.agents).forEach(agentType => {
        state.agents[agentType].status = 'idle';
      });
    },
    resetAgents: (state) => {
      return initialState;
    },
    incrementMessageCount: (state, action: PayloadAction<string>) => {
      const agentType = action.payload;
      if (state.agents[agentType]) {
        state.agents[agentType].messageCount += 1;
      }
    },
  },
});

export const {
  setAgentStatus,
  startCollaboration,
  stopCollaboration,
  resetAgents,
  incrementMessageCount,
} = agentSlice.actions;

export default agentSlice.reducer;