import React, { useState } from 'react';
import { Table, Badge, Button, OverlayTrigger, Tooltip } from 'react-bootstrap';
import TaskDetailModal from './TaskDetailModal';
import TaskVersionModal from './TaskVersionModal';

function TaskTableView({ tasks, projectId, onTasksRefreshed }) {
  const [selectedTask, setSelectedTask] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [showVersionDetail, setShowVersionDetail] = useState(false);

  const handleRowClick = (task) => {
    setSelectedTask(task);
    setShowDetail(true);
  };

  const handleCloseDetail = () => {
    setShowDetail(false);
    setSelectedTask(null);
  };

  const handleVersionClick = (task) => {
    setSelectedTask(task);
    setShowVersionDetail(true);
  };


  const handleCloseVersionDetail = () => {
    setShowVersionDetail(false);
    setSelectedTask(null);
  };

  const handleDeleteTask = async (task, event) => {
    event.stopPropagation();
    
    if (!window.confirm(`确定要删除任务 "${task.name}" 吗？此操作不可恢复。`)) {
      return;
    }

    try {
      const response = await fetch(`/api/${projectId}/tasks/${task._id}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'X-Project-ID': projectId,
        },
      });

      if (response.ok) {
        if (onTasksRefreshed) {
          await onTasksRefreshed();
        }
      } else {
        const error = await response.json();
        alert(`删除失败：${error.detail || error.message || '未知错误'}`);
      }
    } catch (error) {
      console.error('删除任务时发生错误:', error);
      alert(`删除失败：${error.message || '网络错误'}`);
    }
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      pending: { bg: 'warning', text: '待处理' },
      in_progress: { bg: 'info', text: '进行中' },
      completed: { bg: 'success', text: '已完成' },
      failed: { bg: 'danger', text: '失败' },
      cancelled: { bg: 'secondary', text: '已取消' }
    };
    return statusMap[status] || { bg: 'secondary', text: status };
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: '2-digit',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const truncateText = (text, maxLength = 30) => {
    if (!text) return '';
    return text.length > maxLength ? text.slice(0, maxLength) + '...' : text;
  };

  if (!tasks || tasks.length === 0) {
    return (
      <div className="text-center py-4">
        <i className="bi bi-inbox fs-1 text-muted"></i>
        <h5 className="text-muted mt-3">暂无任务</h5>
        <p className="text-muted">当前项目还没有创建任何任务</p>
      </div>
    );
  }

  return (
    <>
      <div className="table-responsive fade-in">
        <Table hover className="mb-0">
          <thead style={{ backgroundColor: '#f8fafc' }}>
            <tr>
              <th style={{ width: '8%' }}>ID</th>
              <th style={{ width: '20%' }}>名称</th>
              <th style={{ width: '28%' }}>描述</th>
              <th style={{ width: '10%' }}>状态</th>
              <th style={{ width: '12%' }}>依赖</th>
              <th style={{ width: '12%' }}>更新时间</th>
              <th style={{ width: '10%' }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task, index) => {
              const statusBadge = getStatusBadge(task.status);
              const taskId = task._id || task.id || `task-${index}`;
              
              return (
                <tr key={taskId} className="cursor-pointer">
                  <td>
                    <small className="font-monospace text-muted">
                      {taskId.slice(-8)}
                    </small>
                  </td>
                  
                  <td>
                    <div className="fw-bold text-primary cursor-pointer text-truncate" 
                         title={task.name} style={{ maxWidth: '200px' }}>
                      {truncateText(task.name, 25)}
                    </div>
                  </td>
                  
                  <td>
                    <OverlayTrigger
                      placement="top"
                      overlay={
                        <Tooltip id={`desc-${taskId}`}>
                          {task.description || '暂无描述'}
                        </Tooltip>
                      }
                    >
                      <div className="text-muted text-truncate" style={{ maxWidth: '300px' }}>
                        {truncateText(task.description, 50)}
                      </div>
                    </OverlayTrigger>
                  </td>
                  
                  <td>
                    <Badge bg={statusBadge.bg} className="px-2 py-1">
                      {statusBadge.text}
                    </Badge>
                  </td>
                  
                  <td>
                    <small className="font-monospace text-muted">
                      {Array.isArray(task.dependencies) && task.dependencies.length > 0 
                        ? task.dependencies.map(dep => dep.slice(-6)).join(', ')
                        : ''
                      }
                    </small>
                  </td>
                  
                  <td>
                    <small className="text-muted text-nowrap">
                      {formatDate(task.updated_at)}
                    </small>
                  </td>
                  
                  <td>
                    <div className="d-flex gap-1">
                      <Button 
                        variant="outline-primary" 
                        size="sm" 
                        onClick={() => handleRowClick(task)}
                        title="查看详情"
                        className="px-1 py-0"
                      >
                        <i className="bi bi-eye"></i>
                      </Button>
                      <Button 
                        variant="outline-success" 
                        size="sm" 
                        onClick={() => handleVersionClick(task)}
                        title="查看版本"
                        className="px-1 py-0"
                      >
                        <i className="bi bi-clock-history"></i>
                      </Button>
                      <Button 
                        variant="outline-danger" 
                        size="sm" 
                        onClick={(e) => handleDeleteTask(task, e)}
                        title="删除任务"
                        className="px-1 py-0"
                      >
                        <i className="bi bi-trash"></i>
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </div>

      <TaskDetailModal 
        show={showDetail} 
        handleClose={handleCloseDetail} 
        task={selectedTask}
        projectId={projectId}
        onTaskUpdated={onTasksRefreshed}
      />
      
      <TaskVersionModal 
        show={showVersionDetail} 
        handleClose={handleCloseVersionDetail} 
        task={selectedTask}
        projectId={projectId}
      />
      
    </>
  );
}

export default TaskTableView;