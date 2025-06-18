import { credentialsService } from './credentialsService';

interface HealthCheckCallback {
  onDisconnected: () => void;
  onReconnected: () => void;
}

class ServerHealthService {
  private healthCheckInterval: number | null = null;
  private isConnected: boolean = true;
  private missedChecks: number = 0;
  private callbacks: HealthCheckCallback | null = null;

  // Settings
  private disconnectScreenEnabled: boolean = true;
  private disconnectScreenDelay: number = 10000; // 10 seconds
  private maxMissedChecks: number = 3; // Show disconnect after 3 missed checks
  private checkInterval: number = 3000; // Check every 3 seconds

  async loadSettings() {
    try {
      // Load disconnect screen settings from API
      const enabledRes = await credentialsService.getCredential('DISCONNECT_SCREEN_ENABLED').catch(() => ({ value: 'true' }));
      this.disconnectScreenEnabled = enabledRes.value === 'true';
    } catch (error) {
      console.error('Failed to load disconnect screen settings:', error);
    }
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch('http://localhost:8080/health', {
        method: 'GET',
        signal: AbortSignal.timeout(5000) // 5 second timeout
      });
      
      if (response.ok) {
        const data = await response.json();
        return data.status === 'healthy' || data.status === 'online';
      }
      return false;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }

  startMonitoring(callbacks: HealthCheckCallback) {
    this.callbacks = callbacks;
    this.missedChecks = 0;
    this.isConnected = true;

    // Load settings first
    this.loadSettings();

    // Start HTTP health polling
    this.healthCheckInterval = window.setInterval(async () => {
      const isHealthy = await this.checkHealth();
      
      if (isHealthy) {
        // Server is healthy
        if (this.missedChecks > 0) {
          // Was disconnected, now reconnected
          this.missedChecks = 0;
          this.handleConnectionRestored();
        }
      } else {
        // Server is not responding
        this.missedChecks++;
        console.log(`Health check failed ${this.missedChecks}/${this.maxMissedChecks}`);
        
        // After maxMissedChecks failures, trigger disconnect screen
        if (this.missedChecks >= this.maxMissedChecks && this.isConnected) {
          this.isConnected = false;
          if (this.disconnectScreenEnabled && this.callbacks) {
            console.log('Triggering disconnect screen after multiple health check failures');
            this.callbacks.onDisconnected();
          }
        }
      }
    }, this.checkInterval);

    // Do an immediate check
    this.checkHealth().then(isHealthy => {
      if (!isHealthy) {
        this.missedChecks = 1;
      }
    });
  }

  private handleConnectionRestored() {
    if (!this.isConnected) {
      this.isConnected = true;
      console.log('Connection to server restored');
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
    this.callbacks = null;
  }

  isServerConnected(): boolean {
    return this.isConnected;
  }

  getSettings() {
    return {
      enabled: this.disconnectScreenEnabled,
      delay: this.disconnectScreenDelay
    };
  }

  async updateSettings(settings: { enabled?: boolean; delay?: number }) {
    if (settings.enabled !== undefined) {
      this.disconnectScreenEnabled = settings.enabled;
      await credentialsService.createCredential({
        key: 'DISCONNECT_SCREEN_ENABLED',
        value: settings.enabled.toString(),
        is_encrypted: false,
        category: 'features',
        description: 'Enable disconnect screen when server is disconnected'
      });
    }
    
    if (settings.delay !== undefined) {
      this.disconnectScreenDelay = settings.delay;
      // You could save this to credentials as well if needed
    }
  }
}

export const serverHealthService = new ServerHealthService();