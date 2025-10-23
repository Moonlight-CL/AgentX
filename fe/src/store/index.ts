import { create } from 'zustand';
import type { AgentEvent, AttachedFileType, BubbleDataType, ConversationItemType, MessageEvent} from '../types';
import { agentAPI, chatAPI } from '../services/api';
import type { Agent } from '../services/api';
import { formatMessageEvent, formatToHTML } from '../utils/agentEventFormatter';

export { useAgentStore } from './agentStore';
export { useMCPStore } from './mcpStore';
export { useUserStore } from './userStore';
export { useUseCaseStore } from './useCaseStore';

interface ChatState {
  // Conversations
  conversations: ConversationItemType[];
  currentChatId: string | null;
  
  // UI State
  attachmentsOpen: boolean;
  attachedFiles: AttachedFileType;
  inputValue: string;
  agents: Agent[];
  selectedAgent: Agent | null;
  chatRecordEnabled: boolean;
  
  // Agent State
  agentEvents: AgentEvent[];
  isProcessing: boolean;
  
  // Messages
  messages: Array<{
    message: BubbleDataType;
    status?: 'loading' | 'done' | 'error';
  }>;
  
  // Actions
  setConversations: (conversations: ConversationItemType[]) => void;
  setCurrentChatId: (chatId: string | null) => void;
  setMessages: (messages: Array<{
    message: BubbleDataType;
    status?: 'loading' | 'done' | 'error';
  }>) => void;
  setAttachmentsOpen: (open: boolean) => void;
  setAttachedFiles: (files: AttachedFileType) => void;
  setInputValue: (value: string) => void;
  setAgents: (agents: Agent[]) => void;
  setSelectedAgent: (agent: Agent | null) => void;
  setChatRecordEnabled: (enabled: boolean) => void;
  setAgentEvents: (events: AgentEvent[]) => void;
  setIsProcessing: (isProcessing: boolean) => void;
  fetchAgents: () => Promise<void>;
  fetchConversations: () => Promise<void>;
  loadChatResponses: (chatId: string) => Promise<void>;
  createNewConversation: () => void;
  deleteConversation: (key: string) => Promise<{ success: boolean; message: string }>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  // Initial state
  conversations: [],
  currentChatId: null,
  attachmentsOpen: false,
  attachedFiles: [],
  inputValue: '',
  messages: [],
  agents: [],
  selectedAgent: null,
  chatRecordEnabled: true,
  agentEvents: [],
  isProcessing: false,
  
  // Actions
  setConversations: (conversations) => set({ conversations }),
  setCurrentChatId: (chatId) => set({ currentChatId: chatId }),
  setMessages: (messages) => set({ messages }),
  setAttachmentsOpen: (open) => set({ attachmentsOpen: open }),
  setAttachedFiles: (files) => set({ attachedFiles: files }),
  setInputValue: (value) => set({ inputValue: value }),
  setAgents: (agents) => set({ agents }),
  setSelectedAgent: (agent) => set({ selectedAgent: agent }),
  setChatRecordEnabled: (enabled) => set({ chatRecordEnabled: enabled }),
  setAgentEvents: (events) => set({ agentEvents: events }),
  setIsProcessing: (isProcessing) => {
    set({ isProcessing });
    
    // When isProcessing changes to false, fetch conversations to update the list
    if (!isProcessing) {
      get().fetchConversations();
    }
  },
  
  fetchAgents: async () => {
    try {
      const data = await agentAPI.getAgents();
      set({ agents: data });
    } catch (error) {
      console.error('Error fetching agents:', error);
    }
  },
  
  fetchConversations: async () => {
    try {
      const records = await chatAPI.getChatRecords();
      
      // Convert ChatRecord[] to ConversationItemType[]
      const conversations: ConversationItemType[] = records.map(record => ({
        key: record.id,
        label: record.user_message.length > 30 
          ? record.user_message.substring(0, 30) + '...' 
          : record.user_message,
        group: new Date(record.create_time).toLocaleDateString()
      }));
      
      set({ conversations });
    } catch (error) {
      console.error('Error fetching conversations:', error);
    }
  },
  
  loadChatResponses: async (chatId: string) => {
    try {
      set({ currentChatId: chatId });
      
      // Get the chat record to find the agent_id
      const records = await chatAPI.getChatRecords();
      const chatRecord = records.find(record => record.id === chatId);
      
      if (chatRecord) {
        // Find the agent used in this chat
        const agents = get().agents;
        if (agents.length === 0) {
          // Fetch agents if not already loaded
          const agentsData = await agentAPI.getAgents();
          set({ agents: agentsData });
          
          // Find the agent with the matching ID
          const agent = agentsData.find(a => a.id === chatRecord.agent_id);
          if (agent) {
            set({ selectedAgent: agent });
          }
        } else {
          // Find the agent with the matching ID
          const agent = agents.find(a => a.id === chatRecord.agent_id);
          if (agent) {
            set({ selectedAgent: agent });
          }
        }
      }
      
      // Get the chat responses
      const responses = await chatAPI.getChatResponses(chatId);
      
      if (responses && responses.length > 0) {
        // Convert responses to agent events
        const events: AgentEvent[] = responses.map(response => {
          try {
            // Try to parse the content as JSON (it might be a serialized agent event)
            return JSON.parse(response.content);
          } catch {
            // If parsing fails, create a simple message event
            return {
              message: {
                role: 'assistant',
                content: [{
                  text: response.content
                }]
              }
            };
          }
        });
        
        set({ agentEvents: events });

        const currentMessageEvents = events as MessageEvent[];
        let htmlContent = '';

        if (currentMessageEvents.length > 0) {
          for (const msgEvent of currentMessageEvents) {
            const formatted = formatMessageEvent(msgEvent);
            htmlContent += formatToHTML(formatted);
          }
          
        }
        
        // Create messages from the responses
        const messages = [
          {
            message: {
              role: 'user',
              content: chatRecord!.user_message
            },
            status: 'done' as const
          },
          {
            message: {
              role: 'assistant',
              content: htmlContent
            },
            status: 'done' as const
          }
      ];
        
        set({ messages });
      }
    } catch (error) {
      console.error(`Error loading chat responses for chat ID ${chatId}:`, error);
    }
  },
  createNewConversation: () => {
    // Reset messages and selectedAgent
    set({
      messages: [],
      selectedAgent: null
    });
  },
  
  deleteConversation: async (key) => {
    try {
      // Call the API to delete the chat
      const result = await chatAPI.deleteChat(key);
      
      if (result.success) {
        // Remove the conversation from the list
        const { conversations, currentChatId } = get();
        const newConversations = conversations.filter((item) => item.key !== key);
        set({ conversations: newConversations });
        
        // Reset messages if the deleted chat was the current one
        if (currentChatId === key) {
          set({ 
            messages: [],
            currentChatId: null,
            agentEvents: []
          });
        }
        
        return { success: true, message: result.message || '对话删除成功' };
      } else {
        return { success: false, message: result.message || '删除对话失败，请稍后重试' };
      }
    } catch (error) {
      console.error(`Error deleting conversation with key ${key}:`, error);
      return { success: false, message: '删除对话时发生错误，请稍后重试' };
    }
  },
}));
