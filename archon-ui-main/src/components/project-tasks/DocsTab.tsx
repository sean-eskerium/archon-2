import React, { useState, useEffect } from 'react';
import { Plus, X, Search, Upload, Link as LinkIcon, Check, Brain, Save, History } from 'lucide-react';
import { Button } from '../ui/Button';
import { knowledgeBaseService, KnowledgeItem } from '../../services/knowledgeBaseService';
import { projectService } from '../../services/projectService';
import { useToast } from '../../contexts/ToastContext';
import { Input } from '../ui/Input';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Select } from '../ui/Select';
import { CrawlProgressData, crawlProgressServiceV2 as crawlProgressService } from '../../services/crawlProgressServiceV2';
import { WebSocketState } from '../../services/EnhancedWebSocketService';
import { BlockNoteEditor } from './BlockNoteEditor';
import { VersionHistoryModal } from './VersionHistoryModal';



// Archon-like Block structure
interface ArchonBlock {
  id: string;
  type: 'paragraph' | 'heading_1' | 'heading_2' | 'heading_3' | 'bulleted_list' | 'numbered_list' | 'to_do' | 'callout' | 'divider' | 'quote';
  content: any;
  properties?: {
    title?: string;
    color?: string;
    checked?: boolean;
    text?: string;
  };
}

interface ProjectDoc {
  id: string;
  title: string;
  blocks?: ArchonBlock[]; // Optional - some docs only have content
  created_at: string;
  updated_at: string;
  // Additional fields for Archon MCP format support
  content?: any;
  document_type?: string;
}

interface Task {
  id: string;
  title: string;
  feature: string;
  status: 'backlog' | 'in-progress' | 'review' | 'complete';
}

// Document Templates
const DOCUMENT_TEMPLATES = {
  'prd': {
    name: 'PRD Template',
    icon: '📋',
    blocks: [
      { id: '1', type: 'heading_1' as const, content: 'Product Requirements Document', properties: { title: 'Product Requirements Document' } },
      { id: '2', type: 'heading_2' as const, content: 'Project Overview', properties: { title: 'Project Overview' } },
      { id: '3', type: 'paragraph' as const, content: 'Describe the project overview here...', properties: {} },
      { id: '4', type: 'heading_2' as const, content: 'Goals', properties: { title: 'Goals' } },
      { id: '5', type: 'bulleted_list' as const, content: ['Goal 1', 'Goal 2', 'Goal 3'], properties: {} },
      { id: '6', type: 'heading_2' as const, content: 'Success Criteria', properties: { title: 'Success Criteria' } },
      { id: '7', type: 'bulleted_list' as const, content: ['Criteria 1', 'Criteria 2'], properties: {} },
      { id: '8', type: 'heading_2' as const, content: 'Requirements', properties: { title: 'Requirements' } },
      { id: '9', type: 'numbered_list' as const, content: ['Requirement 1', 'Requirement 2'], properties: {} }
    ]
  },
  'technical_spec': {
    name: 'Technical Spec',
    icon: '⚙️',
    blocks: [
      { id: '1', type: 'heading_1' as const, content: 'Technical Specification', properties: { title: 'Technical Specification' } },
      { id: '2', type: 'heading_2' as const, content: 'Architecture', properties: { title: 'Architecture' } },
      { id: '3', type: 'paragraph' as const, content: 'Describe the technical architecture...', properties: {} },
      { id: '4', type: 'heading_2' as const, content: 'Tech Stack', properties: { title: 'Tech Stack' } },
      { id: '5', type: 'bulleted_list' as const, content: ['Frontend: React + TypeScript', 'Backend: Node.js + Express', 'Database: PostgreSQL'], properties: {} },
      { id: '6', type: 'heading_2' as const, content: 'Implementation Plan', properties: { title: 'Implementation Plan' } },
      { id: '7', type: 'numbered_list' as const, content: ['Phase 1: Setup', 'Phase 2: Core Features', 'Phase 3: Testing'], properties: {} }
    ]
  },
  'meeting_notes': {
    name: 'Meeting Notes',
    icon: '📝',
    blocks: [
      { id: '1', type: 'heading_1' as const, content: 'Meeting Notes', properties: { title: 'Meeting Notes' } },
      { id: '2', type: 'paragraph' as const, content: 'Date: ' + new Date().toLocaleDateString(), properties: {} },
      { id: '3', type: 'heading_2' as const, content: 'Attendees', properties: { title: 'Attendees' } },
      { id: '4', type: 'bulleted_list' as const, content: ['Person 1', 'Person 2'], properties: {} },
      { id: '5', type: 'heading_2' as const, content: 'Agenda', properties: { title: 'Agenda' } },
      { id: '6', type: 'numbered_list' as const, content: ['Topic 1', 'Topic 2'], properties: {} },
      { id: '7', type: 'heading_2' as const, content: 'Action Items', properties: { title: 'Action Items' } },
      { id: '8', type: 'to_do' as const, content: ['Task 1', 'Task 2'], properties: {} }
    ]
  },
  'blank': {
    name: 'Blank Document',
    icon: '📄',
    blocks: [
      { id: '1', type: 'heading_1' as const, content: 'Untitled', properties: { title: 'Untitled' } },
      { id: '2', type: 'paragraph' as const, content: 'Start writing...', properties: {} }
    ]
  }
};

/* ——————————————————————————————————————————— */
/* Main component                                 */
/* ——————————————————————————————————————————— */
export const DocsTab = ({
  tasks,
  project
}: {
  tasks: Task[];
  project?: {
    id: string;
    title: string;
    created_at?: string;
    updated_at?: string;
  } | null;
}) => {
  // Document state
  const [documents, setDocuments] = useState<ProjectDoc[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<ProjectDoc | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  
  // Dark mode detection
  const [isDarkMode, setIsDarkMode] = useState(false);
  
  useEffect(() => {
    const checkDarkMode = () => {
      const htmlElement = document.documentElement;
      const hasDarkClass = htmlElement.classList.contains('dark');
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setIsDarkMode(hasDarkClass || prefersDark);
    };
    
    checkDarkMode();
    
    // Listen for changes
    const observer = new MutationObserver(checkDarkMode);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', checkDarkMode);
    
    return () => {
      observer.disconnect();
      mediaQuery.removeEventListener('change', checkDarkMode);
    };
  }, []);
  
  // Knowledge management state
  const [showTechnicalModal, setShowTechnicalModal] = useState(false);
  const [showBusinessModal, setShowBusinessModal] = useState(false);
  const [selectedTechnicalSources, setSelectedTechnicalSources] = useState<string[]>([]);
  const [selectedBusinessSources, setSelectedBusinessSources] = useState<string[]>([]);
  const [showAddSourceModal, setShowAddSourceModal] = useState(false);
  const [sourceType, setSourceType] = useState<'technical' | 'business'>('technical');
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeItem[]>([]);
  const [progressItems, setProgressItems] = useState<CrawlProgressData[]>([]);
  const { showToast } = useToast();

  // Load project documents from database
  const loadProjectDocuments = async () => {
    if (!project?.id) return;
    
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8080/api/projects/${project.id}`);
      if (!response.ok) throw new Error('Failed to load project documents');
      
      const data = await response.json();
      const docs = data.docs || [];
      
      // Transform docs to ProjectDoc format with unique IDs
      const projectDocuments: ProjectDoc[] = docs.map((doc: any, index: number) => ({
        id: doc.id || `doc-${Date.now()}-${index}`, // Ensure unique IDs
        title: doc.title || 'Untitled Document',
        blocks: doc.blocks || [],
        created_at: doc.created_at || new Date().toISOString(),
        updated_at: doc.updated_at || new Date().toISOString(),
        // Preserve original data for BlockNote conversion
        content: doc.content,
        document_type: doc.document_type
      }));
      
      setDocuments(projectDocuments);
      
      // Auto-select first document if available
      if (projectDocuments.length > 0) {
        setSelectedDocument(projectDocuments[0]);
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
      showToast('Failed to load documents', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Create new document from template
  const createDocumentFromTemplate = async (templateKey: string) => {
    if (!project?.id) return;
    
    const template = DOCUMENT_TEMPLATES[templateKey as keyof typeof DOCUMENT_TEMPLATES];
    if (!template) return;

    // Create template blocks with unique IDs
    const templateBlocks = template.blocks.map(block => ({
      ...block,
      id: `${Date.now()}-${block.id}`
    }));

    // Convert to clean MCP format using existing converter
    const mcpContent = convertArchonBlocksToMCPContent(templateBlocks);

    const newDoc: ProjectDoc = {
      id: `doc-${Date.now()}`,
      title: template.name,
      content: mcpContent,    // Only clean MCP format like E-commerce
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    try {
      setIsSaving(true);
      
      // Get current project data
      const projectResponse = await fetch(`http://localhost:8080/api/projects/${project.id}`);
      if (!projectResponse.ok) throw new Error('Failed to load project');
      
      const projectData = await projectResponse.json();
      const currentDocs = projectData.docs || [];
      
      // Add new document
      const updatedDocs = [...currentDocs, newDoc];

      // Save updated docs back to project
      const response = await fetch(`http://localhost:8080/api/projects/${project.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ docs: updatedDocs })
      });

      if (!response.ok) throw new Error('Failed to create document');
      
      showToast('Document created successfully', 'success');
      setShowTemplateModal(false);
      loadProjectDocuments();
    } catch (error) {
      console.error('Failed to create document:', error);
      showToast('Failed to create document', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  // Save document changes
  const saveDocument = async () => {
    if (!selectedDocument || !project?.id) return;

    try {
      setIsSaving(true);
      
      // Get current project data
      const projectResponse = await fetch(`http://localhost:8080/api/projects/${project.id}`);
      if (!projectResponse.ok) throw new Error('Failed to load project');
      
      const projectData = await projectResponse.json();
      const currentDocs = projectData.docs || [];
      
      // Update the specific document
      const updatedDocs = currentDocs.map((doc: any) => 
        doc.id === selectedDocument.id ? {
          ...selectedDocument,
          updated_at: new Date().toISOString()
        } : doc
      );

      // Save updated docs back to project
      const response = await fetch(`http://localhost:8080/api/projects/${project.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ docs: updatedDocs })
      });

      if (!response.ok) throw new Error('Failed to save document');
      
      showToast('Document saved successfully', 'success');
      setIsEditing(false);
      loadProjectDocuments();
    } catch (error) {
      console.error('Failed to save document:', error);
      showToast('Failed to save document', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  // Note: Block editing functions removed - now handled by BlockNoteEditor internally

  // Load project data including linked sources
  const loadProjectData = async () => {
    if (!project?.id) return;
    
    try {
      const response = await fetch(`http://localhost:8080/api/projects/${project.id}`);
      if (!response.ok) throw new Error('Failed to load project data');
      
      const projectData = await response.json();
      
      // Initialize selected sources from saved project data
      const technicalSourceIds = (projectData.technical_sources || []).map((source: any) => source.source_id);
      const businessSourceIds = (projectData.business_sources || []).map((source: any) => source.source_id);
      
      setSelectedTechnicalSources(technicalSourceIds);
      setSelectedBusinessSources(businessSourceIds);
      
      console.log('Loaded project sources:', {
        technical: technicalSourceIds,
        business: businessSourceIds
      });
    } catch (error) {
      console.error('Failed to load project data:', error);
      showToast('Failed to load project sources', 'error');
    }
  };

  // Load knowledge items and documents on mount
  useEffect(() => {
    loadKnowledgeItems();
    loadProjectDocuments();
    loadProjectData(); // Load saved sources
    
    // Cleanup function to disconnect crawl progress service
    return () => {
      console.log('🧹 DocsTab: Disconnecting crawl progress service');
      crawlProgressService.disconnect();
    };
  }, [project?.id]);

  // Clear selected document when project changes
  useEffect(() => {
    setSelectedDocument(null);
  }, [project?.id]);

  // Existing knowledge loading function
  const loadKnowledgeItems = async (knowledgeType?: 'technical' | 'business') => {
    try {
      setLoading(true);
      const response = await knowledgeBaseService.getKnowledgeItems({
        knowledge_type: knowledgeType,
        page: 1,
        per_page: 50
      });
      setKnowledgeItems(response.items);
    } catch (error) {
      console.error('Failed to load knowledge items:', error);
      showToast('Failed to load knowledge items', 'error');
      setKnowledgeItems([]);
    } finally {
      setLoading(false);
    }
  };

  // Knowledge management helper functions (simplified for brevity)
  const transformToLegacyFormat = (items: KnowledgeItem[]) => {
    return items.map(item => ({
      id: item.id,
      title: item.title,
      type: item.metadata.source_type || 'url',
      lastUpdated: new Date(item.updated_at).toLocaleDateString()
    }));
  };

  const technicalSources = transformToLegacyFormat(
    knowledgeItems.filter(item => item.metadata.knowledge_type === 'technical')
  );
  
  const businessSources = transformToLegacyFormat(
    knowledgeItems.filter(item => item.metadata.knowledge_type === 'business')
  );

  const toggleTechnicalSource = (id: string) => {
    setSelectedTechnicalSources(prev => prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]);
  };
  const toggleBusinessSource = (id: string) => {
    setSelectedBusinessSources(prev => prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]);
  };
  const saveTechnicalSources = async () => {
    if (!project?.id) return;
    
    try {
      await projectService.updateProject(project.id, {
        technical_sources: selectedTechnicalSources
      });
      showToast('Technical sources updated successfully', 'success');
      setShowTechnicalModal(false);
      // Reload project data to reflect the changes
      await loadProjectData();
    } catch (error) {
      console.error('Failed to save technical sources:', error);
      showToast('Failed to update technical sources', 'error');
    }
  };
  
  const saveBusinessSources = async () => {
    if (!project?.id) return;
    
    try {
      await projectService.updateProject(project.id, {
        business_sources: selectedBusinessSources
      });
      showToast('Business sources updated successfully', 'success');
      setShowBusinessModal(false);
      // Reload project data to reflect the changes
      await loadProjectData();
    } catch (error) {
      console.error('Failed to save business sources:', error);
      showToast('Failed to update business sources', 'error');
    }
  };

  const handleProgressComplete = (data: CrawlProgressData) => {
    console.log('Crawl completed:', data);
    setProgressItems(prev => prev.filter(item => item.progressId !== data.progressId));
    loadKnowledgeItems();
    showToast('Crawling completed successfully', 'success');
  };

  const handleProgressError = (error: string) => {
    console.error('Crawl error:', error);
    showToast(`Crawling failed: ${error}`, 'error');
  };

  const handleProgressUpdate = (data: CrawlProgressData) => {
    setProgressItems(prev => 
      prev.map(item => 
        item.progressId === data.progressId ? data : item
      )
    );
  };

  const handleStartCrawl = async (progressId: string, initialData: Partial<CrawlProgressData>) => {
    console.log(`Starting crawl tracking for: ${progressId}`);
    
    const newProgressItem: CrawlProgressData = {
      progressId,
      status: 'starting',
      percentage: 0,
      logs: ['Starting crawl...'],
      ...initialData
    };
    
    setProgressItems(prev => [...prev, newProgressItem]);
    
    const progressCallback = (data: CrawlProgressData) => {
      console.log(`📨 Progress callback called for ${progressId}:`, data);
      
      if (data.progressId === progressId) {
        handleProgressUpdate(data);
        
        if (data.status === 'completed') {
          handleProgressComplete(data);
        } else if (data.status === 'error') {
          handleProgressError(data.error || 'Crawling failed');
        }
      }
    };
    
    try {
      // Use the enhanced streamProgress method for better connection handling
      await crawlProgressService.streamProgressEnhanced(progressId, {
        onMessage: progressCallback,
        onError: (error) => {
          console.error(`❌ WebSocket error for ${progressId}:`, error);
          handleProgressError(`Connection error: ${error.message}`);
        }
      }, {
        autoReconnect: true,
        reconnectDelay: 5000,
        connectionTimeout: 10000
      });
      
      console.log(`✅ WebSocket connected successfully for ${progressId}`);
    } catch (error) {
      console.error(`❌ Failed to establish WebSocket connection:`, error);
      handleProgressError('Failed to connect to progress updates');
    }
  };

  const openAddSourceModal = (type: 'technical' | 'business') => {
    setSourceType(type);
    setShowAddSourceModal(true);
  };

  return (
    <div className="relative min-h-[70vh] pt-8">
      <div className="max-w-6xl pl-8">
        {/* Document Header */}
        <header className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 text-transparent bg-clip-text mb-2">
                Project Docs
              </h2>
              <p className="text-gray-400">{project?.title || 'No project selected'}</p>
            </div>
            
            {/* Document selector and actions */}
            <div className="flex items-center gap-4">
              {documents.length > 0 && (
                <select 
                  value={selectedDocument?.id || ''} 
                  onChange={(e) => {
                    const doc = documents.find(d => d.id === e.target.value);
                    if (doc) {
                      setSelectedDocument(doc);
                    }
                  }}
                  className="bg-white/50 dark:bg-black/70 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white rounded-md px-3 py-2 focus:outline-none focus:border-blue-400"
                >
                  {documents.map(doc => (
                    <option key={doc.id} value={doc.id}>{doc.title}</option>
                  ))}
                </select>
              )}
              
              {selectedDocument && (
                <div className="flex items-center gap-2">
                  {isEditing && (
                    <Button 
                      onClick={saveDocument} 
                      disabled={isSaving}
                      variant="primary" 
                      accentColor="green"
                      className="flex items-center gap-2"
                    >
                      <Save className="w-4 h-4" />
                      {isSaving ? 'Saving...' : 'Save'}
                    </Button>
                  )}
                </div>
              )}

              <Button 
                onClick={() => setShowTemplateModal(true)}
                variant="primary" 
                accentColor="blue"
                className="flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                New Doc
              </Button>
              <Button
                onClick={() => setShowVersionHistory(true)}
                variant="outline"
                className="flex items-center gap-2"
              >
                <History className="w-4 h-4" />
                History
              </Button>
            </div>
          </div>
        </header>

        {/* Document Content */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-500">Loading documents...</div>
          </div>
        ) : selectedDocument ? (
          <BlockNoteEditor
            document={selectedDocument}
            isDarkMode={isDarkMode}
            onSave={async (updatedDocument) => {
              try {
                setIsSaving(true);
                
                // Get current project data to update docs array
                const projectResponse = await fetch(`http://localhost:8080/api/projects/${project?.id}`);
                if (!projectResponse.ok) throw new Error('Failed to load project');
                
                const projectData = await projectResponse.json();
                const currentDocs = projectData.docs || [];
                
                // Update the specific document
                const updatedDocs = currentDocs.map((doc: any) => 
                  doc.id === updatedDocument.id ? updatedDocument : doc
                );

                // Save updated docs back to project using FastAPI
                const response = await fetch(`http://localhost:8080/api/projects/${project?.id}`, {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ docs: updatedDocs })
                });

                if (!response.ok) throw new Error('Failed to save document');
                
                // Update local state
                setSelectedDocument(updatedDocument);
                setDocuments(prev => prev.map(doc => 
                  doc.id === updatedDocument.id ? updatedDocument : doc
                ));
                
                showToast('Document saved successfully', 'success');
              } catch (error) {
                console.error('Failed to save document:', error);
                showToast('Failed to save document', 'error');
              } finally {
                setIsSaving(false);
              }
            }}
            className="mb-8"
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <Brain className="w-16 h-16 mb-4 opacity-50" />
            <p className="text-lg mb-2">No documents found</p>
            <p className="text-sm">Create a new document to get started</p>
          </div>
        )}

        {/* Knowledge Sections */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-12">
          <KnowledgeSection 
            title="Technical Knowledge" 
            color="blue" 
            sources={selectedTechnicalSources.map(id => technicalSources.find(source => source.id === id))} 
            onAddClick={() => setShowTechnicalModal(true)} 
          />
          <KnowledgeSection 
            title="Business Knowledge" 
            color="purple" 
            sources={selectedBusinessSources.map(id => businessSources.find(source => source.id === id))} 
            onAddClick={() => setShowBusinessModal(true)} 
          />
        </div>
      </div>

      {/* Template Selection Modal */}
      {showTemplateModal && (
        <TemplateModal
          onClose={() => setShowTemplateModal(false)}
          onSelectTemplate={createDocumentFromTemplate}
          isCreating={isSaving}
        />
      )}

      {/* Existing Modals (simplified for brevity) */}
      {showTechnicalModal && (
        <SourceSelectionModal 
          title="Select Technical Knowledge Sources" 
          sources={technicalSources} 
          selectedSources={selectedTechnicalSources} 
          onToggleSource={toggleTechnicalSource} 
          onSave={saveTechnicalSources} 
          onClose={() => setShowTechnicalModal(false)} 
          onAddSource={() => openAddSourceModal('technical')} 
        />
      )}
      
      {showBusinessModal && (
        <SourceSelectionModal 
          title="Select Business Knowledge Sources" 
          sources={businessSources} 
          selectedSources={selectedBusinessSources} 
          onToggleSource={toggleBusinessSource} 
          onSave={saveBusinessSources} 
          onClose={() => setShowBusinessModal(false)} 
          onAddSource={() => openAddSourceModal('business')} 
        />
      )}
      
      {showAddSourceModal && (
        <AddKnowledgeModal 
          sourceType={sourceType}
          onClose={() => setShowAddSourceModal(false)} 
          onSuccess={() => {
            loadKnowledgeItems();
            setShowAddSourceModal(false);
          }}
          onStartCrawl={handleStartCrawl}
        />
      )}

      {/* Version History Modal */}
      {showVersionHistory && project && (
        <VersionHistoryModal
          projectId={project.id}
          fieldName="docs"
          isOpen={showVersionHistory}
          onClose={() => setShowVersionHistory(false)}
          onRestore={() => {
            // Reload documents after restore
            loadProjectDocuments();
            setShowVersionHistory(false);
          }}
        />
      )}
    </div>
  );
};

/* ——————————————————————————————————————————— */
/* Helper functions                               */
/* ——————————————————————————————————————————— */

// Convert Archon blocks to clean MCP content format for AI agents
const convertArchonBlocksToMCPContent = (blocks: ArchonBlock[]) => {
  const content: any = {};
  let currentSection = '';
  let currentItems: string[] = [];
  
  for (const block of blocks) {
    if (block.type === 'heading_1') {
      // Main title - skip
      continue;
    }
    
    if (block.type === 'heading_2') {
      // Save previous section if exists
      if (currentSection && currentItems.length > 0) {
        const sectionKey = currentSection.toLowerCase().replace(/\s+/g, '_');
        if (currentItems.length === 1) {
          content[sectionKey] = { description: currentItems[0] };
        } else {
          content[sectionKey] = currentItems;
        }
      }
      
      // Start new section
      currentSection = block.content || block.properties?.text || '';
      currentItems = [];
    } else if (block.type === 'paragraph' && block.content?.trim()) {
      currentItems.push(block.content);
    } else if (block.type === 'bulleted_list' || block.type === 'numbered_list') {
      if (block.content) {
        // Handle array content or string content
        if (Array.isArray(block.content)) {
          currentItems.push(...block.content);
        } else {
          // Split by newlines for concatenated content
          const items = block.content.split('\n').filter((item: string) => item.trim());
          currentItems.push(...items);
        }
      }
    }
  }
  
  // Save final section
  if (currentSection && currentItems.length > 0) {
    const sectionKey = currentSection.toLowerCase().replace(/\s+/g, '_');
    if (currentItems.length === 1) {
      content[sectionKey] = { description: currentItems[0] };
    } else {
      content[sectionKey] = currentItems;
    }
  }
  
  return content;
};

/* ——————————————————————————————————————————— */
/* Helper components                              */
/* ——————————————————————————————————————————— */

// ArchonEditor component removed - replaced with BlockNoteEditor

// Template Modal Component
const TemplateModal: React.FC<{
  onClose: () => void;
  onSelectTemplate: (templateKey: string) => void;
  isCreating: boolean;
}> = ({ onClose, onSelectTemplate, isCreating }) => {
  const templates = Object.entries(DOCUMENT_TEMPLATES);

  return (
    <div className="fixed inset-0 bg-gray-500/50 dark:bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="relative p-6 rounded-md backdrop-blur-md w-full max-w-2xl
          bg-gradient-to-b from-white/80 to-white/60 dark:from-white/10 dark:to-black/30
          border border-gray-200 dark:border-zinc-800/50
          shadow-[0_10px_30px_-15px_rgba(0,0,0,0.1)] dark:shadow-[0_10px_30px_-15px_rgba(0,0,0,0.7)]
          before:content-[''] before:absolute before:top-0 before:left-0 before:right-0 before:h-[2px] 
          before:rounded-t-[4px] before:bg-blue-500 
          before:shadow-[0_0_10px_2px_rgba(59,130,246,0.4)] dark:before:shadow-[0_0_20px_5px_rgba(59,130,246,0.7)]">
        
        <div className="relative z-10">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 text-transparent bg-clip-text">
              Choose a Template
            </h3>
            <button onClick={onClose} className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {templates.map(([key, template]) => (
              <button
                key={key}
                onClick={() => onSelectTemplate(key)}
                disabled={isCreating}
                className="p-4 text-left border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">{template.icon}</span>
                  <h4 className="font-semibold text-gray-900 dark:text-white">{template.name}</h4>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {template.blocks.length} blocks included
                </p>
              </button>
            ))}
          </div>

          {isCreating && (
            <div className="mt-4 flex items-center justify-center gap-2 text-blue-500">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm">Creating document...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const KnowledgeSection: React.FC<{
  title: string;
  color: 'blue' | 'purple' | 'pink' | 'orange';
  sources: any[];
  onAddClick: () => void;
}> = ({
  title,
  color,
  sources = [],
  onAddClick
}) => {
  const colorMap = {
    blue: {
      bg: 'bg-blue-500/10',
      border: 'border-blue-500/30',
      text: 'text-blue-600 dark:text-blue-400',
      buttonBg: 'bg-blue-500/20',
      buttonHover: 'hover:bg-blue-500/30',
      buttonBorder: 'border-blue-500/40',
      buttonShadow: 'hover:shadow-[0_0_15px_rgba(59,130,246,0.3)]'
    },
    purple: {
      bg: 'bg-purple-500/10',
      border: 'border-purple-500/30',
      text: 'text-purple-600 dark:text-purple-400',
      buttonBg: 'bg-purple-500/20',
      buttonHover: 'hover:bg-purple-500/30',
      buttonBorder: 'border-purple-500/40',
      buttonShadow: 'hover:shadow-[0_0_15px_rgba(168,85,247,0.3)]'
    },
    pink: {
      bg: 'bg-pink-500/10',
      border: 'border-pink-500/30',
      text: 'text-pink-600 dark:text-pink-400',
      buttonBg: 'bg-pink-500/20',
      buttonHover: 'hover:bg-pink-500/30',
      buttonBorder: 'border-pink-500/40',
      buttonShadow: 'hover:shadow-[0_0_15px_rgba(236,72,153,0.3)]'
    },
    orange: {
      bg: 'bg-orange-500/10',
      border: 'border-orange-500/30',
      text: 'text-orange-600 dark:text-orange-400',
      buttonBg: 'bg-orange-500/20',
      buttonHover: 'hover:bg-orange-500/30',
      buttonBorder: 'border-orange-500/40',
      buttonShadow: 'hover:shadow-[0_0_15px_rgba(249,115,22,0.3)]'
    }
  };
  return <section>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-bold text-gray-800 dark:text-white flex items-center">
          <span className={`w-2 h-2 rounded-full bg-${color}-400 shadow-[0_0_8px_rgba(59,130,246,0.6)] mr-2`} />
          {title}
        </h3>
        <button onClick={onAddClick} className={`px-3 py-1.5 rounded-md ${colorMap[color].buttonBg} ${colorMap[color].buttonHover} border ${colorMap[color].buttonBorder} ${colorMap[color].text} ${colorMap[color].buttonShadow} transition-all duration-300 flex items-center gap-2`}>
          <Plus className="w-4 h-4" />
          <span className="text-sm">Add Sources</span>
        </button>
      </div>
      <div className={`bg-white/10 dark:bg-black/30 border ${colorMap[color].border} rounded-lg p-4 backdrop-blur-sm relative overflow-hidden min-h-[200px]`}>
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-blue-500/30"></div>
        {sources && sources.length > 0 ? <div className="space-y-3">
            {sources.map(source => source && <div key={source.id} className="flex items-center gap-3 p-2 rounded-md bg-white/10 dark:bg-black/30 border border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 transition-all">
                    {source.type === 'url' ? <LinkIcon className="w-4 h-4 text-blue-600 dark:text-blue-400" /> : <Upload className="w-4 h-4 text-pink-600 dark:text-pink-400" />}
                    <div className="flex-1">
                      <div className="text-gray-800 dark:text-white text-sm font-medium">
                        {source.title}
                      </div>
                      <div className="text-gray-500 text-xs">
                        Updated {source.lastUpdated}
                      </div>
                    </div>
                  </div>)}
          </div> : <div className="flex flex-col items-center justify-center h-[150px] text-gray-500">
            <p className="mb-2">No knowledge sources added yet</p>
            <p className="text-sm">
              Click "Add Sources" to select relevant documents
            </p>
          </div>}
      </div>
    </section>;
};

const SourceSelectionModal: React.FC<{
  title: string;
  sources: any[];
  selectedSources: string[];
  onToggleSource: (id: string) => void;
  onSave: () => void;
  onClose: () => void;
  onAddSource: () => void;
}> = ({
  title,
  sources,
  selectedSources,
  onToggleSource,
  onSave,
  onClose,
  onAddSource
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  // Filter sources based on search query
  const filteredSources = sources.filter(source => source.title.toLowerCase().includes(searchQuery.toLowerCase()));
  return <div className="fixed inset-0 bg-gray-500/50 dark:bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="relative p-6 rounded-md backdrop-blur-md w-full max-w-3xl
          bg-gradient-to-b from-white/80 to-white/60 dark:from-white/10 dark:to-black/30
          border border-gray-200 dark:border-zinc-800/50
          shadow-[0_10px_30px_-15px_rgba(0,0,0,0.1)] dark:shadow-[0_10px_30px_-15px_rgba(0,0,0,0.7)]
          before:content-[''] before:absolute before:top-0 before:left-0 before:right-0 before:h-[2px] 
          before:rounded-t-[4px] before:bg-blue-500 
          before:shadow-[0_0_10px_2px_rgba(59,130,246,0.4)] dark:before:shadow-[0_0_20px_5px_rgba(59,130,246,0.7)]
          after:content-[''] after:absolute after:top-0 after:left-0 after:right-0 after:h-16
          after:bg-gradient-to-b after:from-blue-100 after:to-white dark:after:from-blue-500/20 dark:after:to-blue-500/5
          after:rounded-t-md after:pointer-events-none">
        <div className="relative z-10">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 text-transparent bg-clip-text">
              {title}
            </h3>
            <button onClick={onClose} className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
          {/* Search and Add Source */}
          <div className="flex gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 w-4 h-4" />
              <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search sources..." className="w-full bg-white/50 dark:bg-black/70 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white rounded-md py-2 pl-10 pr-3 focus:outline-none focus:border-blue-400 focus:shadow-[0_0_10px_rgba(59,130,246,0.2)] transition-all duration-300" />
            </div>
            <Button onClick={onAddSource} variant="primary" accentColor="blue" className="shadow-lg shadow-blue-500/20">
              <Plus className="w-4 h-4 mr-2 inline" />
              <span>Add Source</span>
            </Button>
          </div>
          {/* Sources List */}
          <div className="bg-white/50 dark:bg-black/50 border border-gray-200 dark:border-gray-800 rounded-md p-2 max-h-[50vh] overflow-y-auto mb-6">
            {filteredSources.length > 0 ? <div className="space-y-2">
                {filteredSources.map(source => <div key={source.id} onClick={() => onToggleSource(source.id)} className={`flex items-center gap-3 p-3 rounded-md cursor-pointer transition-all duration-200 
                      ${selectedSources.includes(source.id) ? 'bg-blue-100/80 dark:bg-blue-900/30 border border-blue-300 dark:border-blue-500/50' : 'bg-white/50 dark:bg-black/30 border border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700'}`}>
                    <div className={`w-5 h-5 rounded-md border flex items-center justify-center 
                        ${selectedSources.includes(source.id) ? 'bg-blue-500 border-blue-500' : 'border-gray-400 dark:border-gray-600'}`}>
                      {selectedSources.includes(source.id) && <Check className="w-3 h-3 text-white" />}
                    </div>
                    {source.type === 'url' ? <LinkIcon className="w-4 h-4 text-blue-600 dark:text-blue-400" /> : <Upload className="w-4 h-4 text-pink-600 dark:text-pink-400" />}
                    <div className="flex-1">
                      <div className="text-gray-800 dark:text-white text-sm font-medium">
                        {source.title}
                      </div>
                      <div className="text-gray-500 dark:text-gray-500 text-xs">
                        Updated {source.lastUpdated}
                      </div>
                    </div>
                  </div>)}
              </div> : <div className="flex items-center justify-center h-32 text-gray-500 dark:text-gray-500">
                No sources found matching your search
              </div>}
          </div>
          {/* Action Buttons */}
          <div className="flex justify-end gap-3">
            <Button onClick={onClose} variant="ghost">
              Cancel
            </Button>
            <Button onClick={onSave} variant="primary" accentColor="blue" className="shadow-lg shadow-blue-500/20">
              Save Selected ({selectedSources.length})
            </Button>
          </div>
        </div>
      </div>
    </div>;
};

interface AddKnowledgeModalProps {
  sourceType: 'technical' | 'business';
  onClose: () => void;
  onSuccess: () => void;
  onStartCrawl: (progressId: string, initialData: Partial<CrawlProgressData>) => void;
}

const AddKnowledgeModal = ({
  sourceType,
  onClose,
  onSuccess,
  onStartCrawl
}: AddKnowledgeModalProps) => {
  const [method, setMethod] = useState<'url' | 'file'>('url');
  const [url, setUrl] = useState('');
  const [updateFrequency, setUpdateFrequency] = useState('7');
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const { showToast } = useToast();

  const handleSubmit = async () => {
    try {
      setLoading(true);
      
      if (method === 'url') {
        if (!url.trim()) {
          showToast('Please enter a URL', 'error');
          return;
        }
        
        const result = await knowledgeBaseService.crawlUrl({
          url: url.trim(),
          knowledge_type: sourceType,
          tags,
          update_frequency: parseInt(updateFrequency)
        });
        
        // Check if result contains a progressId for streaming
        if ((result as any).progressId) {
          // Start progress tracking
          onStartCrawl((result as any).progressId, {
            currentUrl: url.trim(),
            totalPages: 0,
            processedPages: 0
          });
          
          showToast('Crawling started - tracking progress', 'success');
          onClose(); // Close modal immediately
        } else {
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
          knowledge_type: sourceType,
          tags
        });
        
        showToast((result as any).message || 'Document uploaded successfully', 'success');
        onSuccess();
      }
    } catch (error) {
      console.error('Failed to add knowledge:', error);
      showToast('Failed to add knowledge source', 'error');
    } finally {
      setLoading(false);
    }
  };

  return <div className="fixed inset-0 bg-gray-500/50 dark:bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
      <Card className="w-full max-w-2xl relative before:content-[''] before:absolute before:top-0 before:left-0 before:w-full before:h-[1px] before:bg-green-500">
        <h2 className="text-xl font-bold text-gray-800 dark:text-white mb-6">
          Add {sourceType === 'technical' ? 'Technical' : 'Business'} Knowledge Source
        </h2>
        
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
            <Input label="URL to Scrape" type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://..." accentColor="blue" />
          </div>}
          
        {/* File Upload */}
        {method === 'file' && <div className="mb-6">
            <label htmlFor="file-upload" className="block text-gray-600 dark:text-zinc-400 text-sm mb-2">
              Upload Document
            </label>
            <input 
              id="file-upload"
              type="file"
              accept=".pdf,.md,.doc,.docx,.txt"
              onChange={e => setSelectedFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
            />
            <p className="text-gray-500 dark:text-zinc-600 text-sm mt-1">
              Supports PDF, MD, DOC up to 10MB
            </p>
          </div>}
          
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
            Tags
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