import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  HomeIcon, 
  UserGroupIcon, 
  ChatBubbleLeftRightIcon, 
  DocumentTextIcon, 
  WrenchScrewdriverIcon, 
  Cog6ToothIcon,
  PlusIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '../../hooks/useAuth';

const Sidebar: React.FC = () => {
  const location = useLocation();
  const { user, logout } = useAuth();

  const navigation = [
    { name: 'Dashboard', href: '/', icon: HomeIcon },
    { name: 'Agents', href: '/agents', icon: UserGroupIcon },
    { name: 'Chat', href: '/chat', icon: ChatBubbleLeftRightIcon },
    { name: 'Logs', href: '/logs', icon: DocumentTextIcon },
    { name: 'Tools', href: '/tools', icon: WrenchScrewdriverIcon },
    { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
  ];

  const isActive = (href: string) => {
    if (href === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(href);
  };

  return (
    <div className="sidebar">
      {/* Logo */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-secondary-200">
        <div className="flex items-center">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">A</span>
          </div>
          <span className="ml-3 text-lg font-semibold text-secondary-900">
            Agent Dev
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-4 space-y-1">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`sidebar-item ${isActive(item.href) ? 'active' : ''}`}
            >
              <Icon className="w-5 h-5 mr-3" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Quick Actions */}
      <div className="px-4 py-4 border-t border-secondary-200">
        <Link
          to="/agents/create"
          className="btn btn-primary w-full"
        >
          <PlusIcon className="w-4 h-4 mr-2" />
          New Agent
        </Link>
      </div>

      {/* User Info */}
      <div className="px-4 py-4 border-t border-secondary-200">
        <div className="flex items-center">
          <div className="w-8 h-8 bg-secondary-300 rounded-full flex items-center justify-center">
            <span className="text-secondary-700 font-medium text-sm">
              {user?.username?.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="ml-3 flex-1">
            <p className="text-sm font-medium text-secondary-900">
              {user?.username}
            </p>
            <p className="text-xs text-secondary-500">
              {user?.is_admin ? 'Admin' : 'User'}
            </p>
          </div>
          <button
            onClick={logout}
            className="text-secondary-400 hover:text-secondary-600"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
