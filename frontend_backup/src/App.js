import React from 'react';
import '../node_modules/bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';
import Header from './components/Header';
import UnifiedTaskManager from './components/UnifiedTaskManager';
import './App.css';

function App() {
  return (
    <div className="App">
      <Header />
      <UnifiedTaskManager />
    </div>
  );
}

export default App;