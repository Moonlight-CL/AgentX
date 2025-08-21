import {
  McpServer,
  ResourceTemplate,
} from "@modelcontextprotocol/sdk/server/mcp.js";

import { MySQLConnection } from "../db/mysql-connection";
import { loadMySQLConfig } from "../config";
import type { Transport } from "@modelcontextprotocol/sdk/shared/transport.js";

import { z } from "zod";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";

export class MySQLMCPServer {
  private server: McpServer;
  private connection: MySQLConnection;

  constructor() {
    // Load configurations
    const mysqlConfig = loadMySQLConfig();

    // Initialize MySQL connection
    this.connection = new MySQLConnection(mysqlConfig);

    this.server = new McpServer({
      name: "mysql",
      version: "1.0.0",
    });

    // Register resources and tools
    this.registerReource();
    this.registerTools();

    // Handle shutdown
    process.on("SIGINT", async () => {
      await this.stop();
      process.exit(0);
    });

    process.on("SIGTERM", async () => {
      await this.stop();
      process.exit(0);
    });
  }

  async connect(transport: Transport): Promise<void> {
    try {
      // await this.connection.connect();
      await this.server.connect(transport);
      console.log("MySQL MCP Server transport connected");
    } catch (error) {
      console.error("Failed to connect to transport", error);
    }
  }

  private registerReource() {
    this.server.resource("databases", "mysql://dbs", async (uri) => {
      const dbs: string[] = await this.connection.getDatabases();
      return {
        contents: dbs.map((db) => ({ uri: uri.href, text: db })),
      };
    });

    this.server.resource(
      "tables",
      new ResourceTemplate("mysql://{db}/tables", { list: undefined }),
      async (uri, { db }) => {
        const database = db as string;
        const tables = await this.connection.getTables(database);
        return {
          contents: tables.map((t) => ({
            uri: `${uri.href}/${t}`,
            text: t,
          })),
        };
      },
    );

    this.server.resource(
      "table-ddl",
      new ResourceTemplate("mysql://{db}/tables/{table}", { list: undefined }),
      async (uri, { db, table }) => {
        const ddl = await this.connection.getTableDDL(
          db as string,
          table as string,
        );
        return {
          contents: [{ uri: uri.href, text: ddl }],
        };
      },
    );
  }

  private registerTools() {
    // register "execute_sql" tool
    this.server.registerTool(
      "execute_sql",
      {
        description: "Execute a SQL query on the MySQL database",
        inputSchema: { sql: z.string(), database: z.string().optional() },
      },
      async ({ sql, database }) => await this.execute_sql(sql, database),
    );

    // register "get_table_count" tool
    this.server.registerTool(
      "get_table_count",
      {
        description: "Get the number of tables in a database",
        inputSchema: { database: z.string().optional() },
      },
      async ({ database }) => await this.getTableCount(database),
    );

    // register "get_total_row_count" tool
    this.server.registerTool(
      "get_total_row_count",
      {
        description:
          "Get the total number of rows across all tables in a database",
        inputSchema: { database: z.string().optional() },
      },
      async ({ database }) => await this.getTotalRowcount(database),
    );

    this.server.registerTool(
      "get_topN_tables",
      {
        description: "Get the top N largest tables in a database",
        inputSchema: { database: z.string(), limit: z.number().optional() },
      },
      async ({ database, limit }) => await this.getTopNTables(database, limit),
    );

    this.server.registerTool(
      "get_slow_querys",
      {
        description: "Get the slow queries during a time period",
        inputSchema: {
          startTime: z.string().optional(),
          endTime: z.string().optional(),
          limit: z.number().optional(),
        },
      },
      async ({ startTime, endTime, limit }) =>
        await this.getSlowQueries(startTime, endTime, limit),
    );
  }

  private async getSlowQueries(
    startTime?: string,
    endTime?: string,
    limit?: number,
  ): Promise<CallToolResult> {
    try {
      const slowQueries = await this.connection.getSlowQueries(
        startTime,
        endTime,
        limit,
      );
      return { content: [{ type: "text", text: slowQueries }] };
    } catch (error: any) {
      return this.createErrorCallResult(error);
    }
  }

  private async getTopNTables(
    database: string,
    limit?: number,
  ): Promise<CallToolResult> {
    try {
      const topNData = await this.connection.getTopNTables(database, limit);
      return {
        content: [{ type: "text", text: JSON.stringify(topNData, null, 2) }],
      };
    } catch (error: any) {
      return this.createErrorCallResult(error);
    }
  }

  private async getTotalRowcount(database?: string): Promise<CallToolResult> {
    try {
      const totalRowCount = await this.connection.getTotalRowCount(database);
      return {
        content: [{ type: "text", text: `${totalRowCount}` }],
      };
    } catch (error: any) {
      return this.createErrorCallResult(error);
    }
  }

  private async getTableCount(database?: string): Promise<CallToolResult> {
    try {
      const totalTableCount = await this.connection.getTableCount(database);
      return {
        content: [{ type: "text", text: `${totalTableCount}` }],
      };
    } catch (error: any) {
      return this.createErrorCallResult(error);
    }
  }

  private async execute_sql(
    sql: string,
    database?: string,
  ): Promise<CallToolResult> {
    
    try {

      // validate sql and check if it is select clause
      const operations = ['update', 'insert', 'delete', 'drop', 'truncate', 'create', 'alter'];
      if(!sql || operations.some(op => sql.trim().toLowerCase().startsWith(op))) {
        return {
          content: [ {type: "text", text: "Only select queries are allowed"} ],
        };
      };
      
      // If database is specified, use it
      if (database) {
        await this.connection.query("USE `" + database + "`");
      }

      const results = await this.connection.queryAsString(sql);
      return { content: [{ type: "text", text: results }] };
    } catch (error: any) {
      return this.createErrorCallResult(error);
    }
  }

  private createErrorCallResult(error: any): CallToolResult {
    return {
      content: [
        {
          type: "text",
          text: error.message || "Unknown error executing SQL",
        },
      ],
    };
  }

  async stop(): Promise<void> {
    try {
      await this.server.close();
      await this.connection.disconnect();
      console.log("MySQL MCP Server stopped");
    } catch (error) {
      console.error("Error stopping MySQL MCP Server:", error);
    }
  }
}
