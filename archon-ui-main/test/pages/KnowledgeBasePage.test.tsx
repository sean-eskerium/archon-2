import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { KnowledgeBasePage } from '@/pages/KnowledgeBasePage';
import { knowledgeBaseService } from '@/services/knowledgeBaseService';
import { performRAGQuery } from '@/services/api';
import { useToast } from '@/contexts/ToastContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { ToastProvider } from '@/contexts/ToastContext';
import { SettingsProvider } from '@/contexts/SettingsContext';

// Clear mocks that might interfere
vi.unmock('@/contexts/ThemeContext');
vi.unmock('@/contexts/ToastContext');
vi.unmock('@/contexts/SettingsContext');

// Mock the services
vi.mock('@/services/knowledgeBaseService');
vi.mock('@/services/api');

// Test wrapper with all providers
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <MemoryRouter>
    <ThemeProvider>
      <ToastProvider>
        <SettingsProvider>
          {children}
        </SettingsProvider>
      </ToastProvider>
    </ThemeProvider>
  </MemoryRouter>
);

describe('KnowledgeBasePage', () => {
  const mockShowToast = vi.fn();
  
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useToast).mockReturnValue({ 
      showToast: mockShowToast,
      hideToast: vi.fn(),
      toasts: []
    });
  });

  describe('Initial Load', () => {
    it('should load and display knowledge items from the API', async () => {
      const mockItems = {
        items: [
          {
            id: '1',
            title: 'React Documentation',
            url: 'https://react.dev',
            source_id: 'react-docs',
            metadata: {
              knowledge_type: 'technical',
              tags: ['react', 'frontend'],
              source_type: 'url',
              status: 'active',
              description: 'Official React documentation',
              last_scraped: '2024-01-20',
              chunks_count: 150,
              word_count: 50000
            },
            created_at: '2024-01-20T10:00:00Z',
            updated_at: '2024-01-20T10:00:00Z'
          },
          {
            id: '2',
            title: 'Project Management Guide',
            url: 'file://uploads/pm-guide.pdf',
            source_id: 'pm-guide',
            metadata: {
              knowledge_type: 'business',
              tags: ['project', 'management'],
              source_type: 'file',
              file_name: 'pm-guide.pdf',
              file_type: 'pdf',
              status: 'active',
              description: 'Internal project management guidelines',
              chunks_count: 45,
              word_count: 12000,
              page_count: 32
            },
            created_at: '2024-01-18T10:00:00Z',
            updated_at: '2024-01-18T10:00:00Z'
          }
        ],
        total: 2,
        page: 1,
        per_page: 20
      };

      (knowledgeBaseService.getKnowledgeItems as any).mockResolvedValue(mockItems);

      render(
        <TestWrapper>
          <KnowledgeBasePage />
        </TestWrapper>
      );

      // Should show loading initially
      expect(screen.getByText('Knowledge Base')).toBeInTheDocument();
      
      // Wait for items to load
      await waitFor(() => {
        expect(screen.getByText('React Documentation')).toBeInTheDocument();
        expect(screen.getByText('Project Management Guide')).toBeInTheDocument();
      });

      // Should show correct tags
      expect(screen.getByText('react')).toBeInTheDocument();
      expect(screen.getByText('frontend')).toBeInTheDocument();
      expect(screen.getByText('project')).toBeInTheDocument();
      expect(screen.getByText('management')).toBeInTheDocument();

      // Should show correct icons for types
      const techIcon = screen.getByTitle('Technical/Coding');
      const businessIcon = screen.getByTitle('Business/Project');
      expect(techIcon).toBeInTheDocument();
      expect(businessIcon).toBeInTheDocument();
    });

    it('should handle empty knowledge base', async () => {
      (knowledgeBaseService.getKnowledgeItems as any).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        per_page: 20
      });

      render(
        <TestWrapper>
          <KnowledgeBasePage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('No knowledge items found for the selected filter.')).toBeInTheDocument();
      });
    });

    it('should handle loading errors', async () => {
      (knowledgeBaseService.getKnowledgeItems as any).mockRejectedValue(
        new Error('Failed to load knowledge items')
      );

      render(
        <TestWrapper>
          <KnowledgeBasePage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockShowToast).toHaveBeenCalledWith(
          'Failed to load knowledge items',
          'error'
        );
      });
    });
  });

  describe('Filtering', () => {
    it('should filter by knowledge type', async () => {
      const mockAllItems = {
        items: [
          { 
            id: '1',
            title: 'React Documentation',
            url: 'https://react.dev',
            source_id: 'react-docs',
            metadata: { 
              knowledge_type: 'technical' as const,
              tags: ['react'],
              source_type: 'url' as const,
              status: 'active' as const
            },
            created_at: '2024-01-20T10:00:00Z',
            updated_at: '2024-01-20T10:00:00Z'
          },
          { 
            id: '2',
            title: 'Business Documentation',
            url: 'file://business.pdf',
            source_id: 'business-docs',
            metadata: { 
              knowledge_type: 'business' as const,
              tags: ['business'],
              source_type: 'file' as const,
              status: 'active' as const
            },
            created_at: '2024-01-18T10:00:00Z',
            updated_at: '2024-01-18T10:00:00Z'
          }
        ],
        total: 2,
        page: 1,
        per_page: 20
      };

      const mockTechnicalItems = {
        items: [mockAllItems.items[0]],
        total: 1,
        page: 1,
        per_page: 20
      };

      // Use implementation that returns different data based on parameters
      (knowledgeBaseService.getKnowledgeItems as any).mockImplementation((params: any) => {
        if (params?.knowledge_type === 'technical') {
          return Promise.resolve(mockTechnicalItems);
        }
        return Promise.resolve(mockAllItems);
      });

      render(
        <TestWrapper>
          <KnowledgeBasePage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('React Documentation')).toBeInTheDocument();
        expect(screen.getByText('Business Documentation')).toBeInTheDocument();
      });

      // Click technical filter
      const techFilterButton = screen.getByTitle('Technical/Coding');
      fireEvent.click(techFilterButton);

      await waitFor(() => {
        expect(knowledgeBaseService.getKnowledgeItems).toHaveBeenCalledWith({
          knowledge_type: 'technical',
          page: 1,
          per_page: 20
        });
        // Should only show technical docs after filtering
        expect(screen.getByText('React Documentation')).toBeInTheDocument();
        expect(screen.queryByText('Business Documentation')).not.toBeInTheDocument();
      });
    });

    it('should search knowledge items', async () => {
      (knowledgeBaseService.getKnowledgeItems as any).mockResolvedValue({
        items: [],
        total: 0
      });

      render(
        <TestWrapper>
          <KnowledgeBasePage />
        </TestWrapper>
      );

      const searchInput = await screen.findByPlaceholderText('Search knowledge base...');
      fireEvent.change(searchInput, { target: { value: 'react hooks' } });

      // Debounce delay
      await waitFor(() => {
        expect(knowledgeBaseService.getKnowledgeItems).toHaveBeenCalledWith({
          search: 'react hooks',
          page: 1,
          per_page: 20
        });
      }, { timeout: 600 });
    });
  });

  describe('Add Knowledge Modal', () => {
    it('should open add knowledge modal when clicking add button', async () => {
      (knowledgeBaseService.getKnowledgeItems as any).mockResolvedValue({
        items: [],
        total: 0
      });

      render(
        <TestWrapper>
          <KnowledgeBasePage />
        </TestWrapper>
      );

      const addButton = await screen.findByText('Knowledge');
      fireEvent.click(addButton);

      expect(screen.getByText('Add Knowledge Source')).toBeInTheDocument();
      expect(screen.getByText('URL / Website')).toBeInTheDocument();
      expect(screen.getByText('Upload File')).toBeInTheDocument();
    });

    it('should crawl URL when submitting URL form', async () => {
      (knowledgeBaseService.getKnowledgeItems as any).mockResolvedValue({
        items: [],
        total: 0
      });

      (knowledgeBaseService.crawlUrl as any).mockResolvedValue({
        success: true,
        source_id: 'new-docs',
        message: 'Crawling started'
      });

      render(
        <TestWrapper>
          <KnowledgeBasePage />
        </TestWrapper>
      );

      // Open modal
      const addButton = await screen.findByText('Knowledge');
      fireEvent.click(addButton);

      // Fill URL form
      const urlInput = screen.getByPlaceholderText('https://...');
      fireEvent.change(urlInput, { target: { value: 'https://docs.example.com' } });

      // Select knowledge type
      const techTypeButton = screen.getByLabelText('Technical/Coding');
      fireEvent.click(techTypeButton);

      // Add tags
      const tagInput = screen.getByPlaceholderText('Add tags...');
      fireEvent.change(tagInput, { target: { value: 'documentation' } });
      fireEvent.keyDown(tagInput, { key: 'Enter' });

      // Submit
      const submitButton = screen.getByText('Add Source');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(knowledgeBaseService.crawlUrl).toHaveBeenCalledWith({
          url: 'https://docs.example.com',
          knowledge_type: 'technical',
          tags: ['documentation'],
          update_frequency: 7
        });
        expect(mockShowToast).toHaveBeenCalledWith('Crawling started', 'success');
      });
    });

    it('should upload file when submitting file form', async () => {
      (knowledgeBaseService.getKnowledgeItems as any).mockResolvedValue({
        items: [],
        total: 0
      });

      (knowledgeBaseService.uploadDocument as any).mockResolvedValue({
        success: true,
        source_id: 'uploaded-doc',
        filename: 'test.pdf',
        message: 'Document uploaded successfully'
      });

      render(
        <TestWrapper>
          <KnowledgeBasePage />
        </TestWrapper>
      );

      // Open modal
      const addButton = await screen.findByText('Knowledge');
      fireEvent.click(addButton);

      // Switch to file upload
      const fileButton = screen.getByText('Upload File');
      fireEvent.click(fileButton);

      // Create a mock file
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      const fileInput = screen.getByLabelText('Upload Document');
      fireEvent.change(fileInput, { target: { files: [file] } });

      // Select business type
      const businessTypeButton = screen.getByLabelText('Business/Project');
      fireEvent.click(businessTypeButton);

      // Submit
      const submitButton = screen.getByText('Add Source');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(knowledgeBaseService.uploadDocument).toHaveBeenCalledWith(
          file,
          {
            knowledge_type: 'business',
            tags: []
          }
        );
        expect(mockShowToast).toHaveBeenCalledWith('Document uploaded successfully', 'success');
      });
    });
  });

  describe('Knowledge Item Actions', () => {
    it('should delete knowledge item when clicking delete', async () => {
      const mockItems = {
        items: [{
          id: '1',
          title: 'React Docs',
          source_id: 'react-docs',
          metadata: { knowledge_type: 'technical', tags: [] }
        }],
        total: 1
      };

      (knowledgeBaseService.getKnowledgeItems as any).mockResolvedValue(mockItems);
      (knowledgeBaseService.deleteKnowledgeItem as any).mockResolvedValue({
        success: true,
        message: 'Item deleted'
      });

      render(
        <TestWrapper>
          <KnowledgeBasePage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('React Docs')).toBeInTheDocument();
      });

      // Click delete button
      const deleteButton = screen.getByTitle('Delete');
      fireEvent.click(deleteButton);

      // Confirm deletion
      const confirmButton = await screen.findByText('Delete');
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(knowledgeBaseService.deleteKnowledgeItem).toHaveBeenCalledWith('react-docs');
        expect(mockShowToast).toHaveBeenCalledWith('Item deleted', 'success');
      });
    });

    it('should test knowledge item with RAG query', async () => {
      const mockItems = {
        items: [{
          id: '1',
          title: 'React Docs',
          source_id: 'react-docs',
          metadata: { knowledge_type: 'technical', tags: [] }
        }],
        total: 1
      };

      (knowledgeBaseService.getKnowledgeItems as any).mockResolvedValue(mockItems);
      (performRAGQuery as any).mockResolvedValue({
        results: [{
          content: 'React is a JavaScript library...',
          score: 0.95,
          source: 'react-docs'
        }],
        query: 'what is react'
      });

      render(
        <TestWrapper>
          <KnowledgeBasePage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('React Docs')).toBeInTheDocument();
      });

      // Click test button
      const testButton = screen.getByTitle('Test with Query');
      fireEvent.click(testButton);

      // Should open test modal
      expect(screen.getByText('Test Knowledge Source')).toBeInTheDocument();

      // Enter query
      const queryInput = screen.getByPlaceholderText('Enter a test query...');
      fireEvent.change(queryInput, { target: { value: 'what is react' } });

      // Submit query
      const searchButton = screen.getByText('Search');
      fireEvent.click(searchButton);

      await waitFor(() => {
        expect(performRAGQuery).toHaveBeenCalledWith('what is react', {
          source: 'react-docs'
        });
        expect(screen.getByText('React is a JavaScript library...')).toBeInTheDocument();
      });
    });
  });
}); 