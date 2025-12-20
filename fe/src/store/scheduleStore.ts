import { create } from 'zustand';
import { message } from 'antd';
import { scheduleAPI } from '../services/api';

export interface ScheduleItem {
  id: string;
  agentId: string;
  agentUserId?: string;
  agentName: string;
  cronExpression: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  user_message?: string;
}

interface ScheduleState {
  // Data
  schedules: ScheduleItem[];
  
  // UI State
  loading: boolean;
  createModalVisible: boolean;
  editModalVisible: boolean;
  selectedSchedule: ScheduleItem | null;
  
  // Actions
  fetchSchedules: () => Promise<void>;
  setCreateModalVisible: (visible: boolean) => void;
  setEditModalVisible: (visible: boolean) => void;
  setSelectedSchedule: (schedule: ScheduleItem | null) => void;
  createSchedule: (schedule: { agentId: string; agentUserId: string; cronExpression: string; user_message?: string }) => Promise<void>;
  updateSchedule: (schedule: ScheduleItem & { agentUserId: string }) => Promise<void>;
  deleteSchedule: (id: string) => Promise<void>;
  handleEditSchedule: (schedule: ScheduleItem) => void;
}

export const useScheduleStore = create<ScheduleState>((set, get) => ({
  // Initial state
  schedules: [],
  loading: false,
  createModalVisible: false,
  editModalVisible: false,
  selectedSchedule: null,
  
  // Actions
  fetchSchedules: async () => {
    set({ loading: true });
    try {
      const data = await scheduleAPI.getSchedules();
      set({ schedules: data });
    } catch (error) {
      message.error('获取调度列表失败');
      console.error('Error fetching schedules:', error);
    } finally {
      set({ loading: false });
    }
  },
  
  setCreateModalVisible: (visible) => set({ createModalVisible: visible }),
  
  setEditModalVisible: (visible) => set({ editModalVisible: visible }),
  
  setSelectedSchedule: (schedule) => set({ selectedSchedule: schedule }),
  
  createSchedule: async (schedule) => {
    try {
      await scheduleAPI.createSchedule(schedule);
      message.success('调度任务创建成功');
      set({ createModalVisible: false });
      get().fetchSchedules(); // Refresh the list
    } catch (error) {
      message.error('创建调度任务失败');
      console.error('Error creating schedule:', error);
      throw error;
    }
  },
  
  updateSchedule: async (schedule) => {
    try {
      await scheduleAPI.updateSchedule(schedule);
      message.success('调度任务更新成功');
      set({ editModalVisible: false, selectedSchedule: null });
      get().fetchSchedules(); // Refresh the list
    } catch (error) {
      message.error('更新调度任务失败');
      console.error('Error updating schedule:', error);
    }
  },
  
  deleteSchedule: async (id) => {
    try {
      await scheduleAPI.deleteSchedule(id);
      message.success('调度任务删除成功');
      get().fetchSchedules(); // Refresh the list
    } catch (error) {
      message.error('删除调度任务失败');
      console.error('Error deleting schedule:', error);
    }
  },
  
  handleEditSchedule: (schedule) => {
    set({ 
      selectedSchedule: schedule,
      editModalVisible: true
    });
  }
}));
