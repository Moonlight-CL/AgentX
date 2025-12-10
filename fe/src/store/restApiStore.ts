import { create } from 'zustand';
import { message } from 'antd';
import { restApiAPI } from '../services/api';
import type { RestAPI } from '../types';

interface RestApiState {
  restApis: RestAPI[];
  loading: boolean;
  createModalVisible: boolean;
  editModalVisible: boolean;
  detailModalVisible: boolean;
  deleteModalVisible: boolean;
  selectedApi: RestAPI | null;
  
  fetchRestAPIs: () => Promise<void>;
  setCreateModalVisible: (visible: boolean) => void;
  setEditModalVisible: (visible: boolean) => void;
  setDetailModalVisible: (visible: boolean) => void;
  setDeleteModalVisible: (visible: boolean) => void;
  createRestAPI: (data: Omit<RestAPI, 'api_id' | 'user_id'>) => Promise<void>;
  updateRestAPI: (data: RestAPI) => Promise<void>;
  deleteRestAPI: () => Promise<void>;
  handleViewApi: (api: RestAPI) => void;
  handleEditApi: (api: RestAPI) => void;
  handleDeleteApi: (api: RestAPI) => void;
  testEndpoint: (apiId: string, endpointPath: string, params?: any) => Promise<any>;
}

export const useRestApiStore = create<RestApiState>((set, get) => ({
  restApis: [],
  loading: false,
  createModalVisible: false,
  editModalVisible: false,
  detailModalVisible: false,
  deleteModalVisible: false,
  selectedApi: null,

  fetchRestAPIs: async () => {
    set({ loading: true });
    try {
      const data = await restApiAPI.getRestAPIs();
      set({ restApis: data });
    } catch (error) {
      message.error('Failed to fetch REST APIs');
    } finally {
      set({ loading: false });
    }
  },

  setCreateModalVisible: (visible) => set({ createModalVisible: visible }),
  setEditModalVisible: (visible) => set({ editModalVisible: visible }),
  setDetailModalVisible: (visible) => set({ detailModalVisible: visible }),
  setDeleteModalVisible: (visible) => set({ deleteModalVisible: visible }),

  createRestAPI: async (data) => {
    try {
      await restApiAPI.createRestAPI(data);
      message.success('REST API created successfully');
      set({ createModalVisible: false });
      get().fetchRestAPIs();
    } catch (error) {
      message.error('Failed to create REST API');
    }
  },

  updateRestAPI: async (data) => {
    try {
      if (!data.api_id) throw new Error('API ID is required');
      await restApiAPI.updateRestAPI(data.api_id, data);
      message.success('REST API updated successfully');
      set({ editModalVisible: false, selectedApi: null });
      get().fetchRestAPIs();
    } catch (error) {
      message.error('Failed to update REST API');
    }
  },

  deleteRestAPI: async () => {
    const { selectedApi } = get();
    if (!selectedApi?.api_id) return;
    
    try {
      await restApiAPI.deleteRestAPI(selectedApi.api_id);
      message.success('REST API deleted successfully');
      set({ deleteModalVisible: false, selectedApi: null });
      get().fetchRestAPIs();
    } catch (error) {
      message.error('Failed to delete REST API');
    }
  },

  handleViewApi: (api) => set({ selectedApi: api, detailModalVisible: true }),
  handleEditApi: (api) => set({ selectedApi: api, editModalVisible: true }),
  handleDeleteApi: (api) => set({ selectedApi: api, deleteModalVisible: true }),

  testEndpoint: async (apiId, endpointPath, params) => {
    try {
      const result = await restApiAPI.testEndpoint(apiId, endpointPath, params);
      message.success('Endpoint test successful');
      return result;
    } catch (error: any) {
      message.error(`Endpoint test failed: ${error.message}`);
      throw error;
    }
  },
}));
