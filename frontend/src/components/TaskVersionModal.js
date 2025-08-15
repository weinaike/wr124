import { useState, useEffect } from 'react';
import { Modal, Row, Col, Card, ListGroup, Badge, Spinner, Button } from 'react-bootstrap';
import { apiEndpoints } from '../api/config';

function TaskVersionModal({ show, handleClose, task, projectId }) {
  const [versions, setVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (show && task && (task._id || task.id)) {
      fetchTaskVersions();
    }
  }, [show, task, projectId]);

  const fetchTaskVersions = async () => {
    const taskId = task?._id || task?.id;
    if (!taskId || !projectId) return;

    setLoading(true);
    try {
      const url = `${apiEndpoints.task(projectId, encodeURIComponent(taskId))}/versions`;
      const response = await fetch(url, {
        headers: {
          'X-Project-ID': projectId,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setVersions(Array.isArray(data) ? data : []);
        if (Array.isArray(data) && data.length > 0) {
          setSelectedVersion(data[0]);
        }
      }
    } catch (error) {
      console.error('获取任务版本失败:', error);
      setVersions([]);
    } finally {
      setLoading(false);
    }
  };

  const revertVersion = async (versionId, versionNumber) => {
    const confirmMessage = `确定要将任务版本回滚到 v${versionNumber || '历史版本'} 吗？\n\n这将创建一个新的版本记录。`;
    if (!window.confirm(confirmMessage)) {
      return;
    }

    try {
      const taskId = task?._id || task?.id;
      if (!taskId || !projectId) {
        alert('错误：缺少任务ID或项目ID');
        return;
      }

      const url = `${apiEndpoints.task(projectId, encodeURIComponent(taskId))}/revert?version_id=${encodeURIComponent(versionId)}`;
      
      console.log('启动回滚:', { projectId, taskId, versionId });
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'X-Project-ID': projectId,
          'Accept': 'application/json'
        }
      });

      if (response.ok) {
        const result = await response.json();
        console.log('回滚成功:', result);
        alert(`版本回滚成功！已创建 v${result.version_number || '新版本'}`);
        fetchTaskVersions(); // 刷新列表获取新版本
      } else {
        let errorMessage = '回滚失败';
        try {
          const errorData = await response.json();
          errorMessage += ': ' + (errorData.detail || errorData.message || response.statusText);
        } catch {
          errorMessage += `: ${response.statusText}`;
        }
        alert(errorMessage);
      }
    } catch (error) {
      console.error('回滚错误:', error);
      alert('回滚错误: ' + (error.message.includes('TypeError') ? '网络连接问题' : error.message));
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('zh-CN');
  };

  const formatJSON = (data) => {
    if (!data) return '';
    return JSON.stringify(data, null, 2);
  };

  const formatOperationType = (operation) => {
    const opMap = {
      'create': { text: '创建', badge: 'success', icon: 'bi-plus-circle', color: '#28a745' },
      'update': { text: '更新', badge: 'warning', icon: 'bi-pencil', color: '#ffc107' },
      'delete': { text: '删除', badge: 'danger', icon: 'bi-trash', color: '#dc3545' },
      'rollback': { text: '回滚', badge: 'info', icon: 'bi-arrow-counterclockwise', color: '#17a2b8' }
    };
    return opMap[operation] || { text: operation || 'N/A', badge: 'secondary', icon: 'bi-question-circle', color: '#6c757d' };
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <Modal show={show} onHide={handleClose} size="xl" fullscreen="lg-down">
        <Modal.Body className="bg-light">
          <div className="text-center py-5">
            <Spinner animation="border" variant="primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </Spinner>
            <h4 className="mt-3 text-primary">加载版本数据中...</h4>
            <p className="text-muted">正在获取任务版本历史，请稍候</p>
          </div>
        </Modal.Body>
      </Modal>
    );
  }

  return (
    <Modal 
      show={show} 
      onHide={handleClose} 
      size="xl" 
      dialogClassName="modal-dialog-scrollable"
      style={{'--bs-modal-height': '80vh'}}
    >
      <Modal.Header closeButton className="bg-white border-bottom">
        <Modal.Title className="d-flex align-items-center">
          <i className="bi bi-clock-history me-2 text-primary"></i>
          <div>
            <div className="h5 mb-0 fw-bold text-dark">任务版本历史</div>
            <div className="small text-muted">{task?.name || '暂无任务名称'}</div>
          </div>
        </Modal.Title>
      </Modal.Header>
      
      <Modal.Body className="bg-light p-0">
        <div className="container-fluid py-3" style={{height: 'calc(80vh - 130px)', maxHeight: 'calc(80vh - 130px)'}}>
          <Row className="g-3 h-100">
            {/* 左侧版本列表 */}
            <Col md={4} className="h-100 pe-3">
              <Card className="shadow-sm border-0 h-100">
                <Card.Header className="bg-white border-bottom">
                  <h6 className="mb-0 text-muted">
                    <i className="bi bi-list me-2"></i>版本列表 ({versions.length})
                  </h6>
                </Card.Header>
                <Card.Body className="p-2" style={{height: 'calc(100% - 50px)', overflowY: 'auto'}}>
                  <div className="d-flex flex-column gap-2">
                    {versions.map((version, index) => {
                      const opInfo = formatOperationType(version.operation);
                      return (
                        <div
                          key={version._id || version.id}
                          className={`border-start ${selectedVersion?._id === version._id || selectedVersion?.id === version.id ? 'border-primary bg-light' : 'border-light bg-white'} p-3 cursor-pointer`}
                          onClick={() => setSelectedVersion(version)}
                          style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
                        >
                          <div className="d-flex justify-content-between">
                            <div>
                              <div className="d-flex align-items-center mb-1">
                                <span className={`fw-semibold ${selectedVersion?._id === version._id || selectedVersion?.id === version.id ? 'text-primary' : 'text-dark'}`}>
                                  版本 {version.version_number || version.payload?.version_number || 'N/A'}
                                </span>
                                {index === 0 && (
                                  <span className="badge bg-success ms-2 fs-7">当前</span>
                                )}
                              </div>
                              
                              <small className="text-muted d-flex gap-2 align-items-center">
                                <span className={`badge bg-${opInfo.badge} bg-opacity-10 border-${opInfo.badge} text-${opInfo.badge}`}>
                                  {opInfo.text}
                                </span>
                                <span>by {version.changed_by || '系统'}</span>
                              </small>
                            </div>
                            
                            <small className="text-nowrap text-muted">
                              {formatDate(version.created_at || version.timestamp)}
                            </small>
                          </div>
                          
                          {version.message && version.message.length <= 60 && (
                            <div className="mt-1">
                              <small className="text-muted text-truncate">{version.message}</small>
                            </div>
                          )}
                          
                          {index !== 0 && (
                            <Button
                              variant="outline-secondary"
                              size="sm"
                              className="mt-2 w-100"
                              onClick={async (e) => {
                                e.stopPropagation();
                                console.log('回滚按钮点击:', {
                                  versionId: version._id || version.id,
                                  versionNumber: version.version_number,
                                  task: task?.name,
                                  taskId: task?._id || task?.id
                                });
                                await revertVersion(
                                  version._id || version.id, 
                                  version.version_number || version.payload?.version_number
                                );
                              }}
                            >
                              <small>
                                <i className="bi bi-arrow-counterclockwise me-1"></i>
                                回滚 v{version.version_number || version.payload?.version_number || ''}
                              </small>
                            </Button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </Card.Body>
              </Card>
            </Col>

            {/* 右侧版本详情 */}
            <Col md={8} className="h-100 ps-3">
              <Card className="shadow-sm border-0 h-100">
                <Card.Header className="bg-white border-bottom">
                  <div className="d-flex justify-content-between align-items-center">
                    <h6 className="mb-0 text-muted">
                      版本详情
                      {selectedVersion && (
                        <span className="text-primary fw-bold ms-2">
                          v{selectedVersion.version_number || selectedVersion.payload?.version_number}
                        </span>
                      )}
                    </h6>
                    {selectedVersion && (
                      <small className="text-muted">
                        {formatDate(selectedVersion.created_at || selectedVersion.timestamp)}
                      </small>
                    )}
                  </div>
                </Card.Header>
                <Card.Body className="p-3" style={{height: 'calc(100% - 50px)', overflowY: 'auto'}}>
                  {selectedVersion ? (
                    <div className="d-flex flex-column h-100">
                      {selectedVersion.message && (
                        <div className="mb-3">
                          <h6 className="text-muted mb-2">
                            <i className="bi bi-chat-left-dots me-2"></i>
                            提交信息
                          </h6>
                          <div className="bg-light p-3 rounded border-start border-info">
                            {selectedVersion.message}
                          </div>
                        </div>
                      )}
                      
                      <div className="flex-grow-1 d-flex flex-column">
                        <h6 className="text-muted mb-2">
                          <i className="bi bi-code-square me-2"></i>
                          完整数据
                          <span className="ms-2 small text-muted">
                            {formatFileSize(selectedVersion.payload ? JSON.stringify(selectedVersion.payload).length : 0)}
                          </span>
                        </h6>
                        
                        <div className="bg-dark text-light rounded flex-grow-1 mb-2">
                          <div className="px-2 py-1 border-bottom border-secondary">
                            <small>version-data.json</small>
                          </div>
                          <div className="px-2 py-1" style={{height: 'calc(100% - 26px)', overflow: 'auto'}}>
                            <pre className="mb-0 text-light" 
                                 style={{fontSize: '0.85rem', whiteSpace: 'pre-wrap'}}>
                              {formatJSON(selectedVersion.payload || selectedVersion) || '无数据'}
                            </pre>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-5">
                      <i className="bi bi-file-earmark-text fs-1 text-muted"></i>
                      <h5 className="text-muted mt-3">请选择左侧版本</h5>
                      <p className="text-muted">从左侧选择要查看的详细版本</p>
                    </div>
                  )}
                </Card.Body>
              </Card>
            </Col>
          </Row>
        </div>
      </Modal.Body>
    </Modal>
  );
}

export default TaskVersionModal;