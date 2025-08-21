import React, { useState, useEffect } from 'react';
import { Row, Col, Container, Card } from 'react-bootstrap';
import ProjectSidebar from './ProjectSidebar';
import TaskTableView from './TaskTableView';
import TaskDetailModal from './TaskDetailModal';
import CreateTaskModal from './CreateTaskModal';
import TaskMemoryModal from './TaskMemoryModal';
import { apiEndpoints } from '../api/config';

function UnifiedTaskManager() {
  const [selectedProject, setSelectedProject] = useState('default');
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [taskStats, setTaskStats] = useState({ total: 0, pending: 0, completed: 0 });
  const [selectedTask, setSelectedTask] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showMemoryModal, setShowMemoryModal] = useState(false);
  const [refreshCounter, setRefreshCounter] = useState(0);

  // 当选择项目变化时，重新加载任务
  useEffect(() => {
    if (selectedProject) {
      fetchTasks();
    }
  }, [selectedProject, refreshCounter]);

  const fetchTasks = async () => {
    if (!selectedProject) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(apiEndpoints.tasks(selectedProject), {
        headers: {
          'X-Project-ID': selectedProject
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setTasks(data || []);
      
      // 计算统计信息
      const stats = {
        total: data.length,
        pending: data.filter(task => task.status === 'pending').length,
        completed: data.filter(task => task.status === 'completed').length,
        inProgress: data.filter(task => task.status === 'in_progress').length,
      };
      setTaskStats(stats);
      
    } catch (e) {
      setError(e.message);
      setTasks([]);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectSelect = (projectId) => {
    setSelectedProject(projectId);
    setTasks([]);
    setError(null);
  };

  const handleTaskClick = (task) => {
    setSelectedTask(task);
    setShowDetail(true);
  };

  const handleCloseDetail = () => {
    setShowDetail(false);
    setSelectedTask(null);
  };

  const refreshTasks = () => {
    setRefreshCounter(prev => prev + 1);
  };

  const handleTaskCreated = () => {
    refreshTasks();
  };

  return (
    <div className="unified-task-manager fade-in-up">
      <Container fluid className="h-100">
        <Row className="h-100 g-0">
          {/* 左侧项目列表 */}
          <Col 
            xs={12} 
            sm={6} 
            md={4} 
            lg={3} 
            xl={2} 
            className="slide-in-left border-end shadow-sm"
            style={{ 
              backgroundColor: 'white', 
              maxHeight: '100vh', 
              overflowY: 'auto' 
            }}
          >
            <div style={{ padding: '1rem 0' }}>
              <ProjectSidebar
                selectedProject={selectedProject}
                onProjectSelect={handleProjectSelect}
                className="h-100"
              />
            </div>
          </Col>

          {/* 右侧任务列表 */}
          <Col xs={12} sm={6} md={8} lg={9} xl={10} className="p-3">
            <div className="slide-in-right">
              <div className="d-flex justify-content-between align-items-center mb-4">
                <div>
                  <h2 className="mb-0" style={{ color: 'var(--text-primary)' }}>
                    <i className="bi bi-clipboard-list me-2 text-primary"></i>
                    {selectedProject === 'default' ? '默认项目' : selectedProject}
                  </h2>
                  <div className="d-flex align-items-center gap-2 mt-1">
                    <small className="text-muted">
                      共 <span className="fw-bold text-primary">{taskStats.total}</span> 个任务
                    </small>
                    <span className="text-muted">•</span>
                    <small className="text-muted">
                      已完成 <span className="fw-bold text-success">{taskStats.completed}</span> 个
                    </small>
                    <span className="text-muted">•</span>
                    <small className="text-muted">
                      进行中 <span className="fw-bold text-info">{taskStats.inProgress}</span> 个
                    </small>
                  </div>
                </div>
                
                <div className="d-flex gap-2">
                  <button
                    className="btn btn-success hover-lift"
                    onClick={() => setShowCreateModal(true)}
                  >
                    <i className="bi bi-plus-circle me-1"></i>
                    添加任务
                  </button>
                  <button
                    className="btn btn-info hover-lift"
                    onClick={() => setShowMemoryModal(true)}
                  >
                    <i className="bi bi-journal-text me-1"></i>
                    记忆查看
                  </button>
                  <button
                    className="btn btn-outline-secondary hover-lift"
                    onClick={refreshTasks}
                  >
                    <i className="bi bi-arrow-clockwise me-1"></i>
                    刷新
                  </button>
                </div>
              </div>

            {/* 统计卡片 */}
            <Row className="mb-4">
              <Col sm={6} md={3} className="mb-3 mb-md-0">
                <Card className="border-0 shadow-sm hover-lift">
                  <Card.Body className="py-3">
                    <Row className="align-items-center">
                      <Col xs="auto" className="pe-2">
                        <div className="stat-icon-horizontal">
                          <i className="bi bi-list-task text-primary" style={{ fontSize: '1.5rem' }}></i>
                        </div>
                      </Col>
                      <Col>
                        <div className="d-flex flex-column">
                          <span className="text-primary fw-bold" style={{ fontSize: '1.6rem', lineHeight: '1' }}>
                            {taskStats.total}
                          </span>
                          <span className="text-muted small">总任务</span>
                        </div>
                      </Col>
                    </Row>
                  </Card.Body>
                </Card>
              </Col>
              <Col sm={6} md={3} className="mb-3 mb-md-0">
                <Card className="border-0 shadow-sm hover-lift">
                  <Card.Body className="py-3">
                    <Row className="align-items-center">
                      <Col xs="auto" className="pe-2">
                        <div className="stat-icon-horizontal">
                          <i className="bi bi-clock text-warning" style={{ fontSize: '1.5rem' }}></i>
                        </div>
                      </Col>
                      <Col>
                        <div className="d-flex flex-column">
                          <span className="text-warning fw-bold" style={{ fontSize: '1.6rem', lineHeight: '1' }}>
                            {taskStats.pending}
                          </span>
                          <span className="text-muted small">待处理</span>
                        </div>
                      </Col>
                    </Row>
                  </Card.Body>
                </Card>
              </Col>
              <Col sm={6} md={3} className="mb-3 mb-md-0">
                <Card className="border-0 shadow-sm hover-lift">
                  <Card.Body className="py-3">
                    <Row className="align-items-center">
                      <Col xs="auto" className="pe-2">
                        <div className="stat-icon-horizontal">
                          <i className="bi bi-play-circle text-info" style={{ fontSize: '1.5rem' }}></i>
                        </div>
                      </Col>
                      <Col>
                        <div className="d-flex flex-column">
                          <span className="text-info fw-bold" style={{ fontSize: '1.6rem', lineHeight: '1' }}>
                            {taskStats.inProgress}
                          </span>
                          <span className="text-muted small">进行中</span>
                        </div>
                      </Col>
                    </Row>
                  </Card.Body>
                </Card>
              </Col>
              <Col sm={6} md={3}>
                <Card className="border-0 shadow-sm hover-lift">
                  <Card.Body className="py-3">
                    <Row className="align-items-center">
                      <Col xs="auto" className="pe-2">
                        <div className="stat-icon-horizontal">
                          <i className="bi bi-check-circle text-success" style={{ fontSize: '1.5rem' }}></i>
                        </div>
                      </Col>
                      <Col>
                        <div className="d-flex flex-column">
                          <span className="text-success fw-bold" style={{ fontSize: '1.6rem', lineHeight: '1' }}>
                            {taskStats.completed}
                          </span>
                          <span className="text-muted small">已完成</span>
                        </div>
                      </Col>
                    </Row>
                  </Card.Body>
                </Card>
              </Col>
            </Row>

            {/* 任务列表 */}
            <div className="fade-in">
              {error && (
                <div className="alert alert-danger" role="alert">
                  <i className="bi bi-exclamation-triangle-fill me-2"></i>
                  加载失败: {error}
                  <button className="btn btn-link ms-2" onClick={refreshTasks}>重试</button>
                </div>
              )}

              {loading ? (
                <div className="text-center py-5">
                  <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                  <p className="text-muted mt-3">正在加载任务...</p>
                </div>
              ) : (
                <TaskTableView
                  tasks={tasks}
                  projectId={selectedProject}
                  onTasksRefreshed={refreshTasks}
                />
              )}
            </div>
            </div>
          </Col>
        </Row>
      </Container>

      <TaskDetailModal 
        show={showDetail} 
        handleClose={handleCloseDetail} 
        task={selectedTask}
        projectId={selectedProject}
        onTaskUpdated={refreshTasks}
      />

      <CreateTaskModal 
        show={showCreateModal}
        handleClose={() => setShowCreateModal(false)}
        projectId={selectedProject}
        onTaskCreated={handleTaskCreated}
      />

      <TaskMemoryModal 
        show={showMemoryModal}
        handleClose={() => setShowMemoryModal(false)}
        task={null}
        projectId={selectedProject}
      />
    </div>
  );
}

export default UnifiedTaskManager;