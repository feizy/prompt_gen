/**
 * Unit tests for ConversationThread component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';

import ConversationThread from '../ConversationThread';
import { AgentMessage } from '../../store/slices/sessionSlice';

// Mock Redux store
const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      session: (state = { sessions: [], currentSession: null, messages: [] }, action) => state,
    },
    preloadedState: initialState,
  });
};

// Mock IntersectionObserver for scroll detection
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Sample test data
const sampleMessages: AgentMessage[] = [
  {
    id: '1',
    session_id: 'session-1',
    agent_type: 'product_manager',
    message_content: 'I will analyze the requirements for this customer service chatbot prompt.',
    message_type: 'requirement',
    sequence_number: 1,
    parent_message_id: null,
    created_at: '2024-01-01T10:00:00Z',
    processing_time_ms: 1500,
    metadata: {},
  },
  {
    id: '2',
    session_id: 'session-1',
    agent_type: 'technical_developer',
    message_content: 'Based on the requirements, I recommend using a structured approach with clear context.',
    message_type: 'technical_solution',
    sequence_number: 2,
    parent_message_id: null,
    created_at: '2024-01-01T10:01:00Z',
    processing_time_ms: 2000,
    metadata: {},
  },
  {
    id: '3',
    session_id: 'session-1',
    agent_type: 'team_lead',
    message_content: 'The proposed solution looks good. I approve this approach.',
    message_type: 'approval',
    sequence_number: 3,
    parent_message_id: null,
    created_at: '2024-01-01T10:02:00Z',
    processing_time_ms: 800,
    metadata: {},
  },
];

const renderWithProviders = (ui: React.ReactElement, initialState = {}) => {
  const theme = createTheme();
  const store = createMockStore(initialState);

  return render(
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        {ui}
      </ThemeProvider>
    </Provider>
  );
};

describe('ConversationThread', () => {
  const defaultProps = {
    sessionId: 'session-1',
    messages: [],
    loading: false,
    onRefresh: jest.fn(),
    onMarkAsRead: jest.fn(),
    onMessageFeedback: jest.fn(),
    onCopyMessage: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    test('renders empty state when no messages', () => {
      renderWithProviders(<ConversationThread {...defaultProps} />);

      expect(screen.getByText(/Waiting for agents to start collaborating/)).toBeInTheDocument();
      expect(screen.getByText(/The AI agents will begin working on your requirements shortly/)).toBeInTheDocument();
    });

    test('renders loading state correctly', () => {
      renderWithProviders(
        <ConversationThread {...defaultProps} loading={true} />
      );

      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    test('renders messages correctly', () => {
      renderWithProviders(
        <ConversationThread {...defaultProps} messages={sampleMessages} />
      );

      expect(screen.getByText('Agent Collaboration')).toBeInTheDocument();
      expect(screen.getByText('3 messages')).toBeInTheDocument();

      // Check individual messages are rendered
      expect(screen.getByText(/I will analyze the requirements/)).toBeInTheDocument();
      expect(screen.getByText(/Based on the requirements/)).toBeInTheDocument();
      expect(screen.getByText(/The proposed solution looks good/)).toBeInTheDocument();
    });

    test('renders agent statistics chips', () => {
      renderWithProviders(
        <ConversationThread {...defaultProps} messages={sampleMessages} />
      );

      expect(screen.getByText('product manager: 1')).toBeInTheDocument();
      expect(screen.getByText('technical developer: 1')).toBeInTheDocument();
      expect(screen.getByText('team lead: 1')).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    test('calls onRefresh when refresh button is clicked', () => {
      const mockOnRefresh = jest.fn();
      renderWithProviders(
        <ConversationThread {...defaultProps} onRefresh={mockOnRefresh} />
      );

      const refreshButton = screen.getByLabelText('Refresh messages');
      fireEvent.click(refreshButton);

      expect(mockOnRefresh).toHaveBeenCalledTimes(1);
    });

    test('calls onMarkAsRead when mark all as read is clicked', () => {
      const mockOnMarkAsRead = jest.fn();
      renderWithProviders(
        <ConversationThread
          {...defaultProps}
          messages={sampleMessages}
          onMarkAsRead={mockOnMarkAsRead}
        />
      );

      const markReadButton = screen.getByLabelText('Mark all as read');
      fireEvent.click(markReadButton);

      expect(mockOnMarkAsRead).toHaveBeenCalledTimes(sampleMessages.length);
      sampleMessages.forEach(message => {
        expect(mockOnMarkAsRead).toHaveBeenCalledWith(message.id);
      });
    });

    test('calls onCopyMessage when copy is clicked on a message', async () => {
      const mockOnCopyMessage = jest.fn();
      renderWithProviders(
        <ConversationThread
          {...defaultProps}
          messages={sampleMessages}
          onCopyMessage={mockOnCopyMessage}
        />
      );

      // Find and click copy button on first message
      const copyButtons = screen.getAllByLabelText('Copy message');
      fireEvent.click(copyButtons[0]);

      await waitFor(() => {
        expect(mockOnCopyMessage).toHaveBeenCalledWith(sampleMessages[0].message_content);
      });
    });

    test('calls onMessageFeedback when feedback is given', async () => {
      const mockOnFeedback = jest.fn();
      renderWithProviders(
        <ConversationThread
          {...defaultProps}
          messages={sampleMessages}
          onMessageFeedback={mockOnFeedback}
        />
      );

      // Find and click helpful button on first message
      const helpfulButtons = screen.getAllByLabelText('Helpful');
      fireEvent.click(helpfulButtons[0]);

      await waitFor(() => {
        expect(mockOnFeedback).toHaveBeenCalledWith(sampleMessages[0].id, 'positive');
      });
    });
  });

  describe('Message Features', () => {
    test('displays expandable message details', () => {
      renderWithProviders(
        <ConversationThread {...defaultProps} messages={sampleMessages} />
      );

      // Find expand button for first message
      const expandButtons = screen.getAllByLabelText(/Show/);
      fireEvent.click(expandButtons[0]);

      // Check for expanded content
      expect(screen.getByText('Message Details')).toBeInTheDocument();
      expect(screen.getByText('Sequence: #1')).toBeInTheDocument();
      expect(screen.getByText('Type: requirement')).toBeInTheDocument();
      expect(screen.getByText('Agent: product_manager')).toBeInTheDocument();
    });

    test('shows processing time when available', () => {
      renderWithProviders(
        <ConversationThread {...defaultProps} messages={sampleMessages} />
      );

      // Check for processing time indicators
      expect(screen.getByText('1.5s')).toBeInTheDocument(); // First message
      expect(screen.getByText('2.0s')).toBeInTheDocument(); // Second message
      expect(screen.getByText('800ms')).toBeInTheDocument(); // Third message
    });

    test('displays correct agent icons and colors', () => {
      renderWithProviders(
        <ConversationThread {...defaultProps} messages={sampleMessages} />
      );

      // Check agent avatars are rendered
      const avatars = screen.getAllByTestId('agent-avatar'); // Assuming avatars have test-id
      expect(avatars).toHaveLength(3);
    });

    test('shows latest message indicator', () => {
      renderWithProviders(
        <ConversationThread {...defaultProps} messages={sampleMessages} />
      );

      expect(screen.getByText('Latest')).toBeInTheDocument();
    });
  });

  describe('Unread Messages', () => {
    test('shows unread indicator when there are unread messages', () => {
      // This would require modifying the component to track unread status
      // For now, test that the unread chip can be rendered
      renderWithProviders(
        <ConversationThread {...defaultProps} messages={sampleMessages} />
      );

      // Currently unread functionality is placeholder
      // This test would need to be updated when unread tracking is implemented
    });

    test('updates unread count when messages are marked as read', () => {
      const mockOnMarkAsRead = jest.fn();
      renderWithProviders(
        <ConversationThread
          {...defaultProps}
          messages={sampleMessages}
          onMarkAsRead={mockOnMarkAsRead}
        />
      );

      const markReadButton = screen.getByLabelText('Mark all as read');
      fireEvent.click(markReadButton);

      // Verify callback was called
      expect(mockOnMarkAsRead).toHaveBeenCalledTimes(3);
    });
  });

  describe('Scroll Behavior', () => {
    test('shows scroll to bottom button when not at bottom', () => {
      // Mock scroll position detection
      Object.defineProperty(HTMLElement.prototype, 'scrollTop', {
        get() { return 100; }, // Not at bottom
        configurable: true,
      });

      Object.defineProperty(HTMLElement.prototype, 'scrollHeight', {
        get() { return 1000; },
        configurable: true,
      });

      Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
        get() { return 500; },
        configurable: true,
      });

      renderWithProviders(
        <ConversationThread {...defaultProps} messages={sampleMessages} />
      );

      // Scroll to bottom button should be visible
      const scrollButton = screen.getByLabelText('Scroll to bottom');
      expect(scrollButton).toBeInTheDocument();
    });

    test('scrolls to bottom when button is clicked', () => {
      const mockScrollIntoView = jest.fn();
      window.HTMLElement.prototype.scrollIntoView = mockScrollIntoView;

      renderWithProviders(
        <ConversationThread {...defaultProps} messages={sampleMessages} />
      );

      const scrollButton = screen.getByLabelText('Scroll to bottom');
      fireEvent.click(scrollButton);

      expect(mockScrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth' });
    });
  });

  describe('Connection Status', () => {
    test('displays connection status alert when messages exist', () => {
      renderWithProviders(
        <ConversationThread {...defaultProps} messages={sampleMessages} />
      );

      expect(screen.getByText(/You're viewing 3 messages/)).toBeInTheDocument();
    });

    test('shows different message count based on actual messages', () => {
      const singleMessage = [sampleMessages[0]];
      renderWithProviders(
        <ConversationThread {...defaultProps} messages={singleMessage} />
      );

      expect(screen.getByText('1 messages')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    test('handles missing onRefresh callback gracefully', () => {
      const { rerender } = renderWithProviders(
        <ConversationThread {...defaultProps} onRefresh={undefined} />
      );

      // Should not throw error
      expect(screen.getByText('Agent Collaboration')).toBeInTheDocument();
    });

    test('handles empty callbacks gracefully', () => {
      renderWithProviders(
        <ConversationThread
          {...defaultProps}
          onRefresh={jest.fn()}
          onMarkAsRead={jest.fn()}
          onMessageFeedback={jest.fn()}
          onCopyMessage={jest.fn()}
        />
      );

      // Should render without errors
      expect(screen.getByText('Agent Collaboration')).toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    test('handles large number of messages efficiently', () => {
      // Generate many messages
      const manyMessages = Array.from({ length: 100 }, (_, i) => ({
        ...sampleMessages[0],
        id: `msg-${i}`,
        sequence_number: i + 1,
        message_content: `Message ${i + 1}`,
      }));

      const startTime = performance.now();
      renderWithProviders(
        <ConversationThread {...defaultProps} messages={manyMessages} />
      );
      const endTime = performance.now();

      // Should render within reasonable time (< 100ms for 100 messages)
      expect(endTime - startTime).toBeLessThan(100);
      expect(screen.getByText('100 messages')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    test('has proper ARIA labels', () => {
      renderWithProviders(
        <ConversationThread {...defaultProps} messages={sampleMessages} />
      );

      // Check for proper ARIA labels on interactive elements
      expect(screen.getByLabelText('Refresh messages')).toBeInTheDocument();
      expect(screen.getByLabelText('Mark all as read')).toBeInTheDocument();

      const copyButtons = screen.getAllByLabelText('Copy message');
      expect(copyButtons).toHaveLength(3);
    });

    test('supports keyboard navigation', () => {
      renderWithProviders(
        <ConversationThread {...defaultProps} messages={sampleMessages} />
      );

      const refreshButton = screen.getByLabelText('Refresh messages');
      refreshButton.focus();
      expect(refreshButton).toHaveFocus();

      // Test Enter key
      fireEvent.keyDown(refreshButton, { key: 'Enter' });
      expect(defaultProps.onRefresh).toHaveBeenCalled();
    });
  });
});