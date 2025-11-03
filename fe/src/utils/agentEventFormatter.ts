import type { AgentEvent, EventEvent, MessageEvent, InitEvent } from '../types';
import { getEventType } from '../types';
import { fileAPI } from '../services/api';
import MarkdownIt from 'markdown-it';
// Import highlight.js for code highlighting
import hljs from 'highlight.js';

// Helper function to escape HTML special characters
const escapeHtml = (unsafe: string): string => {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
};

// Initialize markdown-it
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  highlight: function (str: string, lang: string) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value;
      } catch (error) {
        console.error('Error highlighting code:', error);
      }
    }
    return ''; // use external default escaping
  }
});

// Format text generation event
const formatTextEvent = (event: AgentEvent): string => {
  if ('data' in event) {
    return event.data;
  }
  return '';
};

// Format tool event
const formatToolEvent = (event: AgentEvent): string => {
  if ('current_tool_use' in event) {
    const { name, input } = event.current_tool_use;
    const formattedInput = JSON.stringify(input, null, 2);
    
    return `**Using Tool:** ${name}\n\`\`\`json\n${formattedInput}\n\`\`\``;
  }
  return '';
};

// Format event event (events containing event field)
const formatEventEvent = (event: EventEvent): string => {
  const eventData = event.event;
  
  if (eventData.messageStart) {
    return `**Message Start:** Role - ${eventData.messageStart.role}`;
  }
  
  if (eventData.messageStop) {
    return `**Message Stop:** Reason - ${eventData.messageStop.stopReason}`;
  }
  
  if (eventData.contentBlockStart) {
    let result = `**Content Block Start:** Index - ${eventData.contentBlockStart.contentBlockIndex}`;
    if (eventData.contentBlockStart.start.toolUse) {
      result += `\n**Tool:** ${eventData.contentBlockStart.start.toolUse.name}`;
    }
    return result;
  }
  
  if (eventData.contentBlockDelta) {
    let result = '';
    if (eventData.contentBlockDelta.delta.text) {
      result += eventData.contentBlockDelta.delta.text;
    }
    if (eventData.contentBlockDelta.delta.toolUse) {
      result += `\n**Tool Input:** ${eventData.contentBlockDelta.delta.toolUse.input}`;
    }
    return result;
  }
  
  if (eventData.contentBlockStop) {
    return `**Content Block Stop:** Index - ${eventData.contentBlockStop.contentBlockIndex}`;
  }
  
  if (eventData.metadata) {
    return `**Metadata:** Tokens - ${eventData.metadata.usage.totalTokens}, Latency - ${eventData.metadata.metrics.latencyMs}ms`;
  }
  
  return '';
};

// Helper function to detect content format
const detectContentFormat = (content: string): 'json' | 'markdown' | 'sql' | 'html' | 'text' => {
  // Check if it's JSON
  try {
    JSON.parse(content.trim());
    return 'json';
  } catch {
    // Not JSON, continue with other checks
  }
  
  // Check if it's SQL
  if (/^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|COMMIT|ROLLBACK)\s+/i.test(content)) {
    return 'sql';
  }
  
  // Check if it's HTML
  if (/<[a-z][\s\S]*>/i.test(content)) {
    return 'html';
  }
  
  // Check if it's Markdown
  if (/^#+ |^\* |\[.+\]\(.+\)|^```|^>+ /.test(content)) {
    return 'markdown';
  }
  
  // Default to text
  return 'text';
};

// Helper function to extract HTML code blocks from markdown text
const extractHtmlCodeBlocks = (text: string): { htmlCode: string, fullMatch: string }[] => {
  const regex = /```html\s*([\s\S]*?)```/g;
  const matches: { htmlCode: string, fullMatch: string }[] = [];
  let match;
  
  while ((match = regex.exec(text)) !== null) {
    matches.push({
      htmlCode: match[1],
      fullMatch: match[0]
    });
  }
  
  return matches;
};

// Helper function to generate file download link with JavaScript handler
const generateFileDownloadLink = (s3key: string, filename: string, fileType: 'image' | 'video' | 'document'): string => {
  const iconMap = {
    image: '🖼️',
    video: '🎥',
    document: '📄'
  };
  
  // Generate a unique ID for this download link
  const linkId = `file-download-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
  
  // Create a clickable span with JavaScript handler instead of a direct link
  return `<span id="${linkId}" class="file-download-link" style="color: #1890ff; cursor: pointer; text-decoration: underline;" onclick="downloadFile('${s3key}', '${filename}')">${iconMap[fileType]} ${filename}</span>`;
};

// Add global download function to window object
if (typeof window !== 'undefined') {
  (window as any).downloadFile = async (s3key: string, filename: string) => {
    // Find the clicked element to show loading state
    const clickedElement = document.querySelector(`[onclick*="${s3key}"]`) as HTMLElement;
    
    try {
      // Show loading state
      if (clickedElement) {
        clickedElement.classList.add('downloading');
        clickedElement.style.pointerEvents = 'none';
      }
      
      // Use fileAPI to download with proper authentication
      const blob = await fileAPI.downloadFile(s3key);
      
      // Create a temporary URL for the blob
      const url = window.URL.createObjectURL(blob);
      
      // Create a temporary anchor element and trigger download
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }, 100);
      
    } catch (error) {
      console.error('Error downloading file:', error);
      
      // Show user-friendly error message
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      if (errorMessage.includes('401') || errorMessage.includes('Unauthorized')) {
        alert('认证失败，请重新登录后再试。');
      } else if (errorMessage.includes('404') || errorMessage.includes('Not Found')) {
        alert('文件未找到，可能已被删除。');
      } else {
        alert('文件下载失败，请稍后重试。');
      }
    } finally {
      // Remove loading state
      if (clickedElement) {
        clickedElement.classList.remove('downloading');
        clickedElement.style.pointerEvents = '';
      }
    }
  };
}

// Helper function to format file content
const formatFileContent = (content: any, contentType: 'image' | 'video' | 'document'): string => {
  const source = content.source;
  let result = '';
  
  // Check if we have s3key (file stored in S3)
  if (source.s3key) {
    const filename = content.name ? `${content.name}.${content.format}` : `${contentType}.${content.format}`;
    result += generateFileDownloadLink(source.s3key, filename, contentType);
  }
  // Check if we have bytes data (inline file data)
  else if (source.bytes && source.bytes.data) {
    const filename = content.name || `${contentType}.${content.format}`;
    
    if (contentType === 'image') {
      // For images, we can display them inline using data URL
      const dataUrl = `data:image/${content.format};base64,${source.bytes.data}`;
      result += `![${filename}](${dataUrl})\n\n`;
      result += `[📥 Download ${filename}](${dataUrl})`;
    } else {
      // For videos and documents, just show download link
      const dataUrl = `data:${contentType === 'video' ? 'video' : 'application'}/${content.format};base64,${source.bytes.data}`;
      result += `[${contentType === 'video' ? '🎥' : '📄'} ${filename}](${dataUrl})`;
    }
  }
  
  return result;
};

// Format message event
const formatMessageEvent = (event: MessageEvent): string => {
  const message = event.message; 
  let result = '';
  
  message.content.forEach((content, index) => {
    if (content.text) {
      const text = content.text;
      // Check if the text contains HTML code blocks
      const htmlBlocks = extractHtmlCodeBlocks(text);
      
      if (htmlBlocks.length > 0) {
        // Process text with HTML code blocks
        let processedText = text;
        
        // Replace each HTML code block with tabbed content
        htmlBlocks.forEach((block, blockIndex) => {
          // Clean up the HTML code by removing empty lines
          const cleanedHtmlCode = block.htmlCode
            .replace(/^\s*[\r\n]/gm, '') // Remove empty lines
            .replace(/\n\s*\n/g, '\n')   // Replace multiple newlines with a single one
            .trim();                     // Trim whitespace from beginning and end
          
          // Create a unique ID for this HTML block
          const htmlBlockId = `html-block-${Date.now()}-${blockIndex}-${Math.floor(Math.random() * 10000)}`;
          
          // Create the tabbed interface - Note: We're not escaping the HTML structure itself
          // Only the code content in the HTML tab is escaped
          const tabsHtml = `
<div class="html-tabs-container">
  <div class="html-tabs">
    <input type="radio" name="${htmlBlockId}" id="${htmlBlockId}-render" class="html-tab-input" checked>
    <label for="${htmlBlockId}-render" class="html-tab-label">Web</label>
    <input type="radio" name="${htmlBlockId}" id="${htmlBlockId}-code" class="html-tab-input">
    <label for="${htmlBlockId}-code" class="html-tab-label">HTML</label>
    <div class="html-tab-content html-code-content">
      <pre><code class="language-html">${escapeHtml(cleanedHtmlCode)}</code></pre>
    </div>
    <div class="html-tab-content html-render-content">
      <iframe style="width: 100%; height: 900px; border: none;" sandbox="allow-scripts allow-same-origin"
      srcdoc='${escapeHtml(cleanedHtmlCode)}'>
      </iframe>
    </div>
  </div>
</div>`;
          // Replace the original HTML code block with the tabbed interface
          processedText = processedText.replace(block.fullMatch, tabsHtml);
        });
        
        result += processedText;
      } else {
        // No HTML code blocks, just add the text as is
        result += formatToHTML(text);
      }
    }
    
    // Handle image content
    if (content.image) {
      result += '\n' + formatFileContent(content.image, 'image');
    }
    
    // Handle video content
    if (content.video) {
      result += '\n' + formatFileContent(content.video, 'video');
    }
    
    // Handle document content
    if (content.document) {
      result += '\n' + formatFileContent(content.document, 'document');
    }
    
    if (content.toolUse) {
      const { name, input } = content.toolUse;
      const formattedInput = JSON.stringify(input, null, 2);
      result += `\n**Using Tool:** ${name}\n\`\`\`json\n${formattedInput}\n\`\`\``;
    }
    
    if (content.toolResult) {
      const { status, content: resultContent } = content.toolResult;
      
      // Create a unique ID for this tool result
      const toolResultId = `tool-result-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
      
      // Add a button to toggle the visibility of the tool result
      // Use a checkbox hack for CSS-only toggle
      result += `\n<div class="tool-result-container">
        <input type="checkbox" id="${toolResultId}-toggle" class="tool-result-checkbox" />
        <label for="${toolResultId}-toggle" class="tool-result-toggle-btn">
          Tool Result (${status})
        </label>
        <div class="tool-result-content">`;
      
      // Add the tool result content with appropriate formatting
      resultContent.forEach(item => {
        if (item.text && typeof item.text === 'string') {
          const text = item.text;
          const format = detectContentFormat(text);
          
          // For tool result content, we'll create a div with a specific class for styling
          // and add a data attribute for the format to allow custom styling
          result += `<div class="tool-result-formatted" data-format="${format}">`;
          
          switch (format) {
            case 'json':
              try {
                const jsonObj = JSON.parse(text.trim());
                const formattedJson = JSON.stringify(jsonObj, null, 2);
                // Use pre and code tags directly instead of markdown code blocks
                result += `<pre><code class="language-json">${escapeHtml(formattedJson)}</code></pre>`;
              } catch {
                // If parsing fails, just display as text
                result += `<pre>${escapeHtml(text)}</pre>`;
              }
              break;
            case 'sql':
              result += `<pre><code class="language-sql">${escapeHtml(text)}</code></pre>`;
              break;
            case 'html':
              result += `<pre><code class="language-html">${escapeHtml(text)}</code></pre>`;
              break;
            case 'markdown': {
              // For markdown, we'll render it separately
              const renderedMarkdown = md.render(text);
              result += renderedMarkdown;
              break;
            }
            default:
              result += `<pre>${escapeHtml(text)}</pre>`;
          }
          
          result += '</div>';
        }
      });
      
      // Close the div
      result += `</div>
      </div>`;
    }
    
    if (index < message.content.length - 1) {
      result += '\n\n';
    }
  });
  
  return result;
};

// Format init event
const formatInitEvent = (event: InitEvent): string => {
  if ('init_event_loop' in event && event.init_event_loop) {
    return '**Initializing Event Loop...**';
  }
  if ('start_event_loop' in event && event.start_event_loop) {
    return '**Starting Event Loop...**';
  }
  if ('start' in event && event.start) {
    return '**Starting...**';
  }
  return '';
};

// Format reasoning event
const formatReasoningEvent = (event: AgentEvent): string => {
  if ('reasoning' in event && event.reasoningText) {
    return `<div class="reasoning-block">${event.reasoningText}</div>`;
  }
  return '';
};

// Format lifecycle event
const formatLifecycleEvent = (event: AgentEvent): string => {
  if ('force_stop' in event && event.force_stop) {
    return `**Stopped:** ${event.force_stop_reason || 'Unknown reason'}`;
  }
  return '';
};

// Main formatter function
export const formatAgentEvent = (event: AgentEvent): string => {
  const eventType = getEventType(event);
  
  switch (eventType) {
    case 'text':
      return formatTextEvent(event);
    case 'tool':
      return formatToolEvent(event);
    case 'event':
      return formatEventEvent(event as EventEvent);
    case 'message':
      return formatMessageEvent(event as MessageEvent);
    case 'init':
      return formatInitEvent(event as InitEvent);
    case 'reasoning':
      return formatReasoningEvent(event);
    case 'lifecycle':
      return formatLifecycleEvent(event);
    default:
      return '';
  }
};

// Convert formatted string to HTML using markdown-it
export const formatToHTML = (formattedText: string): string => {
  return md.render(formattedText);
};

// Export the formatMessageEvent function
export { formatMessageEvent };

// Combine multiple events into a single formatted string
export const combineEvents = (events: AgentEvent[]): string => {
  // For streaming mode, we want to focus on extracting the actual content
  // rather than showing all the event metadata
  
  let textContent = '';
  let toolContent = '';
  
  // First pass: extract text content from text events and contentBlockDelta events
  events.forEach(event => {
    // Extract text from TextGenerationEvent
    if ('data' in event) {
      textContent += event.data;
    }
    
    // Extract text from contentBlockDelta events
    if ('event' in event && 
        event.event.contentBlockDelta && 
        event.event.contentBlockDelta.delta.text) {
      textContent += event.event.contentBlockDelta.delta.text;
    }
    
    // Extract tool use information
    if ('current_tool_use' in event) {
      const { name, input } = event.current_tool_use;
      const formattedInput = JSON.stringify(input, null, 2);
      toolContent += `\n**Using Tool:** ${name}\n\`\`\`json\n${formattedInput}\n\`\`\`\n\n`;
    }
    
    // Extract tool input from contentBlockDelta events
    if ('event' in event && 
        event.event.contentBlockDelta && 
        event.event.contentBlockDelta.delta.toolUse) {
      toolContent += `\n**Tool Input:** ${event.event.contentBlockDelta.delta.toolUse.input}\n\n`;
    }
  });
  
  // Combine tool content and text content
  let result = '';
  
  if (toolContent) {
    result += toolContent;
  }
  
  if (textContent) {
    result += textContent;
  }
  
  return result;
};
