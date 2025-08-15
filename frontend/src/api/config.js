// API配置文件
export const API_BASE_URL = '/api';

// API端点构造函数
export const apiEndpoints = {
  // 项目相关
  projects: () => `${API_BASE_URL}/projects`,
  project: (projectId) => `${API_BASE_URL}/project/${projectId}`,
  
  // 任务相关
  tasks: (projectId) => `${API_BASE_URL}/${projectId}/tasks`,
  task: (projectId, taskId) => `${API_BASE_URL}/${projectId}/tasks/${taskId}`,
  taskTodos: (projectId, taskId) => `${API_BASE_URL}/${projectId}/tasks/${taskId}/todos`,
  
  // 记忆相关
  memories: (projectId) => `${API_BASE_URL}/${projectId}/memories`,
  memory: (projectId, memoryId) => `${API_BASE_URL}/${projectId}/memories/${memoryId}`,
  
  // 健康检查
  health: () => `${API_BASE_URL}/health`,
};
