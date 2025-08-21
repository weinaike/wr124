import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Badge, Button, Alert, Spinner } from 'react-bootstrap';
import { apiEndpoints } from '../api/config';

const getStatusBadge = (status) => {
  const statusMap = {
    pending: { bg: 'warning', text: '待处理' },
    in_progress: { bg: 'info', text: '进行中' },
    completed: { bg: 'success', text: '已完成' },
    cancelled: { bg: 'danger', text: '已取消' },
  };
  return statusMap[status] || { bg: 'secondary', text: status };
};

function EnhancedTaskList({ projectId, refreshTasks }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [statistics, setStatistics] = useState({ total: 0, pending: 0, completed: 0 });

  useEffect(() => {
    if (!projectId) return;

    const fetchTasks = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(apiEndpoints.tasks(projectId), {
          headers: {
            'X-Project-ID': projectId
          }
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setTasks(data || []);
        
        // 计算统计数据
        const stats = {
          total: data.length,
          pending: data.filter(task => task.status === 'pending').length,
          completed: data.filter(task => task.status === 'completed').length,
        };
        setStatistics(stats);
        
      } catch (e) {
        setError(e.message);
        setTasks([]);
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
  }, [projectId, refreshTasks]);

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const truncateText = (text, maxLength = 50) => {
    if (!text) return '';
    return text.length > maxLength ? text.slice(0, maxLength) + '...' : text;
  };

  if (loading) {
    return (
      <div className="text-center py-5">
        <Spinner animation="border" role="status" style={{ color: 'var(--primary-color)' }}>
          <span className="visually-hidden">Loading...</span>
        </Spinner>
        <p className="mt-3 text-muted">正在加载任务列表...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="danger" className="fade-in">
        <Alert.Heading>加载失败</Alert.Heading>
        <p>{error}</p>
        <Alert.Link href="#" onClick={() => window.location.reload()}>
          重试
        </Alert.Link>
      </Alert>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="empty-state fade-in">
        <div className="mb-4">
          <i className="bi bi-emoji-frown" style={{ fontSize: '4rem', color: 'var(--text-secondary)' }}></i>
        </div>
        <h3 className="text-muted mb-3">暂无任务</h3>
        <p className="text-muted mb-4">当前项目还没有创建任何任务，点击右上角的"创建任务"开始您的任务管理吧！</p>
        <Button variant="primary" onClick={() => document.querySelector('.btn-outline-success')?.click()}>
          创建第一个任务
        </Button>
      </div>
    );
  }

  return (
    <div className="fade-in">
      {/* 统计卡片 */}
      <Row className="mb-4">
        <Col md={4}>
          <Card className="text-center h-100">
            <Card.Body>
              <Card.Title className="text-primary font-weight-bold" style={{ fontSize: '2rem' }}>
                {statistics.total}
              </Card.Title>
              <Card.Text>总任务数</Card.Text>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="text-center h-100">
            <Card.Body>
              <Card.Title className="text-warning font-weight-bold" style={{ fontSize: '2rem' }}>
                {statistics.pending}
              </Card.Title>
              <Card.Text>待处理</Card.Text>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="text-center h-100">
            <Card.Body>
              <Card.Title className="text-success font-weight-bold" style={{ fontSize: '2rem' }}>
                {statistics.completed}
              </Card.Title>
              <Card.Text>已完成</Card.Text>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* 任务列表 */}
      <Row>
        {tasks.map((task) => (
          <Col lg={6} xl={4} className="mb-4" key={task.id}>
            <Card className="h-100 shadow-sm task-card">
              <Card.Header 
                style={{ 
                  background: 'linear-gradient(135deg, #667eea 0%, #5a6fd8 100%)',
                  color: 'white',
                  borderBottom: 'none'
                }}
              >
                <div className="d-flex justify-content-between align-items-center">
                  <Card.Title className="mb-0 text-truncate" style={{ fontSize: '1.1rem' }}>
                    {task.name}
                  </Card.Title>
                  <Badge bg={getStatusBadge(task.status).bg}>
                    {getStatusBadge(task.status).text}
                  </Badge>
                </div>
              </Card.Header>
              <Card.Body className="d-flex flex-column">
                <Card.Text 
                  className="flex-grow-1"
                  style={{ 
                    fontSize: '0.9rem', 
                    lineHeight: '1.6',
                    color: 'var(--text-secondary)'
                  }}
                >
                  {truncateText(task.description, 120)}
                </Card.Text>
                
                <div className="mt-auto pt-3">
                  <small className="text-muted d-block">
                    <i className="bi bi-calendar3"></i>
                    创建时间: {formatDate(task.created_at)}
                  </small>
                  {task.updated_at && task.updated_at !== task.created_at && (
                    <small className="text-muted d-block">
                      <i className="bi bi-clock-history"></i>
                      更新于: {formatDate(task.updated_at)}
                    </small>
                  )}
                  {task.priority && (
                    <small className="text-info d-block">
                      <i className="bi bi-exclamation-triangle"></i>
                      优先级: {task.priority}
                    </small>
                  )}
                </div>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}

export default EnhancedTaskList;