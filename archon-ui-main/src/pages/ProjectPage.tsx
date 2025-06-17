import { useState, useEffect, useCallback } from 'react';
import { useToast } from '../contexts/ToastContext';
import { motion, AnimatePresence } from 'framer-motion';
import { useStaggeredEntrance } from '../hooks/useStaggeredEntrance';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/project-tasks/Tabs';
import { DocsTab } from '../components/project-tasks/DocsTab';
import { FeaturesTab } from '../components/project-tasks/FeaturesTab';
import { DataTab } from '../components/project-tasks/DataTab';
import { TasksTab } from '../components/project-tasks/TasksTab';
import { Button } from '../components/ui/Button';
import { ChevronRight, ShoppingCart, Code, Briefcase, Layers, Plus, X, AlertCircle, Loader2, Heart, BarChart3, Trash2, Pin } from 'lucide-react';

// Import our service layer and types
import { projectService } from '../services/projectService';
import type { Project, CreateProjectRequest } from '../types/project';
import type { Task } from '../components/project-tasks/TaskTableView';
import { ProjectCreationProgressCard } from '../components/ProjectCreationProgressCard';
import { projectCreationProgressService } from '../services/projectCreationProgressService';
import type { ProjectCreationProgressData } from '../services/projectCreationProgressService';

interface ProjectPageProps {
  className?: string;
  'data-id'?: string;
}

// Icon mapping for projects (since database stores icon names as strings)
const getProjectIcon = (iconName?: string) => {
  const iconMap = {
    'ShoppingCart': <ShoppingCart className="w-5 h-5" />,
    'Briefcase': <Briefcase className="w-5 h-5" />,
    'Code': <Code className="w-5 h-5" />,
    'Layers': <Layers className="w-5 h-5" />,
    'BarChart': <BarChart3 className="w-5 h-5" />,
    'Heart': <Heart className="w-5 h-5" />,
  };
  return iconMap[iconName as keyof typeof iconMap] || <Briefcase className="w-5 h-5" />;
};

export function ProjectPage({
  className = '',
  'data-id': dataId
}: ProjectPageProps) {
  // State management for real data
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [tasksError, setTasksError] = useState<string | null>(null);
  
  // UI state
  const [activeTab, setActiveTab] = useState('tasks');
  const [showProjectDetails, setShowProjectDetails] = useState(false);
  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false);
  
  // New project form state
  const [newProjectForm, setNewProjectForm] = useState({
    title: '',
    description: '',
    color: 'blue' as const
  });
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  
  // Handler for retrying project creation
  const handleRetryProjectCreation = (progressId: string) => {
    // Remove the failed project
    setProjects((prev) => prev.filter(p => p.id !== `temp_${progressId}`));
    // Re-open the modal for retry
    setIsNewProjectModalOpen(true);
  };

  // State for delete confirmation modal
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<{ id: string; title: string } | null>(null);

  const { showToast } = useToast();

  // Load projects on component mount
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        console.log(`[INITIAL LOAD] Starting loadInitialData...`);
        // Load the projects with their database pinned state
        const projectsData = await projectService.listProjects();
        console.log(`[INITIAL LOAD] Projects loaded from API:`, projectsData.map(p => ({id: p.id, title: p.title, pinned: p.pinned})));
        
        // Sort projects - pinned first, then alphabetically
        const sortedProjects = [...projectsData].sort((a, b) => {
          if (a.pinned && !b.pinned) return -1;
          if (!a.pinned && b.pinned) return 1;
          return a.title.localeCompare(b.title);
        });
        console.log(`[INITIAL LOAD] Projects after sorting:`, sortedProjects.map(p => ({id: p.id, title: p.title, pinned: p.pinned})));
        
        setProjects(sortedProjects);
        
        // Find pinned project if any
        const pinnedProject = sortedProjects.find(project => project.pinned);
        console.log(`[INITIAL LOAD] Pinned project:`, pinnedProject ? {id: pinnedProject.id, title: pinnedProject.title, pinned: pinnedProject.pinned} : 'None');
        
        // Always select the pinned project if one exists, otherwise default to first project
        if (sortedProjects.length > 0) {
          // Select either the pinned project or the first project if no pinned project
          const projectToSelect = pinnedProject || sortedProjects[0];
          console.log(`[INITIAL LOAD] Selecting project:`, {id: projectToSelect.id, title: projectToSelect.title, pinned: projectToSelect.pinned});
          setSelectedProject(projectToSelect);
          setShowProjectDetails(true);
        } else {
          console.log(`[INITIAL LOAD] No projects to select`);
        }
        
      } catch (error) {
        console.error('Failed to load projects:', error);
        setProjectsError(error instanceof Error ? error.message : 'Failed to load projects');
      } finally {
        setIsLoadingProjects(false);
      }
    };
    
    loadInitialData();
  }, []);

  // Load tasks when project is selected
  useEffect(() => {
    if (selectedProject) {
      loadTasksForProject(selectedProject.id);
    }
  }, [selectedProject]);

  const loadProjects = async () => {
    try {
      console.log(`[LOAD PROJECTS] Starting loadProjects...`);
      setIsLoadingProjects(true);
      setProjectsError(null);
      
      const projectsData = await projectService.listProjects();
      console.log(`[LOAD PROJECTS] Projects loaded from API:`, projectsData.map(p => ({id: p.id, title: p.title, pinned: p.pinned})));
      
      // Sort projects - pinned first, then alphabetically by title
      const sortedProjects = [...projectsData].sort((a, b) => {
        if (a.pinned && !b.pinned) return -1;
        if (!a.pinned && b.pinned) return 1;
        return a.title.localeCompare(b.title);
      });
      console.log(`[LOAD PROJECTS] Projects after sorting:`, sortedProjects.map(p => ({id: p.id, title: p.title, pinned: p.pinned})));
      
      setProjects(sortedProjects);
      
      // Find pinned project if any
      const pinnedProject = sortedProjects.find(project => project.pinned);
      console.log(`[LOAD PROJECTS] Pinned project:`, pinnedProject ? {id: pinnedProject.id, title: pinnedProject.title, pinned: pinnedProject.pinned} : 'None');
      console.log(`[LOAD PROJECTS] Current selected project:`, selectedProject ? {id: selectedProject.id, title: selectedProject.title, pinned: selectedProject.pinned} : 'None');
      
      // If there's a pinned project and currently selected project is different,
      // switch to the pinned project
      if (pinnedProject && (!selectedProject || selectedProject.id !== pinnedProject.id)) {
        console.log(`[LOAD PROJECTS] Switching selection to pinned project: ${pinnedProject.title}`);
        setSelectedProject(pinnedProject);
        setShowProjectDetails(true);
      } else if (sortedProjects.length > 0 && !selectedProject) {
        // No pinned project but we need a default selection
        console.log(`[LOAD PROJECTS] No pinned project, selecting first project: ${sortedProjects[0].title}`);
        setSelectedProject(sortedProjects[0]);
        setShowProjectDetails(true);
      } else {
        console.log(`[LOAD PROJECTS] Keeping current project selection`);
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
      setProjectsError(error instanceof Error ? error.message : 'Failed to load projects');
    } finally {
      setIsLoadingProjects(false);
    }
  };

  const loadTasksForProject = async (projectId: string) => {
    try {
      setIsLoadingTasks(true);
      setTasksError(null);
      
      const tasksData = await projectService.getTasksByProject(projectId);
      
             // Convert backend tasks to UI format
       const uiTasks: Task[] = tasksData.map(task => ({
         id: task.id,
         title: task.title,
         description: task.description,
         status: (task.uiStatus || 'backlog') as Task['status'],
         assignee: {
           name: (task.assignee || 'User') as 'User' | 'Archon' | 'AI IDE Agent',
           avatar: ''
         },
         feature: task.feature || 'General',
         featureColor: task.featureColor || '#6366f1',
         task_order: task.task_order || 0
       }));
       
       setTasks(uiTasks);
    } catch (error) {
      console.error('Failed to load tasks:', error);
      setTasksError(error instanceof Error ? error.message : 'Failed to load tasks');
    } finally {
      setIsLoadingTasks(false);
    }
  };

  const handleProjectSelect = (project: Project) => {
    setSelectedProject(project);
    setShowProjectDetails(true);
    setActiveTab('docs'); // Reset to docs tab when a new project is selected
    loadTasksForProject(project.id); // Load tasks for the selected project
  };

  const handleDeleteProject = useCallback(async (e: React.MouseEvent, projectId: string, projectTitle: string) => {
    e.stopPropagation();
    setProjectToDelete({ id: projectId, title: projectTitle });
    setShowDeleteConfirm(true);
  }, [setProjectToDelete, setShowDeleteConfirm]);

  const confirmDeleteProject = useCallback(async () => {
    if (!projectToDelete) return;

    try {
      await projectService.deleteProject(projectToDelete.id);
      
      // Update UI
      setProjects(prev => prev.filter(p => p.id !== projectToDelete.id));
      
      if (selectedProject?.id === projectToDelete.id) {
        setSelectedProject(null);
        setShowProjectDetails(false);
      }
      
      showToast(`Project "${projectToDelete.title}" deleted successfully`, 'success');
    } catch (error) {
      console.error('Failed to delete project:', error);
      showToast('Failed to delete project. Please try again.', 'error');
    } finally {
      setShowDeleteConfirm(false);
      setProjectToDelete(null);
    }
  }, [projectToDelete, setProjects, selectedProject, setSelectedProject, setShowProjectDetails, showToast, setShowDeleteConfirm, setProjectToDelete]);

  const cancelDeleteProject = useCallback(() => {
    setShowDeleteConfirm(false);
    setProjectToDelete(null);
  }, [setShowDeleteConfirm, setProjectToDelete]);
  
  const handleTogglePin = useCallback(async (e: React.MouseEvent, project: Project) => {
    e.stopPropagation();
    
    const newPinnedState = !project.pinned;
    console.log(`[PIN] Toggling pin for project ${project.id} (${project.title}) to ${newPinnedState}`);
    
    try {
      // Update the backend first
      console.log(`[PIN] Sending update to backend: project ${project.id}, pinned=${newPinnedState}`);
      const updatedProject = await projectService.updateProject(project.id, {
        pinned: newPinnedState
      });
      console.log(`[PIN] Backend response:`, updatedProject);
      
      // Update local state directly without reloading all projects
      setProjects(prev => {
        // Create updated project
        const updatedProject = { ...project, pinned: newPinnedState };
        console.log(`[PIN] Updated project object:`, updatedProject);
        
        // If pinning: unpin all others and move this to the front
        if (newPinnedState) {
          console.log(`[PIN] Pinning project - will unpin all others locally`);
          const unpinnedProjects = prev.map(p => {
            if (p.id === project.id) return updatedProject;
            if (p.pinned) console.log(`[PIN] Unpinning project locally: ${p.id} (${p.title})`);
            return { ...p, pinned: false };
          });
          
          // Re-sort with the newly pinned project first, then alphabetically
          const sortedProjects = [...unpinnedProjects].sort((a, b) => {
            if (a.pinned && !b.pinned) return -1;
            if (!a.pinned && b.pinned) return 1;
            return a.title.localeCompare(b.title);
          });
          console.log(`[PIN] Projects after sorting:`, sortedProjects.map(p => ({id: p.id, title: p.title, pinned: p.pinned})));
          return sortedProjects;
        } else {
          // Just update this project's pin state
          console.log(`[PIN] Unpinning project - only updating this project locally`);
          return prev.map(p => p.id === project.id ? updatedProject : p);
        }
      });
      
      // Update selected project if necessary
      if (selectedProject?.id === project.id) {
        console.log(`[PIN] Updating selected project's pin state`);
        setSelectedProject(prev => prev ? { ...prev, pinned: newPinnedState } : null);
      }
      
      showToast(
        newPinnedState 
          ? `Pinned "${project.title}" to top` 
          : 'Removed from pinned projects',
        'info'
      );
    } catch (error) {
      console.error('Failed to update project pin status:', error);
      showToast('Failed to update project. Please try again.', 'error');
    }
  }, [projectService, setProjects, selectedProject, setSelectedProject, showToast]);

  const handleCreateProject = async () => {
    if (!newProjectForm.title.trim()) {
      return;
    }

    try {
      setIsCreatingProject(true);
      
      const projectData: CreateProjectRequest = {
        title: newProjectForm.title,
        description: newProjectForm.description,
        color: newProjectForm.color,
        icon: 'Briefcase', // Default icon
        // PRD data will be added as a document in the docs array by backend
        docs: [],
        features: [],
        data: []
      };

      // Call the streaming project creation API
      const response = await projectService.createProjectWithStreaming(projectData);
      
      if (response.progress_id) {
        // Create a temporary project with progress tracking
        const tempId = `temp-${response.progress_id}`;
        const tempProject: Project = {
          id: tempId,
          title: newProjectForm.title,
          description: newProjectForm.description || '',
          github_repo: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          docs: [],
          features: [],
          data: [],
          pinned: false,
          color: newProjectForm.color,
          icon: 'Briefcase',
          creationProgress: {
            progressId: response.progress_id,
            status: 'starting',
            percentage: 0,
            logs: ['🚀 Starting project creation...'],
            project: { title: newProjectForm.title }
          }
        };
        
        // Add temporary project to the list
        setProjects((prev) => [tempProject, ...prev]);
        
        // Close modal immediately
        setIsNewProjectModalOpen(false);
        setNewProjectForm({ title: '', description: '', color: 'blue' });
        setIsCreatingProject(false);
        
        // Set up WebSocket connection for real-time progress
        projectCreationProgressService.streamProgress(
          response.progress_id,
          (data: ProjectCreationProgressData) => {
            console.log('📨 Project creation progress:', data);
            
            // Update the temporary project's progress
            setProjects((prev) => prev.map(p => 
              p.id === tempId 
                ? { ...p, creationProgress: data }
                : p
            ));
            
            // Handle completion
            if (data.status === 'completed' && data.project) {
              // Replace temporary project with real one
              setProjects((prev) => prev.map(p => 
                p.id === tempId ? data.project : p
              ));
              
              // Select the new project
              setSelectedProject(data.project);
              setShowProjectDetails(true);
            }
            
            // Handle error state
            if (data.status === 'error') {
              // Remove failed project after delay
              setTimeout(() => {
                setProjects((prev) => prev.filter(p => p.id !== tempId));
              }, 5000);
            }
          },
          { autoReconnect: true, reconnectDelay: 5000 }
        );
      } else {
        // Fallback to old synchronous flow
        const newProject = await projectService.createProject(projectData);
        
        setProjects((prev) => [...prev, newProject]);
        setSelectedProject(newProject);
        setShowProjectDetails(true);
        
        setNewProjectForm({ title: '', description: '', color: 'blue' });
        setIsNewProjectModalOpen(false);
        setIsCreatingProject(false);
      }
      
      console.log('✅ Project creation initiated successfully');
    } catch (error) {
      console.error('Failed to create project:', error);
      setIsCreatingProject(false);
      showToast(
        error instanceof Error ? error.message : 'Failed to create project. Please try again.',
        'error'
      );
    }
  };

  // Add staggered entrance animations
  const {
    isVisible,
    containerVariants,
    itemVariants,
    titleVariants
  } = useStaggeredEntrance([1, 2, 3], 0.15);

  // Add animation for tab content
  const tabContentVariants = {
    hidden: {
      opacity: 0,
      y: 20
    },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.4,
        ease: 'easeOut'
      }
    },
    exit: {
      opacity: 0,
      y: -20,
      transition: {
        duration: 0.2
      }
    }
  };

  return (
    <motion.div 
      initial="hidden" 
      animate={isVisible ? 'visible' : 'hidden'} 
      variants={containerVariants} 
      className={`max-w-full mx-auto ${className}`} 
      data-id={dataId}
    >
      {/* Page Header with New Project Button */}
      <motion.div className="flex items-center justify-between mb-8" variants={itemVariants}>
        <motion.h1 className="text-3xl font-bold text-gray-800 dark:text-white" variants={titleVariants}>
          Projects
        </motion.h1>
        <Button 
          onClick={() => setIsNewProjectModalOpen(true)} 
          variant="primary" 
          accentColor="purple" 
          className="shadow-lg shadow-purple-500/20"
        >
          <Plus className="w-4 h-4 mr-2 inline" />
          <span>New Project</span>
        </Button>
      </motion.div>

      {/* Projects Loading/Error States */}
      {isLoadingProjects && (
        <motion.div variants={itemVariants} className="mb-10">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-purple-500 mx-auto mb-4 animate-spin" />
              <p className="text-gray-600 dark:text-gray-400">Loading your projects...</p>
            </div>
          </div>
        </motion.div>
      )}

      {projectsError && (
        <motion.div variants={itemVariants} className="mb-10">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-4" />
              <p className="text-red-600 dark:text-red-400 mb-4">{projectsError}</p>
              <Button onClick={loadProjects} variant="primary" accentColor="purple">
                Try Again
              </Button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Project Cards - Horizontally Scrollable */}
      {!isLoadingProjects && !projectsError && (
        <motion.div className="relative mb-10" variants={itemVariants}>
          <div className="overflow-x-auto pb-4 hide-scrollbar">
            <div className="flex gap-4 min-w-max">
              {projects.map(project => (
                project.creationProgress ? (
                  // Show progress card for projects being created
                  <motion.div 
                    key={project.id} 
                    variants={itemVariants}
                    className="w-72"
                  >
                    <ProjectCreationProgressCard
                      progressData={project.creationProgress}
                      onComplete={() => {
                        console.log('Project creation completed');
                      }}
                      onError={(error) => {
                        console.error('Project creation failed:', error);
                        showToast(`Failed to create project: ${error}`, 'error');
                      }}
                      onRetry={() => handleRetryProjectCreation(project.creationProgress!.progressId)}
                    />
                  </motion.div>
                ) : (
                <motion.div 
                  key={project.id} 
                  variants={itemVariants} 
                  onClick={() => handleProjectSelect(project)} 
                  className={`
                    relative p-4 rounded-md backdrop-blur-md w-72 cursor-pointer
                    bg-gradient-to-b from-white/80 to-white/60 dark:from-white/10 dark:to-black/30
                    border border-gray-200 dark:border-zinc-800/50
                    shadow-[0_10px_30px_-15px_rgba(0,0,0,0.1)] dark:shadow-[0_10px_30px_-15px_rgba(0,0,0,0.7)]
                    hover:shadow-[0_15px_40px_-15px_rgba(0,0,0,0.2)] dark:hover:shadow-[0_15px_40px_-15px_rgba(0,0,0,0.9)]
                    transition-all duration-300
                    ${selectedProject?.id === project.id ? 'border-purple-300 dark:border-purple-500/30 translate-y-[-2px]' : 'hover:translate-y-[-2px]'}
                    ${selectedProject?.id === project.id ? `
                        before:content-[""] before:absolute before:top-0 before:left-0 before:right-0 before:h-[2px] 
                        before:rounded-t-[4px] before:bg-purple-500 
                        before:shadow-[0_0_10px_2px_rgba(168,85,247,0.4)] dark:before:shadow-[0_0_20px_5px_rgba(168,85,247,0.7)]
                        after:content-[""] after:absolute after:top-0 after:left-0 after:right-0 after:h-16
                        after:bg-gradient-to-b after:from-purple-100 after:to-white dark:after:from-purple-500/20 dark:after:to-purple-500/5
                        after:rounded-t-md after:pointer-events-none
                      ` : ''}
                  `}
                >
                  {/* Action buttons positioned in top-right corner */}
                  <div className="absolute top-2 right-2 flex gap-2 z-20">
                    {/* Pin button */}
                    <button
                      onClick={(e) => handleTogglePin(e, project)}
                      className={`p-1.5 rounded-full ${project.pinned ? 'bg-purple-100 text-purple-700 dark:bg-purple-700/30 dark:text-purple-400' : 'bg-gray-100 text-gray-500 dark:bg-gray-800/70 dark:text-gray-400'} hover:bg-purple-200 hover:text-purple-800 dark:hover:bg-purple-800/50 dark:hover:text-purple-300 transition-colors`}
                      title={project.pinned ? 'Unpin project' : 'Pin project'}
                      aria-label={project.pinned ? 'Unpin project' : 'Pin project'}
                    >
                      <Pin className="w-3.5 h-3.5" fill={project.pinned ? 'currentColor' : 'none'} />
                    </button>
                    
                    {/* Delete button */}
                    <button
                      onClick={(e) => handleDeleteProject(e, project.id, project.title)}
                      className="p-1.5 rounded-full bg-gray-100 text-gray-500 hover:bg-red-100 hover:text-red-600 dark:bg-gray-800/70 dark:text-gray-400 dark:hover:bg-red-900/30 dark:hover:text-red-400 transition-colors"
                      title="Delete project"
                      aria-label="Delete project"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  
                  <div className="relative z-10">
                    <div className="flex items-center gap-3 mb-3">
                      <div className={`p-2 rounded-md bg-${project.color || 'blue'}-500/10 text-${project.color || 'blue'}-500`}>
                        {getProjectIcon(project.icon)}
                      </div>
                      <h3 className="text-gray-800 dark:text-white font-medium">
                        {project.title}
                      </h3>
                    </div>
                    <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
                      {project.description || 'No description available'}
                    </p>
                    <div className="flex justify-between items-center text-xs text-gray-500 dark:text-gray-500">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
                          <div 
                            className={`h-full bg-${project.color || 'blue'}-500`} 
                            style={{ width: `${project.progress || 0}%` }}
                          />
                        </div>
                        <span>{project.progress || 0}%</span>
                      </div>
                      <span>Updated {project.updated || 'recently'}</span>
                    </div>
                  </div>
                </motion.div>
                )
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* Project Details Section */}
      {showProjectDetails && selectedProject && (
        <motion.div variants={itemVariants}>
          <div className="flex items-center gap-2 mb-6">
            <h2 className="text-2xl font-bold bg-gradient-to-r from-purple-400 via-fuchsia-500 to-purple-400 text-transparent bg-clip-text">
              {selectedProject.title}
            </h2>
            <ChevronRight className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <span className="text-gray-600 dark:text-gray-400 text-sm">
              Project Details
            </span>
          </div>
          
          <Tabs defaultValue="docs" value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList>
              <TabsTrigger value="docs" className="py-3 font-mono transition-all duration-300" color="blue">
                Docs
              </TabsTrigger>
              <TabsTrigger value="features" className="py-3 font-mono transition-all duration-300" color="purple">
                Features
              </TabsTrigger>
              <TabsTrigger value="data" className="py-3 font-mono transition-all duration-300" color="pink">
                Data
              </TabsTrigger>
              <TabsTrigger value="tasks" className="py-3 font-mono transition-all duration-300" color="orange">
                Tasks
              </TabsTrigger>
            </TabsList>
            
            {/* Add AnimatePresence for tab content transitions */}
            <AnimatePresence mode="wait">
              <motion.div 
                key={activeTab} 
                initial="hidden" 
                animate="visible" 
                exit="exit" 
                variants={tabContentVariants}
              >
                {activeTab === 'docs' && (
                  <TabsContent value="docs" className="mt-0">
                    <DocsTab tasks={tasks} project={selectedProject} />
                  </TabsContent>
                )}
                {activeTab === 'features' && (
                  <TabsContent value="features" className="mt-0">
                    <FeaturesTab project={selectedProject} />
                  </TabsContent>
                )}
                {activeTab === 'data' && (
                  <TabsContent value="data" className="mt-0">
                    <DataTab project={selectedProject} />
                  </TabsContent>
                )}
                {activeTab === 'tasks' && (
                  <TabsContent value="tasks" className="mt-0">
                    {isLoadingTasks ? (
                      <div className="flex items-center justify-center py-12">
                        <div className="text-center">
                          <Loader2 className="w-6 h-6 text-orange-500 mx-auto mb-4 animate-spin" />
                          <p className="text-gray-600 dark:text-gray-400">Loading tasks...</p>
                        </div>
                      </div>
                    ) : tasksError ? (
                      <div className="flex items-center justify-center py-12">
                        <div className="text-center">
                          <AlertCircle className="w-6 h-6 text-red-500 mx-auto mb-4" />
                          <p className="text-red-600 dark:text-red-400 mb-4">{tasksError}</p>
                                                     <Button 
                             onClick={() => loadTasksForProject(selectedProject.id)} 
                             variant="primary" 
                             accentColor="purple"
                           >
                            Retry
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <TasksTab initialTasks={tasks} onTasksChange={setTasks} projectId={selectedProject.id} />
                    )}
                  </TabsContent>
                )}
              </motion.div>
            </AnimatePresence>
          </Tabs>
        </motion.div>
      )}

      {/* New Project Modal */}
      {isNewProjectModalOpen && (
        <div className="fixed inset-0 bg-black/50 dark:bg-black/80 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="relative p-6 rounded-md backdrop-blur-md w-full max-w-md
              bg-gradient-to-b from-white/80 to-white/60 dark:from-white/10 dark:to-black/30
              border border-gray-200 dark:border-zinc-800/50
              shadow-[0_10px_30px_-15px_rgba(0,0,0,0.1)] dark:shadow-[0_10px_30px_-15px_rgba(0,0,0,0.7)]
              before:content-[''] before:absolute before:top-0 before:left-0 before:right-0 before:h-[2px] 
              before:rounded-t-[4px] before:bg-purple-500 
              before:shadow-[0_0_10px_2px_rgba(168,85,247,0.4)] dark:before:shadow-[0_0_20px_5px_rgba(168,85,247,0.7)]
              after:content-[''] after:absolute after:top-0 after:left-0 after:right-0 after:h-16
              after:bg-gradient-to-b after:from-purple-100 after:to-white dark:after:from-purple-500/20 dark:after:to-purple-500/5
              after:rounded-t-md after:pointer-events-none">
            <div className="relative z-10">
              {/* Project Creation Form */}
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-xl font-bold bg-gradient-to-r from-purple-400 to-fuchsia-500 text-transparent bg-clip-text">
                      Create New Project
                    </h3>
                    <button 
                      onClick={() => setIsNewProjectModalOpen(false)} 
                      className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-gray-700 dark:text-gray-300 mb-1">
                        Project Name
                      </label>
                      <input 
                        type="text" 
                        placeholder="Enter project name..." 
                        value={newProjectForm.title}
                        onChange={(e) => setNewProjectForm((prev) => ({ ...prev, title: e.target.value }))}
                        className="w-full bg-white/50 dark:bg-black/70 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white rounded-md py-2 px-3 focus:outline-none focus:border-purple-400 focus:shadow-[0_0_10px_rgba(168,85,247,0.2)] transition-all duration-300" 
                      />
                    </div>
                    <div>
                      <label className="block text-gray-700 dark:text-gray-300 mb-1">
                        Description
                      </label>
                      <textarea 
                        placeholder="Enter project description..." 
                        rows={4} 
                        value={newProjectForm.description}
                        onChange={(e) => setNewProjectForm((prev) => ({ ...prev, description: e.target.value }))}
                        className="w-full bg-white/50 dark:bg-black/70 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white rounded-md py-2 px-3 focus:outline-none focus:border-purple-400 focus:shadow-[0_0_10px_rgba(168,85,247,0.2)] transition-all duration-300" 
                      />
                    </div>
                  </div>
                  
                  <div className="flex justify-end gap-3 mt-6">
                    <Button 
                      onClick={() => setIsNewProjectModalOpen(false)} 
                      variant="ghost"
                      disabled={isCreatingProject}
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleCreateProject} 
                      variant="primary" 
                      accentColor="purple" 
                      className="shadow-lg shadow-purple-500/20"
                      disabled={isCreatingProject || !newProjectForm.title.trim()}
                    >
                      {isCreatingProject ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Creating...
                        </>
                      ) : (
                        'Create Project'
                      )}
                    </Button>
                  </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && projectToDelete && (
        <DeleteConfirmModal
          itemName={projectToDelete.title}
          onConfirm={confirmDeleteProject}
          onCancel={cancelDeleteProject}
          type="project"
        />
      )}
    </motion.div>
  );
}

// Reusable Delete Confirmation Modal Component
export interface DeleteConfirmModalProps {
  itemName: string;
  onConfirm: () => void;
  onCancel: () => void;
  type: 'project' | 'task' | 'client';
}

export const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({ itemName, onConfirm, onCancel, type }) => {
  const getTitle = () => {
    switch (type) {
      case 'project': return 'Delete Project';
      case 'task': return 'Delete Task';
      case 'client': return 'Delete MCP Client';
    }
  };

  const getMessage = () => {
    switch (type) {
      case 'project': return `Are you sure you want to delete the "${itemName}" project? This will also delete all associated tasks and documents and cannot be undone.`;
      case 'task': return `Are you sure you want to delete the "${itemName}" task? This action cannot be undone.`;
      case 'client': return `Are you sure you want to delete the "${itemName}" client? This will permanently remove its configuration and cannot be undone.`;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="relative p-6 rounded-md backdrop-blur-md w-full max-w-md
          bg-gradient-to-b from-white/80 to-white/60 dark:from-white/10 dark:to-black/30
          border border-gray-200 dark:border-zinc-800/50
          shadow-[0_10px_30px_-15px_rgba(0,0,0,0.1)] dark:shadow-[0_10px_30px_-15px_rgba(0,0,0,0.7)]
          before:content-[''] before:absolute before:top-0 before:left-0 before:right-0 before:h-[2px] 
          before:rounded-t-[4px] before:bg-red-500 
          before:shadow-[0_0_10px_2px_rgba(239,68,68,0.4)] dark:before:shadow-[0_0_20px_5px_rgba(239,68,68,0.7)]">
        
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <Trash2 className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
                {getTitle()}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                This action cannot be undone
              </p>
            </div>
          </div>
          
          <p className="text-gray-700 dark:text-gray-300 mb-6">
            {getMessage()}
          </p>
          
          <div className="flex justify-end gap-3">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors shadow-lg shadow-red-600/25 hover:shadow-red-700/25"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};