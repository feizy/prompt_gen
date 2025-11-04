/**
 * WebSocket service for real-time session updates
 */

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp?: string;
}

export interface SessionStatusData {
  session_id: string;
  status: string;
  iteration_count: number;
  user_intervention_count: number;
  created_at: string;
  updated_at: string;
  waiting_for_user_since?: string;
  final_prompt?: string;
  next_agent?: string;
  requires_user_input?: boolean;
  completed?: boolean;
  agent_responses?: any;
}

export interface AgentMessageData {
  session_id: string;
  message: {
    id: string;
    agent_type: 'product_manager' | 'technical_developer' | 'team_lead';
    message_content: string;
    message_type: string;
    sequence_number: number;
    created_at: string;
    processing_time_ms?: number;
  };
  messages?: any[];
}

export interface UserInputData {
  session_id: string;
  user_input: {
    id: string;
    input_content: string;
    input_type: string;
    provided_at: string;
  };
  response?: any;
}

export interface ClarifyingQuestionData {
  session_id: string;
  question: {
    id: string;
    question_text: string;
    question_type: string;
    priority: number;
    asked_at: string;
    status: string;
    response_text?: string;
  };
}

export interface ErrorData {
  session_id: string;
  message: string;
  details?: any;
}

type MessageHandler = (data: any) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isConnecting = false;
  private isManualClose = false;
  private pingInterval: NodeJS.Timeout | null = null;
  private messageHandlers: Map<string, MessageHandler[]> = new Map();

  // Event listeners
  private onOpen: (() => void) | null = null;
  private onClose: ((event: CloseEvent) => void) | null = null;
  private onError: ((error: Event) => void) | null = null;
  private onMessage: ((message: WebSocketMessage) => void) | null = null;

  /**
   * Connect to WebSocket for a specific session
   */
  async connect(sessionId: string): Promise<boolean> {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return true;
    }

    this.sessionId = sessionId;
    this.isManualClose = false;
    this.isConnecting = true;

    try {
      // Construct WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/sessions/${sessionId}`;

      console.log(`Connecting to WebSocket: ${wsUrl}`);

      this.ws = new WebSocket(wsUrl);

      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          this.isConnecting = false;
          reject(new Error('WebSocket connection timeout'));
        }, 10000);

        this.ws!.onopen = (event) => {
          clearTimeout(timeout);
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          console.log('WebSocket connected');

          // Start ping interval
          this.startPingInterval();

          this.onOpen?.();
          resolve(true);
        };

        this.ws!.onclose = (event) => {
          clearTimeout(timeout);
          this.isConnecting = false;
          this.stopPingInterval();

          console.log(`WebSocket closed: ${event.code} - ${event.reason}`);

          if (!this.isManualClose && this.shouldReconnect()) {
            this.scheduleReconnect();
          }

          this.onClose?.(event);
        };

        this.ws!.onerror = (error) => {
          clearTimeout(timeout);
          this.isConnecting = false;
          console.error('WebSocket error:', error);
          this.onError?.(error);
          reject(error);
        };

        this.ws!.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
            this.onMessage?.(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };
      });

    } catch (error) {
      this.isConnecting = false;
      console.error('Failed to create WebSocket connection:', error);
      throw error;
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.isManualClose = true;
    this.stopPingInterval();

    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }

    this.sessionId = null;
    this.reconnectAttempts = 0;
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Send a message through WebSocket
   */
  send(type: string, data: any): boolean {
    if (!this.isConnected()) {
      console.warn('WebSocket not connected, cannot send message');
      return false;
    }

    try {
      const message: WebSocketMessage = {
        type,
        data,
        timestamp: new Date().toISOString()
      };

      this.ws!.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      return false;
    }
  }

  /**
   * Send user input
   */
  sendUserInput(inputContent: string, inputType: string = 'supplementary'): boolean {
    return this.send('user_input', {
      input_content: inputContent,
      input_type: inputType
    });
  }

  /**
   * Send continue without input
   */
  sendContinueWithoutInput(): boolean {
    return this.send('continue_without_input', {});
  }

  /**
   * Send ping message
   */
  private sendPing(): void {
    this.send('ping', {});
  }

  /**
   * Register a message handler for a specific message type
   */
  onMessageType(type: string, handler: MessageHandler): void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    this.messageHandlers.get(type)!.push(handler);
  }

  /**
   * Remove a message handler
   */
  offMessageType(type: string, handler: MessageHandler): void {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  /**
   * Set event listeners
   */
  setOnOpen(handler: () => void): void {
    this.onOpen = handler;
  }

  setOnClose(handler: (event: CloseEvent) => void): void {
    this.onClose = handler;
  }

  setOnError(handler: (error: Event) => void): void {
    this.onError = handler;
  }

  setOnMessage(handler: (message: WebSocketMessage) => void): void {
    this.onMessage = handler;
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(message: WebSocketMessage): void {
    const { type, data } = message;

    // Call specific type handlers
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in WebSocket message handler for type ${type}:`, error);
        }
      });
    }

    // Handle built-in message types
    switch (type) {
      case 'pong':
        // Pong received, connection is alive
        break;

      case 'error':
        console.error('WebSocket error message:', data);
        break;

      default:
        // Log unknown message types
        if (!this.messageHandlers.has(type)) {
          console.log(`Unhandled WebSocket message type: ${type}`, data);
        }
    }
  }

  /**
   * Start ping interval to keep connection alive
   */
  private startPingInterval(): void {
    this.stopPingInterval();
    this.pingInterval = setInterval(() => {
      if (this.isConnected()) {
        this.sendPing();
      }
    }, 30000); // Send ping every 30 seconds
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Check if we should attempt to reconnect
   */
  private shouldReconnect(): boolean {
    return this.reconnectAttempts < this.maxReconnectAttempts && !this.isManualClose;
  }

  /**
   * Schedule a reconnection attempt
   */
  private scheduleReconnect(): void {
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;

    console.log(`Scheduling WebSocket reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);

    setTimeout(async () => {
      if (this.sessionId && this.shouldReconnect()) {
        try {
          await this.connect(this.sessionId);
        } catch (error) {
          console.error('WebSocket reconnection failed:', error);
          if (this.shouldReconnect()) {
            this.scheduleReconnect();
          }
        }
      }
    }, delay);
  }

  /**
   * Get connection status
   */
  getStatus(): {
    connected: boolean;
    connecting: boolean;
    sessionId: string | null;
    reconnectAttempts: number;
  } {
    return {
      connected: this.isConnected(),
      connecting: this.isConnecting,
      sessionId: this.sessionId,
      reconnectAttempts: this.reconnectAttempts
    };
  }
}

// Create singleton instance
const websocketService = new WebSocketService();

export default websocketService;