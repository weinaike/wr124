# Shrimp Client - Task Management Frontend

A React-based frontend application for managing tasks and memories in the Shrimp MCP service. This application provides a comprehensive interface for task creation, tracking, and memory management with multi-project support.

## Features

- **Task Management**: Create, edit, delete, and track tasks with status management
- **Multi-Project Support**: Organize tasks across different projects with project-based filtering
- **Memory Management**: View and manage task memories and version history
- **Interactive UI**: Built with React Bootstrap for responsive design
- **Real-time Updates**: Automatic task list refreshing and statistics tracking
- **Detailed Views**: Comprehensive task details, memory modal, and version tracking

## Technology Stack

- **React 18.3.0** with modern React features
- **React Bootstrap 5.3.7** for UI components and responsive design
- **Bootstrap Icons 1.13.1** for iconography
- **Axios 1.7.0** for HTTP client communication
- **Create React App** for build tooling and development environment

## Prerequisites

- Node.js (>= 14.0.0)
- npm (>= 6.0.0)
- Backend Shrimp MCP server running on `http://localhost:4444`

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.com/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.com/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Backend Integration

The frontend is configured to communicate with the Shrimp MCP backend service running on `http://localhost:4444`. The API endpoints include:

- `/api/v1/tasks` - Task CRUD operations
- `/api/v1/memories` - Memory management
- `/api/v1/versions` - Version history tracking
- `/health` - Health check endpoint

## Component Structure

```
src/components/
├── Header.js              - Application header with navigation
├── ProjectSidebar.js      - Project selection sidebar
├── UnifiedTaskManager.js  - Main task management interface
├── TaskTableView.js       - Task table view with filtering
├── TaskDetailModal.js     - Detailed task information modal
├── CreateTaskModal.js     - Task creation modal
├── EditTaskModal.js       - Task editing modal
├── TaskMemoryModal.js     - Memory management modal
└── TaskVersionModal.js    - Version history modal
```

## Development

### Environment Setup

1. Clone the repository
2. Navigate to the frontend directory: `cd frontend`
3. Install dependencies: `npm install`
4. Start the development server: `npm start`

The application will be available at `http://localhost:3000`

### Configuration

The application proxy is configured to forward API requests to `http://localhost:4444` (the backend server). This can be modified in `package.json` if your backend runs on a different port.

### Contributing

When contributing to this project, please ensure:
- All new components are properly documented
- Follow the existing code style and patterns
- Test new functionality thoroughly
- Update documentation as needed

## License

This project is part of the Shrimp MCP service ecosystem.