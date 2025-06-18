import React, { useEffect, useState, useRef } from 'react';
import { Search, Grid, Plus, Upload, Link as LinkIcon, Share2, Brain, Filter, BoxIcon, Trash2, List, RefreshCw, X, Globe, FileText, BookOpen } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { GlassCrawlDepthSelector } from '../components/ui/GlassCrawlDepthSelector';
import { useStaggeredEntrance } from '../hooks/useStaggeredEntrance';
import { useToast } from '../contexts/ToastContext';
import { knowledgeBaseService, KnowledgeItem, KnowledgeItemMetadata } from '../services/knowledgeBaseService';
import { knowledgeWebSocket } from '../services/websocketService';
import { CrawlingProgressCard } from '../components/CrawlingProgressCard';
import { CrawlProgressData, crawlProgressServiceV2 as crawlProgressService } from '../services/crawlProgressServiceV2';
import { WebSocketState } from '../services/EnhancedWebSocketService';
import { KnowledgeTable } from '../components/knowledge-base/KnowledgeTable';

const extractDomain = (url: string): string => {
  try {
    const urlObj = new URL(url);
    const hostname = urlObj.hostname;
    
    // Remove 'www.' prefix if present
    const withoutWww = hostname.startsWith('www.') ? hostname.slice(4) : hostname;
    
    // For domains with subdomains, extract the main domain (last 2 parts)
    const parts = withoutWww.split('.');
    if (parts.length > 2) {
      // Return the main domain (last 2 parts: domain.tld)
      return parts.slice(-2).join('.');
    }
    
    return withoutWww;
  } catch {
    return url; // Return original if URL parsing fails
  }
};

interface GroupedKnowledgeItem {
  id: string;
  title: string;
  domain: string;
  items: KnowledgeItem[];
  metadata: KnowledgeItemMetadata;
  created_at: string;
  updated_at: string;
}

const groupItemsByDomain = (items: KnowledgeItem[]): GroupedKnowledgeItem[] => {
  const groups = new Map<string, KnowledgeItem[]>();
  
  // Group items by domain
  items.forEach(item => {
    // Only group URL-based items, not file uploads
    if (item.metadata.source_type === 'url') {
      const domain = extractDomain(item.url);
      const existing = groups.get(domain) || [];
      groups.set(domain, [...existing, item]);
    } else {
      // File uploads remain ungrouped
      groups.set(`file_${item.id}`, [item]);
    }
  });
  
  // Convert groups to GroupedKnowledgeItem objects
  return Array.from(groups.entries()).map(([domain, groupItems]) => {
    const firstItem = groupItems[0];
    const isFileGroup = domain.startsWith('file_');
    
    // Find the latest update timestamp and convert it properly to ISO string
    const latestTimestamp = Math.max(...groupItems.map(item => new Date(item.updated_at).getTime()));
    const latestDate = new Date(latestTimestamp);
    
    return {
      id: isFileGroup ? firstItem.id : `group_${domain}`,
      title: isFileGroup ? firstItem.title : `${domain} (${groupItems.length} sources)`,
      domain: isFileGroup ? 'file' : domain,
      items: groupItems,
      metadata: {
        ...firstItem.metadata,
        // Merge tags from all items in the group
        tags: [...new Set(groupItems.flatMap(item => item.metadata.tags || []))],
      },
      created_at: firstItem.created_at,
      updated_at: latestDate.toISOString(),
    };
  });
};

interface GroupedKnowledgeItemCardProps {
  groupedItem: GroupedKnowledgeItem;
  onDelete: (sourceId: string) => void;
}

const GroupedKnowledgeItemCard = ({
  groupedItem,
  onDelete
}: GroupedKnowledgeItemCardProps) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  const isGrouped = groupedItem.items.length > 1;
  const firstItem = groupedItem.items[0];
  
  // Determine card properties based on the primary item
  const accentColor = firstItem.metadata.source_type === 'url' ? 'blue' : 'pink';
  const TypeIcon = firstItem.metadata.knowledge_type === 'technical' ? BoxIcon : Brain;
  const typeIconColor = firstItem.metadata.knowledge_type === 'technical' ? 'text-blue-500' : 'text-purple-500';
  
  const statusColorMap = {
    active: 'green',
    processing: 'blue',
    error: 'pink'
  };

  const handleDelete = async () => {
    // Call the main delete handler with the group ID
    await onDelete(groupedItem.id);
    setShowDeleteConfirm(false);
  };

  // Get frequency display for the primary item
  const getFrequencyDisplay = () => {
    const frequency = firstItem.metadata.update_frequency;
    if (!frequency || frequency === 0) {
      return { icon: <X className="w-3 h-3" />, text: 'Never', color: 'text-gray-500 dark:text-zinc-500' };
    } else if (frequency === 1) {
      return { icon: <RefreshCw className="w-3 h-3" />, text: 'Daily', color: 'text-green-500' };
    } else if (frequency === 7) {
      return { icon: <RefreshCw className="w-3 h-3" />, text: 'Weekly', color: 'text-blue-500' };
    } else if (frequency === 30) {
      return { icon: <RefreshCw className="w-3 h-3" />, text: 'Monthly', color: 'text-purple-500' };
    } else {
      return { icon: <RefreshCw className="w-3 h-3" />, text: `Every ${frequency} days`, color: 'text-gray-500 dark:text-zinc-500' };
    }
  };

  const frequencyDisplay = getFrequencyDisplay();

  // Calculate total word count
  const totalWordCount = groupedItem.items.reduce((sum, item) => {
    return sum + (item.metadata.word_count || 0);
  }, 0);

  // Format word count with thousands separator
  const formattedWordCount = totalWordCount.toLocaleString();

  // Generate tooltip content for grouped items
  const tooltipContent = isGrouped ? (
    <div className="space-y-1">
      <div className="font-medium text-white">Grouped Sources:</div>
      {groupedItem.items.map((item, index) => (
        <div key={item.id} className="text-sm text-gray-200">
          {index + 1}. {item.source_id}
        </div>
      ))}
    </div>
  ) : null;

  return (
    <Card accentColor={accentColor} className="relative h-full flex flex-col">
      {/* Header section - fixed height */}
      <div className="flex items-center gap-2 mb-3">
        {/* Source type icon */}
        {firstItem.metadata.source_type === 'url' ? <LinkIcon className="w-4 h-4 text-blue-500" /> : <Upload className="w-4 h-4 text-pink-500" />}
        {/* Knowledge type icon */}
        <TypeIcon className={`w-4 h-4 ${typeIconColor}`} />
        <h3 className="text-gray-800 dark:text-white font-medium flex-1 line-clamp-1">
          {isGrouped ? groupedItem.domain : firstItem.title}
        </h3>
        <div className="flex items-center gap-1">
          <button onClick={() => setShowDeleteConfirm(true)} className="p-1 text-gray-500 hover:text-red-500" title="Delete">
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>
      
      {/* Description section - fixed height */}
      <p className="text-gray-600 dark:text-zinc-400 text-sm mb-3 line-clamp-2 h-10">
        {isGrouped 
          ? `${groupedItem.items.length} sources from ${groupedItem.domain}` 
          : (firstItem.metadata.description || 'No description available')
        }
      </p>
      
      {/* Tags section - fixed height for 2 rows */}
      <div className="mb-4 h-16 flex items-start">
        <TagsDisplay tags={groupedItem.metadata.tags || []} />
      </div>
      
      {/* Footer section - pushed to bottom */}
      <div className="flex items-end justify-between mt-auto">
        {/* Left side - frequency and updated stacked */}
        <div className="flex flex-col">
          <div className={`flex items-center gap-1 ${frequencyDisplay.color} mb-1`}>
            {frequencyDisplay.icon}
            <span className="text-sm font-medium">{frequencyDisplay.text}</span>
          </div>
          <span className="text-xs text-gray-500 dark:text-zinc-500">Updated: {new Date(groupedItem.updated_at).toLocaleDateString()}</span>
        </div>
        
        {/* Right side - sources and status inline */}
        <div className="flex items-center gap-2">
          {/* Grouped sources chip - inline with status */}
          {isGrouped && (
            <div 
              className="cursor-pointer relative"
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
            >
              <div className="flex items-center gap-1 px-2 py-1 bg-blue-500/20 border border-blue-500/40 rounded-full backdrop-blur-sm shadow-[0_0_15px_rgba(59,130,246,0.3)] hover:shadow-[0_0_20px_rgba(59,130,246,0.5)] transition-all duration-300">
                <Globe className="w-3 h-3 text-blue-400" />
                <span className="text-xs text-blue-400 font-medium">{groupedItem.items.length}</span>
              </div>
              
              {/* Tooltip */}
              {showTooltip && (
                <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-black dark:bg-zinc-800 text-white text-xs rounded-lg py-2 px-3 shadow-lg z-50 whitespace-nowrap max-w-xs">
                  <div className="font-semibold text-blue-300 mb-1">Grouped Sources:</div>
                  {groupedItem.items.map((item, index) => (
                    <div key={index} className="text-gray-300">
                      {index + 1}. {item.source_id}
                    </div>
                  ))}
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-black dark:border-t-zinc-800"></div>
                </div>
              )}
            </div>
          )}

          {/* Page count - orange neon container like Active button */}
          <div className="relative group">
            <div className="flex items-center gap-1 px-2 py-1 bg-orange-500/20 border border-orange-500/40 rounded-full backdrop-blur-sm shadow-[0_0_15px_rgba(251,146,60,0.3)] transition-all duration-300 cursor-help">
              <FileText className="w-3 h-3 text-orange-400" />
              <span className="text-xs text-orange-400 font-medium">{Math.ceil(totalWordCount / 250).toLocaleString()}</span>
            </div>
            
            {/* Tooltip */}
            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-200 z-50">
              <div className="bg-black dark:bg-zinc-800 text-white text-xs px-3 py-2 rounded-lg shadow-lg whitespace-nowrap">
                <div className="font-medium mb-1">{totalWordCount.toLocaleString()} words</div>
                <div className="text-gray-300 space-y-0.5">
                  <div>= {Math.ceil(totalWordCount / 250).toLocaleString()} pages</div>
                  <div>= {(totalWordCount / 80000).toFixed(1)} average novels</div>
                </div>
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-black dark:border-t-zinc-800"></div>
              </div>
            </div>
          </div>
          
          <Badge color={statusColorMap[firstItem.metadata.status || 'active'] as any}>
            {(firstItem.metadata.status || 'active').charAt(0).toUpperCase() + (firstItem.metadata.status || 'active').slice(1)}
          </Badge>
        </div>
      </div>

      {showDeleteConfirm && (
        <DeleteConfirmModal 
          onConfirm={handleDelete} 
          onCancel={() => setShowDeleteConfirm(false)} 
          title={isGrouped ? "Delete Grouped Sources" : "Delete Knowledge Item"}
          message={isGrouped 
            ? `Are you sure you want to delete all ${groupedItem.items.length} sources from ${groupedItem.domain}? This action cannot be undone.`
            : "Are you sure you want to delete this knowledge item? This action cannot be undone."
          }
        />
      )}
    </Card>
  );
};

export const KnowledgeBasePage = () => {
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [forceReanimate, setForceReanimate] = useState(0);
  const [typeFilter, setTypeFilter] = useState<'all' | 'technical' | 'business'>('all');
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeItem[]>([]);
  const [progressItems, setProgressItems] = useState<CrawlProgressData[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loadingStrategy, setLoadingStrategy] = useState<'websocket' | 'rest' | 'complete'>('websocket');
  const searchTimeoutRef = useRef<NodeJS.Timeout>();
  const loadTimeoutRef = useRef<NodeJS.Timeout>();
  
  const { showToast } = useToast();

  // Single consolidated loading function
  const loadKnowledgeItems = async (options = {}) => {
    try {
      setLoading(true);
      const response = await knowledgeBaseService.getKnowledgeItems({
        knowledge_type: typeFilter === 'all' ? undefined : typeFilter,
        search: searchQuery || undefined,
        page: currentPage,
        per_page: 20,
        ...options
      });
      
      setKnowledgeItems(response.items);
      setTotalItems(response.total);
      setLoadingStrategy('complete');
    } catch (error) {
      console.error('Failed to load knowledge items:', error);
      showToast('Failed to load knowledge items', 'error');
      setKnowledgeItems([]);
      setLoadingStrategy('complete');
    } finally {
      setLoading(false);
    }
  };

  // Consolidated initialization effect - handles both WebSocket and fallback loading
  useEffect(() => {
    let isComponentMounted = true;
    let wsConnected = false;
    let fallbackExecuted = false;

    console.log('🚀 KnowledgeBasePage: Initializing data loading strategy');

    // Clear any existing timeouts
    if (loadTimeoutRef.current) {
      clearTimeout(loadTimeoutRef.current);
    }

    // Try WebSocket connection first
    const connectWebSocket = () => {
      console.log('📡 Attempting WebSocket connection for real-time updates');
      knowledgeWebSocket.connect('/api/knowledge-items/stream');
      
      const handleKnowledgeUpdate = (data: any) => {
        if (!isComponentMounted) return;
        
        if (data.type === 'knowledge_items_update') {
          console.log('✅ WebSocket: Received knowledge items update');
          setKnowledgeItems(data.data.items);
          setTotalItems(data.data.total);
          setLoading(false);
          setLoadingStrategy('websocket');
          wsConnected = true;
        } else if (data.type === 'crawl_completed') {
          console.log('✅ WebSocket: Received crawl completion');
          if (data.data.success) {
            showToast('Crawling completed successfully', 'success');
          } else {
            showToast('Crawling failed', 'error');
          }
          // Reload items to show the new content
          loadKnowledgeItems();
        }
      };
      
      knowledgeWebSocket.addEventListener('knowledge_items_update', handleKnowledgeUpdate);
      
      // Set fallback timeout - only execute if WebSocket hasn't connected and component is still mounted
      loadTimeoutRef.current = setTimeout(() => {
        if (isComponentMounted && !wsConnected && !fallbackExecuted) {
          console.log('⏰ WebSocket fallback: Loading via REST API after timeout');
          fallbackExecuted = true;
          loadKnowledgeItems();
        }
      }, 2000); // Reduced from 3000ms to 2000ms for better UX
      
      return () => {
        knowledgeWebSocket.removeEventListener('knowledge_items_update', handleKnowledgeUpdate);
      };
    };

    const cleanup = connectWebSocket();
    
    return () => {
      console.log('🧹 KnowledgeBasePage: Cleaning up data loading');
      isComponentMounted = false;
      if (loadTimeoutRef.current) {
        clearTimeout(loadTimeoutRef.current);
      }
      cleanup();
      knowledgeWebSocket.disconnect();
      
      // Clean up any active crawl progress connections
      console.log('🧹 Disconnecting crawl progress service');
      crawlProgressService.disconnect();
    };
  }, []); // Only run once on mount

  // Handle filter changes
  useEffect(() => {
    if (loadingStrategy === 'complete') {
      console.log('🔍 Filter changed, reloading knowledge items');
      setCurrentPage(1);
      loadKnowledgeItems({ page: 1 });
      setForceReanimate(prev => prev + 1);
    }
  }, [typeFilter, loadingStrategy]);

  // Handle search with debounce
  useEffect(() => {
    if (loadingStrategy === 'complete') {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
      
      searchTimeoutRef.current = setTimeout(() => {
        console.log('🔎 Search query changed, reloading knowledge items');
        setCurrentPage(1);
        loadKnowledgeItems({ page: 1 });
      }, 500);
      
      return () => {
        if (searchTimeoutRef.current) {
          clearTimeout(searchTimeoutRef.current);
        }
      };
    }
  }, [searchQuery, loadingStrategy]);

  // Filter items based on selected type and search query
  const filteredItems = knowledgeItems.filter(item => {
    // Type filter
    const typeMatch = typeFilter === 'all' ? true : item.metadata.knowledge_type === typeFilter;
    
    // Search filter - search in title, description, tags, and source_id
    const searchMatch = !searchQuery || 
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.metadata.description && item.metadata.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (item.metadata.tags && item.metadata.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))) ||
      item.source_id.toLowerCase().includes(searchQuery.toLowerCase());
    
    return typeMatch && searchMatch;
  });

  // Group items by domain for grid view
  const groupedItems = viewMode === 'grid' ? groupItemsByDomain(filteredItems) : [];

  // Use our custom staggered entrance hook for the page header
  const {
    isVisible: headerVisible,
    containerVariants: headerContainerVariants,
    itemVariants: headerItemVariants,
    titleVariants
  } = useStaggeredEntrance([1, 2], 0.15);

  // Separate staggered entrance for the content that will reanimate on view changes
  const {
    isVisible: contentVisible,
    containerVariants: contentContainerVariants,
    itemVariants: contentItemVariants
  } = useStaggeredEntrance(filteredItems, 0.15, forceReanimate);

  const handleAddKnowledge = () => {
    setIsAddModalOpen(true);
  };

  const handleDeleteItem = async (sourceId: string) => {
    try {
      // Check if this is a grouped item ID
      if (sourceId.startsWith('group_')) {
        // Find the grouped item and delete all its constituent items
        const domain = sourceId.replace('group_', '');
        const groupedItems = groupItemsByDomain(filteredItems);
        const group = groupedItems.find(g => g.domain === domain);
        
        if (group) {
          // Delete all items in the group
          for (const item of group.items) {
            await knowledgeBaseService.deleteKnowledgeItem(item.source_id);
          }
          showToast(`Deleted ${group.items.length} sources from ${domain}`, 'success');
        }
      } else {
        // Single item delete
        const result = await knowledgeBaseService.deleteKnowledgeItem(sourceId);
        showToast((result as any).message || 'Item deleted', 'success');
      }
      loadKnowledgeItems(); // Reload items
    } catch (error) {
      console.error('Failed to delete item:', error);
      showToast('Failed to delete item', 'error');
    }
  };

  // Progress handling functions
  const handleProgressComplete = (data: CrawlProgressData) => {
    console.log('Crawl completed:', data);
    
    // Update the progress item to show completed state first
    setProgressItems(prev => 
      prev.map(item => 
        item.progressId === data.progressId 
          ? { ...data, status: 'completed', percentage: 100 }
          : item
      )
    );
    
    // Show success toast
    const message = data.uploadType === 'document' 
      ? `Document "${data.fileName}" uploaded successfully! ${data.chunksStored || 0} chunks stored.`
      : `Crawling completed for ${data.currentUrl}! ${data.chunksStored || 0} chunks stored.`;
    showToast(message, 'success');
    
    // Remove from progress items after a brief delay to show completion
    setTimeout(() => {
      setProgressItems(prev => prev.filter(item => item.progressId !== data.progressId));
      // Reload knowledge items to show the new item
      loadKnowledgeItems();
    }, 2000); // 2 second delay to show completion state
  };

  const handleProgressError = (error: string, progressId?: string) => {
    console.error('Crawl error:', error);
    showToast(`Crawling failed: ${error}`, 'error');
    
    // Auto-remove failed progress items after 5 seconds to prevent UI clutter
    if (progressId) {
      setTimeout(() => {
        setProgressItems(prev => prev.filter(item => item.progressId !== progressId));
      }, 5000);
    }
  };

  const handleProgressUpdate = (data: CrawlProgressData) => {
    setProgressItems(prev => 
      prev.map(item => 
        item.progressId === data.progressId ? data : item
      )
    );
  };

  const handleRetryProgress = (progressId: string) => {
    // Find the progress item and restart the crawl
    const progressItem = progressItems.find(item => item.progressId === progressId);
    if (progressItem) {
      // Remove the failed progress item
      setProgressItems(prev => prev.filter(item => item.progressId !== progressId));
      // This would typically trigger a new crawl - but that requires knowing the original URL
      showToast('Retry functionality not implemented yet', 'warning');
    }
  };

  const handleStartCrawl = async (progressId: string, initialData: Partial<CrawlProgressData>) => {
    console.log(`🚨 handleStartCrawl called with progressId: ${progressId}`);
    console.log(`🚨 Initial data:`, initialData);
    
    const newProgressItem: CrawlProgressData = {
      progressId,
      status: 'starting',
      percentage: 0,
      logs: ['Starting crawl...'],
      ...initialData
    };
    
    console.log(`🚨 Adding progress item to state`);
    setProgressItems(prev => [...prev, newProgressItem]);
    
    // Set up callbacks for enhanced progress tracking
    const progressCallback = (data: CrawlProgressData) => {
      console.log(`📨 Progress callback called for ${progressId}:`, data);
      
      if (data.progressId === progressId) {
        // Update progress first
        handleProgressUpdate(data);
        
        // Then handle completion/error states
        if (data.status === 'completed') {
          handleProgressComplete(data);
        } else if (data.status === 'error') {
          handleProgressError(data.error || 'Crawling failed', progressId);
        }
      }
    };
    
    const stateChangeCallback = (state: WebSocketState) => {
      console.log(`🔌 WebSocket state changed for ${progressId}: ${state}`);
      
      // Update UI based on connection state if needed
      if (state === WebSocketState.FAILED) {
        handleProgressError('Connection failed - please check your network', progressId);
      }
    };
    
    const errorCallback = (error: Error) => {
      console.error(`❌ WebSocket error for ${progressId}:`, error);
      handleProgressError(`Connection error: ${error.message}`, progressId);
    };
    
    console.log(`🚀 Starting progress stream for ${progressId}`);
    
    try {
      // Use the enhanced streamProgress method with all callbacks
      await crawlProgressService.streamProgressEnhanced(progressId, {
        onMessage: progressCallback,
        onStateChange: stateChangeCallback,
        onError: errorCallback
      }, {
        autoReconnect: true,
        reconnectDelay: 5000,
        connectionTimeout: 10000
      });
      
      console.log(`✅ WebSocket connected successfully for ${progressId}`);
      
      // Wait for connection to be fully established
      await crawlProgressService.waitForConnection(5000);
      
      console.log(`✅ Connection verified for ${progressId}`);
    } catch (error) {
      console.error(`❌ Failed to establish WebSocket connection:`, error);
      handleProgressError('Failed to connect to progress updates', progressId);
    }
  };

  return <div>
      {/* Header with animation - stays static when changing views */}
      <motion.div className="flex justify-between items-center mb-8" initial="hidden" animate="visible" variants={headerContainerVariants}>
        <motion.h1 className="text-3xl font-bold text-gray-800 dark:text-white flex items-center gap-3" variants={titleVariants}>
          <BookOpen className="w-7 h-7 text-green-500 filter drop-shadow-[0_0_8px_rgba(34,197,94,0.8)]" />
          Knowledge Base
        </motion.h1>
        <motion.div className="flex items-center gap-4" variants={headerItemVariants}>
          {/* Search Bar */}
          <div className="relative">
            <Input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search knowledge base..." accentColor="purple" icon={<Search className="w-4 h-4" />} />
          </div>
          {/* Type Filter */}
          <div className="flex items-center bg-gray-50 dark:bg-black border border-gray-200 dark:border-zinc-900 rounded-md overflow-hidden">
            <button onClick={() => setTypeFilter('all')} className={`p-2 ${typeFilter === 'all' ? 'bg-gray-200 dark:bg-zinc-800 text-gray-800 dark:text-white' : 'text-gray-500 dark:text-zinc-500 hover:text-gray-700 dark:hover:text-zinc-300'}`} title="All Types">
              <Filter className="w-4 h-4" />
            </button>
            <button onClick={() => setTypeFilter('technical')} className={`p-2 ${typeFilter === 'technical' ? 'bg-blue-100 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-zinc-500 hover:text-gray-700 dark:hover:text-zinc-300'}`} title="Technical/Coding">
              <BoxIcon className="w-4 h-4" />
            </button>
            <button onClick={() => setTypeFilter('business')} className={`p-2 ${typeFilter === 'business' ? 'bg-purple-100 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400' : 'text-gray-500 dark:text-zinc-500 hover:text-gray-700 dark:hover:text-zinc-300'}`} title="Business/Project">
              <Brain className="w-4 h-4" />
            </button>
          </div>
          {/* View Toggle */}
          <div className="flex items-center bg-gray-50 dark:bg-black border border-gray-200 dark:border-zinc-900 rounded-md overflow-hidden">
            <button onClick={() => setViewMode('grid')} className={`p-2 ${viewMode === 'grid' ? 'bg-purple-100 dark:bg-purple-500/10 text-purple-600 dark:text-purple-500' : 'text-gray-500 dark:text-zinc-500 hover:text-gray-700 dark:hover:text-zinc-300'}`} title="Grid View">
              <Grid className="w-4 h-4" />
            </button>
            <button onClick={() => setViewMode('table')} className={`p-2 ${viewMode === 'table' ? 'bg-blue-100 dark:bg-blue-500/10 text-blue-600 dark:text-blue-500' : 'text-gray-500 dark:text-zinc-500 hover:text-gray-700 dark:hover:text-zinc-300'}`} title="Table View">
              <List className="w-4 h-4" />
            </button>
          </div>
          {/* Add Button */}
          <Button onClick={handleAddKnowledge} variant="primary" accentColor="purple" className="shadow-lg shadow-purple-500/20">
            <Plus className="w-4 h-4 mr-2 inline" />
            <span>Knowledge</span>
          </Button>
        </motion.div>
      </motion.div>
      {/* Main Content */}
      <div className="relative">
        {loading ? (
          <div className="flex flex-col justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500 mb-3"></div>
            <p className="text-sm text-gray-500 dark:text-zinc-400">
              {loadingStrategy === 'websocket' ? 'Connecting to live updates...' : 'Loading knowledge items...'}
            </p>
          </div>
        ) : viewMode === 'table' ? (
          <KnowledgeTable 
            items={filteredItems} 
            onDelete={handleDeleteItem} 
          />
        ) : (
          <>
            {/* Knowledge Items Grid/List with staggered animation that reanimates on view change */}
            <AnimatePresence mode="wait">
              <motion.div key={`view-${viewMode}-filter-${typeFilter}`} initial="hidden" animate="visible" variants={contentContainerVariants} className={`grid ${viewMode === 'grid' ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' : 'grid-cols-1 gap-3'}`}>
                {/* Progress Items */}
                {progressItems.map(progressData => (
                  <motion.div key={progressData.progressId} variants={contentItemVariants}>
                    <CrawlingProgressCard 
                      progressData={progressData}
                      onComplete={handleProgressComplete}
                      onError={(error) => handleProgressError(error, progressData.progressId)}
                      onProgress={handleProgressUpdate}
                      onRetry={() => handleRetryProgress(progressData.progressId)}
                      onDismiss={() => setProgressItems(prev => prev.filter(item => item.progressId !== progressData.progressId))}
                    />
                  </motion.div>
                ))}
                
                {/* Regular Knowledge Items */}
                {viewMode === 'grid' ? (
                  // Grid view - use grouped items
                  groupedItems.length > 0 ? groupedItems.map(groupedItem => (
                    <motion.div key={groupedItem.id} variants={contentItemVariants}>
                      <GroupedKnowledgeItemCard 
                        groupedItem={groupedItem} 
                        onDelete={handleDeleteItem} 
                      />
                    </motion.div>
                  )) : (progressItems.length === 0 && (
                    <motion.div variants={contentItemVariants} className="col-span-full py-10 text-center text-gray-500 dark:text-zinc-400">
                      No knowledge items found for the selected filter.
                    </motion.div>
                  ))
                ) : (
                  // List view - use individual items
                  filteredItems.length > 0 ? filteredItems.map(item => (
                    <motion.div key={item.id} variants={contentItemVariants}>
                      <KnowledgeItemCard item={item} viewMode={viewMode} onDelete={handleDeleteItem} />
                    </motion.div>
                  )) : (progressItems.length === 0 && (
                    <motion.div variants={contentItemVariants} className="col-span-full py-10 text-center text-gray-500 dark:text-zinc-400">
                      No knowledge items found for the selected filter.
                    </motion.div>
                  ))
                )}
              </motion.div>
            </AnimatePresence>
          </>
        )}
      </div>
      {/* Add Knowledge Modal */}
      {isAddModalOpen && <AddKnowledgeModal 
        onClose={() => setIsAddModalOpen(false)} 
        onSuccess={() => {
          loadKnowledgeItems();
          setIsAddModalOpen(false);
        }}
        onStartCrawl={handleStartCrawl}
      />}
    </div>;
};

interface KnowledgeItemCardProps {
  item: KnowledgeItem;
  viewMode: 'grid' | 'table';
  onDelete: (sourceId: string) => void;
}

const KnowledgeItemCard = ({
  item,
  viewMode,
  onDelete
}: KnowledgeItemCardProps) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const statusColorMap = {
    active: 'green',
    processing: 'blue',
    error: 'pink'
  };
  const accentColor = item.metadata.source_type === 'url' ? 'blue' : 'pink';
  
  // Get the type icon
  const TypeIcon = item.metadata.knowledge_type === 'technical' ? BoxIcon : Brain;
  const typeIconColor = item.metadata.knowledge_type === 'technical' ? 'text-blue-500' : 'text-purple-500';

  const handleDelete = () => {
    onDelete(item.source_id);
    setShowDeleteConfirm(false);
  };

  // Get frequency display - based on update_frequency from database
  const getFrequencyDisplay = () => {
    const frequency = item.metadata.update_frequency;
    if (!frequency || frequency === 0) {
      return { icon: <X className="w-3 h-3" />, text: 'Never', color: 'text-gray-500 dark:text-zinc-500' };
    } else if (frequency === 1) {
      return { icon: <RefreshCw className="w-3 h-3" />, text: 'Daily', color: 'text-green-500' };
    } else if (frequency === 7) {
      return { icon: <RefreshCw className="w-3 h-3" />, text: 'Weekly', color: 'text-blue-500' };
    } else if (frequency === 30) {
      return { icon: <RefreshCw className="w-3 h-3" />, text: 'Monthly', color: 'text-purple-500' };
    } else {
      return { icon: <RefreshCw className="w-3 h-3" />, text: `Every ${frequency} days`, color: 'text-gray-500 dark:text-zinc-500' };
    }
  };

  const frequencyDisplay = getFrequencyDisplay();

  return <Card accentColor={accentColor} className="h-full flex flex-col">
      {/* Header section - fixed height */}
      <div className="flex items-center gap-2 mb-3">
        {/* Source type icon */}
        {item.metadata.source_type === 'url' ? <LinkIcon className="w-4 h-4 text-blue-500" /> : <Upload className="w-4 h-4 text-pink-500" />}
        {/* Knowledge type icon */}
        <TypeIcon className={`w-4 h-4 ${typeIconColor}`} />
        <h3 className="text-gray-800 dark:text-white font-medium flex-1 line-clamp-1">
          {item.title}
        </h3>
        <div className="flex items-center gap-1">
          <button onClick={() => setShowDeleteConfirm(true)} className="p-1 text-gray-500 hover:text-red-500" title="Delete">
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>
      
      {/* Description section - fixed height */}
      <p className="text-gray-600 dark:text-zinc-400 text-sm mb-3 line-clamp-2 h-10">
        {item.metadata.description || 'No description available'}
      </p>
      
      {/* Tags section - fixed height for 2 rows */}
      <div className="mb-4 h-16 flex items-start">
        <TagsDisplay tags={item.metadata.tags || []} />
      </div>
      
      {/* Footer section - pushed to bottom */}
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-zinc-500 mt-auto">
        <div className="flex items-center gap-3">
          <span>Updated: {new Date(item.updated_at).toLocaleDateString()}</span>
          <div className={`flex items-center gap-1 ${frequencyDisplay.color}`}>
            {frequencyDisplay.icon}
            <span>{frequencyDisplay.text}</span>
          </div>
        </div>
        <Badge color={statusColorMap[item.metadata.status || 'active'] as any}>
          {(item.metadata.status || 'active').charAt(0).toUpperCase() + (item.metadata.status || 'active').slice(1)}
        </Badge>
      </div>
      {showDeleteConfirm && <DeleteConfirmModal 
        onConfirm={handleDelete} 
        onCancel={() => setShowDeleteConfirm(false)} 
        title="Delete Knowledge Item"
        message="Are you sure you want to delete this knowledge item? This action cannot be undone."
      />}
    </Card>;
};

interface DeleteConfirmModalProps {
  onConfirm: () => void;
  onCancel: () => void;
  title: string;
  message: string;
}

const DeleteConfirmModal = ({ onConfirm, onCancel, title, message }: DeleteConfirmModalProps) => {
  return <div className="fixed inset-0 bg-gray-500/50 dark:bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
    <Card className="w-full max-w-md">
      <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
        {title}
      </h3>
      <p className="text-gray-600 dark:text-zinc-400 mb-6">
        {message}
      </p>
      <div className="flex justify-end gap-4">
        <Button onClick={onCancel} variant="ghost">
          Cancel
        </Button>
        <Button onClick={onConfirm} variant="primary" accentColor="pink">
          Delete
        </Button>
      </div>
    </Card>
  </div>;
};

interface AddKnowledgeModalProps {
  onClose: () => void;
  onSuccess: () => void;
  onStartCrawl: (progressId: string, initialData: Partial<CrawlProgressData>) => void;
}

const AddKnowledgeModal = ({
  onClose,
  onSuccess,
  onStartCrawl
}: AddKnowledgeModalProps) => {
  const [method, setMethod] = useState<'url' | 'file'>('url');
  const [url, setUrl] = useState('');
  const [updateFrequency, setUpdateFrequency] = useState('7');
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState('');
  const [knowledgeType, setKnowledgeType] = useState<'technical' | 'business'>('technical');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [crawlDepth, setCrawlDepth] = useState(2);
  const [showDepthTooltip, setShowDepthTooltip] = useState(false);
  const { showToast } = useToast();

  // URL validation function that checks domain existence
  const validateUrl = async (url: string): Promise<{ isValid: boolean; error?: string; formattedUrl?: string }> => {
    try {
      // Basic format validation and URL formatting
      let formattedUrl = url.trim();
      if (!formattedUrl.startsWith('http://') && !formattedUrl.startsWith('https://')) {
        formattedUrl = `https://${formattedUrl}`;
      }
      
      // Check if it's a valid URL format
      let urlObj;
      try {
        urlObj = new URL(formattedUrl);
      } catch (urlError) {
        return { isValid: false, error: 'Please enter a valid URL format (e.g., https://example.com)' };
      }
      
      // Check if hostname has a valid domain structure
      const hostname = urlObj.hostname;
      if (!hostname || hostname === 'localhost' || /^\d+\.\d+\.\d+\.\d+$/.test(hostname)) {
        // Allow localhost and IP addresses for development
        return { isValid: true, formattedUrl };
      }
      
      // Check if domain has at least one dot (basic domain validation)
      if (!hostname.includes('.')) {
        return { isValid: false, error: 'Please enter a valid domain name (e.g., example.com)' };
      }
      
      // Check if domain has a valid TLD (at least 2 characters after the last dot)
      const parts = hostname.split('.');
      const tld = parts[parts.length - 1];
      if (tld.length < 2) {
        return { isValid: false, error: 'Please enter a valid domain with a proper extension (e.g., .com, .org)' };
      }
      
      // Basic DNS check by trying to resolve the domain
      try {
        const response = await fetch(`https://dns.google/resolve?name=${hostname}&type=A`, {
          method: 'GET',
          headers: { 'Accept': 'application/json' }
        });
        
        if (response.ok) {
          const dnsResult = await response.json();
          if (dnsResult.Status === 0 && dnsResult.Answer && dnsResult.Answer.length > 0) {
            return { isValid: true, formattedUrl };
          } else {
            return { isValid: false, error: `Domain "${hostname}" could not be resolved. Please check the URL.` };
          }
        } else {
          // If DNS check fails, allow the URL (might be a temporary DNS issue)
          console.warn('DNS check failed, allowing URL anyway:', hostname);
          return { isValid: true, formattedUrl };
        }
      } catch (dnsError) {
        // If DNS check fails, allow the URL (might be a network issue)
        console.warn('DNS check error, allowing URL anyway:', dnsError);
        return { isValid: true, formattedUrl };
      }
    } catch (error) {
      return { isValid: false, error: 'URL validation failed. Please check the URL format.' };
    }
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      
      if (method === 'url') {
        if (!url.trim()) {
          showToast('Please enter a URL', 'error');
          return;
        }
        
        // Validate URL and check domain existence
        showToast('Validating URL...', 'info');
        const validation = await validateUrl(url);
        
        if (!validation.isValid) {
          showToast(validation.error || 'Invalid URL', 'error');
          return;
        }
        
        const formattedUrl = validation.formattedUrl!;
        setUrl(formattedUrl); // Update the input field to show the corrected URL
        
        const result = await knowledgeBaseService.crawlUrl({
          url: formattedUrl,
          knowledge_type: knowledgeType,
          tags,
          update_frequency: parseInt(updateFrequency),
          max_depth: crawlDepth
        });
        
        console.log('🔍 Crawl URL result:', result);
        
        // Check if result contains a progressId for streaming
        if ((result as any).progressId) {
          console.log('✅ Got progressId:', (result as any).progressId);
          console.log('✅ About to call onStartCrawl function');
          console.log('✅ onStartCrawl function is:', onStartCrawl);
          
          // Start progress tracking
          onStartCrawl((result as any).progressId, {
            currentUrl: formattedUrl,
            totalPages: 0,
            processedPages: 0
          });
          
          console.log('✅ onStartCrawl called successfully');
          
          showToast('Crawling started - tracking progress', 'success');
          onClose(); // Close modal immediately
        } else {
          console.log('❌ No progressId in result');
          console.log('❌ Result structure:', JSON.stringify(result, null, 2));
          
          // Fallback for non-streaming response
          showToast((result as any).message || 'Crawling started', 'success');
          onSuccess();
        }
      } else {
        if (!selectedFile) {
          showToast('Please select a file', 'error');
          return;
        }
        
        const result = await knowledgeBaseService.uploadDocument(selectedFile, {
          knowledge_type: knowledgeType,
          tags
        });
        
        if (result.success && result.progressId) {
          console.log(`📄 Upload started with progressId: ${result.progressId}`);
          
          // Start progress tracking for upload
          onStartCrawl(result.progressId, {
            currentUrl: `file://${selectedFile.name}`,
            totalPages: 1,
            processedPages: 0,
            percentage: 0,
            status: 'starting',
            logs: [`Starting upload of ${selectedFile.name}`],
            uploadType: 'document',
            fileName: selectedFile.name,
            fileType: selectedFile.type
          });
          
          console.log('✅ onStartCrawl called successfully for upload');
          
          showToast('Document upload started - tracking progress', 'success');
          onClose(); // Close modal immediately
        } else {
          console.log('❌ No progressId in upload result');
          console.log('❌ Upload result structure:', JSON.stringify(result, null, 2));
          
          // Fallback for non-streaming response
          showToast((result as any).message || 'Document uploaded successfully', 'success');
          onSuccess();
        }
      }
    } catch (error) {
      console.error('Failed to add knowledge:', error);
      showToast('Failed to add knowledge source', 'error');
    } finally {
      setLoading(false);
    }
  };

  return <div className="fixed inset-0 bg-gray-500/50 dark:bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl relative before:content-[''] before:absolute before:top-0 before:left-0 before:w-full before:h-[1px] before:bg-green-500 p-8">
        <h2 className="text-xl font-bold text-gray-800 dark:text-white mb-8">
          Add Knowledge Source
        </h2>
        {/* Knowledge Type Selection */}
        <div className="mb-6">
          <label className="block text-gray-600 dark:text-zinc-400 text-sm mb-2">
            Knowledge Type
          </label>
          <div className="flex gap-4">
            <label className={`
                flex-1 p-4 rounded-md border cursor-pointer transition flex items-center justify-center gap-2
                ${knowledgeType === 'technical' ? 'border-blue-500 text-blue-600 dark:text-blue-500 bg-blue-50 dark:bg-blue-500/5' : 'border-gray-200 dark:border-zinc-900 text-gray-500 dark:text-zinc-400 hover:border-blue-300 dark:hover:border-blue-500/30'}
              `}>
              <input type="radio" name="knowledgeType" value="technical" checked={knowledgeType === 'technical'} onChange={() => setKnowledgeType('technical')} className="sr-only" />
              <BoxIcon className="w-5 h-5" />
              <span>Technical/Coding</span>
            </label>
            <label className={`
                flex-1 p-4 rounded-md border cursor-pointer transition flex items-center justify-center gap-2
                ${knowledgeType === 'business' ? 'border-purple-500 text-purple-600 dark:text-purple-500 bg-purple-50 dark:bg-purple-500/5' : 'border-gray-200 dark:border-zinc-900 text-gray-500 dark:text-zinc-400 hover:border-purple-300 dark:hover:border-purple-500/30'}
              `}>
              <input type="radio" name="knowledgeType" value="business" checked={knowledgeType === 'business'} onChange={() => setKnowledgeType('business')} className="sr-only" />
              <Brain className="w-5 h-5" />
              <span>Business/Project</span>
            </label>
          </div>
        </div>
        {/* Source Type Selection */}
        <div className="flex gap-4 mb-6">
          <button onClick={() => setMethod('url')} className={`flex-1 p-4 rounded-md border ${method === 'url' ? 'border-blue-500 text-blue-600 dark:text-blue-500 bg-blue-50 dark:bg-blue-500/5' : 'border-gray-200 dark:border-zinc-900 text-gray-500 dark:text-zinc-400 hover:border-blue-300 dark:hover:border-blue-500/30'} transition flex items-center justify-center gap-2`}>
            <LinkIcon className="w-4 h-4" />
            <span>URL / Website</span>
          </button>
          <button onClick={() => setMethod('file')} className={`flex-1 p-4 rounded-md border ${method === 'file' ? 'border-pink-500 text-pink-600 dark:text-pink-500 bg-pink-50 dark:bg-pink-500/5' : 'border-gray-200 dark:border-zinc-900 text-gray-500 dark:text-zinc-400 hover:border-pink-300 dark:hover:border-pink-500/30'} transition flex items-center justify-center gap-2`}>
            <Upload className="w-4 h-4" />
            <span>Upload File</span>
          </button>
        </div>
        {/* URL Input */}
        {method === 'url' && <div className="mb-6">
            <Input 
              label="URL to Scrape" 
              type="url" 
              value={url} 
              onChange={e => setUrl(e.target.value)} 
              placeholder="https://example.com or example.com" 
              accentColor="blue" 
            />
            {url && !url.startsWith('http://') && !url.startsWith('https://') && (
              <p className="text-amber-600 dark:text-amber-400 text-sm mt-1">
                ℹ️ Will automatically add https:// prefix
              </p>
            )}
          </div>}
        {/* File Upload */}
        {method === 'file' && (
          <div className="mb-6">
            <label className="block text-gray-600 dark:text-zinc-400 text-sm mb-2">
              Upload Document
            </label>
            <div className="relative">
              <input 
                id="file-upload"
                type="file"
                accept=".pdf,.md,.doc,.docx,.txt"
                onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                className="sr-only"
              />
              <label 
                htmlFor="file-upload"
                className="flex items-center justify-center gap-3 w-full p-6 rounded-md border-2 border-dashed cursor-pointer transition-all duration-300
                  bg-blue-500/10 hover:bg-blue-500/20 
                  border-blue-500/30 hover:border-blue-500/50
                  text-blue-600 dark:text-blue-400
                  hover:shadow-[0_0_15px_rgba(59,130,246,0.3)]
                  backdrop-blur-sm"
              >
                <Upload className="w-6 h-6" />
                <div className="text-center">
                  <div className="font-medium">
                    {selectedFile ? selectedFile.name : 'Choose File'}
                  </div>
                  <div className="text-sm opacity-75 mt-1">
                    {selectedFile ? `${(selectedFile.size / 1024 / 1024).toFixed(2)} MB` : 'Click to browse or drag and drop'}
                  </div>
                </div>
              </label>
            </div>
            <p className="text-gray-500 dark:text-zinc-600 text-sm mt-2">
              Supports PDF, MD, DOC up to 10MB
            </p>
          </div>
        )}
        {/* Crawl Depth - Only for URLs */}
        {method === 'url' && (
          <div className="mb-6">
            <label className="block text-gray-600 dark:text-zinc-400 text-sm mb-4">
              Crawl Depth
              <button
                type="button"
                className="ml-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                onMouseEnter={() => setShowDepthTooltip(true)}
                onMouseLeave={() => setShowDepthTooltip(false)}
              >
                <svg className="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
            </label>
            
            <GlassCrawlDepthSelector
              value={crawlDepth}
              onChange={setCrawlDepth}
              showTooltip={showDepthTooltip}
              onTooltipToggle={setShowDepthTooltip}
            />
          </div>
        )}
        
        {/* Update Frequency */}
        {method === 'url' && <div className="mb-6">
            <Select label="Update Frequency" value={updateFrequency} onChange={e => setUpdateFrequency(e.target.value)} options={[{
          value: '1',
          label: 'Daily'
        }, {
          value: '7',
          label: 'Weekly'
        }, {
          value: '30',
          label: 'Monthly'
        }, {
          value: '0',
          label: 'Never'
        }]} accentColor="blue" />
          </div>}
        {/* Tags */}
        <div className="mb-6">
          <label className="block text-gray-600 dark:text-zinc-400 text-sm mb-2">
            Tags (AI will add recommended tags if left blank)
          </label>
          <div className="flex flex-wrap gap-2 mb-2">
            {tags.map(tag => <Badge key={tag} color="purple" variant="outline">
                {tag}
              </Badge>)}
          </div>
          <Input type="text" value={newTag} onChange={e => setNewTag(e.target.value)} onKeyDown={e => {
          if (e.key === 'Enter' && newTag.trim()) {
            setTags([...tags, newTag.trim()]);
            setNewTag('');
          }
        }} placeholder="Add tags..." accentColor="purple" />
        </div>
        {/* Action Buttons */}
        <div className="flex justify-end gap-4">
          <Button onClick={onClose} variant="ghost" disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} variant="primary" accentColor={method === 'url' ? 'blue' : 'pink'} disabled={loading}>
            {loading ? 'Adding...' : 'Add Source'}
          </Button>
        </div>
      </Card>
    </div>;
};

interface TagsDisplayProps {
  tags: string[];
}

const TagsDisplay = ({ tags }: TagsDisplayProps) => {
  const [showTooltip, setShowTooltip] = useState(false);
  
  if (!tags || tags.length === 0) return null;
  
  // Limit to first 4 tags to ensure we stay within 2 rows (approximate)
  const visibleTags = tags.slice(0, 4);
  const remainingTags = tags.slice(4);
  const hasMoreTags = remainingTags.length > 0;

  return (
    <div className="w-full">
      <div className="flex flex-wrap gap-2 h-full">
        {visibleTags.map((tag, index) => (
          <Badge key={index} color="purple" variant="outline" className="text-xs">
            {tag}
          </Badge>
        ))}
        {hasMoreTags && (
          <div 
            className="cursor-pointer relative"
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
          >
            <Badge color="purple" variant="outline" className="bg-purple-100/50 dark:bg-purple-900/30 border-dashed text-xs">
              +{remainingTags.length} more...
            </Badge>
            {showTooltip && (
              <div className="absolute top-full mt-2 left-1/2 transform -translate-x-1/2 bg-black dark:bg-zinc-800 text-white text-xs rounded-lg py-2 px-3 shadow-lg z-50 whitespace-nowrap max-w-xs">
                <div className="font-semibold text-purple-300 mb-1">Additional Tags:</div>
                {remainingTags.map((tag, index) => (
                  <div key={index} className="text-gray-300">
                    • {tag}
                  </div>
                ))}
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-b-black dark:border-b-zinc-800"></div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};