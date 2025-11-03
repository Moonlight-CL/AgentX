import { useRef, useEffect } from 'react';
import { useXAgent, useXChat } from '@ant-design/x';
import { getEventType, type AgentEvent, type BubbleDataType, type MessageEvent} from '../types';
import { useChatStore } from '../store';
import { combineEvents, formatToHTML, formatMessageEvent } from '../utils/agentEventFormatter';
import { agentAPI } from '../services/api';

export const useAgent = () => {
  const abortController = useRef<AbortController | null>(null);
  // Use Zustand's selector pattern to properly subscribe to state changes
  const agentEvents = useChatStore(state => state.agentEvents);
  const isProcessing = useChatStore(state => state.isProcessing);
  const setAgentEvents = useChatStore(state => state.setAgentEvents);
  const setIsProcessing = useChatStore(state => state.setIsProcessing);

  // Custom request function for the agent
  const customRequest = async (
    info: { message: {content: string, fileattachments?: any[]}},
    callbacks: {
      onUpdate: (chunk: string) => void;
      onSuccess: (chunks: string[]) => void;
      onError: (error: Error) => void;
      onStream?: (abortController: AbortController) => void;
    }
  ) => {
    // Get the latest selectedAgent value directly from the store
    const currentSelectedAgent = useChatStore.getState().selectedAgent;
    
    if (!currentSelectedAgent) {
      callbacks.onError(new Error('No agent selected'));
      return;
    }

    setIsProcessing(true);
    setAgentEvents([]);
    
    try {
      // Create a new AbortController for this request
      const controller = new AbortController();
      if (callbacks.onStream) {
        callbacks.onStream(controller);
      }
      
      // Get the chatRecordEnabled value from the store
      const chatRecordEnabled = useChatStore.getState().chatRecordEnabled;
      
      // Get current chat ID from store for session continuation
      const currentChatId = useChatStore.getState().currentChatId;
      
      // Use the unified agentAPI.streamChat method which includes authentication
      const response = await agentAPI.streamChat(
        currentSelectedAgent.id,
        info.message.content,
        chatRecordEnabled,
        currentChatId || undefined,  // Pass current chat ID for session continuation
        info.message.fileattachments  // Pass file attachments
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Get the reader from the response body
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is null');
      }
      
      // Process the stream
      const decoder = new TextDecoder();
      let accumulatedEvents: AgentEvent[] = [];
      
      // Buffer to accumulate partial SSE messages
      let buffer = '';
      
      const processSSEMessage = (data: string) => {
        try {
          const eventData = JSON.parse(data);
          
          // Check if this is a chat_id event (sent by backend for new conversations)
          if (eventData.chat_id && !useChatStore.getState().currentChatId) {
            useChatStore.getState().setCurrentChatId(eventData.chat_id);
          }
          
          if (getEventType(eventData) === "message") {
            accumulatedEvents = [...accumulatedEvents, eventData];
            setAgentEvents(accumulatedEvents);
          }
          
          let htmlContent = '';
          
          // Filter to only include message events
          const currentMessageEvents = accumulatedEvents.filter(
            event => getEventType(event) === 'message'
          ) as MessageEvent[];
          
          if (currentMessageEvents.length > 0) {
            for (const msgEvent of currentMessageEvents) {
              const formatted = formatMessageEvent(msgEvent);
              htmlContent += formatToHTML(formatted);
            }
          } else {
            // If no message events yet, show a loading message
            htmlContent = formatToHTML("Processing...");
          }
          
          // Update the UI with the formatted HTML content
          callbacks.onUpdate(htmlContent);
        } catch (e) {
          console.error('Error parsing SSE data:', data, e);
        }
      };
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }
        
        // Decode the chunk and add it to our buffer
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        
        // Find complete SSE messages (data: ... followed by \n\n)
        let dataStart = 0;
        let dataEnd = 0;
        
        while ((dataStart = buffer.indexOf('data: ', dataEnd)) !== -1) {
          dataEnd = buffer.indexOf('\n\n', dataStart);
          
          if (dataEnd === -1) {
            // No complete message yet, wait for more data
            break;
          }
          
          // Extract the data part (remove 'data: ' prefix)
          const data = buffer.substring(dataStart + 6, dataEnd).trim();
          
          // Process the complete SSE message
          processSSEMessage(data);
          
          // Move past this message
          dataEnd += 2;
        }
        
        // Keep any incomplete message in the buffer
        if (dataStart !== -1 && dataEnd === -1) {
          buffer = buffer.substring(dataStart);
        } else if (dataEnd > 0) {
          buffer = buffer.substring(dataEnd);
        }
      }
      
      // Complete the request
      let htmlContent = '';
      
      // Only show message events
      const finalMessageEvents = accumulatedEvents.filter(event => getEventType(event) === 'message') as MessageEvent[];
      if (finalMessageEvents.length > 0) {
        for (const msgEvent of finalMessageEvents) {
          const formatted = formatMessageEvent(msgEvent);
          htmlContent += formatToHTML(formatted);
        }
      } else {
        // If no message events, show all events as fallback
        const finalContent = combineEvents(accumulatedEvents);
        htmlContent = formatToHTML(finalContent);
      }
      
      callbacks.onSuccess([htmlContent]);
    } catch (error) {
      console.error('Error in stream chat:', error);
      callbacks.onError(error instanceof Error ? error : new Error(String(error)));
    } finally {
      setIsProcessing(false);
    }
  };

  // Create the agent with our custom request function
  const [agent] = useXAgent<BubbleDataType, { message: {content: string}}, string>({
    request: customRequest,
  });
  
  const loading = agent.isRequesting() || isProcessing;
  
  // Use the XChat hook with our agent
  const { onRequest, messages: agentMessages, setMessages: setXChatMessages} = useXChat({
    agent,
    requestFallback: (_, { error }) => {
      if (error.name === 'AbortError') {
        return {
          content: 'Request is aborted',
          role: 'assistant',
        };
      }
      console.error('Request failed:', error);
      return {
        content: 'Request failed, please try again!',
        role: 'assistant',
      };
    },
    transformMessage: (info) => {
      const { originMessage, chunk } = info || {};
      
      // If we have a chunk, use it directly
      if (chunk) {
        return {
          content: chunk,
          role: 'assistant',
        };
      }
      // Otherwise, return the original message or an empty one
      return {
        content: originMessage?.content || '',
        role: 'assistant',
      };
    },
    resolveAbortController: (controller) => {
      abortController.current = controller;
    },
  });

  // Get setMessages from store using selector pattern
  const setMessages = useChatStore(state => state.setMessages);

  // Sync agent messages with store
  useEffect(() => {
    if (agentMessages && agentMessages.length > 0) {
      // Convert agent messages to the format expected by the store
      const convertedMessages = agentMessages.map(item => ({
        message: item.message,
        status: item.status === 'loading' ? 'loading' as const : 
                item.status === 'error' ? 'error' as const : 'done' as const
      }));

      setMessages(convertedMessages);
    }
  }, [agentMessages, setMessages]);


  // Use useEffect to create a memoized handleSubmit function that updates when selectedAgent changes
  const handleSubmit = (val: string, fileattachments?: any[]) => {
    if (!val && (!fileattachments || fileattachments.length === 0)) return;

    if (loading) {
      console.error('Request is in progress, please wait for the request to complete.');
      return;
    }

    // Get the latest selectedAgent value directly from the store
    const currentSelectedAgent = useChatStore.getState().selectedAgent;
    
    if (!currentSelectedAgent) {
      console.error('Please select an agent first');
      return;
    }

    // Store fileAttachments separately to avoid passing it to UI components
    // The customRequest function will access it from the message object
    onRequest({
      stream: true,
      message: {role: 'user', content: val, fileattachments: fileattachments, userinput: "true"}
    });
  };

  const handleAbort = () => {
    abortController.current?.abort();
  };

  return {
    agent,
    loading,
    handleSubmit,
    handleAbort,
    agentEvents,
    setXChatMessages
  };
};
