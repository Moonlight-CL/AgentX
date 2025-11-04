import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useUserStore } from '../../store/userStore';
import { userAPI } from '../../services/api';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, token, logout, login } = useUserStore();
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  useEffect(() => {
    const verifyToken = async () => {
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        // Verify token with backend
        const response = await userAPI.verifyToken();
        if (response.valid) {
          // Update user info if token is valid
          login(response.user, token);
        } else {
          // Token is invalid, logout
          logout();
        }
      } catch (error) {
        // Token verification failed, logout
        console.error('Token verification failed:', error);
        logout();
      } finally {
        setLoading(false);
      }
    };

    if (isAuthenticated && token) {
      verifyToken();
    } else {
      setLoading(false);
    }
  }, [isAuthenticated, token, login, logout]);

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh'
      }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login page with return url
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
