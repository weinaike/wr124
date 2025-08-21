import React, { useState, useEffect } from 'react';
import { Table, Alert } from 'react-bootstrap';
import { apiEndpoints } from '../api/config';

function TaskList({ projectId, refreshTasks }) {
  const [tasks, setTasks] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!projectId) return;

    const fetchTasks = async () => {
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
        setTasks(data);
      } catch (e) {
        setError(e.message);
        setTasks([]);
      }
    };

    fetchTasks();
  }, [projectId, refreshTasks]);

  if (error) {
    return <Alert variant="danger">Error fetching tasks: {error}</Alert>;
  }

  return (
    <Table striped bordered hover responsive>
      <thead>
        <tr>
          <th>#</th>
          <th>Title</th>
          <th>Description</th>
          <th>Status</th>
          <th>Created At</th>
        </tr>
      </thead>
      <tbody>
        {tasks.length > 0 ? (
          tasks.map((task, index) => (
            <tr key={task.id}>
              <td>{index + 1}</td>
              <td>{task.name}</td>
              <td>{task.description}</td>
              <td>{task.status}</td>
              <td>{task.created_at ? new Date(task.created_at).toLocaleString() : 'N/A'}</td>
            </tr>
          ))
        ) : (
          <tr>
            <td colSpan="5" className="text-center">No tasks found.</td>
          </tr>
        )}
      </tbody>
    </Table>
  );
}

export default TaskList;
