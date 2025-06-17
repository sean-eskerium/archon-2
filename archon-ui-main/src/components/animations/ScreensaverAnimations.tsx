import React, { useEffect, useRef } from 'react';

/**
 * Quantum Flux Screensaver
 * The Archon logo pulsates with energy waves radiating outward
 */
export const QuantumFluxScreensaver: React.FC = () => {
  return (
    <div className="relative w-full h-full flex items-center justify-center bg-black overflow-hidden">
      {/* Energy waves */}
      <div className="absolute inset-0 flex items-center justify-center">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full border border-cyan-400/30"
            style={{
              width: `${200 + i * 150}px`,
              height: `${200 + i * 150}px`,
              animation: `pulse ${2 + i * 0.5}s ease-out infinite`,
              animationDelay: `${i * 0.3}s`,
            }}
          />
        ))}
      </div>

      {/* Central logo with glow */}
      <div className="relative z-10">
        <img 
          src="/logo-neon.svg" 
          alt="Archon" 
          className="w-32 h-32 animate-pulse"
          style={{
            filter: 'drop-shadow(0 0 30px rgba(34, 211, 238, 0.8)) drop-shadow(0 0 60px rgba(168, 85, 247, 0.6))',
          }}
        />
      </div>

      {/* Floating particles */}
      <div className="absolute inset-0">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-cyan-400 rounded-full"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animation: `float ${10 + Math.random() * 10}s ease-in-out infinite`,
              animationDelay: `${Math.random() * 5}s`,
            }}
          />
        ))}
      </div>

      <style jsx>{`
        @keyframes pulse {
          0% {
            transform: scale(0);
            opacity: 1;
          }
          100% {
            transform: scale(1);
            opacity: 0;
          }
        }
        @keyframes float {
          0%, 100% {
            transform: translateY(0) translateX(0);
          }
          33% {
            transform: translateY(-30px) translateX(10px);
          }
          66% {
            transform: translateY(30px) translateX(-10px);
          }
        }
      `}</style>
    </div>
  );
};

/**
 * Aurora Glass Screensaver
 * Frosted glass medallion with aurora borealis light show behind it
 */
export const AuroraGlassScreensaver: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    let time = 0;

    const drawAurora = () => {
      // Create dark background with vignette
      const gradient = ctx.createRadialGradient(
        canvas.width / 2, canvas.height / 2, 0,
        canvas.width / 2, canvas.height / 2, canvas.width / 1.5
      );
      gradient.addColorStop(0, 'rgba(0, 0, 0, 0.3)');
      gradient.addColorStop(1, 'rgba(0, 0, 0, 0.95)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw aurora waves
      const colors = [
        { r: 34, g: 211, b: 238, a: 0.3 },  // Cyan
        { r: 168, g: 85, b: 247, a: 0.3 },  // Purple
        { r: 236, g: 72, b: 153, a: 0.3 },  // Pink
        { r: 59, g: 130, b: 246, a: 0.3 },  // Blue
        { r: 16, g: 185, b: 129, a: 0.3 },  // Green
      ];

      colors.forEach((color, index) => {
        ctx.beginPath();
        
        const waveHeight = 200;
        const waveOffset = index * 50;
        const speed = 0.001 + index * 0.0002;
        
        for (let x = 0; x <= canvas.width; x += 5) {
          const y = canvas.height / 2 + 
            Math.sin(x * 0.003 + time * speed) * waveHeight +
            Math.sin(x * 0.005 + time * speed * 1.5) * (waveHeight / 2) +
            waveOffset - 100;
          
          if (x === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        
        // Create gradient for each wave
        const waveGradient = ctx.createLinearGradient(0, canvas.height / 2 - 200, 0, canvas.height / 2 + 200);
        waveGradient.addColorStop(0, `rgba(${color.r}, ${color.g}, ${color.b}, 0)`);
        waveGradient.addColorStop(0.5, `rgba(${color.r}, ${color.g}, ${color.b}, ${color.a})`);
        waveGradient.addColorStop(1, `rgba(${color.r}, ${color.g}, ${color.b}, 0)`);
        
        ctx.strokeStyle = waveGradient;
        ctx.lineWidth = 3;
        ctx.stroke();
        
        // Add glow effect
        ctx.shadowBlur = 30;
        ctx.shadowColor = `rgba(${color.r}, ${color.g}, ${color.b}, 0.5)`;
        ctx.stroke();
        ctx.shadowBlur = 0;
      });

      time += 16;
      requestAnimationFrame(drawAurora);
    };

    drawAurora();

    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);
    
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className="relative w-full h-full bg-black overflow-hidden">
      <canvas ref={canvasRef} className="absolute inset-0" />
      
      {/* Glass medallion with frosted effect */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative">
          {/* Frosted glass background */}
          <div 
            className="absolute inset-0 w-64 h-64 rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 50%, transparent 100%)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255,255,255,0.1)',
              boxShadow: 'inset 0 0 30px rgba(255,255,255,0.05), 0 0 50px rgba(34, 211, 238, 0.2)',
            }}
          />
          
          {/* Embossed logo */}
          <div className="relative w-64 h-64 flex items-center justify-center">
            <img 
              src="/logo-neon.svg" 
              alt="Archon" 
              className="w-40 h-40 z-10"
              style={{
                filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3)) drop-shadow(0 -1px 2px rgba(255,255,255,0.2))',
                opacity: 0.8,
                mixBlendMode: 'screen',
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Ethereal Waves Screensaver
 * Amorphous, jellyfish-like flowing neon colors
 */
export const EtherealWavesScreensaver: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    // Ethereal blob properties
    const blobs = [
      { x: 0.3, y: 0.5, radius: 150, color: { r: 34, g: 211, b: 238 }, phase: 0 },
      { x: 0.7, y: 0.4, radius: 120, color: { r: 168, g: 85, b: 247 }, phase: 1 },
      { x: 0.5, y: 0.7, radius: 100, color: { r: 236, g: 72, b: 153 }, phase: 2 },
      { x: 0.2, y: 0.3, radius: 130, color: { r: 59, g: 130, b: 246 }, phase: 3 },
      { x: 0.8, y: 0.6, radius: 110, color: { r: 16, g: 185, b: 129 }, phase: 4 },
    ];

    let time = 0;

    const drawEtherealWaves = () => {
      // Dark background
      ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      blobs.forEach((blob, index) => {
        const centerX = blob.x * canvas.width + Math.sin(time * 0.0005 + blob.phase) * 100;
        const centerY = blob.y * canvas.height + Math.cos(time * 0.0007 + blob.phase) * 80;
        
        // Create morphing shape using multiple sine waves
        ctx.beginPath();
        for (let angle = 0; angle <= Math.PI * 2; angle += 0.05) {
          const radiusVariation = 
            Math.sin(angle * 3 + time * 0.002 + blob.phase) * 20 +
            Math.sin(angle * 5 + time * 0.003 + blob.phase * 2) * 15 +
            Math.sin(angle * 7 + time * 0.001 + blob.phase * 3) * 10;
          
          const r = blob.radius + radiusVariation;
          const x = centerX + Math.cos(angle) * r;
          const y = centerY + Math.sin(angle) * r;
          
          if (angle === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.closePath();

        // Create radial gradient for each blob
        const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, blob.radius);
        gradient.addColorStop(0, `rgba(${blob.color.r}, ${blob.color.g}, ${blob.color.b}, 0.3)`);
        gradient.addColorStop(0.5, `rgba(${blob.color.r}, ${blob.color.g}, ${blob.color.b}, 0.1)`);
        gradient.addColorStop(1, `rgba(${blob.color.r}, ${blob.color.g}, ${blob.color.b}, 0)`);

        ctx.fillStyle = gradient;
        ctx.fill();

        // Add glow
        ctx.shadowBlur = 50;
        ctx.shadowColor = `rgba(${blob.color.r}, ${blob.color.g}, ${blob.color.b}, 0.5)`;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      time += 16;
      requestAnimationFrame(drawEtherealWaves);
    };

    drawEtherealWaves();

    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className="relative w-full h-full bg-black overflow-hidden">
      <canvas ref={canvasRef} className="absolute inset-0" />
      
      {/* Central logo with ethereal glow */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative">
          <img 
            src="/logo-neon.svg" 
            alt="Archon" 
            className="w-48 h-48 z-10"
            style={{
              filter: 'drop-shadow(0 0 30px rgba(255,255,255,0.3))',
              opacity: 0.6,
              animation: 'etherealFloat 8s ease-in-out infinite',
            }}
          />
        </div>
      </div>

      <style jsx>{`
        @keyframes etherealFloat {
          0%, 100% {
            transform: translateY(0) scale(1);
            opacity: 0.6;
          }
          50% {
            transform: translateY(-20px) scale(1.05);
            opacity: 0.8;
          }
        }
      `}</style>
    </div>
  );
};