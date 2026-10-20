import React from 'react';
import { NavLink } from 'react-router-dom';
import '../styles/Sidebar.css';

const navItems = [
  { name: 'Overview', path: '/overview', icon: '📊' },
  { name: 'Analyze Transaction', path: '/analyze', icon: '🔍' },
  { name: 'Transactions', path: '/transactions', icon: '💳' },
  { name: 'Users', path: '/users', icon: '👤' },
  { name: 'Alerts', path: '/alerts', icon: '⚠️' },
  { name: 'System', path: '/system', icon: '⚙️' },
];

function Sidebar() {
  return (
    <nav className="sidebar">
      <div className="sidebar-header">FraudLens</div>
      <ul className="sidebar-list">
        {navItems.map(item => (
          <li key={item.path}>
            <NavLink
              to={item.path}
              aria-label={item.name}
              className={({ isActive }) => isActive ? 'active' : ''}
            >
              <span className="icon">{item.icon}</span>
              <span className="label">{item.name}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export default Sidebar;
