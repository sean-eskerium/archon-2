import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChevronDown, 
  ChevronUp, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Globe, 
  FileText,
  RotateCcw,
  X,
  Search,
  Download,
  Cpu,
  Database,
  Code,
  Zap
} from 'lucide-react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { CrawlProgressData } from '../services/crawlProgressServiceV2';
import { useTerminalScroll } from '../hooks/useTerminalScroll';

interface CrawlingProgressCardProps {
  progressData: CrawlProgressData;
  onComplete: (data: CrawlProgressData) => void;
  onError: (error: string) => void;
  onProgress?: (data: CrawlProgressData) => void;
  onRetry?: () => void;
  onDismiss?: () => void;
}

interface ProgressStep {
  id: string;
  label: string;
  icon: React.ReactNode;
  percentage: number;
  status: 'pending' | 'active' | 'completed' | 'error';
  message?: string;
}

export const CrawlingProgressCard: React.FC<CrawlingProgressCardProps> = ({
  progressData,
  onComplete,
  onError,
  onProgress,
  onRetry,
  onDismiss
}) => {
  const [showDetailedProgress, setShowDetailedProgress] = useState(true);
  const [showLogs, setShowLogs] = useState(false);
  
  // Use the terminal scroll hook for auto-scrolling logs
  const logsContainerRef = useTerminalScroll([progressData.logs], showLogs);

  // Calculate individual progress steps based on current status and percentage
  const getProgressSteps = (): ProgressStep[] => {
    // Check if this is an upload operation
    const isUpload = progressData.uploadType === 'document';
    
    const steps: ProgressStep[] = isUpload ? [
      {
        id: 'reading',
        label: 'Reading File',
        icon: <Download className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      },
      {
        id: 'extracting',
        label: 'Text Extraction',
        icon: <FileText className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      },
      {
        id: 'chunking',
        label: 'Content Chunking',
        icon: <Cpu className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      },
      {
        id: 'creating_source',
        label: 'Creating Source',
        icon: <Database className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      },
      {
        id: 'summarizing',
        label: 'AI Summary',
        icon: <Search className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      },
      {
        id: 'storing',
        label: 'Storing Chunks',
        icon: <Database className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      }
    ] : [
      {
        id: 'analyzing',
        label: 'URL Analysis',
        icon: <Search className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      },
      {
        id: 'crawling',
        label: 'Web Crawling',
        icon: <Globe className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      },
      {
        id: 'processing',
        label: 'Content Processing',
        icon: <Cpu className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      },
      {
        id: 'source_creation',
        label: 'Source Creation',
        icon: <FileText className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      },
      {
        id: 'document_storage',
        label: 'Document Storage',
        icon: <Database className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      },
      {
        id: 'code_storage',
        label: 'Code Examples',
        icon: <Code className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      },
      {
        id: 'finalization',
        label: 'Finalization',
        icon: <Zap className="w-4 h-4" />,
        percentage: 0,
        status: 'pending'
      }
    ];

    // Map current status directly to step progress
    const currentStatus = progressData.status;
    const currentPercentage = progressData.percentage || 0;

    // Define step order for completion tracking
    const stepOrder = isUpload 
      ? ['reading', 'extracting', 'chunking', 'creating_source', 'summarizing', 'storing']
      : ['analyzing', 'crawling', 'processing', 'source_creation', 'document_storage', 'code_storage', 'finalization'];
    
    // Update step progress based on current status
    steps.forEach((step, index) => {
      const stepIndex = stepOrder.indexOf(step.id);
      const currentStepIndex = stepOrder.indexOf(currentStatus);
      
      if (currentStatus === 'error') {
        if (stepIndex <= currentStepIndex) {
          step.status = stepIndex === currentStepIndex ? 'error' : 'completed';
          step.percentage = stepIndex === currentStepIndex ? currentPercentage : 100;
        } else {
          step.status = 'pending';
          step.percentage = 0;
        }
      } else if (currentStatus === 'completed') {
        step.status = 'completed';
        step.percentage = 100;
      } else if (step.id === currentStatus) {
        // This is the active step - use the reported percentage directly
        step.status = 'active';
        step.percentage = currentPercentage;
      } else if (stepIndex < currentStepIndex) {
        // Previous steps are completed
        step.status = 'completed';
        step.percentage = 100;
      } else {
        // Future steps are pending
        step.status = 'pending';
        step.percentage = 0;
      }

      // Set specific messages based on current status
      if (step.status === 'active') {
        // Always use the log message from backend if available
        if (progressData.log) {
          step.message = progressData.log;
        } else if (!progressData.log) {
          // Only use fallback messages if no log provided
          if (isUpload) {
            switch (step.id) {
              case 'reading':
                step.message = `Reading ${progressData.fileName || 'file'}...`;
                break;
              case 'extracting':
                step.message = `Extracting text from ${progressData.fileType || 'document'}...`;
                break;
              case 'chunking':
                step.message = 'Breaking into chunks...';
                break;
              case 'creating_source':
                step.message = 'Creating source entry...';
                break;
              case 'summarizing':
                step.message = 'Generating AI summary...';
                break;
              case 'storing':
                step.message = 'Storing in database...';
                break;
            }
          } else {
            switch (step.id) {
              case 'analyzing':
                step.message = 'Detecting URL type...';
                break;
              case 'crawling':
                step.message = `${progressData.processedPages || 0} of ${progressData.totalPages || 0} pages`;
                break;
              case 'processing':
                step.message = 'Chunking content...';
                break;
              case 'source_creation':
                step.message = 'Creating source records...';
                break;
              case 'document_storage':
                step.message = 'Saving to database...';
                break;
              case 'code_storage':
                step.message = 'Extracting code blocks...';
                break;
              case 'finalization':
                step.message = 'Completing crawl...';
                break;
            }
          }
        }
      }
    });

    return steps;
  };

  const progressSteps = getProgressSteps();
  const overallStatus = progressData.status;

  const getOverallStatusDisplay = () => {
    const isUpload = progressData.uploadType === 'document';
    
    switch (overallStatus) {
      case 'starting':
        return {
          text: isUpload ? 'Starting upload...' : 'Starting crawl...',
          color: 'blue' as const,
          icon: <Clock className="w-4 h-4" />
        };
      case 'completed':
        return {
          text: isUpload ? 'Upload completed!' : 'Crawling completed!',
          color: 'green' as const,
          icon: <CheckCircle className="w-4 h-4" />
        };
      case 'error':
        return {
          text: isUpload ? 'Upload failed' : 'Crawling failed',
          color: 'pink' as const,
          icon: <AlertTriangle className="w-4 h-4" />
        };
      case 'reading':
        return {
          text: 'Reading file...',
          color: 'blue' as const,
          icon: <Download className="w-4 h-4" />
        };
      case 'extracting':
        return {
          text: 'Extracting text...',
          color: 'blue' as const,
          icon: <FileText className="w-4 h-4" />
        };
      case 'chunking':
        return {
          text: 'Processing content...',
          color: 'blue' as const,
          icon: <Cpu className="w-4 h-4" />
        };
      case 'creating_source':
        return {
          text: 'Creating source...',
          color: 'blue' as const,
          icon: <Database className="w-4 h-4" />
        };
      case 'summarizing':
        return {
          text: 'Generating summary...',
          color: 'blue' as const,
          icon: <Search className="w-4 h-4" />
        };
      case 'storing':
        return {
          text: 'Storing chunks...',
          color: 'blue' as const,
          icon: <Database className="w-4 h-4" />
        };
      case 'source_creation':
        return {
          text: 'Creating source records...',
          color: 'blue' as const,
          icon: <FileText className="w-4 h-4" />
        };
      case 'document_storage':
        return {
          text: 'Storing documents...',
          color: 'blue' as const,
          icon: <Database className="w-4 h-4" />
        };
      case 'code_storage':
        return {
          text: 'Processing code examples...',
          color: 'blue' as const,
          icon: <Code className="w-4 h-4" />
        };
      case 'finalization':
        return {
          text: 'Finalizing...',
          color: 'blue' as const,
          icon: <Zap className="w-4 h-4" />
        };
      default:
        const activeStep = progressSteps.find(step => step.status === 'active');
        return {
          text: activeStep ? activeStep.label : 'Processing...',
          color: 'blue' as const,
          icon: activeStep ? activeStep.icon : <Clock className="w-4 h-4" />
        };
    }
  };

  const status = getOverallStatusDisplay();

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  const getStepStatusColor = (stepStatus: string) => {
    switch (stepStatus) {
      case 'completed':
        return 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-500/10';
      case 'active':
        return 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-500/10';
      case 'error':
        return 'text-pink-600 dark:text-pink-400 bg-pink-100 dark:bg-pink-500/10';
      default:
        return 'text-gray-400 dark:text-gray-600 bg-gray-100 dark:bg-gray-500/10';
    }
  };

  return (
    <Card accentColor={status.color} className="relative overflow-hidden">
      {/* Status Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className={`p-2 rounded-md ${
          status.color === 'blue' ? 'bg-blue-100 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400' :
          status.color === 'green' ? 'bg-green-100 dark:bg-green-500/10 text-green-600 dark:text-green-400' :
          status.color === 'pink' ? 'bg-pink-100 dark:bg-pink-500/10 text-pink-600 dark:text-pink-400' :
          'bg-gray-100 dark:bg-gray-500/10 text-gray-600 dark:text-gray-400'
        }`}>
          {status.icon}
        </div>
        <div className="flex-1">
          <h3 className="font-medium text-gray-800 dark:text-white">
            {status.text}
          </h3>
          {progressData.currentUrl && (
            <p className="text-sm text-gray-500 dark:text-zinc-400 truncate">
              {progressData.currentUrl}
            </p>
          )}
        </div>

      </div>



      {/* Detailed Progress Toggle */}
      {progressData.status !== 'completed' && progressData.status !== 'error' && (
        <div className="mb-4">
          <button
            onClick={() => setShowDetailedProgress(!showDetailedProgress)}
            className="flex items-center gap-2 text-sm text-gray-600 dark:text-zinc-400 hover:text-gray-800 dark:hover:text-white transition-colors"
          >
            <FileText className="w-4 h-4" />
            <span>Detailed Progress</span>
            {showDetailedProgress ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      )}

      {/* Multi-Progress Bars */}
      <AnimatePresence>
        {showDetailedProgress && progressData.status !== 'completed' && progressData.status !== 'error' && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden mb-4"
          >
            <div className="space-y-3 p-3 bg-gray-50 dark:bg-zinc-900/50 rounded-md">
              {progressSteps.map((step) => (
                <div key={step.id} className="flex items-center gap-3">
                  <div className={`p-1.5 rounded-md ${getStepStatusColor(step.status)}`}>
                    {step.status === 'active' ? (
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                      >
                        {step.icon}
                      </motion.div>
                    ) : (
                      step.icon
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {step.label}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {Math.round(step.percentage)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-zinc-700 rounded-full h-1.5">
                      <motion.div
                        className={`h-1.5 rounded-full ${
                          step.status === 'completed' ? 'bg-green-500' :
                          step.status === 'active' ? 'bg-blue-500' :
                          step.status === 'error' ? 'bg-pink-500' :
                          'bg-gray-300 dark:bg-gray-600'
                        }`}
                        initial={{ width: 0 }}
                        animate={{ width: `${step.percentage}%` }}
                        transition={{ duration: 0.5, ease: 'easeOut' }}
                      />
                    </div>
                    {step.message && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
                        {step.message}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Progress Details */}
      <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
        {progressData.uploadType === 'document' ? (
          // Upload-specific details
          <>
            {progressData.fileName && (
              <div className="col-span-2">
                <span className="text-gray-500 dark:text-zinc-400">File:</span>
                <span className="ml-2 font-medium text-gray-800 dark:text-white">
                  {progressData.fileName}
                </span>
              </div>
            )}
            {progressData.status === 'completed' && (
              <>
                {progressData.chunksStored && (
                  <div>
                    <span className="text-gray-500 dark:text-zinc-400">Chunks:</span>
                    <span className="ml-2 font-medium text-gray-800 dark:text-white">
                      {formatNumber(progressData.chunksStored)} chunks stored
                    </span>
                  </div>
                )}
                {progressData.wordCount && (
                  <div>
                    <span className="text-gray-500 dark:text-zinc-400">Words:</span>
                    <span className="ml-2 font-medium text-gray-800 dark:text-white">
                      {formatNumber(progressData.wordCount)} words processed
                    </span>
                  </div>
                )}
                {progressData.sourceId && (
                  <div className="col-span-2">
                    <span className="text-gray-500 dark:text-zinc-400">Source ID:</span>
                    <span className="ml-2 font-medium text-gray-800 dark:text-white font-mono text-xs">
                      {progressData.sourceId}
                    </span>
                  </div>
                )}
              </>
            )}
          </>
        ) : (
          // Crawl-specific details
          <>
            {progressData.totalPages && progressData.processedPages !== undefined && (
              <div>
                <span className="text-gray-500 dark:text-zinc-400">Pages:</span>
                <span className="ml-2 font-medium text-gray-800 dark:text-white">
                  {progressData.processedPages} of {progressData.totalPages} pages processed
                </span>
              </div>
            )}
            
            {progressData.status === 'completed' && (
              <>
                {progressData.chunksStored && (
                  <div>
                    <span className="text-gray-500 dark:text-zinc-400">Chunks:</span>
                    <span className="ml-2 font-medium text-gray-800 dark:text-white">
                      {formatNumber(progressData.chunksStored)} chunks stored
                    </span>
                  </div>
                )}
                {progressData.wordCount && (
                  <div>
                    <span className="text-gray-500 dark:text-zinc-400">Words:</span>
                    <span className="ml-2 font-medium text-gray-800 dark:text-white">
                      {formatNumber(progressData.wordCount)} words processed
                    </span>
                  </div>
                )}
                {progressData.duration && (
                  <div className="col-span-2">
                    <span className="text-gray-500 dark:text-zinc-400">Duration:</span>
                    <span className="ml-2 font-medium text-gray-800 dark:text-white">
                      {progressData.duration}
                    </span>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>

      {/* Error Message */}
      {progressData.status === 'error' && progressData.error && (
        <div className="mb-4 p-3 bg-pink-50 dark:bg-pink-500/10 border border-pink-200 dark:border-pink-500/20 rounded-md">
          <p className="text-pink-700 dark:text-pink-400 text-sm">
            {progressData.error}
          </p>
        </div>
      )}

      {/* Console Logs */}
      {progressData.logs && progressData.logs.length > 0 && (
        <div className="border-t border-gray-200 dark:border-zinc-800 pt-4">
          <button
            onClick={() => setShowLogs(!showLogs)}
            className="flex items-center gap-2 text-sm text-gray-600 dark:text-zinc-400 hover:text-gray-800 dark:hover:text-white transition-colors mb-2"
          >
            <FileText className="w-4 h-4" />
            <span>View Console Output</span>
            {showLogs ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          
          <AnimatePresence>
            {showLogs && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div 
                  ref={logsContainerRef}
                  className="bg-gray-900 dark:bg-black rounded-md p-3 max-h-32 overflow-y-auto"
                >
                  <div className="space-y-1 font-mono text-xs">
                    {progressData.logs.map((log, index) => (
                      <div key={index} className="text-green-400">
                        {log}
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Action Buttons */}
      {progressData.status === 'error' && (onRetry || onDismiss) && (
        <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-gray-200 dark:border-zinc-800">
          {onDismiss && (
            <Button 
              onClick={onDismiss}
              variant="ghost" 
              className="text-sm"
            >
              <X className="w-4 h-4 mr-2" />
              Dismiss
            </Button>
          )}
          {onRetry && (
            <Button 
              onClick={onRetry}
              variant="primary" 
              accentColor="blue"
              className="text-sm"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          )}
        </div>
      )}
    </Card>
  );
}; 