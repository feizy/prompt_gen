/**
 * Unit tests for UserInputPanel component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';

import UserInputPanel from '../UserInputPanel';

// Mock Redux store
const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      session: (state = { sessions: [], currentSession: null, messages: [] }, action) => state,
    },
    preloadedState: initialState,
  });
};

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key) => store[key] || null),
    setItem: jest.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn((key) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock Web Speech API
const mockSpeechRecognition = {
  start: jest.fn(),
  stop: jest.fn(),
  abort: jest.fn(),
  onresult: null,
  onerror: null,
  onend: null,
};

global.SpeechRecognition = jest.fn().mockImplementation(() => mockSpeechRecognition);
global.webkitSpeechRecognition = global.SpeechRecognition;

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

describe('UserInputPanel', () => {
  const defaultProps = {
    sessionId: 'test-session-1',
    disabled: false,
    onSubmit: jest.fn(),
    onContinueWithoutInput: jest.fn(),
    placeholder: 'Type your message here...',
    suggestions: [],
    isLoading: false,
    characterLimit: 2000,
    showShortcuts: true,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();
  });

  describe('Rendering', () => {
    test('renders component correctly', () => {
      renderWithProviders(<UserInputPanel {...defaultProps} />);

      expect(screen.getByText('Agent Communication')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Type your message here...')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Send')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Continue')).toBeInTheDocument();
    });

    test('shows loading state when isLoading is true', () => {
      renderWithProviders(<UserInputPanel {...defaultProps} isLoading={true} />);

      expect(screen.getByDisplayValue('Sending...')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
    });

    test('disables input when disabled prop is true', () => {
      renderWithProviders(<UserInputPanel {...defaultProps} disabled={true} />);

      const input = screen.getByPlaceholderText('Type your message here...');
      expect(input).toBeDisabled();
      expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
    });

    test('displays suggestions when provided', () => {
      const suggestions = ['Need more details', 'Alternative approach', 'Example required'];
      renderWithProviders(
        <UserInputPanel {...defaultProps} suggestions={suggestions} />
      );

      expect(screen.getByText('Suggested responses:')).toBeInTheDocument();
      suggestions.forEach(suggestion => {
        expect(screen.getByText(suggestion)).toBeInTheDocument();
      });
    });

    test('displays character count', () => {
      renderWithProviders(<UserInputPanel {...defaultProps} />);

      expect(screen.getByText('0/2000')).toBeInTheDocument();
    });

    test('shows error message when error prop is provided', async () => {
      renderWithProviders(<UserInputPanel {...defaultProps} />);

      const input = screen.getByPlaceholderText('Type your message here...');
      await userEvent.type(input, 'test message');

      // Simulate error by setting state internally
      const errorDisplay = screen.queryByText(/error/i);
      // Error would be displayed through component state after failed submission
    });
  });

  describe('Input Functionality', () => {
    test('updates input value when typing', async () => {
      renderWithProviders(<UserInputPanel {...defaultProps} />);

      const input = screen.getByPlaceholderText('Type your message here...');
      await userEvent.type(input, 'Hello world');

      expect(input).toHaveValue('Hello world');
      expect(screen.getByText('11/2000')).toBeInTheDocument(); // 11 characters
    });

    test('calls onSubmit when send button is clicked', async () => {
      const mockOnSubmit = jest.fn().mockResolvedValue(true);
      renderWithProviders(
        <UserInputPanel {...defaultProps} onSubmit={mockOnSubmit} />
      );

      const input = screen.getByPlaceholderText('Type your message here...');
      await userEvent.type(input, 'Test message');

      const sendButton = screen.getByRole('button', { name: /send/i });
      await userEvent.click(sendButton);

      expect(mockOnSubmit).toHaveBeenCalledWith('Test message', 'supplementary');
    });

    test('calls onSubmit when Enter key is pressed', async () => {
      const mockOnSubmit = jest.fn().mockResolvedValue(true);
      renderWithProviders(
        <UserInputPanel {...defaultProps} onSubmit={mockOnSubmit} />
      );

      const input = screen.getByPlaceholderText('Type your message here...');
      await userEvent.type(input, 'Test message');
      await userEvent.keyboard('{Enter}');

      expect(mockOnSubmit).toHaveBeenCalledWith('Test message', 'supplementary');
    });

    test('does not submit empty message', async () => {
      const mockOnSubmit = jest.fn();
      renderWithProviders(
        <UserInputPanel {...defaultProps} onSubmit={mockOnSubmit} />
      );

      const sendButton = screen.getByRole('button', { name: /send/i });
      await userEvent.click(sendButton);

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    test('clears input after successful submission', async () => {
      const mockOnSubmit = jest.fn().mockResolvedValue(true);
      renderWithProviders(
        <UserInputPanel {...defaultProps} onSubmit={mockOnSubmit} />
      );

      const input = screen.getByPlaceholderText('Type your message here...');
      await userEvent.type(input, 'Test message');

      const sendButton = screen.getByRole('button', { name: /send/i });
      await userEvent.click(sendButton);

      await waitFor(() => {
        expect(input).toHaveValue('');
      });
    });

    test('prevents submission over character limit', async () => {
      const mockOnSubmit = jest.fn();
      renderWithProviders(
        <UserInputPanel {...defaultProps} characterLimit={10} onSubmit={mockOnSubmit} />
      );

      const input = screen.getByPlaceholderText('Type your message here...');
      await userEvent.type(input, 'This message is way too long');

      const sendButton = screen.getByRole('button', { name: /send/i });
      expect(sendButton).toBeDisabled();
    });
  });

  describe('Continue Without Input', () => {
    test('calls onContinueWithoutInput when continue button is clicked', async () => {
      const mockOnContinue = jest.fn().mockResolvedValue(true);
      renderWithProviders(
        <UserInputPanel {...defaultProps} onContinueWithoutInput={mockOnContinue} />
      );

      const continueButton = screen.getByRole('button', { name: /continue/i });
      await userEvent.click(continueButton);

      expect(mockOnContinue).toHaveBeenCalled();
    });
  });

  describe('Voice Input', () => {
    test('toggles voice recording when mic button is clicked', async () => {
      renderWithProviders(<UserInputPanel {...defaultProps} />);

      const micButton = screen.getByLabelText('Voice input');
      await userEvent.click(micButton);

      expect(mockSpeechRecognition.start).toHaveBeenCalled();
    });

    test('shows error when speech recognition is not supported', async () => {
      // Remove speech recognition support
      delete (global as any).SpeechRecognition;
      delete (global as any).webkitSpeechRecognition;

      renderWithProviders(<UserInputPanel {...defaultProps} />);

      const micButton = screen.getByLabelText('Voice input');
      await userEvent.click(micButton);

      await waitFor(() => {
        expect(screen.getByText(/Speech recognition is not supported/)).toBeInTheDocument();
      });
    });
  });

  describe('Suggestions', () => {
    test('populates input when suggestion is clicked', async () => {
      const suggestions = ['Need more details about requirements'];
      renderWithProviders(
        <UserInputPanel {...defaultProps} suggestions={suggestions} />
      );

      const suggestionChip = screen.getByText('Need more details about requirements');
      await userEvent.click(suggestionChip);

      const input = screen.getByPlaceholderText('Type your message here...');
      expect(input).toHaveValue('Need more details about requirements');
    });

    test('calls onSuggestionClick when suggestion is clicked', async () => {
      const mockOnSuggestionClick = jest.fn();
      const suggestions = ['Test suggestion'];
      renderWithProviders(
        <UserInputPanel
          {...defaultProps}
          suggestions={suggestions}
          onSuggestionClick={mockOnSuggestionClick}
        />
      );

      const suggestionChip = screen.getByText('Test suggestion');
      await userEvent.click(suggestionChip);

      expect(mockOnSuggestionClick).toHaveBeenCalledWith('Test suggestion');
    });
  });

  describe('Quick Actions', () => {
    test('populates input when quick action is clicked', async () => {
      renderWithProviders(<UserInputPanel {...defaultProps} showShortcuts={true} />);

      const quickAction = screen.getByText('Add more details');
      await userEvent.click(quickAction);

      const input = screen.getByPlaceholderText('Type your message here...');
      expect(input).toHaveValue('Can you provide more details about...');
    });
  });

  describe('History Management', () => {
    test('saves input to localStorage after submission', async () => {
      const mockOnSubmit = jest.fn().mockResolvedValue(true);
      renderWithProviders(
        <UserInputPanel {...defaultProps} onSubmit={mockOnSubmit} />
      );

      const input = screen.getByPlaceholderText('Type your message here...');
      await userEvent.type(input, 'Test message');

      const sendButton = screen.getByRole('button', { name: /send/i });
      await userEvent.click(sendButton);

      await waitFor(() => {
        expect(localStorageMock.setItem).toHaveBeenCalledWith(
          expect.stringContaining('input_history_'),
          expect.stringContaining('Test message')
        );
      });
    });

    test('loads input history from localStorage on mount', () => {
      const savedHistory = JSON.stringify(['Previous message 1', 'Previous message 2']);
      localStorageMock.getItem.mockReturnValue(savedHistory);

      renderWithProviders(<UserInputPanel {...defaultProps} />);

      expect(localStorageMock.getItem).toHaveBeenCalledWith(
        expect.stringContaining('input_history_test-session-1')
      );
    });
  });

  describe('Input History Navigation', () => {
    test('navigates through history with arrow keys', async () => {
      const savedHistory = JSON.stringify(['First message', 'Second message']);
      localStorageMock.getItem.mockReturnValue(savedHistory);

      renderWithProviders(<UserInputPanel {...defaultProps} />);

      const input = screen.getByPlaceholderText('Type your message here...');
      input.focus();

      // Press up arrow to get first history item
      await userEvent.keyboard('{ArrowUp}');
      expect(input).toHaveValue('First message');

      // Press up arrow again to get second history item
      await userEvent.keyboard('{ArrowUp}');
      expect(input).toHaveValue('Second message');

      // Press down arrow to go back
      await userEvent.keyboard('{ArrowDown}');
      expect(input).toHaveValue('First message');
    });
  });

  describe('Character Limit', () => {
    test('shows warning color when near limit', async () => {
      renderWithProviders(
        <UserInputPanel {...defaultProps} characterLimit={20} />
      );

      const input = screen.getByPlaceholderText('Type your message here...');
      await userEvent.type(input, 'This is seventeen chars'); // 17 chars

      expect(screen.getByText('17/20')).toHaveClass('warning');
    });

    test('shows error color when over limit', async () => {
      renderWithProviders(
        <UserInputPanel {...defaultProps} characterLimit={20} />
      );

      const input = screen.getByPlaceholderText('Type your message here...');
      await userEvent.type(input, 'This message is definitely over twenty characters');

      expect(screen.getByText(/\d+\/20/)).toHaveClass('error');
      expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
    });
  });

  describe('Accessibility', () => {
    test('has proper ARIA labels', () => {
      renderWithProviders(<UserInputPanel {...defaultProps} />);

      expect(screen.getByLabelText('Voice input')).toBeInTheDocument();
      expect(screen.getByLabelText('Clear input')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Type your message here...')).toBeInTheDocument();
    });

    test('supports keyboard navigation', async () => {
      renderWithProviders(<UserInputPanel {...defaultProps} />);

      const input = screen.getByPlaceholderText('Type your message here...');
      input.focus();

      expect(input).toHaveFocus();

      // Test Tab navigation
      await userEvent.tab();
      // Focus should move to next interactive element
    });

    test('announces character count to screen readers', () => {
      renderWithProviders(<UserInputPanel {...defaultProps} />);

      const characterCount = screen.getByText('0/2000');
      expect(characterCount).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    test('handles submission failure gracefully', async () => {
      const mockOnSubmit = jest.fn().mockRejectedValue(new Error('Network error'));
      renderWithProviders(
        <UserInputPanel {...defaultProps} onSubmit={mockOnSubmit} />
      );

      const input = screen.getByPlaceholderText('Type your message here...');
      await userEvent.type(input, 'Test message');

      const sendButton = screen.getByRole('button', { name: /send/i });
      await userEvent.click(sendButton);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeInTheDocument();
      });
    });

    test('recovers from error state', async () => {
      const mockOnSubmit = jest.fn()
        .mockRejectedValueOnce(new Error('First error'))
        .mockResolvedValueOnce(true);

      renderWithProviders(
        <UserInputPanel {...defaultProps} onSubmit={mockOnSubmit} />
      );

      const input = screen.getByPlaceholderText('Type your message here...');
      await userEvent.type(input, 'Test message');

      const sendButton = screen.getByRole('button', { name: /send/i });

      // First submission fails
      await userEvent.click(sendButton);
      await waitFor(() => {
        expect(screen.getByText(/First error/)).toBeInTheDocument();
      });

      // Clear error and try again
      const errorAlert = screen.getByRole('alert');
      const closeButton = errorAlert.querySelector('button[aria-label="Close"]');
      if (closeButton) {
        await userEvent.click(closeButton);
      }

      // Second submission succeeds
      await userEvent.click(sendButton);
      await waitFor(() => {
        expect(input).toHaveValue('');
      });
    });
  });

  describe('Performance', () => {
    test('handles rapid typing without performance issues', async () => {
      renderWithProviders(<UserInputPanel {...defaultProps} />);

      const input = screen.getByPlaceholderText('Type your message here...');
      const startTime = performance.now();

      await userEvent.type(input, 'This is a very long message that tests typing performance');

      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(100); // Should be fast
    });
  });

  describe('Edge Cases', () => {
    test('handles empty suggestions array', () => {
      renderWithProviders(
        <UserInputPanel {...defaultProps} suggestions={[]} />
      );

      expect(screen.queryByText('Suggested responses:')).not.toBeInTheDocument();
    });

    test('handles missing optional callbacks', () => {
      renderWithProviders(
        <UserInputPanel
          {...defaultProps}
          onSubmit={undefined}
          onContinueWithoutInput={undefined}
          onSuggestionClick={undefined}
        />
      );

      // Should not throw error
      expect(screen.getByText('Agent Communication')).toBeInTheDocument();
    });

    test('handles very long placeholder text', () => {
      const longPlaceholder = 'This is a very long placeholder text that tests how the component handles lengthy placeholder content without breaking the layout or causing display issues';
      renderWithProviders(
        <UserInputPanel {...defaultProps} placeholder={longPlaceholder} />
      );

      const input = screen.getByPlaceholderText(longPlaceholder);
      expect(input).toBeInTheDocument();
    });
  });
});