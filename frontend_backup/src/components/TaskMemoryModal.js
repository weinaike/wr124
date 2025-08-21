import { useState, useEffect } from 'react';
import { Modal, Row, Col, Card, ListGroup, Badge, Spinner } from 'react-bootstrap';
import { apiEndpoints } from '../api/config';

function TaskMemoryModal({ show, handleClose, task, projectId }) {
  const [memories, setMemories] = useState([]);
  const [selectedMemory, setSelectedMemory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [relatedTaskNames, setRelatedTaskNames] = useState({});

  useEffect(() => {
    console.log('Modal show:', show, 'projectId:', projectId, 'task:', task);
    if (show && projectId) {
      fetchMemories();
    }
  }, [show, task, projectId]);

  useEffect(() => {
    const fetchRelatedTaskNames = async () => {
      const taskIds = [...new Set(memories.map(memory => memory.task_id).filter(Boolean))];
      const taskNames = {};
      
      for (const taskId of taskIds) {
        if (!relatedTaskNames[taskId]) {
          const taskName = await fetchTaskName(taskId);
          if (taskName) {
            taskNames[taskId] = taskName;
          }
        }
      }
      
      if (Object.keys(taskNames).length > 0) {
        setRelatedTaskNames(prev => ({ ...prev, ...taskNames }));
      }
    };

    if (memories.length > 0) {
      fetchRelatedTaskNames();
    }
  }, [memories]);

  const fetchMemories = async () => {
    if (!projectId) return;

    setLoading(true);
    try {
      let url;
      if (task && (task._id || task.id)) {
        // 任务级别记忆
        url = `${apiEndpoints.memories(projectId)}?task_id=${encodeURIComponent(task?._id || task?.id || '')}`;
      } else {
        // 项目级别记忆
        url = apiEndpoints.memories(projectId);
      }
      console.log('Fetching memories from:', url);
      const response = await fetch(url, {
        headers: {
          'X-Project-ID': projectId,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Memories data:', data);
        setMemories(Array.isArray(data) ? data : []);
        
        if (Array.isArray(data) && data.length > 0) {
          setSelectedMemory(data[0]);
        }
      } else {
        console.error('Response not OK:', response.status);
      }
    } catch (error) {
      console.error('获取记忆失败:', error);
      setMemories([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchTaskName = async (taskId) => {
    if (!taskId || !projectId) return null;
    
    try {
      const response = await fetch(apiEndpoints.task(projectId, taskId), {
        headers: {
          'X-Project-ID': projectId,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const taskData = await response.json();
        return taskData.name;
      }
    } catch (error) {
      console.error('获取任务名称失败:', error);
    }
    return null;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('zh-CN');
  };

  const getModalTitle = () => {
    if (task && task.name) {
      return `任务记忆 - ${task.name}`;
    }
    return "项目记忆";
  };

  const truncateText = (text, maxLength = 50) => {
    if (!text) return '';
    return text.length > maxLength ? text.slice(0, maxLength) + '...' : text;
  };

  
  if (loading) {
    return (
      <Modal show={show} onHide={handleClose} size="xl">
        <Modal.Body>
          <div className="text-center py-5">
            <Spinner animation="border" variant="primary">
              <span className="visually-hidden">Loading...</span>
            </Spinner>
            <p className="mt-3 text-muted">加载记忆...</p>
          </div>
        </Modal.Body>
      </Modal>
    );
  }

  return (
    <Modal show={show} onHide={handleClose} size="xl" dialogClassName="modal-fullscreen-lg-down">
      <Modal.Header closeButton style={{ backgroundColor: '#f8fafc' }}>
        <Modal.Title>
          <i className="bi bi-journal-text me-2"></i>
          {getModalTitle()}
        </Modal.Title>
      </Modal.Header>
      
      <Modal.Body style={{ backgroundColor: '#f8fafc', padding: '20px' }}>
        <Row className="g-4" style={{ margin: 0 }}>
          {/* 左侧记忆列表 */}
          <Col md={4} style={{ paddingLeft: 0, paddingRight: '15px' }}>
            <Card className="shadow-sm border-0">
              <Card.Header className="bg-light text-dark sticky-top" style={{ top: 0, zIndex: 1 }}>
                <h6 className="mb-0">
                  <i className="bi bi-list-ul me-2"></i>
                  记忆列表 ({memories.length})
                </h6>
              </Card.Header>
              <div style={{ height: '70vh', overflowY: 'auto' }}>
                {memories.length > 0 ? (
                  <ListGroup variant="flush">
                    {memories.map((memory) => (
                      <ListGroup.Item
                        key={memory.id}
                        action
                        active={selectedMemory?.id === memory.id}
                        onClick={() => setSelectedMemory(memory)}
                        className="py-3 px-3 border-0 border-bottom border-light"
                        style={{
                          backgroundColor: selectedMemory?.id === memory.id ? '#f8f9fa' : 'transparent',
                          borderLeft: selectedMemory?.id === memory.id ? '4px solid #6c757d' : 'none',
                          borderRadius: '8px',
                          margin: '4px 8px',
                          transition: 'all 0.3s ease',
                          boxShadow: selectedMemory?.id === memory.id ? '0 2px 8px rgba(108, 117, 125, 0.15)' : 'none'
                        }}
                        onMouseEnter={(e) => {
                          if (!selectedMemory?.id === memory.id) {
                            e.currentTarget.style.backgroundColor = '#f5f5f5';
                            e.currentTarget.style.transform = 'translateX(2px)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!selectedMemory?.id === memory.id) {
                            e.currentTarget.style.backgroundColor = 'transparent';
                            e.currentTarget.style.transform = 'translateX(0)';
                          }
                        }}
                      >
                        <div className="d-flex align-items-center">
                          <i className="bi bi-file-text me-3" style={{ 
                            fontSize: '1rem', 
                            color: selectedMemory?.id === memory.id ? '#495057' : '#666'
                          }}></i>
                          <div className="flex-grow-1">
                            <h6 className="mb-1 text-truncate" style={{ 
                              fontWeight: 500, 
                              color: selectedMemory?.id === memory.id ? '#495057' : '#333',
                              fontSize: '0.9rem'
                            }}>
                              {memory.title || '无标题'}
                            </h6>
                            <small className="text-muted" style={{ fontSize: '0.8rem' }}>
                              {formatDate(memory.created_at).split(' ')[0]}
                            </small>
                          </div>
                          {selectedMemory?.id === memory.id && (
                            <i className="bi bi-check2 text-success ms-2" style={{ fontSize: '1rem' }}></i>
                          )}
                        </div>
                      </ListGroup.Item>
                    ))}
                  </ListGroup>
                ) : (
                  <div className="text-center py-5">
                    <i className="bi bi-journal-x fs-1 text-muted"></i>
                    <p className="text-muted mt-2">暂无相关记忆</p>
                  </div>
                )}
              </div>
            </Card>
          </Col>

          {/* 右侧记忆详情 */}
          <Col md={8} style={{ paddingRight: 0, paddingLeft: '15px' }}>
            <Card className="shadow-sm border-0" style={{ height: '70vh', display: 'flex', flexDirection: 'column' }}>
              <Card.Header className="bg-light sticky-top" style={{ top: 0, zIndex: 1 }}>
                <h6 className="mb-0">
                  <i className="bi bi-file-text me-2"></i>
                  {selectedMemory ? `记忆详情 - ${selectedMemory.title || '无标题'}` : '记忆详情'}
                </h6>
              </Card.Header>
              <Card.Body className="p-4" style={{ overflowY: 'auto', flex: 1 }}>
                    {/* 基本信息 */}
                    {selectedMemory && selectedMemory.version && (
                      <div className="mb-4">
                        <Row className="g-3">
                          <Col md={6}>
                            <div className="bg-light rounded p-3">
                              <small className="text-muted d-block mb-1">版本号</small>
                              <span className="fw-bold">v{selectedMemory.version}</span>
                            </div>
                          </Col>
                        </Row>
                      </div>
                    )}

                    {/* 标题字段 */}
                    {selectedMemory && selectedMemory.title && (
                      <div className="mb-4">
                        <h6 className="text-primary mb-2">
                          <i className="bi bi-tag me-1"></i>
                          标题
                        </h6>
                        <p className="bg-white border rounded p-3 mb-0">
                          {selectedMemory.title}
                        </p>
                      </div>
                    )}

                    
                    {/* 内容 */}
                    {selectedMemory && selectedMemory.raw_text && (
                      <div className="mb-4">
                        <h6 className="text-success mb-2">
                          <i className="bi bi-file-text me-1"></i>
                          内容
                        </h6>
                        <div className="bg-white border rounded p-3">
                          <pre className="mb-0" 
                               style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem', lineHeight: '1.5' }}>
                            {selectedMemory.raw_text}
                          </pre>
                        </div>
                      </div>
                    )}

                    {/* 总结 */}
                    {selectedMemory && selectedMemory.summary && (
                      <div className="mb-4">
                        <h6 className="text-warning mb-2">
                          <i className="bi bi-stars me-1"></i>
                          总结
                        </h6>
                        <div className="bg-warning-subtle border rounded p-3">
                          <p className="mb-0">{selectedMemory.summary}</p>
                        </div>
                      </div>
                    )}

                    {/* 元数据 */}
                    {selectedMemory && selectedMemory.metadata && (
                      <div className="mb-4">
                        <h6 className="text-info mb-2">
                          <i className="bi bi-gear me-1"></i>
                          元数据
                        </h6>
                        <pre className="bg-dark text-light rounded p-3 mb-0"
                             style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap', maxHeight: '300px', overflow: 'auto' }}>
                          {JSON.stringify(selectedMemory.metadata, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* 标签 */}
                    {selectedMemory && selectedMemory.tags && selectedMemory.tags.length > 0 && (
                      <div className="mb-4">
                        <h6 className="text-secondary mb-2">
                          <i className="bi bi-hash me-1"></i>
                          标签
                        </h6>
                        <div className="d-flex flex-wrap gap-1">
                          {selectedMemory.tags.map((tag, index) => (
                            <Badge bg="secondary" key={index}>{tag}</Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 嵌入相关 */}
                    {selectedMemory && selectedMemory.embedding_id && (
                      <div className="mb-4">
                        <h6 className="text-dark mb-2">
                          <i className="bi bi-hexagon me-1"></i>
                          嵌入信息
                        </h6>
                        <div className="bg-light border rounded p-3">
                          <div className="row g-3">
                            <Col md={12}>
                              <small className="text-muted d-block mb-1">嵌入ID</small>
                              <code className="text-primary">{selectedMemory.embedding_id}</code>
                            </Col>
                            <Col md={12}>
                              <small className="text-muted d-block mb-2">状态</small>
                              <Badge bg="success">
                                <i className="bi bi-check-circle me-1"></i>
                                已生成向量索引，可用于语义搜索和RAG应用
                              </Badge>
                            </Col>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 任务关联 */}
                    {selectedMemory && selectedMemory.task_id && (
                      <div className="mb-4">
                        <h6 className="text-primary mb-2">
                          <i className="bi bi-link-45deg me-1"></i>
                          任务关联
                        </h6>
                        <div className="bg-light border rounded p-3">
                          <div className="row g-3">
                            <Col md={12}>
                              <small className="text-muted d-block mb-1">关联任务名称</small>
                              <code className="text-success">
                                {relatedTaskNames[selectedMemory.task_id] || selectedMemory.related_task_name || task?.name || '未知任务'}
                              </code>
                            </Col>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 记忆完整JSON内容 */}
                    {selectedMemory && (
                      <div className="mb-4">
                      <h6 className="text-dark mb-2">
                        <i className="bi bi-braces me-1"></i>
                        记忆完整内容 (JSON)
                      </h6>
                      <div className="bg-dark text-light rounded p-3">
                        <pre 
                          className="mb-0" 
                          style={{ 
                            fontSize: '0.8rem', 
                            whiteSpace: 'pre-wrap', 
                            wordBreak: 'break-word',
                            maxHeight: '400px', 
                            overflow: 'auto',
                            fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace'
                          }}
                        >
                          {JSON.stringify(selectedMemory, null, 2)}
                        </pre>
                      </div>
                      </div>
                    )}
                    {!selectedMemory && (
                      <div className="d-flex align-items-center justify-content-center" style={{ height: '50vh' }}>
                        <div className="text-center">
                          <i className="bi bi-journal-text fs-1 text-muted"></i>
                          <h5 className="text-muted mt-3">请选择要查看的记忆</h5>
                        </div>
                      </div>
                    )}
                  </Card.Body>
                </Card>
          </Col>
        </Row>
      </Modal.Body>
    </Modal>
  );
}

export default TaskMemoryModal;