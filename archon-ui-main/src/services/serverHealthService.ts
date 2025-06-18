import { credentialsService } from './credentialsService';

interface HealthCheckCallback {
  onDisconnected: () => void;
  onReconnected: () => void;
}

class ServerHealthService {
  private healthCheckInterval: number | null = null;
  private wsHealthInterval: number | null = null;
  private isConnected: boolean = true;
  private missedPings: number = 0;
  private callbacks: HealthCheckCallback | null = null;
  private ws: WebSocket | null = null;
  private reconnectTimeout: number | null = null;

  // Settings
  private disconnectScreenEnabled: boolean = true;
  private disconnectScreenDelay: number = 10000; // 10 seconds

  async loadSettings() {
    try {
      // Load disconnect screen settings from API
      const enabledRes = await credentialsService.getCredential('DISCONNECT_SCREEN_ENABLED').catch(() => ({ value: 'true' }));
      this.disconnectScreenEnabled = enabledRes.value === 'true';
    } catch (error) {
      console.error('Failed to load disconnect screen settings:', error);
    }
  }

  async updateSettings(enabled: boolean) {
    this.disconnectScreenEnabled = enabled;

    // Save to backend
    try {
      await credentialsService.createCredential({
        key: 'DISCONNECT_SCREEN_ENABLED',
        value: enabled.toString(),
        is_encrypted: false,
        category: 'features',
        description: 'Enable disconnect screen when server is disconnected'
      });
    } catch (error) {
      console.error('Failed to save disconnect screen settings:', error);
    }
  }

  getSettings() {
    return {
      enabled: this.disconnectScreenEnabled,
      delay: this.disconnectScreenDelay
    };
  }

  startMonitoring(callbacks: HealthCheckCallback) {
    this.callbacks = callbacks;
    this.missedPings = 0;
    this.isConnected = true;

    // Load settings first
    this.loadSettings();

    // Start WebSocket health monitoring
    this.connectWebSocket();

    // Disable HTTP health check - rely on WebSocket only
    // Fallback HTTP health check every 2 seconds
    // this.healthCheckInterval = window.setInterval(() => {
    //   this.checkHealth();
    // }, 2000);
  }

  private connectWebSocket() {
    try {
      // Connect directly to the FastAPI server WebSocket endpoint
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // Use port 8080 directly for the FastAPI server
      const wsUrl = `${wsProtocol}//localhost:8080/ws/health`;
      
      console.log('Attempting to connect health WebSocket:', wsUrl);
      this.ws = new WebSocket(wsUrl);

      // Track ping/pong responses
      let lastPongReceived = Date.now();

      this.ws.onopen = () => {
        console.log('Health WebSocket connected');
        this.missedPings = 0;
        lastPongReceived = Date.now();
        this.handleConnectionRestored();

        // Send ping every 2 seconds and check for pong responses
        this.wsHealthInterval = window.setInterval(() => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            // Check if we've received a pong recently (within 6 seconds)
            const timeSinceLastPong = Date.now() - lastPongReceived;
            if (timeSinceLastPong > 6000) {
              // No pong received in 6 seconds, count as missed ping
              this.handleMissedPing();
            }
            
            // Send new ping
            this.ws.send(JSON.stringify({ type: 'ping' }));
          } else {
            // WebSocket not open, count as missed ping
            this.handleMissedPing();
          }
        }, 2000);
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'pong') {
            lastPongReceived = Date.now();
            this.missedPings = 0;
            this.handleConnectionRestored();
          }
        } catch (error) {
          console.error('Failed to parse health message:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('Health WebSocket disconnected', { code: event.code, reason: event.reason });
        
        // Count disconnection as missed pings
        this.handleMissedPing();
        
        if (this.wsHealthInterval) {
          window.clearInterval(this.wsHealthInterval);
          this.wsHealthInterval = null;
        }

        // Only try to reconnect if it wasn't a normal closure
        if (event.code !== 1000) {
          // Try to reconnect after 5 seconds
          this.reconnectTimeout = window.setTimeout(() => {
            this.connectWebSocket();
          }, 5000);
        }
      };

      this.ws.onerror = (error) => {
        console.error('Health WebSocket error:', error);
        // Count errors as missed pings
        this.handleMissedPing();
      };
    } catch (error) {
      console.error('Failed to connect health WebSocket:', error);
      // Count connection failure as missed ping
      this.handleMissedPing();
      
      // Try to reconnect after 5 seconds
      this.reconnectTimeout = window.setTimeout(() => {
        this.connectWebSocket();
      }, 5000);
    }
  }

  private async checkHealth() {
    try {
      // Use the same API pattern as other services - relative URL that gets proxied
      const response = await fetch('/api/health', {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
        // Add cache control to prevent cached responses
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });

      if (response.ok) {
        const data = await response.json();
        // Check for actual health status
        if (data.ready === true || data.status === 'healthy') {
          this.missedPings = 0;
          this.handleConnectionRestored();
        } else {
          // Server is starting up
          this.handleMissedPing();
        }
      } else {
        this.handleMissedPing();
      }
    } catch (error) {
      // Only count as missed ping if it's a network error
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        this.handleMissedPing();
      } else {
        console.warn('Health check error (not counting as disconnect):', error);
      }
    }
  }

  private handleMissedPing() {
    this.missedPings++;
    console.log(`Missed ping ${this.missedPings}/5`);
    
    // After 5 missed pings (10 seconds), trigger disconnect screen
    if (this.missedPings >= 5 && this.isConnected) {
      this.isConnected = false;
      if (this.disconnectScreenEnabled && this.callbacks) {
        console.log('Triggering disconnect screen after 5 missed pings');
        this.callbacks.onDisconnected();
      }
    }
  }

  private handleConnectionRestored() {
    if (!this.isConnected) {
      this.isConnected = true;
      if (this.callbacks) {
        this.callbacks.onReconnected();
      }
    }
  }

  stopMonitoring() {
    if (this.healthCheckInterval) {
      window.clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }

    if (this.wsHealthInterval) {
      window.clearInterval(this.wsHealthInterval);
      this.wsHealthInterval = null;
    }

    if (this.reconnectTimeout) {
      window.clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.callbacks = null;
  }

  isServerConnected() {
    return this.isConnected;
  }
}

export const serverHealthService = new ServerHealthService();