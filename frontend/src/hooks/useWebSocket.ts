/**
 * React hook for WebSocket integration
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../store';
import { addMessage, updateSessionStatus } from '../store/slices/sessionSlice';
import websocketService, {
  WebSocketMessage,
  SessionStatusData,
  AgentMessageData,
  UserInputData,
  ClarifyingQuestionData,
  ErrorData
} from '../services/websocketService';

interface UseWebSocketOptions {
  autoConnect?: boolean;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
  onSessionStatus?: (data: SessionStatusData) => void;
  onAgentMessage?: (data: AgentMessageData) => void;
  onUserInput?: (data: UserInputData) => void;
  onClarifyingQuestion?: (data: ClarifyingQuestionData) => void;
  onError?: (data: ErrorData) => void;
}

interface UseWebSocketReturn {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  sendUserInput: (input: string, type?: string) => boolean;
  sendContinueWithoutInput: () => boolean;
  disconnect: () => void;
  reconnect: () => Promise<boolean>;
  status: any;
}

export const useWebSocket = (
  sessionId: string | null,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn => {
  const dispatch = useDispatch();
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    autoConnect = true,
    onConnect,
    onDisconnect,
    onError: onPropError,
    onSessionStatus,
    onAgentMessage,
    onUserInput,
    onClarifyingQuestion,
    onError: onPropErrorMessage
  } = options;

  const optionsRef = useRef(options);
  optionsRef.current = options;

  // Memoize event handlers
  const handleConnect = useCallback(() => {
    setConnected(true);
    setConnecting(false);
    setError(null);
    optionsRef.current.onConnect?.();
  }, []);

  const handleDisconnect = useCallback((event: CloseEvent) => {
    setConnected(false);
    setConnecting(false);
    optionsRef.current.onDisconnect?.();

    // Log disconnect reason
    if (event.code !== 1000) {
      console.warn(`WebSocket disconnected unexpectedly: ${event.code} - ${event.reason}`);
    }
  }, []);

  const handleError = useCallback((error: Event) => {
    setConnecting(false);
    setError('WebSocket connection error');
    const errorObj = new Error('WebSocket connection error');
    optionsRef.current.onError?.(errorObj);
  }, []);

  const handleSessionStatus = useCallback((data: SessionStatusData) => {
    // Update Redux store
    if (data.session_id === sessionId) {
      dispatch(updateSessionStatus({
        id: data.session_id,
        status: data.status
      }));
    }

    optionsRef.current.onSessionStatus?.(data);
  }, [sessionId, dispatch]);

  const handleAgentMessage = useCallback((data: AgentMessageData) => {
    // Update Redux store
    if (data.session_id === sessionId && data.message) {
      dispatch(addMessage({
        id: data.message.id,
        session_id: data.session_id,
        agent_type: data.message.agent_type,
        message_content: data.message.message_content,
        message_type: data.message.message_type,
        sequence_number: data.message.sequence_number,
        parent_message_id: null,
        created_at: data.message.created_at,
        processing_time_ms: data.message.processing_time_ms || null,
        metadata: {}
      }));
    }

    optionsRef.current.onAgentMessage?.(data);
  }, [sessionId, dispatch]);

  const handleUserInput = useCallback((data: UserInputData) => {
    optionsRef.current.onUserInput?.(data);
  }, []);

  const handleClarifyingQuestion = useCallback((data: ClarifyingQuestionData) => {
    optionsRef.current.onClarifyingQuestion?.(data);
  }, []);

  const handleErrorMessage = useCallback((data: ErrorData) => {
    setError(data.message);
    optionsRef.current.onError?.(data);
  }, []);

  // Setup WebSocket event listeners
  useEffect(() => {
    if (!sessionId) return;

    const service = websocketService;

    // Set event listeners
    service.setOnOpen(handleConnect);
    service.setOnClose(handleDisconnect);
    service.SetOnError(handleError);

    // Set message type handlers
    service.onMessageType('session_status', handleSessionStatus);
    service.onMessageType('agent_message', handleAgentMessage);
    service.onMessageType('user_input', handleUserInput);
    service.onMessageType('clarifying_question', handleClarifyingQuestion);
    service.onMessageType('error', handleErrorMessage);

    // Cleanup function
    return () => {
      service.setOnOpen(null);
      service.setOnClose(null);
      service.SetOnError(null);
      // Note: We don't remove message type handlers here as they might be used by other components
    };
  }, [
    sessionId,
    handleConnect,
    handleDisconnect,
    handleError,
    handleSessionStatus,
    handleAgentMessage,
    handleUserInput,
    handleClarifyingQuestion,
    handleErrorMessage
  ]);

  // Auto-connect when sessionId changes
  useEffect(() => {
    if (!sessionId || !autoConnect) return;

    const connect = async () => {
      try {
        setConnecting(true);
        setError(null);
        await websocketService.connect(sessionId);
      } catch (error) {
        setConnecting(false);
        setError('Failed to connect to WebSocket');
        console.error('WebSocket connection failed:', error);
      }
    };

    connect();

    // Cleanup on unmount
    return () => {
      if (websocketService.getStatus().sessionId === sessionId) {
        websocketService.disconnect();
      }
    };
  }, [sessionId, autoConnect]);

  // Send user input
  const sendUserInput = useCallback((input: string, type: string = 'supplementary'): boolean => {
    if (!input.trim()) {
      return false;
    }

    return websocketService.sendUserInput(input, type);
  }, []);

  // Send continue without input
  const sendContinueWithoutInput = useCallback((): boolean => {
    return websocketService.sendContinueWithoutInput();
  }, []);

  // Manual disconnect
  const disconnect = useCallback(() => {
    websocketService.disconnect();
  }, []);

  // Manual reconnect
  const reconnect = useCallback(async (): Promise<boolean> => {
    if (!sessionId) return false;

    try {
      setConnecting(true);
      setError(null);
      await websocketService.connect(sessionId);
      return true;
    } catch (error) {
      setConnecting(false);
      setError('Failed to reconnect to WebSocket');
      return false;
    }
  }, [sessionId]);

  // Get current status
  const status = websocketService.getStatus();

  return {
    connected,
    connecting,
    error,
    sendUserInput,
    sendContinueWithoutInput,
    disconnect,
    reconnect,
    status
  };
};

/**
 * Hook for managing WebSocket connection with automatic reconnection
 */
export const useWebSocketWithReconnect = (
  sessionId: string | null,
  options: UseWebSocketOptions = {}
) => {
  const ws = useWebSocket(sessionId, options);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Enhanced error handling with reconnection
  useEffect(() => {
    if (ws.error && !ws.connected && !ws.connecting && sessionId) {
      const attemptReconnect = async () => {
        setReconnectAttempts(prev => prev + 1);
        const success = await ws.reconnect();
        if (success) {
          setReconnectAttempts(0);
        }
      };

      // Only attempt reconnect a few times
      if (reconnectAttempts < 3) {
        const timer = setTimeout(attemptReconnect, 2000 * Math.pow(2, reconnectAttempts));
        return () => clearTimeout(timer);
      }
    } else if (ws.connected) {
      setReconnectAttempts(0);
    }
  }, [ws.error, ws.connected, ws.connecting, sessionId, reconnectAttempts, ws.reconnect]);

  return {
    ...ws,
    reconnectAttempts
  };
};

export default useWebSocket;