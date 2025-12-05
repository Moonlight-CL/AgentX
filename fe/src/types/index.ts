import type { GetProp } from 'antd';
import type { Attachments, Prompts } from '@ant-design/x';

export type BubbleDataType = {
  role: string;
  content: string;
};

export type ConversationItemType = {
  key: string;
  label: string;
  group: string;
};

export type MessageHistoryType = Record<string, Array<{
  message: BubbleDataType;
  status?: 'loading' | 'done' | 'error';
}>>;

export type AttachedFileType = GetProp<typeof Attachments, 'items'>;
export type PromptsItemType = GetProp<typeof Prompts, 'items'>;

// Agent Event Types
export interface ToolMetrics {
  tool: {
    toolUseId: string;
    name: string;
    input: Record<string, unknown>;
  };
  call_count: number;
  success_count: number;
  error_count: number;
  total_time: number;
}

export interface EventLoopMetrics {
  cycle_count: number;
  tool_metrics: Record<string, ToolMetrics>;
  cycle_durations: number[];
  accumulated_usage: {
    inputTokens: number;
    outputTokens: number;
    totalTokens: number;
  };
  accumulated_metrics: {
    latencyMs: number;
  };
}

export interface TextGenerationEvent {
  data: string;
  delta: {
    text: string;
  };
  event_loop_metrics: EventLoopMetrics;
  event_loop_cycle_id: string;
  request_state: Record<string, unknown>;
  event_loop_parent_cycle_id?: string;
}

export interface ToolEvent {
  delta: {
    toolUse: {
      input: string;
    };
  };
  current_tool_use: {
    toolUseId: string;
    name: string;
    input: Record<string, unknown>;
  };
  event_loop_metrics: EventLoopMetrics;
  event_loop_cycle_id: string;
  request_state: Record<string, unknown>;
  event_loop_parent_cycle_id?: string;
}

export interface ContentBlockDelta {
  delta: {
    text?: string;
    toolUse?: {
      input: string;
    };
  };
  contentBlockIndex: number;
}

export interface ContentBlockStart {
  start: {
    toolUse?: {
      toolUseId: string;
      name: string;
    };
  };
  contentBlockIndex: number;
}

export interface ContentBlockStop {
  contentBlockIndex: number;
}

export interface MessageStart {
  role: string;
}

export interface MessageStop {
  stopReason: string;
}

export interface MetadataEvent {
  usage: {
    inputTokens: number;
    outputTokens: number;
    totalTokens: number;
  };
  metrics: {
    latencyMs: number;
  };
}

export interface EventType {
  messageStart?: MessageStart;
  messageStop?: MessageStop;
  contentBlockStart?: ContentBlockStart;
  contentBlockDelta?: ContentBlockDelta;
  contentBlockStop?: ContentBlockStop;
  metadata?: MetadataEvent;
}

export interface EventEvent {
  event: EventType;
}

export interface MessageContent {
  text?: string;
  toolUse?: {
    toolUseId: string;
    name: string;
    input: Record<string, unknown>;
  };
  toolResult?: {
    status: string;
    content: Array<Record<string, unknown>>;
    toolUseId: string;
  };
  image?: {
    format: string;
    source: {
      bytes?: {
        __bytes_encoded__?: boolean;
        data: string;
      };
      s3key?: string;
    };
  };
  video?: {
    format: string;
    source: {
      bytes?: {
        __bytes_encoded__?: boolean;
        data: string;
      };
      s3key?: string;
    };
  };
  document?: {
    format: string;
    name?: string;
    source: {
      bytes?: {
        __bytes_encoded__?: boolean;
        data: string;
      };
      s3key?: string;
    };
  };
}

export interface Message {
  role: string;
  content: MessageContent[];
}

export interface MessageEvent {
  message: Message;
}

export interface InitEvent {
  init_event_loop?: boolean;
  start?: boolean;
  start_event_loop?: boolean;
}

export interface LifecycleEvent {
  force_stop?: boolean;
  force_stop_reason?: string;
}

export interface ReasoningEvent {
  reasoning: boolean;
  reasoningText: string;
  reasoning_signature?: string;
}

export type AgentEvent = 
  | TextGenerationEvent 
  | ToolEvent 
  | EventEvent
  | MessageEvent
  | InitEvent
  | LifecycleEvent 
  | ReasoningEvent;

// Helper function to determine event type
export const getEventType = (event: AgentEvent): 'text' | 'tool' | 'event' | 'message' | 'init' | 'lifecycle' | 'reasoning' => {
  if ('data' in event) return 'text';
  if ('current_tool_use' in event) return 'tool';
  if ('event' in event) return 'event';
  if ('message' in event) return 'message';
  if ('init_event_loop' in event || 'start' in event || 'start_event_loop' in event) return 'init';
  if ('reasoning' in event) return 'reasoning';
  return 'lifecycle';
};

// REST API Types
export interface EndpointParameters {
  query?: Record<string, string>;
  body?: Record<string, string>;
  headers?: Record<string, string>;
}

export interface EndpointConfig {
  path: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  tool_name: string;
  tool_description: string;
  parameters?: EndpointParameters;
  response_mapping?: any;
}

export interface AuthConfig {
  header?: string;
  value: string;
}

export interface RestAPI {
  api_id?: string;
  user_id?: string;
  name: string;
  base_url: string;
  auth_type: 'bearer' | 'api_key' | 'basic' | 'none';
  auth_config?: AuthConfig;
  endpoints: EndpointConfig[];
}
