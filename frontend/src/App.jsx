import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar.jsx';
import Header from './components/Header.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Analyze from './pages/Analyze.jsx';
import Transactions from './pages/Transactions.jsx';
import Users from './pages/Users.jsx';
import Alerts from './pages/Alerts.jsx';
import System from './pages/System.jsx';
import './styles/App.css';
import './styles/DataStates.css';
import ProjectFooter from "./components/ProjectFooter";

function App() {
  return (
    <Router>
      <div className="app-container">
        <Sidebar />
        <div className="main-content">
          <Header />
          <Routes>
            <Route path="/" element={<Navigate to="/overview" replace />} />
            <Route path="/overview" element={<Dashboard />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/users" element={<Users />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/system" element={<System />} />
          </Routes>
         <ProjectFooter />
        </div>
      </div>
    </Router>
  );
}

export default App;
