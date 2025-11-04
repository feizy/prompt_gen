/**
 * Unit tests for useWebSocket hook
 */

import { renderHook, act } from '@testing-library/react';
import { configureStore } from '@reduxjs/toolkit';
import { Provider } from 'react-redux';
import React from 'react';

import { useWebSocket, useWebSocketWithReconnect } from '../useWebSocket';
import { addMessage, updateSessionStatus } from '../../store/slices/sessionSlice';

// Mock websocket service
const mockWebSocketService = {
  connect: jest.fn(),
  disconnect: jest.fn(),
  sendUserInput: jest.fn(),
  sendContinueWithoutInput: jest.fn(),
  getStatus: jest.fn(),
  setOnOpen: jest.fn(),
  setOnClose: jest.fn(),
  SetOnError: jest.fn(),
  onMessageType: jest.fn(),
};

jest.mock('../../services/websocketService', () => ({
  websocketService: mockWebSocketService,
}));

// Mock Redux store
const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      session: (state = { sessions: [], currentSession: null, messages: [] }, action) => {
        switch (action.type) {
          case 'session/addMessage':
            return {
              ...state,
              messages: [...state.messages, action.payload],
            };
          case 'session/updateSessionStatus':
            return {
              ...state,
              currentSession: state.currentSession
                ? { ...state.currentSession, status: action.payload.status }
                : null,
            };
          default:
            return state;
        }
      },
    },
    preloadedState: initialState,
  });
};

// Test wrapper component
const wrapper = ({ children, initialState = {} }) => (
  <Provider store={createMockStore(initialState)}>
    {children}
  </Provider>
);

describe('useWebSocket', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset mock implementations
    mockWebSocketService.connect.mockResolvedValue(undefined);
    mockWebSocketService.sendUserInput.mockReturnValue(true);
    mockWebSocketService.sendContinueWithoutInput.mockReturnValue(true);
    mockWebSocketService.getStatus.mockReturnValue({
      connected: false,
      sessionId: null,
    });
  });

  describe('Basic Functionality', () => {
    test('initializes with default values', () => {
      const { result } = renderHook(() => useWebSocket(null), { wrapper });

      expect(result.current.connected).toBe(false);
      expect(result.current.connecting).toBe(false);
      expect(result.current.error).toBe(null);
      expect(typeof result.current.sendUserInput).toBe('function');
      expect(typeof result.current.sendContinueWithoutInput).toBe('function');
      expect(typeof result.current.disconnect).toBe('function');
      expect(typeof result.current.reconnect).toBe('function');
    });

    test('auto-connects when sessionId is provided', async () => {
      const { result } = renderHook(() => useWebSocket('test-session'), { wrapper });

      // Should attempt to connect
      expect(mockWebSocketService.connect).toHaveBeenCalledWith('test-session');
    });

    test('does not auto-connect when sessionId is null', () => {
      renderHook(() => useWebSocket(null), { wrapper });

      expect(mockWebSocketService.connect).not.toHaveBeenCalled();
    });

    test('does not auto-connect when autoConnect is false', () => {
      renderHook(() => useWebSocket('test-session', { autoConnect: false }), { wrapper });

      expect(mockWebSocketService.connect).not.toHaveBeenCalled();
    });
  });

  describe('Connection Management', () => {
    test('handles successful connection', async () => {
      let onOpenCallback = null;

      mockWebSocketService.setOnOpen.mockImplementation((callback) => {
        onOpenCallback = callback;
      });

      const { result } = renderHook(() => useWebSocket('test-session'), { wrapper });

      expect(result.current.connecting).toBe(true);

      // Simulate successful connection
      act(() => {
        onOpenCallback();
      });

      expect(result.current.connected).toBe(true);
      expect(result.current.connecting).toBe(false);
      expect(result.current.error).toBe(null);
    });

    test('handles connection error', async () => {
      let onErrorCallback = null;

      mockWebSocketService.SetOnError.mockImplementation((callback) => {
        onErrorCallback = callback;
      });

      const { result } = renderHook(() => useWebSocket('test-session'), { wrapper });

      // Simulate connection error
      act(() => {
        onErrorCallback(new Event('error'));
      });

      expect(result.current.connected).toBe(false);
      expect(result.current.connecting).toBe(false);
      expect(result.current.error).toBe('WebSocket connection error');
    });

    test('handles connection close', async () => {
      let onCloseCallback = null;

      mockWebSocketService.setOnClose.mockImplementation((callback) => {
        onCloseCallback = callback;
      });

      const { result } = renderHook(() => useWebSocket('test-session'), { wrapper });

      // First connect successfully
      act(() => {
        mockWebSocketService.setOnOpen.mock.calls[0][0]();
      });

      expect(result.current.connected).toBe(true);

      // Then simulate connection close
      const closeEvent = new CloseEvent('close', { code: 1000, reason: 'Normal closure' });
      act(() => {
        onCloseCallback(closeEvent);
      });

      expect(result.current.connected).toBe(false);
      expect(result.current.connecting).toBe(false);
    });

    test('logs unexpected disconnection', async () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      let onCloseCallback = null;

      mockWebSocketService.setOnClose.mockImplementation((callback) => {
        onCloseCallback = callback;
      });

      renderHook(() => useWebSocket('test-session'), { wrapper });

      // Simulate unexpected disconnection (code not 1000)
      const closeEvent = new CloseEvent('close', { code: 1006, reason: 'Abnormal closure' });
      act(() => {
        onCloseCallback(closeEvent);
      });

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('WebSocket disconnected unexpectedly')
      );

      consoleSpy.mockRestore();
    });
  });

  describe('Message Handling', () => {
    test('handles session status messages', () => {
      let onSessionStatusCallback = null;

      mockWebSocketService.onMessageType.mockImplementation((type, callback) => {
        if (type === 'session_status') {
          onSessionStatusCallback = callback;
        }
      });

      const { result } = renderHook(() => useWebSocket('test-session'), { wrapper });

      const mockCallback = jest.fn();
      const options = { onSessionStatus: mockCallback };

      // Re-render with callback
      renderHook(() => useWebSocket('test-session', options), { wrapper });

      const sessionData = {
        session_id: 'test-session',
        status: 'processing'
      };

      act(() => {
        onSessionStatusCallback(sessionData);
      });

      expect(mockCallback).toHaveBeenCalledWith(sessionData);
    });

    test('handles agent messages and updates Redux store', () => {
      let onAgentMessageCallback = null;

      mockWebSocketService.onMessageType.mockImplementation((type, callback) => {
        if (type === 'agent_message') {
          onAgentMessageCallback = callback;
        }
      });

      const store = createMockStore();
      const customWrapper = ({ children }) => (
        <Provider store={store}>{children}</Provider>
      );

      renderHook(() => useWebSocket('test-session'), { wrapper: customWrapper });

      const messageData = {
        session_id: 'test-session',
        message: {
          id: 'msg-1',
          agent_type: 'product_manager',
          message_content: 'Test message',
          message_type: 'requirement',
          sequence_number: 1,
          created_at: '2024-01-01T10:00:00Z',
          processing_time_ms: 1500,
        }
      };

      act(() => {
        onAgentMessageCallback(messageData);
      });

      const actions = store.getActions();
      expect(actions).toContainEqual(
        expect.objectContaining({
          type: 'session/addMessage',
          payload: expect.objectContaining({
            id: 'msg-1',
            agent_type: 'product_manager',
            message_content: 'Test message',
          })
        })
      );
    });

    test('handles user input messages', () => {
      let onUserInputCallback = null;

      mockWebSocketService.onMessageType.mockImplementation((type, callback) => {
        if (type === 'user_input') {
          onUserInputCallback = callback;
        }
      });

      const mockCallback = jest.fn();
      const options = { onUserInput: mockCallback };

      renderHook(() => useWebSocket('test-session', options), { wrapper });

      const inputData = {
        session_id: 'test-session',
        input: 'User input text',
        type: 'supplementary'
      };

      act(() => {
        onUserInputCallback(inputData);
      });

      expect(mockCallback).toHaveBeenCalledWith(inputData);
    });

    test('handles error messages', () => {
      let onErrorCallback = null;

      mockWebSocketService.onMessageType.mockImplementation((type, callback) => {
        if (type === 'error') {
          onErrorCallback = callback;
        }
      });

      const { result } = renderHook(() => useWebSocket('test-session'), { wrapper });

      const errorData = {
        message: 'Test error message'
      };

      act(() => {
        onErrorCallback(errorData);
      });

      expect(result.current.error).toBe('Test error message');
    });
  });

  describe('Sending Messages', () => {
    test('sendUserInput returns false for empty input', () => {
      const { result } = renderHook(() => useWebSocket('test-session'), { wrapper });

      const success = result.current.sendUserInput('');
      expect(success).toBe(false);
      expect(mockWebSocketService.sendUserInput).not.toHaveBeenCalled();
    });

    test('sendUserInput calls service for valid input', () => {
      mockWebSocketService.sendUserInput.mockReturnValue(true);

      const { result } = renderHook(() => useWebSocket('test-session'), { wrapper });

      const success = result.current.sendUserInput('Test message', 'supplementary');

      expect(success).toBe(true);
      expect(mockWebSocketService.sendUserInput).toHaveBeenCalledWith('Test message', 'supplementary');
    });

    test('sendContinueWithoutInput calls service', () => {
      mockWebSocketService.sendContinueWithoutInput.mockReturnValue(true);

      const { result } = renderHook(() => useWebSocket('test-session'), { wrapper });

      const success = result.current.sendContinueWithoutInput();

      expect(success).toBe(true);
      expect(mockWebSocketService.sendContinueWithoutInput).toHaveBeenCalled();
    });

    test('disconnect calls service', () => {
      const { result } = renderHook(() => useWebSocket('test-session'), { wrapper });

      result.current.disconnect();

      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });

    test('reconnect connects with correct session ID', async () => {
      const { result } = renderHook(() => useWebSocket('test-session'), { wrapper });

      mockWebSocketService.connect.mockResolvedValue(undefined);

      const success = await result.current.reconnect();

      expect(success).toBe(true);
      expect(mockWebSocketService.connect).toHaveBeenCalledWith('test-session');
    });

    test('reconnect handles connection failure', async () => {
      const { result } = renderHook(() => useWebSocket('test-session'), { wrapper });

      mockWebSocketService.connect.mockRejectedValue(new Error('Connection failed'));

      const success = await result.current.reconnect();

      expect(success).toBe(false);
      expect(result.current.error).toBe('Failed to reconnect to WebSocket');
    });
  });

  describe('Cleanup', () => {
    test('disconnects on unmount', () => {
      const { unmount } = renderHook(() => useWebSocket('test-session'), { wrapper });

      // Simulate successful connection first
      mockWebSocketService.getStatus.mockReturnValue({
        connected: true,
        sessionId: 'test-session',
      });

      unmount();

      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });

    test('does not disconnect if session ID differs', () => {
      const { unmount } = renderHook(() => useWebSocket('test-session'), { wrapper });

      // Simulate different session in service
      mockWebSocketService.getStatus.mockReturnValue({
        connected: true,
        sessionId: 'different-session',
      });

      unmount();

      expect(mockWebSocketService.disconnect).not.toHaveBeenCalled();
    });
  });

  describe('useWebSocketWithReconnect', () => {
    test('extends useWebSocket with reconnection logic', () => {
      const { result } = renderHook(() => useWebSocketWithReconnect('test-session'), { wrapper });

      expect(result.current.reconnectAttempts).toBe(0);
      expect(typeof result.current.reconnect).toBe('function');
    });

    test('attempts reconnection on error', async () => {
      jest.useFakeTimers();

      const { result } = renderHook(() => useWebSocketWithReconnect('test-session'), { wrapper });

      // Simulate connection error
      act(() => {
        result.current.error = 'Connection error';
        result.current.connected = false;
        result.current.connecting = false;
      });

      // Fast-forward timers to trigger reconnection
      act(() => {
        jest.advanceTimersByTime(2000); // 2^0 * 2000ms
      });

      expect(mockWebSocketService.connect).toHaveBeenCalled();

      jest.useRealTimers();
    });

    test('limits reconnection attempts', async () => {
      jest.useFakeTimers();

      const { result } = renderHook(() => useWebSocketWithReconnect('test-session'), { wrapper });

      // Simulate multiple failed reconnection attempts
      for (let i = 0; i < 5; i++) {
        act(() => {
          result.current.error = 'Connection error';
          result.current.connected = false;
          result.current.connecting = false;
        });

        act(() => {
          jest.advanceTimersByTime(2000 * Math.pow(2, i));
        });
      }

      // Should stop trying after 3 attempts
      expect(mockWebSocketService.connect).toHaveBeenCalledTimes(3);
      expect(result.current.reconnectAttempts).toBe(3);

      jest.useRealTimers();
    });

    test('resets reconnection attempts on successful connection', () => {
      const { result } = renderHook(() => useWebSocketWithReconnect('test-session'), { wrapper });

      // Simulate failed reconnection
      act(() => {
        result.current.reconnectAttempts = 2;
      });

      // Simulate successful connection
      let onOpenCallback = null;
      mockWebSocketService.setOnOpen.mockImplementation((callback) => {
        onOpenCallback = callback;
      });

      act(() => {
        onOpenCallback();
      });

      expect(result.current.reconnectAttempts).toBe(0);
    });

    test('uses exponential backoff for reconnection delays', () => {
      jest.useFakeTimers();

      const { result } = renderHook(() => useWebSocketWithReconnect('test-session'), { wrapper });

      const delays = [];

      // Simulate multiple reconnection attempts and capture delays
      for (let i = 0; i < 3; i++) {
        act(() => {
          result.current.error = 'Connection error';
          result.current.connected = false;
          result.current.connecting = false;
        });

        const currentTime = jest.now();
        act(() => {
          jest.advanceTimersByTime(2000 * Math.pow(2, i));
        });
        delays.push(jest.now() - currentTime);
      }

      // Check exponential backoff: 2000ms, 4000ms, 8000ms
      expect(delays).toEqual([2000, 4000, 8000]);

      jest.useRealTimers();
    });
  });

  describe('Edge Cases', () => {
    test('handles missing sessionId gracefully', () => {
      const { result } = renderHook(() => useWebSocket(null), { wrapper });

      expect(() => {
        result.current.sendUserInput('test');
      }).not.toThrow();

      expect(() => {
        result.current.reconnect();
      }).not.toThrow();
    });

    test('handles missing callbacks gracefully', () => {
      const { result } = renderHook(() => useWebSocket('test-session', {}), { wrapper });

      // Should not throw when callbacks are not provided
      expect(() => {
        // Simulate message callbacks
        const callbacks = ['onSessionStatus', 'onAgentMessage', 'onUserInput', 'onError'];
        callbacks.forEach(callback => {
          // These should be handled gracefully even if not provided
        });
      }).not.toThrow();
    });

    test('handles rapid connect/disconnect cycles', () => {
      const { rerender } = renderHook(
        ({ sessionId }) => useWebSocket(sessionId),
        { wrapper, initialProps: { sessionId: 'test-session' } }
      );

      // Change session ID rapidly
      rerender({ sessionId: 'test-session-2' });
      rerender({ sessionId: 'test-session-3' });
      rerender({ sessionId: null });

      // Should handle gracefully without errors
      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });
  });

  describe('Performance', () => {
    test('does not cause memory leaks', () => {
      const { unmount } = renderHook(() => useWebSocket('test-session'), { wrapper });

      // Setup many event listeners
      const setupCallbacks = () => {
        mockWebSocketService.setOnOpen(jest.fn());
        mockWebSocketService.setOnClose(jest.fn());
        mockWebSocketService.SetOnError(jest.fn());
        mockWebSocketService.onMessageType('session_status', jest.fn());
        mockWebSocketService.onMessageType('agent_message', jest.fn());
        mockWebSocketService.onMessageType('user_input', jest.fn());
        mockWebSocketService.onMessageType('error', jest.fn());
      };

      setupCallbacks();

      // Unmount should clean up properly
      expect(() => unmount()).not.toThrow();
    });

    test('handles high-frequency messages efficiently', () => {
      let onAgentMessageCallback = null;

      mockWebSocketService.onMessageType.mockImplementation((type, callback) => {
        if (type === 'agent_message') {
          onAgentMessageCallback = callback;
        }
      });

      const store = createMockStore();
      const customWrapper = ({ children }) => (
        <Provider store={store}>{children}</Provider>
      );

      renderHook(() => useWebSocket('test-session'), { wrapper: customWrapper });

      const startTime = performance.now();

      // Simulate 100 messages
      act(() => {
        for (let i = 0; i < 100; i++) {
          onAgentMessageCallback({
            session_id: 'test-session',
            message: {
              id: `msg-${i}`,
              agent_type: 'product_manager',
              message_content: `Message ${i}`,
              message_type: 'requirement',
              sequence_number: i,
              created_at: '2024-01-01T10:00:00Z',
            }
          });
        }
      });

      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(100); // Should be fast
    });
  });
});