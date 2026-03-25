import { useState, useContext } from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import { AuthContext } from '../context/AuthContext'
import { LayoutDashboard, LogOut, Receipt, ShieldQuestion } from 'lucide-react'

export default function Layout() {
  const { logout } = useContext(AuthContext)
  
  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: <LayoutDashboard size={20} /> },
    { name: 'Financial Inputs', path: '/input', icon: <Receipt size={20} /> },
    { name: 'Decision Engine', path: '/decisions', icon: <ShieldQuestion size={20} /> },
  ]

  return (
    <div className="flex bg-slate-50 min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-6 border-b border-slate-200">
          <h1 className="text-2xl font-bold tracking-tight text-blue-600">CFM</h1>
          <p className="text-sm text-slate-500">Corporate Finance Manager</p>
        </div>
        
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                  isActive 
                    ? 'bg-blue-50 text-blue-700 font-medium' 
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              {item.icon}
              <span>{item.name}</span>
            </NavLink>
          ))}
        </nav>
        
        <div className="p-4 border-t border-slate-200">
          <button 
            onClick={logout}
            className="flex items-center space-x-3 px-3 py-2 w-full text-slate-600 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors"
          >
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-h-screen overflow-hidden">
        {/* Simple Header */}
        <header className="bg-white border-b border-slate-200 h-16 flex items-center px-8 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-800">Overview</h2>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
