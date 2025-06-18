import React, { useRef, useState, useCallback } from 'react';
import { useDrag, useDrop } from 'react-dnd';
import { Network } from 'lucide-react';
import { Toggle } from '../ui/Toggle';
import { useToast } from '../../contexts/ToastContext';
import { DeleteConfirmModal } from '../../pages/ProjectPage';
import { projectService } from '../../services/projectService';
import { Task } from './TaskTableView'; // Import Task interface
import { ItemTypes, getAssigneeIcon, getAssigneeGlow, getOrderColor, getOrderGlow } from '../../lib/task-utils';
import { DraggableTaskCard, DraggableTaskCardProps } from './DraggableTaskCard'; // Import the new component and its props

interface TaskBoardViewProps {
  tasks: Task[];
  onTaskView: (task: Task) => void;
  onTaskComplete: (taskId: string) => void;
  onTaskDelete: (task: Task) => void;
  onTaskMove: (taskId: string, newStatus: Task['status']) => void;
  onTaskReorder: (taskId: string, newOrder: number, status: Task['status']) => void;
  showSubtasks?: boolean;
  showSubtasksToggle?: boolean;
  onShowSubtasksChange?: (show: boolean) => void;
}

interface ColumnDropZoneProps {
  status: Task['status'];
  title: string;
  tasks: Task[];
  onTaskMove: (taskId: string, newStatus: Task['status']) => void;
  onTaskView: (task: Task) => void;
  onTaskComplete: (taskId: string) => void;
  onTaskDelete: (task: Task) => void;
  onTaskReorder: (taskId: string, newOrder: number, status: Task['status']) => void;
  allTasks: Task[];
  showSubtasks: boolean;
  hoveredTaskId: string | null;
  onTaskHover: (taskId: string | null) => void;
}

const ColumnDropZone = ({
  status,
  title,
  tasks,
  onTaskMove,
  onTaskView,
  onTaskComplete,
  onTaskDelete,
  onTaskReorder,
  allTasks,
  showSubtasks,
  hoveredTaskId,
  onTaskHover
}: ColumnDropZoneProps) => {
  const ref = useRef<HTMLDivElement>(null);
  
  const [{ isOver }, drop] = useDrop({
    accept: ItemTypes.TASK,
    drop: (item: { id: string; status: string }) => {
      if (item.status !== status) {
        // Moving to different status - use length of current column as new order
        onTaskMove(item.id, status);
      }
    },
    collect: (monitor) => ({
      isOver: !!monitor.isOver()
    })
  });

  drop(ref);

  // Get column header color based on status
  const getColumnColor = () => {
    switch (status) {
      case 'backlog':
        return 'text-gray-600 dark:text-gray-400';
      case 'in-progress':
        return 'text-blue-600 dark:text-blue-400';
      case 'review':
        return 'text-purple-600 dark:text-purple-400';
      case 'complete':
        return 'text-green-600 dark:text-green-400';
    }
  };

  // Get column header glow based on status
  const getColumnGlow = () => {
    switch (status) {
      case 'backlog':
        return 'bg-gray-500/30';
      case 'in-progress':
        return 'bg-blue-500/30 shadow-[0_0_10px_2px_rgba(59,130,246,0.2)]';
      case 'review':
        return 'bg-purple-500/30 shadow-[0_0_10px_2px_rgba(168,85,247,0.2)]';
      case 'complete':
        return 'bg-green-500/30 shadow-[0_0_10px_2px_rgba(16,185,129,0.2)]';
    }
  };

  // Just use the tasks as-is since they're already parent tasks only
  const organizedTasks = tasks;

  return (
    <div 
      ref={ref} 
      className={`flex flex-col bg-white/20 dark:bg-black/30 ${isOver ? 'bg-gray-100/50 dark:bg-gray-800/20 border-t-2 border-t-[#00ff00] shadow-[inset_0_1px_10px_rgba(0,255,0,0.1)]' : ''} transition-colors duration-200 h-full`}
    >
      <div className="text-center py-3 sticky top-0 z-10 bg-white/80 dark:bg-black/80 backdrop-blur-sm">
        <h3 className={`font-mono ${getColumnColor()} text-sm`}>{title}</h3>
        {/* Column header divider with glow */}
        <div className={`absolute bottom-0 left-[15%] right-[15%] w-[70%] mx-auto h-[1px] ${getColumnGlow()}`}></div>
      </div>
      
      <div className="px-1 flex-1 overflow-y-auto space-y-3 py-3">
        {organizedTasks.map((task, index) => (
          <DraggableTaskCard
            key={task.id}
            task={task}
            index={index}
            onView={() => onTaskView(task)}
            onComplete={() => onTaskComplete(task.id)}
            onDelete={onTaskDelete}
            onTaskReorder={onTaskReorder}
            tasksInStatus={organizedTasks}
            allTasks={allTasks}
            hoveredTaskId={hoveredTaskId}
            onTaskHover={onTaskHover}
            showSubtasks={showSubtasks}
          />
        ))}
      </div>
    </div>
  );
};

export const TaskBoardView = ({
  tasks,
  onTaskView,
  onTaskComplete,
  onTaskDelete,
  onTaskMove,
  onTaskReorder,
  showSubtasks = false,
  showSubtasksToggle = false,
  onShowSubtasksChange
}: TaskBoardViewProps) => {
  const [hoveredTaskId, setHoveredTaskId] = useState<string | null>(null);

  // State for delete confirmation modal
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [taskToDelete, setTaskToDelete] = useState<Task | null>(null);

  const { showToast } = useToast();

  // Handle task deletion (opens confirmation modal)
  const handleDeleteTask = useCallback((task: Task) => {
    setTaskToDelete(task);
    setShowDeleteConfirm(true);
  }, [setTaskToDelete, setShowDeleteConfirm]);

  // Confirm deletion and execute
  const confirmDeleteTask = useCallback(async () => {
    if (!taskToDelete) return;

    try {
      await projectService.deleteTask(taskToDelete.id); // Assuming projectService has deleteTask
      // Notify parent to update tasks
      onTaskDelete(taskToDelete); // Pass the full taskToDelete object
      showToast(`Task "${taskToDelete.title}" deleted successfully`, 'success');
    } catch (error) {
      console.error('Failed to delete task:', error);
      showToast(error instanceof Error ? error.message : 'Failed to delete task', 'error');
    } finally {
      setShowDeleteConfirm(false);
      setTaskToDelete(null);
    }
  }, [taskToDelete, onTaskDelete, showToast, setShowDeleteConfirm, setTaskToDelete, projectService]);

  // Cancel deletion
  const cancelDeleteTask = useCallback(() => {
    setShowDeleteConfirm(false);
    setTaskToDelete(null);
  }, [setShowDeleteConfirm, setTaskToDelete]);

  // Simple task filtering for board view - only show parent tasks
  const getTasksByStatus = (status: Task['status']) => {
    // Always only show parent tasks in columns
    // Subtasks will be displayed inside parent cards when showSubtasks is true
    const parentTasks = tasks
      .filter(task => task.status === status && !task.parent_task_id)
      .sort((a, b) => a.task_order - b.task_order);
    
    return parentTasks;
  };

  return (
    <div className="flex flex-col h-full min-h-[70vh]">
      {/* Show Subtasks Toggle */}
      {showSubtasksToggle && onShowSubtasksChange && (
        <div className="mb-4 flex justify-end">
          <Toggle 
            checked={showSubtasks} 
            onCheckedChange={onShowSubtasksChange} 
            accentColor="blue" 
            icon={<Network className="w-5 h-5" />} 
          />
        </div>
      )}

      {/* Board Columns */}
      <div className="grid grid-cols-4 gap-0 flex-1">
        {/* Backlog Column */}
        <ColumnDropZone
          status="backlog"
          title="Backlog"
          tasks={getTasksByStatus('backlog')}
          onTaskMove={onTaskMove}
          onTaskView={onTaskView}
          onTaskComplete={onTaskComplete}
          onTaskDelete={onTaskDelete}
          onTaskReorder={onTaskReorder}
          allTasks={tasks}
          showSubtasks={showSubtasks}
          hoveredTaskId={hoveredTaskId}
          onTaskHover={setHoveredTaskId}
        />
        
        {/* In Progress Column */}
        <ColumnDropZone
          status="in-progress"
          title="In Process"
          tasks={getTasksByStatus('in-progress')}
          onTaskMove={onTaskMove}
          onTaskView={onTaskView}
          onTaskComplete={onTaskComplete}
          onTaskDelete={onTaskDelete}
          onTaskReorder={onTaskReorder}
          allTasks={tasks}
          showSubtasks={showSubtasks}
          hoveredTaskId={hoveredTaskId}
          onTaskHover={setHoveredTaskId}
        />
        
        {/* Review Column */}
        <ColumnDropZone
          status="review"
          title="Review"
          tasks={getTasksByStatus('review')}
          onTaskMove={onTaskMove}
          onTaskView={onTaskView}
          onTaskComplete={onTaskComplete}
          onTaskDelete={onTaskDelete}
          onTaskReorder={onTaskReorder}
          allTasks={tasks}
          showSubtasks={showSubtasks}
          hoveredTaskId={hoveredTaskId}
          onTaskHover={setHoveredTaskId}
        />
        
        {/* Complete Column */}
        <ColumnDropZone
          status="complete"
          title="Complete"
          tasks={getTasksByStatus('complete')}
          onTaskMove={onTaskMove}
          onTaskView={onTaskView}
          onTaskComplete={onTaskComplete}
          onTaskDelete={onTaskDelete}
          onTaskReorder={onTaskReorder}
          allTasks={tasks}
          showSubtasks={showSubtasks}
          hoveredTaskId={hoveredTaskId}
          onTaskHover={setHoveredTaskId}
        />
      </div>

      {/* Delete Confirmation Modal for Tasks */}
      {showDeleteConfirm && taskToDelete && (
        <DeleteConfirmModal
          itemName={taskToDelete.title}
          onConfirm={confirmDeleteTask}
          onCancel={cancelDeleteTask}
          type="task"
        />
      )}
    </div>
  );
}; 