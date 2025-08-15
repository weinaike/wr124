import React from 'react';
import { Navbar, Container, Nav } from 'react-bootstrap';

function Header() {
  return (
    <Navbar expand="lg" className="navbar-custom">
      <Container fluid>
        <Navbar.Brand href="/" className="d-flex align-items-center">
          <div className="brand-icon me-3">
            <i className="bi bi-kanban"></i>
          </div>
          <div>
            <div className="brand-name">Shrimp Task Manager</div>
            <div className="brand-subtitle">智能任务管理系统</div>
          </div>
        </Navbar.Brand>
        
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="ms-auto align-items-center">
            <Nav.Item className="me-3">
              <Nav.Link 
                href={`http://${window.location.hostname}:16686`}
                target="_blank" 
                className="text-light d-flex align-items-center"
                title="打开 Jaeger 链路追踪"
              >
                <i className="bi bi-diagram-3 me-1"></i>
                <span>Jaeger</span>
              </Nav.Link>
            </Nav.Item>
            <Nav.Item className="me-3">
              <div className="nav-info">
                <i className="bi bi-circle-fill text-success me-2" style={{ fontSize: '0.6rem' }}></i>
                <span className="text-light">系统运行正常</span>
              </div>
            </Nav.Item>
            <Nav.Item>
              <div className="nav-user">
                <i className="bi bi-person-circle text-light" style={{ fontSize: '1.5rem' }}></i>
              </div>
            </Nav.Item>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
}

export default Header;
