import React, { useState, useEffect } from 'react';
import { Moon, Sun, FileText, Layout, Bot, Settings, Palette, Flame, Monitor } from 'lucide-react';
import { Toggle } from '../ui/Toggle';
import { Card } from '../ui/Card';
import { useTheme } from '../../contexts/ThemeContext';
import { credentialsService } from '../../services/credentialsService';
import { useToast } from '../../contexts/ToastContext';
import { serverHealthService, ScreensaverStyle } from '../../services/serverHealthService';
import { Select } from '../ui/Select';

export const FeaturesSection = () => {
  const {
    theme,
    setTheme
  } = useTheme();
  const { showToast } = useToast();
  const isDarkMode = theme === 'dark';
  const [projectsEnabled, setProjectsEnabled] = useState(true);
  
  // Commented out for future release
  const [agUILibraryEnabled, setAgUILibraryEnabled] = useState(false);
  const [agentsEnabled, setAgentsEnabled] = useState(false);
  
  const [logfireEnabled, setLogfireEnabled] = useState(false);
  const [screensaverEnabled, setScreensaverEnabled] = useState(true);
  const [screensaverStyle, setScreensaverStyle] = useState<ScreensaverStyle>('quantum-flux');
  const [loading, setLoading] = useState(true);
  const [projectsSchemaValid, setProjectsSchemaValid] = useState(true);
  const [projectsSchemaError, setProjectsSchemaError] = useState<string | null>(null);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      
      // Load both Logfire and Projects settings, plus check projects schema
      const [logfireResponse, projectsResponse, projectsHealthResponse, screensaverEnabledRes, screensaverStyleRes] = await Promise.all([
        credentialsService.getCredential('LOGFIRE_ENABLED').catch(() => ({ value: undefined })),
        credentialsService.getCredential('PROJECTS_ENABLED').catch(() => ({ value: undefined })),
        fetch(`${credentialsService['baseUrl']}/api/projects/health`).catch(() => null),
        credentialsService.getCredential('SCREENSAVER_ENABLED').catch(() => ({ value: 'true' })),
        credentialsService.getCredential('SCREENSAVER_STYLE').catch(() => ({ value: 'quantum-flux' }))
      ]);
      
      // Set Logfire setting
      if (logfireResponse.value !== undefined) {
        setLogfireEnabled(logfireResponse.value === 'true');
      } else {
        setLogfireEnabled(false);
      }
      
      // Set Screensaver settings
      setScreensaverEnabled(screensaverEnabledRes.value === 'true');
      setScreensaverStyle((screensaverStyleRes.value || 'quantum-flux') as ScreensaverStyle);
      
      // Check projects schema health
      console.log('🔍 Projects health response:', {
        response: projectsHealthResponse,
        ok: projectsHealthResponse?.ok,
        status: projectsHealthResponse?.status,
        url: `${credentialsService['baseUrl']}/api/projects/health`
      });
      
      if (projectsHealthResponse && projectsHealthResponse.ok) {
        const healthData = await projectsHealthResponse.json();
        console.log('🔍 Projects health data:', healthData);
        
        const schemaValid = healthData.schema?.valid === true;
        setProjectsSchemaValid(schemaValid);
        
        if (!schemaValid) {
          setProjectsSchemaError(
            'Projects table not detected. Please ensure you have installed the archon_tasks.sql structure to your database and restart the server.'
          );
        } else {
          setProjectsSchemaError(null);
        }
      } else {
        // If health check fails, assume schema is invalid
        console.log('🔍 Projects health check failed');
        setProjectsSchemaValid(false);
        setProjectsSchemaError(
          'Unable to verify projects schema. Please ensure the backend is running and database is accessible.'
        );
      }
      
      // Set Projects setting (but only if schema is valid)
      if (projectsResponse.value !== undefined) {
        setProjectsEnabled(projectsResponse.value === 'true');
      } else {
        setProjectsEnabled(true); // Default to true
      }
      
    } catch (error) {
      console.error('Failed to load settings:', error);
      // Default values on error
      setLogfireEnabled(false);
      setProjectsEnabled(true);
      setScreensaverEnabled(true);
      setScreensaverStyle('quantum-flux');
      setProjectsSchemaValid(false);
      setProjectsSchemaError('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleProjectsToggle = async (checked: boolean) => {
    // Prevent duplicate calls while one is already in progress
    if (loading) return;
    
    try {
      setLoading(true);
      // Update local state immediately for responsive UI
      setProjectsEnabled(checked);

      // Save to backend
      await credentialsService.createCredential({
        key: 'PROJECTS_ENABLED',
        value: checked.toString(),
        is_encrypted: false,
        category: 'features',
        description: 'Enable or disable Projects and Tasks functionality'
      });

      showToast(
        checked ? 'Projects Enabled Successfully!' : 'Projects Now Disabled', 
        checked ? 'success' : 'warning'
      );
    } catch (error) {
      console.error('Failed to update projects setting:', error);
      // Revert local state on error
      setProjectsEnabled(!checked);
      showToast('Failed to update Projects setting', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleLogfireToggle = async (checked: boolean) => {
    // Prevent duplicate calls while one is already in progress
    if (loading) return;
    
    try {
      setLoading(true);
      // Update local state immediately for responsive UI
      setLogfireEnabled(checked);

      // Save to backend
      await credentialsService.createCredential({
        key: 'LOGFIRE_ENABLED',
        value: checked.toString(),
        is_encrypted: false,
        category: 'monitoring',
        description: 'Enable or disable Pydantic Logfire logging and observability'
      });

      showToast(
        checked ? 'Logfire Enabled Successfully!' : 'Logfire Now Disabled', 
        checked ? 'success' : 'warning'
      );
    } catch (error) {
      console.error('Failed to update logfire setting:', error);
      // Revert local state on error
      setLogfireEnabled(!checked);
      showToast('Failed to update Logfire setting', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleThemeToggle = (checked: boolean) => {
    setTheme(checked ? 'dark' : 'light');
  };

  const handleScreensaverToggle = async (checked: boolean) => {
    if (loading) return;
    
    try {
      setLoading(true);
      setScreensaverEnabled(checked);

      await serverHealthService.updateSettings(checked, screensaverStyle);

      showToast(
        checked ? 'Screensaver Enabled' : 'Screensaver Disabled', 
        checked ? 'success' : 'warning'
      );
    } catch (error) {
      console.error('Failed to update screensaver setting:', error);
      setScreensaverEnabled(!checked);
      showToast('Failed to update screensaver setting', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleScreensaverStyleChange = async (value: string) => {
    if (loading) return;
    
    try {
      setLoading(true);
      const style = value as ScreensaverStyle;
      setScreensaverStyle(style);

      await serverHealthService.updateSettings(screensaverEnabled, style);

      showToast('Screensaver style updated', 'success');
    } catch (error) {
      console.error('Failed to update screensaver style:', error);
      showToast('Failed to update screensaver style', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="flex items-center mb-4">
        <Palette className="mr-2 text-purple-500 filter drop-shadow-[0_0_8px_rgba(168,85,247,0.8)]" size={20} />
        <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
          Features & Theme
        </h2>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Theme Toggle */}
        <div className="flex items-center gap-4 p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-purple-600/5 backdrop-blur-sm border border-purple-500/20 shadow-lg">
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-800 dark:text-white">
              Dark Mode
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Switch between light and dark themes
            </p>
          </div>
          <div className="flex-shrink-0">
            <Toggle checked={isDarkMode} onCheckedChange={handleThemeToggle} accentColor="purple" icon={isDarkMode ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />} />
          </div>
        </div>

        {/* Projects Toggle */}
        <div className="flex items-center gap-4 p-4 rounded-xl bg-gradient-to-br from-blue-500/10 to-blue-600/5 backdrop-blur-sm border border-blue-500/20 shadow-lg">
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-800 dark:text-white">
              Projects
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Enable Projects and Tasks functionality
            </p>
            {!projectsSchemaValid && projectsSchemaError && (
              <p className="text-xs text-red-500 dark:text-red-400 mt-1">
                ⚠️ {projectsSchemaError}
              </p>
            )}
          </div>
          <div className="flex-shrink-0">
            <Toggle 
              checked={projectsEnabled} 
              onCheckedChange={handleProjectsToggle} 
              accentColor="blue" 
              icon={<FileText className="w-5 h-5" />}
              disabled={loading || !projectsSchemaValid}
            />
          </div>
        </div>

        {/* COMMENTED OUT FOR FUTURE RELEASE - AG-UI Library Toggle */}
        {/*
        <div className="flex items-center gap-4 p-4 rounded-xl bg-gradient-to-br from-pink-500/10 to-pink-600/5 backdrop-blur-sm border border-pink-500/20 shadow-lg">
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-800 dark:text-white">
              AG-UI Library
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Enable component library functionality
            </p>
          </div>
          <div className="flex-shrink-0">
            <Toggle checked={agUILibraryEnabled} onCheckedChange={setAgUILibraryEnabled} accentColor="pink" icon={<Layout className="w-5 h-5" />} />
          </div>
        </div>
        */}

        {/* COMMENTED OUT FOR FUTURE RELEASE - Agents Toggle */}
        {/*
        <div className="flex items-center gap-4 p-4 rounded-xl bg-gradient-to-br from-green-500/10 to-green-600/5 backdrop-blur-sm border border-green-500/20 shadow-lg">
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-800 dark:text-white">
              Agents
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Enable AI agents for automated tasks
            </p>
          </div>
          <div className="flex-shrink-0">
            <Toggle checked={agentsEnabled} onCheckedChange={setAgentsEnabled} accentColor="green" icon={<Bot className="w-5 h-5" />} />
          </div>
        </div>
        */}

        {/* Pydantic Logfire Toggle */}
        <div className="flex items-center gap-4 p-4 rounded-xl bg-gradient-to-br from-orange-500/10 to-orange-600/5 backdrop-blur-sm border border-orange-500/20 shadow-lg">
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-800 dark:text-white">
              Pydantic Logfire
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Structured logging and observability platform
            </p>
          </div>
          <div className="flex-shrink-0">
            <Toggle 
              checked={logfireEnabled} 
              onCheckedChange={handleLogfireToggle} 
              accentColor="orange" 
              icon={<Flame className="w-5 h-5" />}
              disabled={loading}
            />
          </div>
        </div>

        {/* Screensaver Toggle */}
        <div className="flex items-center gap-4 p-4 rounded-xl bg-gradient-to-br from-cyan-500/10 to-cyan-600/5 backdrop-blur-sm border border-cyan-500/20 shadow-lg">
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-800 dark:text-white">
              Screensaver
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Show animated screensaver when server disconnects
            </p>
            {screensaverEnabled && (
              <div className="mt-2">
                <Select
                  value={screensaverStyle}
                  onValueChange={handleScreensaverStyleChange}
                  disabled={loading}
                  className="text-xs"
                >
                  <option value="quantum-flux">Quantum Flux</option>
                  <option value="neural-network">Neural Network</option>
                  <option value="matrix-rain">Matrix Rain</option>
                </Select>
              </div>
            )}
          </div>
          <div className="flex-shrink-0">
            <Toggle 
              checked={screensaverEnabled} 
              onCheckedChange={handleScreensaverToggle} 
              accentColor="cyan" 
              icon={<Monitor className="w-5 h-5" />}
              disabled={loading}
            />
          </div>
        </div>
      </div>
    </div>
  );
};