import { createContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('cfm_token'));
  const [userId, setUserId] = useState(localStorage.getItem('cfm_user_id'));
  const navigate = useNavigate();

  const login = (newToken, newUserId) => {
    localStorage.setItem('cfm_token', newToken);
    localStorage.setItem('cfm_user_id', newUserId);
    setToken(newToken);
    setUserId(newUserId);
    navigate('/dashboard');
  };

  const logout = () => {
    localStorage.removeItem('cfm_token');
    localStorage.removeItem('cfm_user_id');
    setToken(null);
    setUserId(null);
    navigate('/auth');
  };

  return (
    <AuthContext.Provider value={{ token, userId, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
