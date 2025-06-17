import { credentialsService } from './credentialsService';

export type ScreensaverStyle = 'quantum-flux' | 'neural-network' | 'matrix-rain';

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
  private screensaverEnabled: boolean = true;
  private screensaverStyle: ScreensaverStyle = 'quantum-flux';
  private screensaverDelay: number = 10000; // 10 seconds

  async loadSettings() {
    try {
      // Load screensaver settings from API
      const [enabledRes, styleRes] = await Promise.all([
        credentialsService.getCredential('SCREENSAVER_ENABLED').catch(() => ({ value: 'true' })),
        credentialsService.getCredential('SCREENSAVER_STYLE').catch(() => ({ value: 'quantum-flux' }))
      ]);

      this.screensaverEnabled = enabledRes.value === 'true';
      this.screensaverStyle = (styleRes.value || 'quantum-flux') as ScreensaverStyle;
    } catch (error) {
      console.error('Failed to load screensaver settings:', error);
    }
  }

  async updateSettings(enabled: boolean, style?: ScreensaverStyle) {
    this.screensaverEnabled = enabled;
    if (style) {
      this.screensaverStyle = style;
    }

    // Save to backend
    try {
      await Promise.all([
        credentialsService.createCredential({
          key: 'SCREENSAVER_ENABLED',
          value: enabled.toString(),
          is_encrypted: false,
          category: 'features',
          description: 'Enable screensaver when server is disconnected'
        }),
        style && credentialsService.createCredential({
          key: 'SCREENSAVER_STYLE',
          value: style,
          is_encrypted: false,
          category: 'features',
          description: 'Screensaver animation style'
        })
      ]);
    } catch (error) {
      console.error('Failed to save screensaver settings:', error);
    }
  }

  getSettings() {
    return {
      enabled: this.screensaverEnabled,
      style: this.screensaverStyle,
      delay: this.screensaverDelay
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

    // Fallback HTTP health check every 2 seconds
    this.healthCheckInterval = setInterval(() => {
      this.checkHealth();
    }, 2000);
  }

  private connectWebSocket() {
    try {
      // Use the same WebSocket URL pattern as other services
      const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}://${window.location.host}/ws/health`;
      
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('Health WebSocket connected');
        this.missedPings = 0;
        this.handleConnectionRestored();

        // Send ping every 2 seconds
        this.wsHealthInterval = setInterval(() => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 2000);
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'pong') {
            this.missedPings = 0;
            this.handleConnectionRestored();
          }
        } catch (error) {
          console.error('Failed to parse health message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('Health WebSocket disconnected');
        if (this.wsHealthInterval) {
          clearInterval(this.wsHealthInterval);
          this.wsHealthInterval = null;
        }

        // Try to reconnect after 5 seconds
        this.reconnectTimeout = setTimeout(() => {
          this.connectWebSocket();
        }, 5000);
      };

      this.ws.onerror = (error) => {
        console.error('Health WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to connect health WebSocket:', error);
    }
  }

  private async checkHealth() {
    try {
      const response = await fetch('/api/health', {
        method: 'GET',
        signal: AbortSignal.timeout(5000)
      });

      if (response.ok) {
        const data = await response.json();
        if (data.ready) {
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
      this.handleMissedPing();
    }
  }

  private handleMissedPing() {
    this.missedPings++;
    
    // After 5 missed pings (10 seconds), trigger screensaver
    if (this.missedPings >= 5 && this.isConnected) {
      this.isConnected = false;
      if (this.screensaverEnabled && this.callbacks) {
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
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }

    if (this.wsHealthInterval) {
      clearInterval(this.wsHealthInterval);
      this.wsHealthInterval = null;
    }

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
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