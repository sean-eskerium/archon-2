import React, { useState } from 'react';
import { X, Wifi, WifiOff } from 'lucide-react';
import { QuantumFluxScreensaver, NeuralNetworkScreensaver, MatrixRainScreensaver } from './animations/ScreensaverAnimations';
import { ScreensaverStyle } from '../services/serverHealthService';
import { NeonButton } from './ui/NeonButton';

interface ScreensaverOverlayProps {
  isActive: boolean;
  style: ScreensaverStyle;
  onDismiss?: () => void;
}

export const ScreensaverOverlay: React.FC<ScreensaverOverlayProps> = ({
  isActive,
  style,
  onDismiss
}) => {
  const [showControls, setShowControls] = useState(false);

  if (!isActive) return null;

  const renderScreensaver = () => {
    switch (style) {
      case 'neural-network':
        return <NeuralNetworkScreensaver />;
      case 'matrix-rain':
        return <MatrixRainScreensaver />;
      case 'quantum-flux':
      default:
        return <QuantumFluxScreensaver />;
    }
  };

  return (
    <div 
      className="fixed inset-0 z-[9999] bg-black"
      onMouseMove={() => setShowControls(true)}
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => setTimeout(() => setShowControls(false), 3000)}
    >
      {/* Screensaver Animation */}
      {renderScreensaver()}

      {/* Status Overlay */}
      <div 
        className={`absolute inset-0 pointer-events-none transition-opacity duration-500 ${
          showControls ? 'opacity-100' : 'opacity-0'
        }`}
      >
        {/* Connection Status */}
        <div className="absolute top-8 left-8 flex items-center gap-3 text-white/80">
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-red-500/20 border border-red-500/50 backdrop-blur-sm">
            <WifiOff className="w-5 h-5 text-red-400" />
            <span className="text-sm font-medium">Server Disconnected</span>
          </div>
        </div>

        {/* Override Button */}
        {onDismiss && (
          <div className="absolute bottom-8 right-8 pointer-events-auto">
            <NeonButton
              onClick={onDismiss}
              variant="outline"
              className="flex items-center gap-2"
            >
              <X className="w-4 h-4" />
              Dismiss Screensaver
            </NeonButton>
          </div>
        )}

        {/* Info Text */}
        <div className="absolute bottom-8 left-8 max-w-md">
          <p className="text-white/60 text-sm">
            The screensaver is active because the server connection was lost. 
            The UI will automatically reconnect when the server is available.
          </p>
        </div>
      </div>
    </div>
  );
};