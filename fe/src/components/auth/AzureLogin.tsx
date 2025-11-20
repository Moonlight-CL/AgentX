import React, { useState } from 'react';
import { Button, message } from 'antd';
import { WindowsOutlined } from '@ant-design/icons';
import { useMsal } from '@azure/msal-react';
import { loginRequest } from '../../config/msalConfig';
import { userAPI } from '../../services/api';
import { useUserStore } from '../../store/userStore';
import { useNavigate } from 'react-router-dom';

interface AzureLoginProps {
  onSuccess?: () => void;
  onError?: (error: string) => void;
  disabled?: boolean;
}

export const AzureLogin: React.FC<AzureLoginProps> = ({
  onSuccess,
  onError,
  disabled = false
}) => {
  const [loading, setLoading] = useState(false);
  const { instance} = useMsal();
  const { login } = useUserStore();
  const navigate = useNavigate();

  const handleAzureLogin = async () => {
    setLoading(true);
    
    try {
      // Perform Azure AD login
      const response = await instance.loginPopup(loginRequest);
      
      if (response.account && response.accessToken && response.idToken) {
        // Send tokens to backend for validation and user creation/update
        const backendResponse = await userAPI.azureLogin({
          access_token: response.accessToken,
          id_token: response.idToken
        });
        
        // Store user data and local JWT token
        login(backendResponse.user, backendResponse.access_token);
        
        message.success(backendResponse.message || 'Azure AD login successful!');
        
        if (onSuccess) {
          onSuccess();
        } else {
          navigate('/chat');
        }
      }
    } catch (error: any) {
      console.error('Azure AD login error:', error);
      
      let errorMessage = 'Azure AD login failed';
      
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      message.error(errorMessage);
      
      if (onError) {
        onError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      type="default"
      icon={<WindowsOutlined />}
      onClick={handleAzureLogin}
      loading={loading}
      disabled={disabled}
      block
      size="large"
      style={{
        height: '45px',
        fontSize: '16px',
        borderRadius: '6px',
        borderColor: '#0078d4',
        color: '#0078d4'
      }}
    >
      Sign in with Microsoft
    </Button>
  );
};

// Wrapper component that checks if Azure AD is configured
interface AzureLoginWrapperProps extends AzureLoginProps {
  showIfNotConfigured?: boolean;
}

export const AzureLoginWrapper: React.FC<AzureLoginWrapperProps> = ({
  showIfNotConfigured = false,
  ...props
}) => {
  // Check if Azure AD is configured (basic check)
  // @ts-ignore - window._env_ is injected at runtime
  const clientId = window._env_?.VITE_AZURE_CLIENT_ID || import.meta.env.VITE_AZURE_CLIENT_ID;
  const isConfigured = clientId && clientId !== 'your-client-id';

  if (!isConfigured && !showIfNotConfigured) {
    return null;
  }

  if (!isConfigured && showIfNotConfigured) {
    return (
      <Button
        type="default"
        icon={<WindowsOutlined />}
        disabled
        block
        size="large"
        style={{
          height: '45px',
          fontSize: '16px',
          borderRadius: '6px',
          borderColor: '#ccc',
          color: '#ccc'
        }}
      >
        Azure AD Not Configured
      </Button>
    );
  }

  return <AzureLogin {...props} />;
};
