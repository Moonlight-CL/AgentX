import * as http from 'http';
import * as https from 'https';
import { URL } from 'url';

// API endpoint for async chat
const API_ENDPOINT = process.env.API_ENDPOINT || 'https://api.example.com/api/agent/async_chat';
// AWS region from environment variables
const AWS_REGION = process.env.AWS_REGION || 'us-west-2';
// Service API Key for authentication
const SERVICE_API_KEY = process.env.SERVICE_API_KEY || '';

/**
 * Helper function to make HTTP/HTTPS requests
 */
const makeRequest = (url: string, method: string, data: any): Promise<any> => {
  return new Promise((resolve, reject) => {
    try {
      const parsedUrl = new URL(url);
      const postData = JSON.stringify(data);
      
      // Determine if we should use HTTP or HTTPS based on the URL protocol
      const isHttps = parsedUrl.protocol === 'https:';
      const defaultPort = isHttps ? 443 : 80;
      
      const options = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || defaultPort,
        path: parsedUrl.pathname + parsedUrl.search,
        method: method,
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(postData),
          'X-API-Key': SERVICE_API_KEY
        }
      };

      // Use the appropriate request function based on the protocol
      const requestFn = isHttps ? https.request : http.request;
      const req = requestFn(options, (res) => {
        let responseData = '';
        
        res.on('data', (chunk) => {
          responseData += chunk;
        });
        
        res.on('end', () => {
          try {
            const parsedData = JSON.parse(responseData);
            resolve({
              statusCode: res.statusCode,
              data: parsedData
            });
          } catch (error) {
            resolve({
              statusCode: res.statusCode,
              data: responseData
            });
          }
        });
      });
      
      req.on('error', (error) => {
        reject(error);
      });
      
      req.write(postData);
      req.end();
    } catch (error) {
      reject(error);
    }
  });
};

/**
 * Lambda function that is triggered by EventBridge Scheduler
 * to execute an agent chat asynchronously.
 */
export const handler = async (event: any): Promise<any> => {
  console.log('Event received:', JSON.stringify(event, null, 2));
  console.log(`Using AWS region: ${AWS_REGION}`);
  
  try {
    // Extract parameters from the event
    const userId = event.user_id;
    const agentId = event.agent_id;
    const agentOwnerId = event.agent_owner_id;
    const scheduleId = event.schedule_id;
    const userMessage = event.user_message || `[Scheduled Task] Execute scheduled task for agent ${agentId}`;
    
    if (!userId || !agentId || !agentOwnerId) {
      throw new Error('User Id / Agent ID / Agent User Id is required');
    }
    
    console.log(`Executing scheduled task for user: ${userId}, agent ${agentId}-${agentOwnerId} (Schedule ID: ${scheduleId})`);
    
    // Call the async chat API
    const response = await makeRequest(API_ENDPOINT, 'POST', {
      user_id : userId,
      agent_id: agentId,
      agent_owner_id: agentOwnerId,
      user_message: userMessage,
    });
    
    console.log('API response:', response.statusCode, response.data);
    
    return {
      statusCode: 200,
      body: JSON.stringify({
        message: 'Scheduled task executed successfully',
        scheduleId,
        agentId,
        chatId: response.data?.chat_id,
        region: AWS_REGION,
      }),
    };
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('Error executing scheduled task:', errorMessage);
    
    return {
      statusCode: 500,
      body: JSON.stringify({
        message: 'Error executing scheduled task',
        error: errorMessage,
        region: AWS_REGION,
      }),
    };
  }
};
