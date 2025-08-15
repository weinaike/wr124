import React, { useState, useEffect } from 'react';
import { ListGroup, Spinner, Alert, Button, Modal } from 'react-bootstrap';
import { apiEndpoints } from '../api/config';

function ProjectSidebar({ selectedProject, onProjectSelect, className = '' }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await fetch(apiEndpoints.projects());
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setProjects(data.projects || []);
    } catch (e) {
      setError(e.message);
      setProjects([]);
    } finally {
      setLoading(false);
    }
  };

  const refreshProjects = () => {
    fetchProjects();
  };

  const handleDeleteClick = (project, e) => {
    e.stopPropagation();
    setProjectToDelete(project);
    setShowDeleteModal(true);
  };

  const handleDeleteProject = async () => {
    if (!projectToDelete) return;
    
    setDeleting(true);
    try {
      const response = await fetch(apiEndpoints.project(projectToDelete), {
        method: 'DELETE',
        headers: {
          'X-Project-ID': projectToDelete
        }
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP error! status: ${response.status}`);
      }
      
      // If the deleted project was the selected one, switch to default
      if (selectedProject === projectToDelete) {
        onProjectSelect('default');
      }
      
      setShowDeleteModal(false);
      setProjectToDelete(null);
      refreshProjects();
    } catch (e) {
      console.error('删除项目失败:', e);
      alert(`删除项目失败: ${e.message}`);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center p-4">
        <Spinner size="sm" animation="border" />
        <div className="mt-2">
          <small className="text-muted">加载项目列表...</small>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="danger" className="m-3 p-2">
        <small>{error}</small>
        <div className="mt-2">
          <button 
            className="btn btn-link p-0 text-decoration-none" 
            onClick={refreshProjects}
            style={{fontSize: '0.8rem'}}
          >
            重试
          </button>
        </div>
      </Alert>
    );
  }

  return (
    <>
      <div className={`project-sidebar ${className}`}>
        <div className="d-flex justify-content-between align-items-center p-3 border-bottom">
          <h6 className="mb-0 text-muted">项目列表</h6>
          <button 
            className="btn btn-link p-0 text-decoration-none"
            onClick={refreshProjects}
            style={{ fontSize: '0.8rem' }}
            title="刷新项目列表"
          >
            <i className="bi bi-arrow-clockwise"></i>
          </button>
        </div>
        
        <ListGroup variant="flush" className="border-0">
          {projects.map((project, index) => (
            <ListGroup.Item
              key={`${project}-${index}`}
              action
              active={selectedProject === project}
              onClick={() => onProjectSelect(project)}
              className="border-0 px-3 py-2 d-flex justify-content-between align-items-center"
              style={{ cursor: 'pointer' }}
            >
              <div>
                <i className="bi bi-folder2-open me-2 text-primary"></i>
                <span className="text-truncate" style={{maxWidth: '120px'}} title={project}>
                  {project === 'default' ? '默认项目' : 
                    project.length > 20 ? project.substring(0, 10) + '...' + project.substring(project.length-10) : project
                  }
                </span>
              </div>
              <div className="d-flex align-items-center gap-2">
                {project !== 'default' && (
                  <Button
                    variant="outline-danger"
                    size="sm"
                    className="border-0 p-1 hover-lift"
                    style={{ opacity: 0.7 }}
                    onClick={(e) => handleDeleteClick(project, e)}
                    title={`删除项目: ${project}`}
                  >
                    <i className="bi bi-trash fs-6"></i>
                  </Button>
                )}
              </div>
            </ListGroup.Item>
          ))}
        </ListGroup>
      </div>

      {/* 删除确认模态框 */}
      <Modal show={showDeleteModal} onHide={() => setShowDeleteModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>确认删除项目</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p className="text-danger fw-bold">
            <i className="bi bi-exclamation-triangle-fill me-2"></i>
            危操作：此操作将删除项目及其所有任务数据
          </p>
          <p>您确定要删除项目 <strong className="text-primary">{projectToDelete}</strong> 吗？</p>
          <p className="text-muted">已添加的对审计日志将被保留。</p>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>
            取消
          </Button>
          <Button
            variant="danger"
            onClick={handleDeleteProject}
            disabled={deleting}
          >
            {deleting ? (
              <>
                <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                删除中...
              </>
            ) : (
              <>
                <i className="bi bi-trash me-2"></i>
                确认删除
              </>
            )}
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
}

export default ProjectSidebar;