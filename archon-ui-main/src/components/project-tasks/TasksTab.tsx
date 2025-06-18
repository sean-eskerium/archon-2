import React, { useState, useEffect, useCallback } from 'react';
import { X, Table, LayoutGrid, RefreshCw, Plus, Wifi, WifiOff, Check, Trash2, List, ChevronDown, ChevronRight } from 'lucide-react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { Button } from '../ui/Button';
import { ArchonLoadingSpinner } from '../animations/Animations';
import { Toggle } from '../ui/Toggle';
import { projectService } from '../../services/projectService';
import { taskUpdateWebSocket } from '../../services/taskUpdateService';
import type { CreateTaskRequest, UpdateTaskRequest, DatabaseTaskStatus } from '../../types/project';
import { Task } from '../../types/project';
import { TaskTableView } from './TaskTableView';
import { TaskBoardView } from './TaskBoardView';

// Assignee utilities
const ASSIGNEE_OPTIONS = ['User', 'Archon', 'AI IDE Agent'] as const;

// Mapping functions for status conversion
const mapUIStatusToDBStatus = (uiStatus: Task['status']): DatabaseTaskStatus => {
  switch (uiStatus) {
    case 'backlog': return 'todo';
    case 'in-progress': return 'doing';
    case 'review': return 'review'; // Map UI 'review' to database 'review'
    case 'complete': return 'done';
    default: return 'todo';
  }
};

const mapDBStatusToUIStatus = (dbStatus: DatabaseTaskStatus): Task['status'] => {
  switch (dbStatus) {
    case 'todo': return 'backlog';
    case 'doing': return 'in-progress';
    case 'review': return 'review'; // Map database 'review' to UI 'review'
    case 'done': return 'complete';
    default: return 'backlog';
  }
};

// Helper function to map database task format to UI task format
const mapDatabaseTaskToUITask = (dbTask: any): Task => {
  return {
    id: dbTask.id,
    title: dbTask.title,
    description: dbTask.description || '',
    status: mapDBStatusToUIStatus(dbTask.status),
    assignee: {
      name: dbTask.assignee || 'User',
      avatar: ''
    },
    feature: dbTask.feature || 'General',
    featureColor: '#3b82f6', // Default blue color
    task_order: dbTask.task_order || 0,
    parent_task_id: dbTask.parent_task_id || undefined
  };
};

export const TasksTab = ({
  initialTasks,
  onTasksChange,
  projectId
}: {
  initialTasks: Task[];
  onTasksChange: (tasks: Task[]) => void;
  projectId: string;
}) => {
  const [viewMode, setViewMode] = useState<'table' | 'board'>('board');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [projectFeatures, setProjectFeatures] = useState<any[]>([]);
  const [isLoadingFeatures, setIsLoadingFeatures] = useState(false);
  const [isWebSocketConnected, setIsWebSocketConnected] = useState(false);
  
  // Subtask-related state
  const [currentSubtasks, setCurrentSubtasks] = useState<Task[]>([]);
  const [isLoadingSubtasks, setIsLoadingSubtasks] = useState<boolean>(false);
  const [isSavingTask, setIsSavingTask] = useState<boolean>(false);
  const [showSubtasksInTable, setShowSubtasksInTable] = useState(false);
  const [showSubtasksInBoard, setShowSubtasksInBoard] = useState(false);
  
  // Accordion state
  const [isSubtasksExpanded, setIsSubtasksExpanded] = useState(false);
  
  // Temporary subtasks for new tasks
  const [tempSubtasks, setTempSubtasks] = useState<Omit<Task, 'id'>[]>([]);

  // Initialize tasks
  useEffect(() => {
    setTasks(initialTasks);
  }, [initialTasks]);

  // Load project features on component mount
  useEffect(() => {
    loadProjectFeatures();
  }, [projectId]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    console.log(`🔌 Initializing WebSocket connection for project: ${projectId}`);
    if (!projectId) {
      console.log('❌ No projectId provided, skipping WebSocket connection');
      return;
    }

    const connectWebSocket = async () => {
      console.log(`🔄 Connecting WebSocket for project: ${projectId}...`);
      
      try {
        await taskUpdateWebSocket.connect(projectId, {
          onTaskCreated: (task) => {
            console.log('🆕 Task created via WebSocket:', task);
            setTasks(prevTasks => {
              const newTask = mapDatabaseTaskToUITask(task);
              const updatedTasks = [...prevTasks, newTask];
              onTasksChange(updatedTasks);
              return updatedTasks;
            });
          },
          onTaskUpdated: (task) => {
            console.log('📝 Task updated via WebSocket:', task);
            setTasks(prevTasks => {
              const newTask = mapDatabaseTaskToUITask(task);
              const updatedTasks = prevTasks.map(t => 
                t.id === newTask.id ? newTask : t
              );
              onTasksChange(updatedTasks);
              return updatedTasks;
            });
          },
          onTaskDeleted: (task) => {
            console.log('🗑️ Task deleted via WebSocket:', task);
            setTasks(prevTasks => {
              const updatedTasks = prevTasks.filter(t => t.id !== task.id);
              onTasksChange(updatedTasks);
              return updatedTasks;
            });
          },
          onTaskArchived: (task) => {
            console.log('📦 Task archived via WebSocket:', task);
            setTasks(prevTasks => {
              const updatedTasks = prevTasks.filter(t => t.id !== task.id);
              onTasksChange(updatedTasks);
              return updatedTasks;
            });
          },
          onConnectionEstablished: () => {
            console.log('✅ WebSocket connection established for project:', projectId);
            setIsWebSocketConnected(true);
          },
          onInitialTasks: (tasksData) => {
            console.log('� Initial tasks received via WebSocket:', tasksData);
            if (tasksData && tasksData.length > 0) {
              const uiTasks = tasksData.map(mapDatabaseTaskToUITask);
              setTasks(uiTasks);
              onTasksChange(uiTasks);
            }
          },
          onTasksChange: (tasksData) => {
            console.log('� Tasks updated via MCP WebSocket:', tasksData);
            if (tasksData && tasksData.length > 0) {
              const uiTasks = tasksData.map(mapDatabaseTaskToUITask);
              setTasks(uiTasks);
              onTasksChange(uiTasks);
            }
          },
          onError: (error) => {
            console.error('❌ WebSocket error:', error);
            setIsWebSocketConnected(false);
          },
          onClose: () => {
            console.log('🔌 WebSocket closed');
            setIsWebSocketConnected(false);
          }
        });
        
        console.log('✅ WebSocket setup completed');
      } catch (error) {
        console.error('❌ Failed to connect WebSocket:', error);
        setIsWebSocketConnected(false);
      }
    };

    connectWebSocket();

    // Cleanup on unmount or projectId change
    return () => {
      console.log('🧹 Cleaning up WebSocket connection');
      taskUpdateWebSocket.disconnect();
      setIsWebSocketConnected(false);
    };
  }, [projectId]); // Removed onTasksChange from dependency array

  const loadProjectFeatures = async () => {
    if (!projectId) return;
    
    setIsLoadingFeatures(true);
    try {
      const response = await projectService.getProjectFeatures(projectId);
      setProjectFeatures(response.features || []);
    } catch (error) {
      console.error('Failed to load project features:', error);
      setProjectFeatures([]);
    } finally {
      setIsLoadingFeatures(false);
    }
  };

  // Load subtasks when editing an existing task
  const loadSubtasks = async (parentTaskId: string) => {
    setIsLoadingSubtasks(true);
    try {
      const response = await projectService.getTaskSubtasks(parentTaskId);
      const subtasks = response.map(mapDatabaseTaskToUITask);
      setCurrentSubtasks(subtasks);
    } catch (error) {
      console.error('Failed to load subtasks:', error);
      setCurrentSubtasks([]);
    } finally {
      setIsLoadingSubtasks(false);
    }
  };

  // Modal management functions
  const openEditModal = async (task: Task) => {
    setEditingTask(task);
    setIsModalOpen(true);
    if (task.id) {
      // Load existing subtasks into tempSubtasks so we can modify them before saving
      setIsLoadingSubtasks(true);
      try {
        const subtasks = await projectService.getTaskSubtasks(task.id, false);
        setTempSubtasks(subtasks.map(subtask => ({
          title: subtask.title,
          description: subtask.description,
          status: mapDBStatusToUIStatus(subtask.status),
          assignee: { name: subtask.assignee as 'User' | 'Archon' | 'AI IDE Agent', avatar: '' },
          feature: subtask.feature || '',
          featureColor: subtask.featureColor || '#3b82f6',
          task_order: subtask.task_order,
          parent_task_id: task.id
        })));
        setCurrentSubtasks([]); // Clear this since we're using tempSubtasks now
      } catch (error) {
        console.error('Failed to load subtasks:', error);
        setTempSubtasks([]);
      } finally {
        setIsLoadingSubtasks(false);
      }
    } else {
      setCurrentSubtasks([]);
      setTempSubtasks([]);
    }
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingTask(null);
    setCurrentSubtasks([]);
    setTempSubtasks([]);
    setIsSubtasksExpanded(false);
  };

  const saveTask = async () => {
    if (!editingTask) return;
    
    setIsSavingTask(true);
    try {
      let parentTaskId = editingTask.id;
      
      if (editingTask.id) {
        // Update existing task
        const updateData: UpdateTaskRequest = {
          title: editingTask.title,
          description: editingTask.description,
          status: mapUIStatusToDBStatus(editingTask.status),
          assignee: editingTask.assignee?.name || 'User',
          task_order: editingTask.task_order,
          ...(editingTask.feature && { feature: editingTask.feature }),
          ...(editingTask.featureColor && { featureColor: editingTask.featureColor })
        };
        
        await projectService.updateTask(editingTask.id, updateData);
        
        // Delete all existing subtasks first
        const existingSubtasks = await projectService.getTaskSubtasks(editingTask.id, false);
        for (const subtask of existingSubtasks) {
          await projectService.deleteTask(subtask.id);
        }
        
        // Create all tempSubtasks as new subtasks
        for (const subtask of tempSubtasks) {
          const subtaskCreateData: CreateTaskRequest = {
            project_id: projectId,
            title: subtask.title,
            description: subtask.description,
            status: mapUIStatusToDBStatus(subtask.status),
            assignee: subtask.assignee?.name || 'User',
            task_order: subtask.task_order,
            parent_task_id: editingTask.id,
            ...(subtask.feature && { feature: subtask.feature }),
            ...(subtask.featureColor && { featureColor: subtask.featureColor })
          };
          
          await projectService.createTask(subtaskCreateData);
        }
      } else {
        // Create new task first to get UUID
        const createData: CreateTaskRequest = {
          project_id: projectId,
          title: editingTask.title,
          description: editingTask.description,
          status: mapUIStatusToDBStatus(editingTask.status),
          assignee: editingTask.assignee?.name || 'User',
          task_order: editingTask.task_order,
          ...(editingTask.feature && { feature: editingTask.feature }),
          ...(editingTask.featureColor && { featureColor: editingTask.featureColor })
        };
        
        const createdTask = await projectService.createTask(createData);
        parentTaskId = createdTask.id;
        
        // Now create any temporary subtasks
        if (tempSubtasks.length > 0) {
          for (const subtask of tempSubtasks) {
            const subtaskCreateData: CreateTaskRequest = {
              project_id: projectId,
              title: subtask.title,
              description: subtask.description,
              status: mapUIStatusToDBStatus(subtask.status),
              assignee: subtask.assignee?.name || 'User',
              task_order: subtask.task_order,
              parent_task_id: parentTaskId,
              ...(subtask.feature && { feature: subtask.feature }),
              ...(subtask.featureColor && { featureColor: subtask.featureColor })
            };
            
            await projectService.createTask(subtaskCreateData);
          }
        }
      }
      
      // Reload tasks from backend
      const updatedTasks = await projectService.getTasksByProject(projectId);
      const uiTasks: Task[] = updatedTasks.map(mapDatabaseTaskToUITask);
      
      updateTasks(uiTasks);
      closeModal();
    } catch (error) {
      console.error('Failed to save task:', error);
      alert(`Failed to save task: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSavingTask(false);
    }
  };

  // Update tasks helper
  const updateTasks = (newTasks: Task[]) => {
    setTasks(newTasks);
    onTasksChange(newTasks);
  };

  // Helper function to reorder tasks by status to ensure no gaps (1,2,3...)
  const reorderTasksByStatus = async (status: Task['status']) => {
    const tasksInStatus = tasks
      .filter(task => task.status === status && !task.parent_task_id) // Only parent tasks
      .sort((a, b) => a.task_order - b.task_order);
    
    const updatePromises = tasksInStatus.map((task, index) => 
      projectService.updateTask(task.id, { task_order: index + 1 })
    );
    
    await Promise.all(updatePromises);
  };

  // Helper function to get next available order number for a status
  const getNextOrderForStatus = (status: Task['status']): number => {
    const tasksInStatus = tasks.filter(task => 
      task.status === status && !task.parent_task_id // Only parent tasks
    );
    
    if (tasksInStatus.length === 0) return 1;
    
    const maxOrder = Math.max(...tasksInStatus.map(task => task.task_order));
    return maxOrder + 1;
  };

  // React DnD optimized task reordering - immediate visual feedback, async persistence  
  const handleTaskReorder = (taskId: string, targetIndex: number, status: Task['status']) => {
    console.log('REORDER: Moving task', taskId, 'to index', targetIndex, 'in status', status);
    
    // Get all tasks in the target status, sorted by current order
    const statusTasks = tasks
      .filter(task => task.status === status)
      .sort((a, b) => a.task_order - b.task_order);
    
    const otherTasks = tasks.filter(task => task.status !== status);
    
    // Find the moving task
    const movingTaskIndex = statusTasks.findIndex(task => task.id === taskId);
    if (movingTaskIndex === -1) {
      console.log('REORDER: Task not found in status');
      return;
    }
    
    // Prevent invalid moves
    if (targetIndex < 0 || targetIndex >= statusTasks.length) {
      console.log('REORDER: Invalid target index', targetIndex);
      return;
    }
    
    const movingTask = statusTasks[movingTaskIndex];
    console.log('REORDER: Moving', movingTask.title, 'from', movingTaskIndex, 'to', targetIndex);
    
    // Create new array with the task moved to the target position
    const reorderedTasks = [...statusTasks];
    
    // Remove the task from its current position
    reorderedTasks.splice(movingTaskIndex, 1);
    
    // Insert the task at the new position
    reorderedTasks.splice(targetIndex, 0, movingTask);
    
    // Renumber all tasks sequentially based on their new array positions
    const renumberedTasks = reorderedTasks.map((task, index) => ({
      ...task,
      task_order: index + 1
    }));
    
    // Update UI immediately for smooth visual feedback
    const allUpdatedTasks = [...otherTasks, ...renumberedTasks];
    updateTasks(allUpdatedTasks);
    
    // Persist to backend asynchronously (debounced)
    debouncedPersistReorder(renumberedTasks);
  };
  
  // Simple debounce function
  const debounce = (func: Function, delay: number) => {
    let timeoutId: NodeJS.Timeout;
    return (...args: any[]) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func(...args), delay);
    };
  };

  // Debounced persistence to avoid too many API calls during rapid dragging
  const debouncedPersistReorder = useCallback(
    debounce(async (tasksToUpdate: Task[]) => {
      try {
        console.log('REORDER: Persisting order changes for', tasksToUpdate.length, 'tasks');
        
        const updatePromises = tasksToUpdate.map(task => 
          projectService.updateTask(task.id, { task_order: task.task_order })
        );
        
        await Promise.all(updatePromises);
        console.log('REORDER: Persistence completed');
        
      } catch (error) {
        console.error('REORDER: Failed to persist order changes:', error);
        // Reload tasks from backend on error to restore correct state
        try {
          const updatedTasks = await projectService.getTasksByProject(projectId);
          const uiTasks: Task[] = updatedTasks.map(mapDatabaseTaskToUITask);
          updateTasks(uiTasks);
        } catch (reloadError) {
          console.error('REORDER: Failed to reload tasks:', reloadError);
        }
      }
    }, 500), // 500ms delay to batch rapid changes
    [projectId]
  );

  // Task move function (for board view)
  const moveTask = async (taskId: string, newStatus: Task['status']) => {
    console.log(`[TasksTab] Attempting to move task ${taskId} to new status: ${newStatus}`);
    try {
      const movingTask = tasks.find(task => task.id === taskId);
      if (!movingTask) {
        console.warn(`[TasksTab] Task ${taskId} not found for move operation.`);
        return;
      }
      
      const oldStatus = movingTask.status;
      const newOrder = getNextOrderForStatus(newStatus);

      console.log(`[TasksTab] Moving task ${movingTask.title} from ${oldStatus} to ${newStatus} with order ${newOrder}`);

      // Update the task with new status and order
      await projectService.updateTask(taskId, {
        status: mapUIStatusToDBStatus(newStatus),
        task_order: newOrder
      });
      console.log(`[TasksTab] Successfully updated task ${taskId} status in backend.`);
      
      // Update local state immediately
      const newTasks = tasks.map(task => task.id === taskId ? {
        ...task,
        status: newStatus,
        task_order: newOrder
      } : task);
      updateTasks(newTasks);
      console.log(`[TasksTab] UI state updated for task ${taskId}.`)
      
      // Reorder the old status to close gaps (if different from new status)
      if (oldStatus !== newStatus) {
        console.log(`[TasksTab] Reordering tasks in old status ${oldStatus}.`);
        await reorderTasksByStatus(oldStatus);
        
        // Reload tasks to reflect reordering
        console.log(`[TasksTab] Reloading all tasks after status change and reordering.`);
        const updatedTasks = await projectService.getTasksByProject(projectId);
        const uiTasks: Task[] = updatedTasks.map(mapDatabaseTaskToUITask);
        updateTasks(uiTasks);
        console.log(`[TasksTab] All tasks reloaded and UI updated.`);
      }
    } catch (error) {
      console.error(`[TasksTab] Failed to move task ${taskId}:`, error);
      alert(`Failed to move task: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const completeTask = (taskId: string) => {
    console.log(`[TasksTab] Calling completeTask for ${taskId}`);
    moveTask(taskId, 'complete');
  };

  const deleteTask = async (task: Task) => {
    try {
      const deletingTask = tasks.find(t => t.id === task.id);
      if (!deletingTask) return;
      
      const taskStatus = deletingTask.status;
      
      // Delete the task
      await projectService.deleteTask(task.id);
      
      // Update local state immediately
      const newTasks = tasks.filter(t => t.id !== task.id);
      updateTasks(newTasks);
      
      // Reorder remaining tasks in the same status to close gaps
      await reorderTasksByStatus(taskStatus);
      
      // Reload tasks to reflect reordering
      const updatedTasks = await projectService.getTasksByProject(projectId);
      const uiTasks: Task[] = updatedTasks.map(mapDatabaseTaskToUITask);
      updateTasks(uiTasks);
    } catch (error) {
      console.error('Failed to delete task:', error);
      // Note: The toast notification for deletion is now handled by TaskBoardView and TaskTableView
    }
  };

  // Inline task creation function
  const createTaskInline = async (newTask: Omit<Task, 'id'>) => {
    try {
      // Auto-assign next order number if not provided
      const nextOrder = newTask.task_order || getNextOrderForStatus(newTask.status);
      
      const createData: CreateTaskRequest = {
        project_id: projectId,
        title: newTask.title,
        description: newTask.description,
        status: mapUIStatusToDBStatus(newTask.status),
        assignee: newTask.assignee?.name || 'User',
        task_order: nextOrder,
        ...(newTask.feature && { feature: newTask.feature }),
        ...(newTask.featureColor && { featureColor: newTask.featureColor })
      };
      
      await projectService.createTask(createData);
      
      // Reload tasks from backend to get the new task with ID
      const updatedTasks = await projectService.getTasksByProject(projectId);
      const uiTasks: Task[] = updatedTasks.map(mapDatabaseTaskToUITask);
      
      updateTasks(uiTasks);
    } catch (error) {
      console.error('Failed to create task:', error);
      throw error;
    }
  };

  // Inline task update function
  const updateTaskInline = async (taskId: string, updates: Partial<Task>) => {
    console.log(`[TasksTab] Inline update for task ${taskId} with updates:`, updates);
    try {
      const updateData: Partial<UpdateTaskRequest> = {};
      
      if (updates.title !== undefined) updateData.title = updates.title;
      if (updates.description !== undefined) updateData.description = updates.description;
      if (updates.status !== undefined) {
        console.log(`[TasksTab] Mapping UI status ${updates.status} to DB status.`);
        updateData.status = mapUIStatusToDBStatus(updates.status);
        console.log(`[TasksTab] Mapped status for ${taskId}: ${updates.status} -> ${updateData.status}`);
      }
      if (updates.assignee !== undefined) updateData.assignee = updates.assignee.name;
      if (updates.task_order !== undefined) updateData.task_order = updates.task_order;
      if (updates.feature !== undefined) updateData.feature = updates.feature;
      if (updates.featureColor !== undefined) updateData.featureColor = updates.featureColor;
      
      console.log(`[TasksTab] Sending update request for task ${taskId} to projectService:`, updateData);
      await projectService.updateTask(taskId, updateData);
      console.log(`[TasksTab] projectService.updateTask successful for ${taskId}.`);
      
      // Update local state optimistically
      const newTasks = tasks.map(task => 
        task.id === taskId ? { ...task, ...updates } : task
      );
      updateTasks(newTasks);
      console.log(`[TasksTab] UI state updated optimistically for task ${taskId}.`);
    } catch (error) {
      console.error(`[TasksTab] Failed to update task ${taskId} inline:`, error);
      alert(`Failed to update task: ${error instanceof Error ? error.message : 'Unknown error'}`);
      throw error;
    }
  };

  // Get tasks for priority selection with descriptive labels
  const getTasksForPrioritySelection = (status: Task['status']): Array<{value: number, label: string}> => {
    const tasksInStatus = tasks
      .filter(task => task.status === status && task.id !== editingTask?.id) // Exclude current task if editing
      .sort((a, b) => a.task_order - b.task_order);
    
    const options: Array<{value: number, label: string}> = [];
    
    if (tasksInStatus.length === 0) {
      // No tasks in this status
      options.push({ value: 1, label: "1 - First task in this status" });
    } else {
      // Add option to be first
      options.push({ 
        value: 1, 
        label: `1 - Before "${tasksInStatus[0].title.substring(0, 30)}${tasksInStatus[0].title.length > 30 ? '...' : ''}"` 
      });
      
      // Add options between existing tasks
      for (let i = 0; i < tasksInStatus.length - 1; i++) {
        const currentTask = tasksInStatus[i];
        const nextTask = tasksInStatus[i + 1];
        options.push({ 
          value: i + 2, 
          label: `${i + 2} - After "${currentTask.title.substring(0, 20)}${currentTask.title.length > 20 ? '...' : ''}", Before "${nextTask.title.substring(0, 20)}${nextTask.title.length > 20 ? '...' : ''}"` 
        });
      }
      
      // Add option to be last
      const lastTask = tasksInStatus[tasksInStatus.length - 1];
      options.push({ 
        value: tasksInStatus.length + 1, 
        label: `${tasksInStatus.length + 1} - After "${lastTask.title.substring(0, 30)}${lastTask.title.length > 30 ? '...' : ''}"` 
      });
    }
    
    return options;
  };

  // Create subtask function
  const createSubtask = async (parentTaskId: string, subtaskData: Omit<Task, 'id'>) => {
    try {
      const createData: CreateTaskRequest = {
        project_id: projectId,
        title: subtaskData.title,
        description: subtaskData.description,
        status: mapUIStatusToDBStatus(subtaskData.status),
        assignee: subtaskData.assignee?.name || 'User',
        task_order: subtaskData.task_order,
        parent_task_id: parentTaskId,
        ...(subtaskData.feature && { feature: subtaskData.feature }),
        ...(subtaskData.featureColor && { featureColor: subtaskData.featureColor })
      };
      
      await projectService.createTask(createData);
      
      // Reload subtasks
      await loadSubtasks(parentTaskId);
      
      // Reload all tasks to update parent status if needed
      const updatedTasks = await projectService.getTasksByProject(projectId);
      const uiTasks: Task[] = updatedTasks.map(mapDatabaseTaskToUITask);
      updateTasks(uiTasks);
    } catch (error) {
      console.error('Failed to create subtask:', error);
      throw error;
    }
  };

  // Delete subtask function
  const deleteSubtask = async (subtaskId: string, parentTaskId: string) => {
    try {
      await projectService.deleteTask(subtaskId);
      
      // Reload subtasks
      await loadSubtasks(parentTaskId);
      
      // Reload all tasks
      const updatedTasks = await projectService.getTasksByProject(projectId);
      const uiTasks: Task[] = updatedTasks.map(mapDatabaseTaskToUITask);
      updateTasks(uiTasks);
    } catch (error) {
      console.error('Failed to delete subtask:', error);
      throw error;
    }
  };

  // Update subtask function
  const updateSubtask = async (subtaskId: string, updates: Partial<Task>, parentTaskId: string) => {
    try {
      const updateData: Partial<UpdateTaskRequest> = {};
      
      if (updates.title !== undefined) updateData.title = updates.title;
      if (updates.description !== undefined) updateData.description = updates.description;
      if (updates.status !== undefined) updateData.status = mapUIStatusToDBStatus(updates.status);
      if (updates.assignee !== undefined) updateData.assignee = updates.assignee.name;
      if (updates.task_order !== undefined) updateData.task_order = updates.task_order;
      if (updates.feature !== undefined) updateData.feature = updates.feature;
      if (updates.featureColor !== undefined) updateData.featureColor = updates.featureColor;
      
      await projectService.updateTask(subtaskId, updateData);
      
      // Reload subtasks
      await loadSubtasks(parentTaskId);
    } catch (error) {
      console.error('Failed to update subtask:', error);
      throw error;
    }
  };

  // Handle temporary subtasks for new tasks
  const addTempSubtask = (subtaskData: Omit<Task, 'id'>) => {
    setTempSubtasks(prev => [...prev, {
      ...subtaskData,
      parent_task_id: 'temp' // Will be replaced when parent is saved
    }]);
  };

  const deleteTempSubtask = (index: number) => {
    setTempSubtasks(prev => prev.filter((_, i) => i !== index));
  };

  const updateTempSubtask = (index: number, updates: Partial<Omit<Task, 'id'>>) => {
    setTempSubtasks(prev => prev.map((subtask, i) => 
      i === index ? { ...subtask, ...updates } : subtask
    ));
  };

// SubtaskAddRow component for inline subtask creation
interface SubtaskAddRowProps {
  parentTaskId: string;
  onSubtaskCreate: (parentTaskId: string, subtaskData: Omit<Task, 'id'>) => Promise<void>;
  inheritedFeature?: string;
}

const SubtaskAddRow = ({ parentTaskId, onSubtaskCreate, inheritedFeature }: SubtaskAddRowProps) => {
  const [newSubtask, setNewSubtask] = useState<Omit<Task, 'id'>>({
    title: '',
    description: '',
    status: 'backlog',
    assignee: { name: 'AI IDE Agent', avatar: '' },
    feature: inheritedFeature || '',
    featureColor: '#3b82f6',
    task_order: 1,
    parent_task_id: parentTaskId
  });

  const handleCreateSubtask = async () => {
    if (!newSubtask.title.trim()) return;
    
    try {
      await onSubtaskCreate(parentTaskId, newSubtask);
      
      // Reset form
      setNewSubtask(prev => ({
        ...prev,
        title: '',
        description: ''
      }));
    } catch (error) {
      console.error('Failed to create subtask:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleCreateSubtask();
    }
  };

  return (
    <div className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <input
        type="text"
        value={newSubtask.title}
        onChange={(e) => setNewSubtask(prev => ({ ...prev, title: e.target.value }))}
        onKeyPress={handleKeyPress}
        placeholder="Add subtask..."
        className="flex-1 bg-white/90 dark:bg-black/90 border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-cyan-500 focus:shadow-[0_0_5px_rgba(34,211,238,0.3)]"
      />
      
      <select
        value={newSubtask.assignee?.name || 'User'}
        onChange={(e) => setNewSubtask(prev => ({ 
          ...prev, 
          assignee: { name: e.target.value as 'User' | 'Archon' | 'AI IDE Agent', avatar: '' } 
        }))}
        className="bg-white/90 dark:bg-black/90 border border-gray-300 dark:border-gray-600 rounded px-2 py-2 text-sm focus:outline-none focus:border-cyan-500"
      >
        {ASSIGNEE_OPTIONS.map(option => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
      
      <select
        value={newSubtask.status}
        onChange={(e) => setNewSubtask(prev => ({ 
          ...prev, 
          status: e.target.value as Task['status'] 
        }))}
        className="bg-white/90 dark:bg-black/90 border border-gray-300 dark:border-gray-600 rounded px-2 py-2 text-sm focus:outline-none focus:border-cyan-500"
      >
        <option value="backlog">Backlog</option>
        <option value="in-progress">In Progress</option>
        <option value="review">Review</option>
        <option value="complete">Complete</option>
      </select>
      
      <button
        onClick={handleCreateSubtask}
        disabled={!newSubtask.title.trim()}
        className="p-2 rounded-full bg-cyan-500 text-white hover:bg-cyan-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
      >
        <Plus className="w-4 h-4" />
      </button>
    </div>
  );
};

// Component for adding temporary subtasks (for new tasks)
interface TempSubtaskAddRowProps {
  onSubtaskCreate: (subtaskData: Omit<Task, 'id'>) => void;
  inheritedFeature?: string;
}

const TempSubtaskAddRow = ({ onSubtaskCreate, inheritedFeature }: TempSubtaskAddRowProps) => {
  const [newSubtask, setNewSubtask] = useState<Omit<Task, 'id'>>({
    title: '',
    description: '',
    status: 'backlog',
    assignee: { name: 'AI IDE Agent', avatar: '' },
    feature: inheritedFeature || '',
    featureColor: '#3b82f6',
    task_order: 1
  });

  const handleCreateSubtask = () => {
    if (!newSubtask.title.trim()) return;
    
    onSubtaskCreate(newSubtask);
    
    // Reset form
    setNewSubtask(prev => ({
      ...prev,
      title: '',
      description: ''
    }));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleCreateSubtask();
    }
  };

  return (
    <div className="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
      <input
        type="text"
        value={newSubtask.title}
        onChange={(e) => setNewSubtask(prev => ({ ...prev, title: e.target.value }))}
        onKeyPress={handleKeyPress}
        placeholder="Add subtask..."
        className="flex-1 bg-white/90 dark:bg-black/90 border border-blue-300 dark:border-blue-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500 focus:shadow-[0_0_5px_rgba(59,130,246,0.3)]"
      />
      
      <select
        value={newSubtask.assignee?.name || 'User'}
        onChange={(e) => setNewSubtask(prev => ({ 
          ...prev, 
          assignee: { name: e.target.value as 'User' | 'Archon' | 'AI IDE Agent', avatar: '' } 
        }))}
        className="bg-white/90 dark:bg-black/90 border border-blue-300 dark:border-blue-600 rounded px-2 py-2 text-sm focus:outline-none focus:border-blue-500"
      >
        {ASSIGNEE_OPTIONS.map(option => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
      
      <select
        value={newSubtask.status}
        onChange={(e) => setNewSubtask(prev => ({ 
          ...prev, 
          status: e.target.value as Task['status'] 
        }))}
        className="bg-white/90 dark:bg-black/90 border border-blue-300 dark:border-blue-600 rounded px-2 py-2 text-sm focus:outline-none focus:border-blue-500"
      >
        <option value="backlog">Backlog</option>
        <option value="in-progress">In Progress</option>
        <option value="review">Review</option>
        <option value="complete">Complete</option>
      </select>
      
      <button
        onClick={handleCreateSubtask}
        disabled={!newSubtask.title.trim()}
        className="p-2 rounded-full bg-blue-500 text-white hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
      >
        <Plus className="w-4 h-4" />
      </button>
    </div>
  );
};

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="min-h-[70vh] relative">
        {/* Main content - Table or Board view */}
        <div className="relative h-[calc(100vh-220px)] overflow-auto">
          {viewMode === 'table' ? (
            <TaskTableView
              tasks={tasks}
              onTaskView={openEditModal}
              onTaskComplete={completeTask}
              onTaskDelete={deleteTask}
              onTaskReorder={handleTaskReorder}
              onTaskCreate={createTaskInline}
              onTaskUpdate={updateTaskInline}
              showSubtasks={showSubtasksInTable}
              showSubtasksToggle={true}
              onShowSubtasksChange={setShowSubtasksInTable}
            />
          ) : (
            <TaskBoardView
              tasks={tasks}
              onTaskView={openEditModal}
              onTaskComplete={completeTask}
              onTaskDelete={deleteTask}
              onTaskMove={moveTask}
              onTaskReorder={handleTaskReorder}
              showSubtasks={showSubtasksInBoard}
              showSubtasksToggle={true}
              onShowSubtasksChange={setShowSubtasksInBoard}
            />
          )}
        </div>

        {/* Fixed View Controls */}
        <div className="fixed bottom-6 left-0 right-0 flex justify-center z-50 pointer-events-none">
          <div className="flex items-center gap-4">
            {/* WebSocket Status Indicator */}
            <div className="flex items-center gap-2 px-3 py-2 bg-white/80 dark:bg-black/90 border border-gray-200 dark:border-gray-800 rounded-lg shadow-[0_0_20px_rgba(0,0,0,0.1)] dark:shadow-[0_0_20px_rgba(0,0,0,0.5)] backdrop-blur-md pointer-events-auto">
              {isWebSocketConnected ? (
                <>
                  <Wifi className="w-4 h-4 text-green-500" />
                  <span className="text-xs text-green-600 dark:text-green-400">Live</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-4 h-4 text-red-500" />
                  <span className="text-xs text-red-600 dark:text-red-400">Offline</span>
                </>
              )}
            </div>
            
            {/* Add Task Button with Luminous Style */}
            <button 
              onClick={() => {
                const defaultOrder = getTasksForPrioritySelection('backlog')[0]?.value || 1;
                setEditingTask({
                  id: '',
                  title: '',
                  description: '',
                  status: 'backlog',
                  assignee: { name: 'AI IDE Agent', avatar: '' },
                  feature: '',
                  featureColor: '#3b82f6',
                  task_order: defaultOrder
                });
                setIsModalOpen(true);
              }}
              className="relative px-5 py-2.5 flex items-center gap-2 bg-white/80 dark:bg-black/90 border border-gray-200 dark:border-gray-800 rounded-lg shadow-[0_0_20px_rgba(0,0,0,0.1)] dark:shadow-[0_0_20px_rgba(0,0,0,0.5)] backdrop-blur-md pointer-events-auto text-cyan-600 dark:text-cyan-400 hover:text-cyan-700 dark:hover:text-cyan-300 transition-all duration-300"
            >
              <Plus className="w-4 h-4 mr-1" />
              <span>Add Task</span>
              <span className="absolute bottom-0 left-[0%] right-[0%] w-[95%] mx-auto h-[2px] bg-cyan-500 shadow-[0_0_10px_2px_rgba(34,211,238,0.4)] dark:shadow-[0_0_20px_5px_rgba(34,211,238,0.7)]"></span>
            </button>
          
            {/* View Toggle Controls */}
            <div className="flex items-center bg-white/80 dark:bg-black/90 border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden shadow-[0_0_20px_rgba(0,0,0,0.1)] dark:shadow-[0_0_20px_rgba(0,0,0,0.5)] backdrop-blur-md pointer-events-auto">
              <button 
                onClick={() => setViewMode('table')} 
                className={`px-5 py-2.5 flex items-center gap-2 relative transition-all duration-300 ${viewMode === 'table' ? 'text-cyan-600 dark:text-cyan-400' : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300'}`}
              >
                <Table className="w-4 h-4" />
                <span>Table</span>
                {viewMode === 'table' && <span className="absolute bottom-0 left-[15%] right-[15%] w-[70%] mx-auto h-[2px] bg-cyan-500 shadow-[0_0_10px_2px_rgba(34,211,238,0.4)] dark:shadow-[0_0_20px_5px_rgba(34,211,238,0.7)]"></span>}
              </button>
              <button 
                onClick={() => setViewMode('board')} 
                className={`px-5 py-2.5 flex items-center gap-2 relative transition-all duration-300 ${viewMode === 'board' ? 'text-purple-600 dark:text-purple-400' : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300'}`}
              >
                <LayoutGrid className="w-4 h-4" />
                <span>Board</span>
                {viewMode === 'board' && <span className="absolute bottom-0 left-[15%] right-[15%] w-[70%] mx-auto h-[2px] bg-purple-500 shadow-[0_0_10px_2px_rgba(168,85,247,0.4)] dark:shadow-[0_0_20px_5px_rgba(168,85,247,0.7)]"></span>}
              </button>
            </div>
          </div>
        </div>

        {/* Edit Task Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 bg-gray-500/50 dark:bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="relative p-6 rounded-md backdrop-blur-md w-full max-w-2xl bg-gradient-to-b from-white/80 to-white/60 dark:from-white/10 dark:to-black/30 border border-gray-200 dark:border-zinc-800/50 shadow-[0_10px_30px_-15px_rgba(0,0,0,0.1)] dark:shadow-[0_10px_30px_-15px_rgba(0,0,0,0.7)] before:content-[''] before:absolute before:top-0 before:left-0 before:right-0 before:h-[2px] before:rounded-t-[4px] before:bg-gradient-to-r before:from-cyan-500 before:to-fuchsia-500 before:shadow-[0_0_10px_2px_rgba(34,211,238,0.4)] dark:before:shadow-[0_0_20px_5px_rgba(34,211,238,0.7)] after:content-[''] after:absolute after:top-0 after:left-0 after:right-0 after:h-16 after:bg-gradient-to-b after:from-cyan-100 after:to-white dark:after:from-cyan-500/20 dark:after:to-fuchsia-500/5 after:rounded-t-md after:pointer-events-none">
              <div className="relative z-10">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-fuchsia-500 text-transparent bg-clip-text">
                    {editingTask?.id ? 'Edit Task' : 'New Task'}
                  </h3>
                  <button onClick={closeModal} className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white transition-colors">
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-gray-700 dark:text-gray-300 mb-1">Title</label>
                    <input 
                      type="text" 
                      value={editingTask?.title || ''} 
                      onChange={e => setEditingTask(editingTask ? { ...editingTask, title: e.target.value } : null)} 
                      className="w-full bg-white/50 dark:bg-black/70 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white rounded-md py-2 px-3 focus:outline-none focus:border-cyan-400 focus:shadow-[0_0_10px_rgba(34,211,238,0.2)] transition-all duration-300" 
                    />
                  </div>

                  <div>
                    <label className="block text-gray-700 dark:text-gray-300 mb-1">Description</label>
                    <textarea 
                      value={editingTask?.description || ''} 
                      onChange={e => setEditingTask(editingTask ? { ...editingTask, description: e.target.value } : null)} 
                      rows={5} 
                      className="w-full bg-white/50 dark:bg-black/70 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-white rounded-md py-2 px-3 focus:outline-none focus:border-cyan-400 focus:shadow-[0_0_10px_rgba(34,211,238,0.2)] transition-all duration-300" 
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-gray-700 dark:text-gray-300 mb-1">Status</label>
                      <select 
                        value={editingTask?.status || 'backlog'} 
                        onChange={e => {
                          const newStatus = e.target.value as Task['status'];
                          const newOrder = getTasksForPrioritySelection(newStatus)[0]?.value || 1;
                          setEditingTask(editingTask ? { ...editingTask, status: newStatus, task_order: newOrder } : null);
                        }} 
                        className="w-full bg-white/50 dark:bg-black/70 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-white rounded-md py-2 px-3 focus:outline-none focus:border-cyan-400 focus:shadow-[0_0_10px_rgba(34,211,238,0.2)] transition-all duration-300"
                      >
                        <option value="backlog">Backlog</option>
                        <option value="in-progress">In Process</option>
                        <option value="review">Review</option>
                        <option value="complete">Complete</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-gray-700 dark:text-gray-300 mb-1">Priority</label>
                      <select 
                        value={editingTask?.task_order || 1} 
                        onChange={e => setEditingTask(editingTask ? { ...editingTask, task_order: parseInt(e.target.value) } : null)} 
                        className="w-full bg-white/50 dark:bg-black/70 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-white rounded-md py-2 px-3 focus:outline-none focus:border-cyan-400 focus:shadow-[0_0_10px_rgba(34,211,238,0.2)] transition-all duration-300"
                      >
                        {getTasksForPrioritySelection(editingTask?.status || 'backlog').map((option, index) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-gray-700 dark:text-gray-300 mb-1">Assignee</label>
                      <select 
                        value={editingTask?.assignee?.name || 'User'} 
                        onChange={e => setEditingTask(editingTask ? {
                          ...editingTask,
                          assignee: { name: e.target.value as 'User' | 'Archon' | 'AI IDE Agent', avatar: '' }
                        } : null)} 
                        className="w-full bg-white/50 dark:bg-black/70 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-white rounded-md py-2 px-3 focus:outline-none focus:border-cyan-400 focus:shadow-[0_0_10px_rgba(34,211,238,0.2)] transition-all duration-300"
                      >
                        {ASSIGNEE_OPTIONS.map(option => (
                          <option key={option} value={option}>{option}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-gray-700 dark:text-gray-300 mb-1">Feature</label>
                      <div className="relative">
                        <input 
                          type="text" 
                          value={editingTask?.feature || ''} 
                          onChange={e => setEditingTask(editingTask ? { ...editingTask, feature: e.target.value } : null)} 
                          placeholder="Type feature name"
                          className="w-full bg-white/50 dark:bg-black/70 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-white rounded-md py-2 px-3 pr-10 focus:outline-none focus:border-cyan-400 focus:shadow-[0_0_10px_rgba(34,211,238,0.2)] transition-all duration-300" 
                          list="features-list"
                        />
                        <datalist id="features-list">
                          {projectFeatures.map((feature) => (
                            <option key={feature.id} value={feature.label}>
                              {feature.label} ({feature.type})
                            </option>
                          ))}
                        </datalist>
                        {isLoadingFeatures && (
                          <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                            <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Subtasks Section - Accordion for both new and existing tasks */}
                <div className="mt-6 border-t border-gray-200 dark:border-gray-700 pt-6">
                  <button
                    onClick={() => setIsSubtasksExpanded(!isSubtasksExpanded)}
                    className="flex items-center justify-between w-full mb-4 text-left hover:bg-gray-50 dark:hover:bg-gray-800 p-2 rounded-lg transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                        Subtasks
                      </h4>
                      {tempSubtasks.length > 0 && (
                        <span className="px-2 py-1 text-xs bg-blue-200 dark:bg-blue-700 text-blue-600 dark:text-blue-400 rounded-full">
                          {tempSubtasks.length}
                        </span>
                      )}
                      {isLoadingSubtasks && (
                        <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                      )}
                    </div>
                    {isSubtasksExpanded ? (
                      <ChevronDown className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                    )}
                  </button>
                  
                  {isSubtasksExpanded && (
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {/* Temporary Subtasks (for both new and existing tasks) */}
                      {tempSubtasks.map((subtask, index) => (
                        <div key={index} className="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-500">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                {subtask.title}
                              </span>
                              <span className={`px-2 py-1 text-xs rounded-full ${
                                subtask.status === 'complete' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                                subtask.status === 'in-progress' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                                subtask.status === 'review' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                                'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                              }`}>
                                {subtask.status}
                              </span>
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                {subtask.assignee?.name || 'User'}
                              </span>
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => updateTempSubtask(index, { 
                                status: subtask.status === 'complete' ? 'backlog' : 'complete' 
                              })}
                              className={`p-1 rounded-full transition-colors ${
                                subtask.status === 'complete' 
                                  ? 'bg-gray-200 text-gray-500 hover:bg-gray-300 dark:bg-gray-600 dark:text-gray-400' 
                                  : 'bg-green-100 text-green-600 hover:bg-green-200 dark:bg-green-900 dark:text-green-400'
                              }`}
                            >
                              <Check className="w-3 h-3" />
                            </button>
                            <button
                              onClick={() => deleteTempSubtask(index)}
                              className="p-1 rounded-full bg-red-100 text-red-600 hover:bg-red-200 dark:bg-red-900 dark:text-red-400 transition-colors"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      ))}
                      
                      {/* Add New Subtask Row */}
                      <TempSubtaskAddRow 
                        onSubtaskCreate={addTempSubtask}
                        inheritedFeature={editingTask?.feature}
                      />
                    </div>
                  )}
                </div>

                <div className="flex justify-end gap-3 mt-6">
                  <Button onClick={closeModal} variant="ghost" disabled={isSavingTask}>Cancel</Button>
                  <Button 
                    onClick={saveTask} 
                    variant="primary" 
                    accentColor="cyan" 
                    className="shadow-lg shadow-cyan-500/20"
                    disabled={isSavingTask}
                  >
                    {isSavingTask ? (
                      <span className="flex items-center">
                        <ArchonLoadingSpinner size="sm" className="mr-2" />
                        {editingTask?.id ? 'Saving...' : 'Creating...'}
                      </span>
                    ) : (
                      editingTask?.id ? 'Save Changes' : 'Create Task'
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </DndProvider>
  );
};