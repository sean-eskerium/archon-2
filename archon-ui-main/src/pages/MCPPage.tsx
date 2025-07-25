import { useState, useEffect, useRef } from 'react';
import { Play, Square, Copy, Clock, Server, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { motion } from 'framer-motion';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useStaggeredEntrance } from '../hooks/useStaggeredEntrance';
import { useToast } from '../contexts/ToastContext';
import { mcpServerService, ServerStatus, LogEntry, ServerConfig } from '../services/mcpServerService';
// import { MCPClients } from '../components/mcp/MCPClients'; // Commented out - feature not implemented

/**
 * MCP Dashboard Page Component
 * 
 * This is the main dashboard for managing the MCP (Model Context Protocol) server.
 * It provides a comprehensive interface for:
 * 
 * 1. Server Control Tab:
 *    - Start/stop the MCP server
 *    - Monitor server status and uptime
 *    - View and copy connection configuration
 *    - Real-time log streaming via WebSocket
 *    - Historical log viewing and clearing
 * 
 * 2. MCP Clients Tab:
 *    - Interactive client management interface
 *    - Tool discovery and testing
 *    - Real-time tool execution
 *    - Parameter input and result visualization
 * 
 * The page uses a tab-based layout with preserved server functionality
 * and enhanced client management capabilities.
 * 
 * @component
 */
export const MCPPage = () => {
  const [serverStatus, setServerStatus] = useState<ServerStatus>({
    status: 'stopped',
    uptime: null,
    logs: []
  });
  const [config, setConfig] = useState<ServerConfig | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [selectedIDE, setSelectedIDE] = useState<'windsurf' | 'cursor' | 'claudecode'>('windsurf');
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const statusPollInterval = useRef<NodeJS.Timeout | null>(null);
  const { showToast } = useToast();

  // Tab state for switching between Server Control and Clients
  const [activeTab, setActiveTab] = useState<'server' | 'clients'>('server');

  // Use staggered entrance animation
  const { isVisible, containerVariants, itemVariants, titleVariants } = useStaggeredEntrance(
    [1, 2, 3],
    0.15
  );

  // Load initial status and start polling
  useEffect(() => {
    loadStatus();
    loadConfiguration();

    // Start polling for status updates every 5 seconds
    statusPollInterval.current = setInterval(loadStatus, 5000);

    return () => {
      if (statusPollInterval.current) {
        clearInterval(statusPollInterval.current);
      }
      mcpServerService.disconnectLogs();
    };
  }, []);


  // Start WebSocket connection when server is running
  useEffect(() => {
    if (serverStatus.status === 'running') {
      // Fetch historical logs first (last 100 entries)
      mcpServerService.getLogs({ limit: 100 }).then(historicalLogs => {
        setLogs(historicalLogs);
      }).catch(console.error);

      // Then start streaming new logs via WebSocket
      mcpServerService.streamLogs((log) => {
        setLogs(prev => [...prev, log]);
      }, { autoReconnect: true });
      
      // Ensure configuration is loaded when server is running
      if (!config) {
        loadConfiguration();
      }
    } else {
      mcpServerService.disconnectLogs();
    }
  }, [serverStatus.status]);

  // Auto-scroll logs to bottom when new logs arrive
  useEffect(() => {
    if (logsContainerRef.current && logsEndRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs]);

  /**
   * Load the current MCP server status
   * Called on mount and every 5 seconds via polling
   */
  const loadStatus = async () => {
    try {
      const status = await mcpServerService.getStatus();
      setServerStatus(status);
      setIsLoading(false);
    } catch (error) {
      console.error('Failed to load server status:', error);
      setIsLoading(false);
    }
  };

  /**
   * Load the MCP server configuration
   * Falls back to default values if database load fails
   */
  const loadConfiguration = async () => {
    try {
      const cfg = await mcpServerService.getConfiguration();
      console.log('Loaded configuration:', cfg);
      setConfig(cfg);
    } catch (error) {
      console.error('Failed to load configuration:', error);
      // Set a default config if loading fails
      setConfig({
        transport: 'http',
        host: 'localhost',
        port: 8051
      });
    }
  };


  /**
   * Start the MCP server
   */
  const handleStartServer = async () => {
    try {
      setIsStarting(true);
      const response = await mcpServerService.startServer();
      showToast(response.message, 'success');
      // Immediately refresh status
      await loadStatus();
    } catch (error: any) {
      showToast(error.message || 'Failed to start server', 'error');
    } finally {
      setIsStarting(false);
    }
  };

  const handleStopServer = async () => {
    try {
      setIsStopping(true);
      const response = await mcpServerService.stopServer();
      showToast(response.message, 'success');
      // Clear logs when server stops
      setLogs([]);
      // Immediately refresh status
      await loadStatus();
    } catch (error: any) {
      showToast(error.message || 'Failed to stop server', 'error');
    } finally {
      setIsStopping(false);
    }
  };

  const handleClearLogs = async () => {
    try {
      await mcpServerService.clearLogs();
      setLogs([]);
      showToast('Logs cleared', 'success');
    } catch (error) {
      showToast('Failed to clear logs', 'error');
    }
  };

  const handleCopyConfig = () => {
    if (!config) return;
    
    const configText = getConfigForIDE(selectedIDE);
    navigator.clipboard.writeText(configText);
    showToast('Configuration copied to clipboard', 'success');
  };

  const generateCursorDeeplink = () => {
    if (!config) return '';
    
    const httpConfig = {
      url: `http://${config.host}:${config.port}/mcp`
    };
    
    const configString = JSON.stringify(httpConfig);
    const base64Config = btoa(configString);
    return `cursor://anysphere.cursor-deeplink/mcp/install?name=archon&config=${base64Config}`;
  };

  const handleCursorOneClick = () => {
    const deeplink = generateCursorDeeplink();
    window.location.href = deeplink;
    showToast('Opening Cursor with Archon MCP configuration...', 'info');
  };



  const getConfigForIDE = (ide: 'windsurf' | 'cursor' | 'claudecode') => {
    if (!config) return '';
    
    if (ide === 'cursor') {
      // Cursor connecting to Streamable HTTP server
      const cursorConfig = {
        mcpServers: {
          archon: {
            url: `http://${config.host}:${config.port}/mcp`
          }
        }
      };
      return JSON.stringify(cursorConfig, null, 2);
    } else if (ide === 'windsurf') {
      // Windsurf can use Streamable HTTP transport
      const windsurfConfig = {
        mcpServers: {
          archon: {
            "serverUrl": `http://${config.host}:${config.port}/mcp`
          }
        }
      };
      return JSON.stringify(windsurfConfig, null, 2);
    } else {
      // Claude Code uses CLI commands, show HTTP config as example
      const claudeConfig = {
        name: "archon",
        transport: "http",
        url: `http://${config.host}:${config.port}/mcp`
      };
      return JSON.stringify(claudeConfig, null, 2);
    }
  };

  const getIDEInstructions = (ide: 'windsurf' | 'cursor' | 'claudecode') => {
    switch (ide) {
      case 'windsurf':
        return {
          title: 'Windsurf Configuration',
          steps: [
            '1. Open Windsurf and click the "MCP servers" button (hammer icon)',
            '2. Click "Configure" and then "View raw config"',
            '3. Add the configuration shown below to the mcpServers object',
            '4. Click "Refresh" to connect to the server'
          ]
        };
      case 'cursor':
        return {
          title: 'Cursor Configuration',
          steps: [
            '1. Option A: Use the one-click install button below (recommended)',
            '2. Option B: Manually edit ~/.cursor/mcp.json',
            '3. Add the configuration shown below',
            '4. Restart Cursor for changes to take effect'
          ]
        };
      case 'claudecode':
        return {
          title: 'Claude Code Configuration',
          steps: [
            '1. Open a terminal and run the following command:',
            `2. claude mcp add --transport http archon http://${config?.host}:${config?.port}/mcp`,
            '3. The connection will be established automatically'
          ]
        };
    }
  };

  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}h ${minutes}m ${secs}s`;
  };

  const formatLogEntry = (log: LogEntry | string): string => {
    if (typeof log === 'string') {
      return log;
    }
    return `[${log.level}] ${log.message}`;
  };

  const getStatusIcon = () => {
    switch (serverStatus.status) {
      case 'running':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'starting':
      case 'stopping':
        return <Loader className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <AlertCircle className="w-5 h-5 text-red-500" />;
    }
  };

  const getStatusColor = () => {
    switch (serverStatus.status) {
      case 'running':
        return 'text-green-500';
      case 'starting':
      case 'stopping':
        return 'text-blue-500';
      default:
        return 'text-red-500';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader className="animate-spin text-gray-500" size={32} />
      </div>
    );
  }

  return (
    <motion.div
      initial="hidden"
      animate={isVisible ? 'visible' : 'hidden'}
      variants={containerVariants}
    >
      <motion.h1
        className="text-3xl font-bold text-gray-800 dark:text-white mb-8 flex items-center gap-3"
        variants={titleVariants}
      >
        <svg fill="currentColor" fillRule="evenodd" height="28" width="28" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" className="text-pink-500 filter drop-shadow-[0_0_8px_rgba(236,72,153,0.8)]">
          <path d="M15.688 2.343a2.588 2.588 0 00-3.61 0l-9.626 9.44a.863.863 0 01-1.203 0 .823.823 0 010-1.18l9.626-9.44a4.313 4.313 0 016.016 0 4.116 4.116 0 011.204 3.54 4.3 4.3 0 013.609 1.18l.05.05a4.115 4.115 0 010 5.9l-8.706 8.537a.274.274 0 000 .393l1.788 1.754a.823.823 0 010 1.18.863.863 0 01-1.203 0l-1.788-1.753a1.92 1.92 0 010-2.754l8.706-8.538a2.47 2.47 0 000-3.54l-.05-.049a2.588 2.588 0 00-3.607-.003l-7.172 7.034-.002.002-.098.097a.863.863 0 01-1.204 0 .823.823 0 010-1.18l7.273-7.133a2.47 2.47 0 00-.003-3.537z"></path>
          <path d="M14.485 4.703a.823.823 0 000-1.18.863.863 0 00-1.204 0l-7.119 6.982a4.115 4.115 0 000 5.9 4.314 4.314 0 006.016 0l7.12-6.982a.823.823 0 000-1.18.863.863 0 00-1.204 0l-7.119 6.982a2.588 2.588 0 01-3.61 0 2.47 2.47 0 010-3.54l7.12-6.982z"></path>
        </svg>
        MCP Dashboard
      </motion.h1>

      {/* Tab Navigation */}
      <motion.div className="mb-6 border-b border-gray-200 dark:border-gray-800" variants={itemVariants}>
        <div className="flex space-x-8">
          <button
            onClick={() => setActiveTab('server')}
            className={`pb-3 relative ${
              activeTab === 'server'
                ? 'text-blue-600 dark:text-blue-400 font-medium'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Server Control
            {activeTab === 'server' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]"></span>
            )}
          </button>
          {/* TODO: MCP Client feature not implemented - commenting out for now
          <button
            onClick={() => setActiveTab('clients')}
            className={`pb-3 relative ${
              activeTab === 'clients'
                ? 'text-cyan-600 dark:text-cyan-400 font-medium'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            MCP Clients
            {activeTab === 'clients' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-500 shadow-[0_0_10px_rgba(34,211,238,0.5)]"></span>
            )}
          </button>
          */}
        </div>
      </motion.div>

      {/* Server Control Tab */}
      {activeTab === 'server' && (
        <>
          {/* Server Control + Server Logs */}
          <motion.div className="grid grid-cols-1 lg:grid-cols-2 gap-6" variants={itemVariants}>
            
            {/* Left Column: Archon MCP Server */}
            <div className="flex flex-col">
              <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4 flex items-center">
                <Server className="mr-2 text-blue-500" size={20} />
                Archon MCP Server
              </h2>
              
              <Card accentColor="blue" className="space-y-6 flex-1">
                {/* Status Display */}
                <div className="flex items-center justify-between">
                  <div 
                    className="flex items-center gap-3 cursor-help" 
                    title={process.env.NODE_ENV === 'development' ? 
                      `Debug Info:\nStatus: ${serverStatus.status}\nConfig: ${config ? 'loaded' : 'null'}\n${config ? `Details: ${JSON.stringify(config, null, 2)}` : ''}` : 
                      undefined
                    }
                  >
                    {getStatusIcon()}
                    <div>
                      <p className={`font-semibold ${getStatusColor()}`}>
                        Status: {serverStatus.status.charAt(0).toUpperCase() + serverStatus.status.slice(1)}
                      </p>
                      {serverStatus.uptime !== null && (
                        <p className="text-sm text-gray-600 dark:text-zinc-400">
                          Uptime: {formatUptime(serverStatus.uptime)}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  {/* Control Buttons */}
                  <div className="flex gap-2 items-center">
                    {serverStatus.status === 'stopped' ? (
                      <Button
                        onClick={handleStartServer}
                        disabled={isStarting}
                        variant="primary"
                        accentColor="green"
                        className="shadow-emerald-500/20 shadow-sm"
                      >
                        {isStarting ? (
                          <>
                            <Loader className="w-4 h-4 mr-2 animate-spin inline" />
                            Starting...
                          </>
                        ) : (
                          <>
                            <Play className="w-4 h-4 mr-2 inline" />
                            Start Server
                          </>
                        )}
                      </Button>
                    ) : (
                      <Button
                        onClick={handleStopServer}
                        disabled={isStopping || serverStatus.status !== 'running'}
                        variant="primary"
                        accentColor="pink"
                        className="shadow-pink-500/20 shadow-sm"
                      >
                        {isStopping ? (
                          <>
                            <Loader className="w-4 h-4 mr-2 animate-spin inline" />
                            Stopping...
                          </>
                        ) : (
                          <>
                            <Square className="w-4 h-4 mr-2 inline" />
                            Stop Server
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                </div>

                {/* Connection Details */}
                {serverStatus.status === 'running' && config && (
                  <div className="border-t border-gray-200 dark:border-zinc-800 pt-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-medium text-gray-700 dark:text-zinc-300">
                        IDE Configuration
                        <span className="ml-2 px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full">
                          HTTP Mode
                        </span>
                      </h3>
                      <Button
                        variant="secondary"
                        accentColor="blue"
                        size="sm"
                        onClick={handleCopyConfig}
                      >
                        <Copy className="w-3 h-3 mr-1 inline" />
                        Copy
                      </Button>
                    </div>
                    
                    {/* IDE Selection Tabs */}
                    <div className="mb-4">
                      <div className="flex border-b border-gray-200 dark:border-zinc-700 mb-3">
                        <button
                          onClick={() => setSelectedIDE('windsurf')}
                          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                            selectedIDE === 'windsurf'
                              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                              : 'border-transparent text-gray-500 dark:text-zinc-400 hover:text-gray-700 dark:hover:text-zinc-300'
                          } cursor-pointer`}
                        >
                          Windsurf
                        </button>
                        <button
                          onClick={() => setSelectedIDE('cursor')}
                          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                            selectedIDE === 'cursor'
                              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                              : 'border-transparent text-gray-500 dark:text-zinc-400 hover:text-gray-700 dark:hover:text-zinc-300'
                          } cursor-pointer`}
                        >
                          Cursor
                        </button>
                        <button
                          onClick={() => setSelectedIDE('claudecode')}
                          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                            selectedIDE === 'claudecode'
                              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                              : 'border-transparent text-gray-500 dark:text-zinc-400 hover:text-gray-700 dark:hover:text-zinc-300'
                          } cursor-pointer`}
                        >
                          Claude Code
                        </button>
                      </div>
                    </div>

                    {/* IDE Instructions */}
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-700 dark:text-zinc-300 mb-2">
                        {getIDEInstructions(selectedIDE).title}
                      </h4>
                      <ul className="text-sm text-gray-600 dark:text-zinc-400 space-y-1">
                        {getIDEInstructions(selectedIDE).steps.map((step, index) => (
                          <li key={index}>{step}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="bg-gray-50 dark:bg-black/50 rounded-lg p-4 font-mono text-sm relative">
                      <pre className="text-gray-600 dark:text-zinc-400 whitespace-pre-wrap">
                        {getConfigForIDE(selectedIDE)}
                      </pre>
                      <p className="text-xs text-gray-500 dark:text-zinc-500 mt-3 font-sans">
                        {selectedIDE === 'cursor' 
                          ? 'Copy this configuration and add it to ~/.cursor/mcp.json'
                          : selectedIDE === 'windsurf'
                          ? 'Copy this configuration and add it to your Windsurf MCP settings'
                          : 'This shows the configuration format for Claude Code'
                        }
                      </p>
                    </div>
                    
                    {/* One-click install button for Cursor */}
                    {selectedIDE === 'cursor' && serverStatus.status === 'running' && (
                      <div className="mt-4">
                        <Button
                          variant="primary"
                          accentColor="blue"
                          onClick={handleCursorOneClick}
                          className="w-full"
                        >
                          <Server className="w-4 h-4 mr-2 inline" />
                          One-Click Install for Cursor
                        </Button>
                        <p className="text-xs text-gray-500 dark:text-zinc-500 mt-2 text-center">
                          Requires Cursor to be installed and will open a deeplink
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </Card>
            </div>

            {/* Right Column: Server Logs */}
            <div className="flex flex-col">
              <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4 flex items-center">
                <Clock className="mr-2 text-purple-500" size={20} />
                Server Logs
              </h2>
              
              <Card accentColor="purple" className="h-full flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm text-gray-600 dark:text-zinc-400">
                    {logs.length > 0 
                      ? `Showing ${logs.length} log entries`
                      : 'No logs available'
                    }
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearLogs}
                    disabled={logs.length === 0}
                  >
                    Clear Logs
                  </Button>
                </div>
                
                <div 
                  id="mcp-logs-container"
                  ref={logsContainerRef}
                  className="bg-gray-50 dark:bg-black border border-gray-200 dark:border-zinc-900 rounded-md p-4 flex-1 overflow-y-auto font-mono text-sm max-h-[600px]"
                >
                  {logs.length === 0 ? (
                    <p className="text-gray-500 dark:text-zinc-500 text-center py-8">
                      {serverStatus.status === 'running' 
                        ? 'Waiting for log entries...'
                        : 'Start the server to see logs'
                      }
                    </p>
                  ) : (
                    logs.map((log, index) => (
                      <div
                        key={index}
                        className={`py-1.5 border-b border-gray-100 dark:border-zinc-900 last:border-0 ${
                          typeof log !== 'string' && log.level === 'ERROR' 
                            ? 'text-red-600 dark:text-red-400' 
                            : typeof log !== 'string' && log.level === 'WARNING'
                            ? 'text-yellow-600 dark:text-yellow-400'
                            : 'text-gray-600 dark:text-zinc-400'
                        }`}
                      >
                        {formatLogEntry(log)}
                      </div>
                    ))
                  )}
                  <div ref={logsEndRef} />
                </div>
              </Card>
            </div>
          </motion.div>
        </>
      )}

      {/* Clients Tab - commented out as feature not implemented
      {activeTab === 'clients' && (
        <motion.div variants={itemVariants}>
          <MCPClients />
        </motion.div>
      )}
      */}
    </motion.div>
  );
};