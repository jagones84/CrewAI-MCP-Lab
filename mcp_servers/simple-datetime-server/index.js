#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';

class DateTimeServer {
  server; // Removed 'private' and ': Server'

  constructor() {
    this.server = new Server(
      {
        name: 'simple-datetime-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          resources: {}, // No resources needed for this simple server
          tools: {},
        },
      }
    );

    this.setupToolHandlers();

    // Basic error handling
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  setupToolHandlers() { // Removed 'private'
    // List the available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'get_current_datetime',
          description: 'Gets the current date and time on the server.',
          inputSchema: { // No input parameters needed
            type: 'object',
            properties: {},
            required: [],
          },
        },
      ],
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name !== 'get_current_datetime') {
        throw new McpError(
          ErrorCode.MethodNotFound,
          `Unknown tool: ${request.params.name}`
        );
      }

      // No arguments to validate for this tool

      try {
        const now = new Date();
        const dateTimeString = now.toISOString(); // Use ISO format for clarity

        return {
          content: [
            {
              type: 'text',
              text: `The current date and time is: ${dateTimeString}`,
            },
          ],
        };
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error getting date/time: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('DateTime MCP server running on stdio');
  }
}

const server = new DateTimeServer();
server.run().catch(console.error);
