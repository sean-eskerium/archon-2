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
 * Neural Network Screensaver
 * Animated connection lines between floating nodes around the logo
 */
export const NeuralNetworkScreensaver: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const nodes: Array<{x: number; y: number; vx: number; vy: number; radius: number}> = [];
    const nodeCount = 50;

    // Initialize nodes
    for (let i = 0; i < nodeCount; i++) {
      nodes.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        radius: Math.random() * 2 + 1,
      });
    }

    let animationId: number;

    const animate = () => {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Update and draw nodes
      nodes.forEach((node, i) => {
        node.x += node.vx;
        node.y += node.vy;

        // Bounce off edges
        if (node.x < 0 || node.x > canvas.width) node.vx *= -1;
        if (node.y < 0 || node.y > canvas.height) node.vy *= -1;

        // Draw node
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = '#22d3ee';
        ctx.fill();

        // Draw connections
        nodes.forEach((otherNode, j) => {
          if (i === j) return;
          const distance = Math.sqrt(
            Math.pow(node.x - otherNode.x, 2) + Math.pow(node.y - otherNode.y, 2)
          );
          if (distance < 150) {
            ctx.beginPath();
            ctx.moveTo(node.x, node.y);
            ctx.lineTo(otherNode.x, otherNode.y);
            ctx.strokeStyle = `rgba(34, 211, 238, ${1 - distance / 150})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        });
      });

      animationId = requestAnimationFrame(animate);
    };

    animate();

    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);
    
    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className="relative w-full h-full bg-black overflow-hidden">
      <canvas ref={canvasRef} className="absolute inset-0" />
      
      {/* Central logo */}
      <div className="absolute inset-0 flex items-center justify-center">
        <img 
          src="/logo-neon.svg" 
          alt="Archon" 
          className="w-40 h-40 z-10 animate-pulse"
          style={{
            filter: 'drop-shadow(0 0 40px rgba(34, 211, 238, 0.9)) drop-shadow(0 0 80px rgba(168, 85, 247, 0.7))',
          }}
        />
      </div>
    </div>
  );
};

/**
 * Matrix Rain Screensaver
 * Cyberpunk-style falling code with the Archon logo glowing in the center
 */
export const MatrixRainScreensaver: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const chars = 'ARCHON01アーコン</>{}[]()';
    const fontSize = 14;
    const columns = Math.floor(canvas.width / fontSize);
    const drops: number[] = [];

    for (let i = 0; i < columns; i++) {
      drops[i] = Math.random() * -100;
    }

    const draw = () => {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.fillStyle = '#22d3ee';
      ctx.font = `${fontSize}px monospace`;

      for (let i = 0; i < drops.length; i++) {
        const text = chars[Math.floor(Math.random() * chars.length)];
        const x = i * fontSize;
        const y = drops[i] * fontSize;

        // Gradient effect
        const gradient = ctx.createLinearGradient(0, y - fontSize * 10, 0, y);
        gradient.addColorStop(0, 'rgba(34, 211, 238, 0)');
        gradient.addColorStop(0.5, 'rgba(34, 211, 238, 0.5)');
        gradient.addColorStop(1, 'rgba(34, 211, 238, 1)');
        ctx.fillStyle = gradient;

        ctx.fillText(text, x, y);

        if (y > canvas.height && Math.random() > 0.975) {
          drops[i] = 0;
        }
        drops[i]++;
      }
    };

    const interval = setInterval(draw, 33);

    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);
    return () => {
      clearInterval(interval);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className="relative w-full h-full bg-black overflow-hidden">
      <canvas ref={canvasRef} className="absolute inset-0" />
      
      {/* Central logo with holographic effect */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative">
          <img 
            src="/logo-neon.svg" 
            alt="Archon" 
            className="w-48 h-48 z-10"
            style={{
              filter: 'drop-shadow(0 0 50px rgba(34, 211, 238, 1)) drop-shadow(0 0 100px rgba(168, 85, 247, 0.8))',
              animation: 'hologram 3s ease-in-out infinite',
            }}
          />
          {/* Holographic scan line */}
          <div 
            className="absolute inset-0 bg-gradient-to-b from-transparent via-cyan-400/20 to-transparent"
            style={{
              animation: 'scan 2s linear infinite',
              pointerEvents: 'none'
            }}
          />
        </div>
      </div>

      <style jsx>{`
        @keyframes hologram {
          0%, 100% {
            opacity: 1;
            transform: rotateY(0deg) scale(1);
          }
          50% {
            opacity: 0.8;
            transform: rotateY(10deg) scale(1.02);
          }
        }
        @keyframes scan {
          0% {
            transform: translateY(-100%);
          }
          100% {
            transform: translateY(100%);
          }
        }
      `}</style>
    </div>
  );
};