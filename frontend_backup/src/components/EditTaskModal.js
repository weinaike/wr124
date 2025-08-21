import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Row, Col, Badge, Card } from 'react-bootstrap';
import { apiEndpoints } from '../api/config';

function EditTaskModal({ show, handleClose, task, projectId, onTaskUpdated }) {
  const [taskData, setTaskData] = useState({
    name: '',
    description: '',
    status: 'pending',
    dependencies: [],
    notes: '',
    implementation_guide: '',
    verification_criteria: '',
    related_files: []
  });
  const [submitting, setSubmitting] = useState(false);
  const [availableTasks, setAvailableTasks] = useState([]);

  useEffect(() => {
    if (show && task) {
      setTaskData({
        name: task.name || '',
        description: task.description || '',
        status: task.status || 'pending',
        dependencies: task.dependencies || [],
        notes: task.notes || '',
        implementation_guide: task.implementation_guide || '',
        verification_criteria: task.verification_criteria || '',
        related_files: task.related_files || []
      });
      fetchAvailableTasks();
    }
  }, [show, task, projectId]);

  const fetchAvailableTasks = async () => {
    try {
      const response = await fetch(apiEndpoints.tasks(projectId), {
        headers: {
          'X-Project-ID': projectId
        }
      });
      if (response.ok) {
        const tasks = await response.json();
        // Filter out current task to prevent self-dependency
        const currentTaskId = task?._id || task?.id;
        const filteredTasks = currentTaskId 
          ? tasks.filter(t => (t._id || t.id) !== currentTaskId)
          : tasks;
        setAvailableTasks(filteredTasks);
      }
    } catch (error) {
      console.error('获取可用任务失败:', error);
      setAvailableTasks([]);
    }
  };

  const handleSubmit = async () => {
    if (!taskData.name.trim()) {
      alert('请填写任务名称');
      return;
    }

    setSubmitting(true);
    try {
      const taskId = task._id || task.id;
      const response = await fetch(apiEndpoints.task(projectId, taskId), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-Project-ID': projectId
        },
        body: JSON.stringify(taskData),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP error! status: ${response.status}`);
      }
      
      handleClose();
      onTaskUpdated();
    } catch (e) {
      console.error('更新任务失败:', e);
      alert(`更新任务失败: ${e.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleInputChange = (field, value) => {
    setTaskData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleDependencyChange = (task, isChecked) => {
    const taskId = task._id || task.id;
    setTaskData(prev => {
      const dependencies = prev.dependencies || [];
      if (isChecked) {
        return {
          ...prev,
          dependencies: [...dependencies, taskId]
        };
      } else {
        return {
          ...prev,
          dependencies: dependencies.filter(dep => dep !== taskId)
        };
      }
    });
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

  return (
    <Modal show={show} onHide={handleClose} size="xl" scrollable>
      <Modal.Header closeButton style={{ backgroundColor: '#f8fafc' }}>
        <Modal.Title>
          <i className="bi bi-pencil me-2"></i>
          编辑任务: {taskData.name}
        </Modal.Title>
      </Modal.Header>
      
      <Modal.Body style={{ backgroundColor: '#f8fafc', padding: '20px' }}>
        <Form>
          <Row className="g-4">
            {/* 基本信息 */}
            <Col lg={8}>
              <Card className="shadow-sm mb-4">
                <Card.Header className="bg-primary text-white">
                  <h6 className="mb-0">基本信息</h6>
                </Card.Header>
                <Card.Body>
                  <Form.Group className="mb-3">
                    <Form.Label className="fw-bold">任务名称 *</Form.Label>
                    <Form.Control
                      type="text"
                      value={taskData.name}
                      onChange={(e) => handleInputChange('name', e.target.value)}
                      maxLength={100}
                    />
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label className="fw-bold">任务描述</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={4}
                      value={taskData.description}
                      onChange={(e) => handleInputChange('description', e.target.value)}
                      style={{ resize: 'vertical' }}
                    />
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label className="fw-bold">状态</Form.Label>
                    <Form.Select 
                      value={taskData.status} 
                      onChange={(e) => handleInputChange('status', e.target.value)}
                    >
                      <option value="pending">待处理</option>
                      <option value="in_progress">进行中</option>
                      <option value="completed">已完成</option>
                      <option value="failed">失败</option>
                      <option value="cancelled">已取消</option>
                    </Form.Select>
                  </Form.Group>
                </Card.Body>
              </Card>

              {/* 任务内容 */}
              <Card className="shadow-sm">
                <Card.Header className="bg-success text-white">
                  <h6 className="mb-0">任务内容</h6>
                </Card.Header>
                <Card.Body>
                  <Form.Group className="mb-3">
                    <Form.Label className="fw-bold">实施指南</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={4}
                      value={taskData.implementation_guide}
                      onChange={(e) => handleInputChange('implementation_guide', e.target.value)}
                      style={{ resize: 'vertical' }}
                    />
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label className="fw-bold">验证标准</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={4}
                      value={taskData.verification_criteria}
                      onChange={(e) => handleInputChange('verification_criteria', e.target.value)}
                      style={{ resize: 'vertical' }}
                    />
                  </Form.Group>
                </Card.Body>
              </Card>
            </Col>

            {/* 右侧信息 */}
            <Col lg={4}>
              {/* 依赖关系 */}
              <Card className="shadow-sm mb-4">
                <Card.Header className="bg-warning text-dark">
                  <h6 className="mb-0">依赖关系</h6>
                </Card.Header>
                <Card.Body>
                  <div className="mb-3">
                    <small className="text-muted mb-2 d-block">选择依赖的任务：</small>
                    <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                      {availableTasks.length > 0 ? (
                        availableTasks.map((availableTask) => {
                          const isChecked = taskData.dependencies.includes(availableTask._id || availableTask.id);
                          return (
                            <Form.Check
                              key={availableTask._id || availableTask.id}
                              type="checkbox"
                              id={`dep-${availableTask._id || availableTask.id}`}
                              label={
                                <span>
                                  {availableTask.name} 
                                  <Badge bg="secondary" className="ms-2" style={{ fontSize: '0.7rem' }}>
                                    {(availableTask._id || availableTask.id).slice(-6)}
                                  </Badge>
                                </span>
                              }
                              checked={isChecked}
                              onChange={(e) => handleDependencyChange(availableTask, e.target.checked)}
                              className="mb-2"
                            />
                          );
                        })
                      ) : (
                        <div className="text-center py-3">
                          <i className="bi bi-inbox fs-4 text-muted"></i>
                          <p className="text-muted mb-0 mt-2">当前项目中暂无其他任务可选作为依赖</p>
                        </div>
                      )}
                      {taskData.dependencies.length > 0 && (
                        <div className="mt-2 p-2 bg-light rounded">
                          <small className="text-primary">
                            已选择 {taskData.dependencies.length} 个依赖任务
                          </small>
                        </div>
                      )}
                    </div>
                  </div>
                </Card.Body>
              </Card>

              {/* 附加信息 */}
              <Card className="shadow-sm">
                <Card.Header className="bg-light">
                  <h6 className="mb-0">附加信息</h6>
                </Card.Header>
                <Card.Body>
                  <Form.Group className="mb-3">
                    <Form.Label className="fw-bold">备注</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={4}
                      value={taskData.notes}
                      onChange={(e) => handleInputChange('notes', e.target.value)}
                      style={{ resize: 'vertical' }}
                    />
                  </Form.Group>

                  <div className="mb-3">
                    <small className="text-muted d-block">当前状态</small>
                    <Badge bg={getStatusBadge(taskData.status).bg}>
                      {getStatusBadge(taskData.status).text}
                    </Badge>
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        </Form>
      </Modal.Body>
      
      <Modal.Footer style={{ backgroundColor: '#f8fafc' }}>
        <Button variant="outline-secondary" onClick={handleClose}>
          取消
        </Button>
        <Button 
          variant="primary" 
          onClick={handleSubmit}
          disabled={submitting || !taskData.name.trim()}
        >
          {submitting ? '保存中...' : '保存修改'}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}

export default EditTaskModal;