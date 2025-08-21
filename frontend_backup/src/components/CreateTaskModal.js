import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Row, Col, Badge, Card } from 'react-bootstrap';
import { apiEndpoints } from '../api/config';

function CreateTaskModal({ show, handleClose, projectId, onTaskCreated }) {
  const [taskName, setTaskName] = useState('');
  const [description, setDescription] = useState('');
  const [implementationGuide, setImplementationGuide] = useState('');
  const [verificationCriteria, setVerificationCriteria] = useState('');
  const [selectedDependencies, setSelectedDependencies] = useState([]);
  const [availableTasks, setAvailableTasks] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (show) {
      fetchAvailableTasks();
    } else {
      // Reset form when modal closes
      setTaskName('');
      setDescription('');
      setImplementationGuide('');
      setVerificationCriteria('');
      setSelectedDependencies([]);
    }
  }, [show, projectId]);

  const fetchAvailableTasks = async () => {
    try {
      const response = await fetch(apiEndpoints.tasks(projectId), {
        headers: {
          'X-Project-ID': projectId
        }
      });
      if (response.ok) {
        const tasks = await response.json();
        setAvailableTasks(tasks);
      }
    } catch (error) {
      console.error('获取可用任务失败:', error);
      setAvailableTasks([]);
    }
  };

  const handleDependencyChange = (task, isChecked) => {
    const taskId = task._id || task.id;
    if (isChecked) {
      setSelectedDependencies(prev => [...prev, taskId]);
    } else {
      setSelectedDependencies(prev => prev.filter(dep => dep !== taskId));
    }
  };

  const handleSubmit = async () => {
    if (!taskName.trim()) {
      alert('请填写任务名称');
      return;
    }
    if (!description.trim()) {
      alert('请填写任务描述');
      return;
    }
    if (!implementationGuide.trim()) {
      alert('请填写实施指南');
      return;
    }
    if (!verificationCriteria.trim()) {
      alert('请填写验证标准');
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch(apiEndpoints.tasks(projectId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Project-ID': projectId
        },
        body: JSON.stringify({ 
          name: taskName.trim(), 
          description: description.trim(),
          implementation_guide: implementationGuide.trim(),
          verification_criteria: verificationCriteria.trim(),
          dependencies: selectedDependencies,
          status: 'pending'
        }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP error! status: ${response.status}`);
      }
      
      setTaskName('');
      setDescription('');
      setImplementationGuide('');
      setVerificationCriteria('');
      handleClose();
      onTaskCreated();
    } catch (e) {
      console.error('创建任务失败:', e);
      alert(`创建任务失败: ${e.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal show={show} onHide={handleClose} size="xl" scrollable>
      <Modal.Header closeButton style={{ backgroundColor: '#f8fafc' }}>
        <Modal.Title>
          <i className="bi bi-plus-circle me-2"></i>
          创建新任务
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
                      placeholder="请输入任务标题"
                      value={taskName}
                      onChange={(e) => setTaskName(e.target.value)}
                      maxLength={100}
                      autoFocus
                    />
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label className="fw-bold">任务描述 *</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={4}
                      placeholder="详细描述任务内容、要求、注意事项..."
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      maxLength={1000}
                      style={{ resize: 'vertical' }}
                    />
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
                    <Form.Label className="fw-bold">实施指南 *</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={4}
                      placeholder="详细说明任务的实施步骤、技术要点、注意事项..."
                      value={implementationGuide}
                      onChange={(e) => setImplementationGuide(e.target.value)}
                      maxLength={1000}
                      style={{ resize: 'vertical' }}
                    />
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label className="fw-bold">验证标准 *</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={3}
                      placeholder="说明如何验证任务完成的标准和方法..."
                      value={verificationCriteria}
                      onChange={(e) => setVerificationCriteria(e.target.value)}
                      maxLength={1000}
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
                  {availableTasks.length > 0 ? (
                    <div>
                      <small className="text-muted mb-2 d-block">选择依赖的任务：</small>
                      <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                        {availableTasks.map((task) => {
                          const taskId = task._id || task.id;
                          const isChecked = selectedDependencies.includes(taskId);
                          return (
                            <Form.Check
                              key={taskId}
                              type="checkbox"
                              id={`dep-${taskId}`}
                              label={
                                <span>
                                  {task.name} 
                                  <Badge bg="secondary" className="ms-2" style={{ fontSize: '0.7rem' }}>
                                    {(taskId).slice(-6)}
                                  </Badge>
                                </span>
                              }
                              checked={isChecked}
                              onChange={(e) => handleDependencyChange(task, e.target.checked)}
                              className="mb-2"
                            />
                          );
                        })}
                      </div>
                      {selectedDependencies.length > 0 && (
                        <div className="mt-2 p-2 bg-light rounded">
                          <small className="text-primary">
                            已选择 {selectedDependencies.length} 个依赖任务
                          </small>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-3">
                      <i className="bi bi-inbox fs-4 text-muted"></i>
                      <p className="text-muted mb-0 mt-2">当前项目中暂无其他任务可选作为依赖</p>
                    </div>
                  )}
                </Card.Body>
              </Card>

              {/* 项目信息 */}
              <Card className="shadow-sm">
                <Card.Header className="bg-light">
                  <h6 className="mb-0">项目信息</h6>
                </Card.Header>
                <Card.Body>
                  <Form.Group className="mb-3">
                    <Form.Label className="fw-bold">项目ID</Form.Label>
                    <Form.Control
                      type="text"
                      value={projectId}
                      readOnly
                      className="bg-light"
                      style={{ cursor: 'not-allowed' }}
                    />
                  </Form.Group>
                  
                  <div className="alert alert-info mb-0">
                    <i className="bi bi-info-circle me-2"></i>
                    <small>
                      新任务将自动设置为 <strong>待处理</strong> 状态
                    </small>
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        </Form>
      </Modal.Body>
      
      <Modal.Footer style={{ backgroundColor: '#f8fafc' }}>
        <Button variant="outline-secondary" onClick={handleClose}>
          <i className="bi bi-x-lg me-1"></i>
          取消
        </Button>
        <Button 
          variant="primary" 
          onClick={handleSubmit}
          disabled={submitting || !taskName.trim() || !description.trim() || !implementationGuide.trim() || !verificationCriteria.trim()}
        >
          <i className="bi bi-check-lg me-1"></i>
          {submitting ? '创建中...' : '创建任务'}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}

export default CreateTaskModal;