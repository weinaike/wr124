import React, { useState, useEffect } from 'react';
import { Modal, Button, Row, Col, Badge, Card, ListGroup } from 'react-bootstrap';
import EditTaskModal from './EditTaskModal';
import { apiEndpoints } from '../api/config';

function TaskDetailModal({ show, handleClose, task, projectId, onTaskUpdated }) {
  const [loading, setLoading] = useState(!task);
  const [currentTask, setCurrentTask] = useState(task);
  const [todos, setTodos] = useState([]);
  const [showEditModal, setShowEditModal] = useState(false);

  useEffect(() => {
    if (show) {
      if (task && (task._id || task.id)) {
        // 每次打开或编辑回来后都刷新
        fetchTaskDetails();
      } else {
        setCurrentTask(task);
        setLoading(false);
      }
    }
  }, [show, task, projectId]);

  const fetchTaskDetails = async () => {
    const taskId = currentTask?._id || currentTask?.id || task?._id || task?.id;
    if (!taskId) return;
    
    setLoading(true);
    try {
      const [taskResponse, todosResponse] = await Promise.all([
        fetch(apiEndpoints.task(projectId, taskId), {
          headers: {
            'X-Project-ID': projectId
          }
        }),
        fetch(apiEndpoints.taskTodos(projectId, taskId), {
          headers: {
            'X-Project-ID': projectId
          }
        })
      ]);
      
      if (taskResponse.ok) {
        const updatedTask = await taskResponse.json();
        setCurrentTask(updatedTask);
      }
      
      if (todosResponse.ok) {
        const todosData = await todosResponse.json();
        setTodos(todosData || []);
      }
    } catch (error) {
      console.error('获取任务详情失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEditClick = () => {
    setShowEditModal(true);
  };

  const handleModalClose = () => {
    handleClose();
    // 关闭详情页时触发刷新
    if (onTaskUpdated) {
      onTaskUpdated();
    }
  };

  const handleTaskUpdated = async () => {
    setShowEditModal(false);
    await fetchTaskDetails(); // 刷新任务详情数据
    // 通知父组件刷新
    if (onTaskUpdated) {
      onTaskUpdated();
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

  const getPriorityBadge = (priority) => {
    const priorityMap = {
      low: { bg: 'success', text: '低' },
      medium: { bg: 'warning', text: '中' },
      high: { bg: 'danger', text: '高' },
      urgent: { bg: 'dark', text: '紧急' },
    };
    return priorityMap[priority?.toLowerCase()] || { bg: 'secondary', text: priority };
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('zh-CN');
  };

  if (loading) {
    return (
      <Modal show={show} onHide={handleClose} size="lg">
        <Modal.Body>
          <div className="text-center py-5">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <p className="mt-3 text-muted">加载任务详情...</p>
          </div>
        </Modal.Body>
      </Modal>
    );
  }

  if (!currentTask) {
    return (
      <Modal show={show} onHide={handleClose} size="lg">
        <Modal.Body>
          <div className="text-center py-5">
            <h5 className="text-muted">任务详情不可用</h5>
          </div>
        </Modal.Body>
      </Modal>
    );
  }

return (
    <Modal 
      show={show} 
      onHide={() => {
        handleClose();
        // 关闭详情页时触发刷新
        if (onTaskUpdated) {
          onTaskUpdated();
        }
      }}
      size="xl" 
      centered 
      scrollable 
      dialogClassName="modal-fullscreen-sm-down"
    >
      <Modal.Header closeButton style={{ backgroundColor: '#f8fafc' }}>
        <Modal.Title style={{ color: 'var(--text-primary)' }}>
          <i className="bi bi-card-text me-2"></i>
          任务详情 - {loading ? <span className="text-muted small">加载中...</span> : currentTask.name}
        </Modal.Title>
      </Modal.Header>
      
      <Modal.Body style={{ backgroundColor: '#f8fafc', padding: '20px' }}>
        <div className="task-details-scrollable" style={{ maxHeight: '75vh', overflowY: 'auto', paddingRight: '10px' }}>
          
          {/* 基本信息 */}
          <div className="mb-4">
            <div className="d-flex align-items-center mb-3">
              <div className="flex-shrink-0">
                <i className="bi bi-info-circle text-primary me-2" style={{ fontSize: '1.2rem' }}></i>
              </div>
              <div>
                <h6 className="mb-0 text-primary fw-bold">基本信息</h6>
              </div>
            </div>
            <Card className="border-0 shadow-sm">
              <Card.Body className="p-3">
                <Row className="g-2 mb-3">
                  <Col sm={6}>
                    <div className="bg-light rounded p-2">
                      <small className="text-muted d-block">任务ID</small>
                      <code className="text-primary fw-bold">{currentTask._id || currentTask.id}</code>
                    </div>
                  </Col>
                  <Col sm={6}>
                    <div className="bg-light rounded p-2">
                      <small className="text-muted d-block">项目ID</small>
                      <code className="text-primary fw-bold">{currentTask.project_id}</code>
                    </div>
                  </Col>
                </Row>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <div>
                    <h5 className="mb-1">{currentTask.name}</h5>
                    <Badge bg={getStatusBadge(currentTask.status).bg}>
                      {getStatusBadge(currentTask.status).text}
                    </Badge>
                  </div>
                  <small className="text-muted">v{currentTask.version_number}</small>
                </div>
              </Card.Body>
            </Card>
          </div>

          {/* 时间信息 */}
          <div className="mb-4">
            <div className="d-flex align-items-center mb-3">
              <div className="flex-shrink-0">
                <i className="bi bi-clock text-info me-2" style={{ fontSize: '1.2rem' }}></i>
              </div>
              <div>
                <h6 className="mb-0 text-info fw-bold">时间信息</h6>
              </div>
            </div>
            <Card className="border-0 shadow-sm">
              <Card.Body className="p-3">
                <Row className="g-3">
                  <Col md={6}>
                    <div className="d-flex flex-column">
                      <small className="text-muted">创建时间</small>
                      <span className="font-monospace text-sm">{formatDate(currentTask.created_at)}</span>
                    </div>
                  </Col>
                  <Col md={6}>
                    <div className="d-flex flex-column">
                      <small className="text-muted">更新时间</small>
                      <span className="font-monospace text-sm">{formatDate(currentTask.updated_at)}</span>
                    </div>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          </div>

          {/* 任务内容 */}
          <div className="mb-4">
            <div className="d-flex align-items-center mb-3">
              <div className="flex-shrink-0">
                <i className="bi bi-file-text text-success me-2" style={{ fontSize: '1.2rem' }}></i>
              </div>
              <div>
                <h6 className="mb-0 text-success fw-bold">任务内容</h6>
              </div>
            </div>
            <Card className="border-0 shadow-sm">
              <Card.Body className="p-3">
                <div className="mb-3">
                  <label className="text-muted fw-bold mb-1 d-block">描述</label>
                  <div className="bg-white border rounded p-2" style={{ minHeight: '50px' }}>
                    {currentTask.description || <span className="text-muted fst-italic">暂无描述</span>}
                  </div>
                </div>
                
                <div className="mb-3">
                  <label className="text-muted fw-bold mb-1 d-block">实施指南</label>
                  <div className="bg-white border rounded p-2" style={{ minHeight: '50px' }}>
                    {currentTask.implementation_guide || <span className="text-muted fst-italic">暂无指南</span>}
                  </div>
                </div>
                
                <div>
                  <label className="text-muted fw-bold mb-1 d-block">验证标准</label>
                  <div className="bg-white border rounded p-2" style={{ minHeight: '50px' }}>
                    {currentTask.verification_criteria || <span className="text-muted fst-italic">暂无标准</span>}
                  </div>
                </div>
              </Card.Body>
            </Card>
          </div>

          {/* 待办事项 */}
          <div className="mb-4">
            <div className="d-flex align-items-center mb-3">
              <div className="flex-shrink-0">
                <i className="bi bi-check2-square text-primary me-2" style={{ fontSize: '1.2rem' }}></i>
              </div>
              <div>
                <h6 className="mb-0 text-primary fw-bold">待办事项</h6>
              </div>
            </div>
            <Card className="border-0 shadow-sm">
              <Card.Body className="p-3">
                {Array.isArray(todos) && todos.length > 0 ? (
                  <ListGroup variant="flush">
                    {todos.map((todo, idx) => (
                      <ListGroup.Item key={todo.id || idx} className="d-flex justify-content-between align-items-center px-0 py-2 border-bottom">
                        <div className="d-flex align-items-center flex-grow-1">
                          <div className={`form-check ${todo.status === 'completed' ? 'text-success' : todo.status === 'in_progress' ? 'text-warning' : 'text-muted'}`}>
                            <input
                              type="checkbox"
                              className="form-check-input me-2"
                              checked={todo.status === 'completed'}
                              readOnly
                            />
                            <label className="form-check-label">
                              {todo.content}
                            </label>
                          </div>
                        </div>
                        <div className="d-flex align-items-center gap-2">
                          <Badge 
                            bg={todo.priority === 'high' ? 'danger' : todo.priority === 'medium' ? 'warning' : 'info'} 
                            className="text-white"
                          >
                            {todo.priority === 'high' ? '高' : todo.priority === 'medium' ? '中' : '低'}
                          </Badge>
                          <Badge 
                            bg={todo.status === 'completed' ? 'success' : todo.status === 'in_progress' ? 'warning' : 'secondary'} 
                            className="text-white"
                          >
                            {todo.status === 'completed' ? '已完成' : todo.status === 'in_progress' ? '进行中' : '待办'}
                          </Badge>
                        </div>
                      </ListGroup.Item>
                    ))}
                  </ListGroup>
                ) : (
                  <span className="text-muted fst-italic">暂无待办事项</span>
                )}
              </Card.Body>
            </Card>
          </div>

          {/* 依赖关系 */}
          <div className="mb-4">
            <div className="d-flex align-items-center mb-3">
              <div className="flex-shrink-0">
                <i className="bi bi-diagram-3 text-warning me-2" style={{ fontSize: '1.2rem' }}></i>
              </div>
              <div>
                <h6 className="mb-0 text-warning fw-bold">依赖关系</h6>
              </div>
            </div>
            <Card className="border-0 shadow-sm">
              <Card.Body className="p-3">
                {Array.isArray(currentTask.dependencies) && currentTask.dependencies.length > 0 ? (
                  <div className="d-flex flex-wrap gap-2">
                    {currentTask.dependencies.map((dep, idx) => (
                      <Badge key={idx} bg="secondary" className="font-monospace px-2 py-1">
                        {dep.slice(-8)}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <span className="text-muted fst-italic">无依赖任务</span>
                )}
              </Card.Body>
            </Card>
          </div>

          {/* 相关文件 */}
          {Array.isArray(currentTask.related_files) && currentTask.related_files.length > 0 && (
            <div className="mb-4">
              <div className="d-flex align-items-center mb-3">
                <div className="flex-shrink-0">
                  <i className="bi bi-folder2-open text-secondary me-2" style={{ fontSize: '1.2rem' }}></i>
                </div>
                <div>
                  <h6 className="mb-0 text-secondary fw-bold">相关文件</h6>
                </div>
              </div>
              <Card className="border-0 shadow-sm">
                <Card.Body className="p-3">
                  <div className="space-y-2">
                    {currentTask.related_files.map((file, idx) => (
                      <div key={idx} className="d-flex justify-content-between align-items-center p-2 bg-light rounded">
                        <div>
                          <small className="text-muted d-block">{file.type}</small>
                          <code className="text-sm">{file.path}</code>
                        </div>
                        {file.lineStart && (
                          <Badge bg="light" text="dark">{file.lineStart}-{file.lineEnd}</Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </Card.Body>
              </Card>
            </div>
          )}

          {/* 附加信息 */}
          {(currentTask.notes || currentTask.summary) && (
            <div>
              <div className="d-flex align-items-center mb-3">
                <div className="flex-shrink-0">
                  <i className="bi bi-exclamation-circle text-dark me-2" style={{ fontSize: '1.2rem' }}></i>
                </div>
                <div>
                  <h6 className="mb-0 text-dark fw-bold">附加信息</h6>
                </div>
              </div>
              <Card className="border-0 shadow-sm">
                <Card.Body className="p-3">
                  {currentTask.notes && (
                    <div className="mb-3">
                      <label className="text-muted fw-bold mb-1 d-block">备注</label>
                      <div className="bg-white border rounded p-2">
                        {currentTask.notes}
                      </div>
                    </div>
                  )}
                  {currentTask.summary && (
                    <div>
                      <label className="text-muted fw-bold mb-1 d-block">摘要</label>
                      <div className="bg-white border rounded p-2">
                        {currentTask.summary}
                      </div>
                    </div>
                  )}
                </Card.Body>
              </Card>
            </div>
          )}

        </div>
      </Modal.Body>
      
      <Modal.Footer style={{ backgroundColor: '#f8fafc' }}>
        <Button 
          variant="outline-secondary" 
          onClick={() => {
            handleClose();
            if (onTaskUpdated) {
              onTaskUpdated();
            }
          }}
        >
          <i className="bi bi-arrow-left me-1"></i>
          返回列表
        </Button>
        
        <Button 
          variant="primary"
          onClick={handleEditClick}
        >
          <i className="bi bi-pencil me-1"></i>
          编辑任务
        </Button>
      </Modal.Footer>

      <EditTaskModal 
        show={showEditModal}
        handleClose={() => setShowEditModal(false)}
        task={currentTask}
        projectId={projectId}
        onTaskUpdated={handleTaskUpdated}
      />
    </Modal>
  );
}

export default TaskDetailModal;