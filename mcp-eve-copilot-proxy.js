#!/usr/bin/env node

/**
 * MCP EVE Co-Pilot Proxy for Claude Desktop
 * Version: 1.0.0
 *
 * Connects Claude Desktop to the EVE Co-Pilot FastAPI server
 * Provides access to EVE Online market data, production costs, and character info
 *
 * Protocol Version: 2025-06-18
 */

const http = require('http');

// ============================================================================
// CONFIGURATION
// ============================================================================
const SERVER_URL = process.env.EVE_COPILOT_URL || 'http://77.24.99.81:8000';
// ============================================================================

// Enable debug logging if DEBUG environment variable is set
const DEBUG = process.env.DEBUG === 'true';

function log(message, data) {
  if (DEBUG) {
    console.error(`[MCP EVE Co-Pilot] ${message}`, data ? JSON.stringify(data) : '');
  }
}

/**
 * Convert backend tool format to MCP inputSchema format
 */
function convertToolToMCPFormat(backendTool) {
  const properties = {};
  const required = [];

  if (backendTool.parameters && Array.isArray(backendTool.parameters)) {
    for (const param of backendTool.parameters) {
      properties[param.name] = {
        type: param.type,
        description: param.description
      };

      if (param.enum && Array.isArray(param.enum) && param.enum.length > 0) {
        properties[param.name].enum = param.enum;
      }

      if (param.required) {
        required.push(param.name);
      }
    }
  }

  const mcpTool = {
    name: backendTool.name,
    description: backendTool.description,
    inputSchema: {
      type: 'object',
      properties: properties
    }
  };

  if (required.length > 0) {
    mcpTool.inputSchema.required = required;
  }

  return mcpTool;
}

/**
 * List all available MCP tools from the server
 */
async function listTools() {
  return new Promise((resolve, reject) => {
    log('Fetching tools list from EVE Co-Pilot server...');

    const req = http.get(`${SERVER_URL}/mcp/tools/list`, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          log('Tools list received from backend');

          if (result.tools && Array.isArray(result.tools)) {
            const mcpTools = result.tools.map(convertToolToMCPFormat);
            log(`Converted ${mcpTools.length} tools to MCP format`);
            resolve({ tools: mcpTools });
          } else {
            log('Warning: Backend returned invalid tools format');
            resolve({ tools: [] });
          }
        } catch (error) {
          log('Error parsing tools list:', error);
          reject(error);
        }
      });
    });

    req.on('error', (error) => {
      log('Error fetching tools list:', error);
      reject(error);
    });

    req.end();
  });
}

/**
 * Call a specific MCP tool on the server
 */
async function callTool(name, args) {
  return new Promise((resolve, reject) => {
    log(`Calling tool: ${name}`, args);

    const postData = JSON.stringify({ name, arguments: args });
    const url = new URL(`${SERVER_URL}/mcp/tools/call`);

    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          log('Tool call result received');
          resolve(result);
        } catch (error) {
          log('Error parsing tool call result:', error);
          reject(error);
        }
      });
    });

    req.on('error', (error) => {
      log('Error calling tool:', error);
      reject(error);
    });

    req.write(postData);
    req.end();
  });
}

/**
 * Handle MCP protocol messages
 */
async function handleMessage(request) {
  log('Received request:', request);

  try {
    // MCP Protocol: Notifications (no response needed)
    if (!('id' in request)) {
      log('Received notification (no response needed):', request.method);
      return null;
    }

    // MCP Protocol: Initialize
    if (request.method === 'initialize') {
      log('Handling initialize request');
      return {
        jsonrpc: '2.0',
        id: request.id,
        result: {
          protocolVersion: '2025-06-18',
          capabilities: {
            tools: {}
          },
          serverInfo: {
            name: 'mcp-eve-copilot',
            version: '1.1.0'
          },
          instructions: `EVE Online Co-Pilot - WICHTIG: Rufe ZUERST das Tool "eve_copilot_context" auf um alle Character-IDs, Region-IDs und Workflows zu erhalten!

SCHNELLREFERENZ:
- Cytrex (CEO): character_id = 1117367444 (hat Corp-Wallet Zugriff)
- Cytricia: character_id = 110592475
- Artallus: character_id = 526379435
- Jita (The Forge): region_id = 10000002
- Amarr (Domain): region_id = 10000043

TYPISCHE WORKFLOWS:
1. "Wie viel ISK hat Cytrex?" → get_character_wallet(character_id=1117367444)
2. "Lohnt sich Hobgoblin Produktion?" → search_item(q="Hobgoblin") dann get_production_cost(type_id=2454, me_level=10)
3. "Corp Wallet?" → get_corporation_wallet(character_id=1117367444)
4. "Arbitrage Drones?" → search_group(q="Combat Drones") dann find_arbitrage(group_id=100)`
        }
      };
    }

    // MCP Protocol: Tools List
    if (request.method === 'tools/list') {
      log('Handling tools/list request');
      const result = await listTools();
      return {
        jsonrpc: '2.0',
        id: request.id,
        result: {
          tools: result.tools || []
        }
      };
    }

    // MCP Protocol: Tool Call
    if (request.method === 'tools/call') {
      log('Handling tools/call request');
      const toolName = request.params.name;
      const toolArgs = request.params.arguments || {};

      const result = await callTool(toolName, toolArgs);

      return {
        jsonrpc: '2.0',
        id: request.id,
        result: {
          content: result.content || [],
          isError: result.isError || false
        }
      };
    }

    // MCP Protocol: Ping
    if (request.method === 'ping') {
      log('Handling ping request');
      return {
        jsonrpc: '2.0',
        id: request.id,
        result: {}
      };
    }

    // Unknown method
    log('Unknown method:', request.method);
    return {
      jsonrpc: '2.0',
      id: request.id,
      error: {
        code: -32601,
        message: `Method not found: ${request.method}`
      }
    };

  } catch (error) {
    log('Error handling message:', error);
    return {
      jsonrpc: '2.0',
      id: request.id,
      error: {
        code: -32603,
        message: `Internal error: ${error.message}`
      }
    };
  }
}

/**
 * Main event loop - read from stdin, process messages, write to stdout
 */
async function main() {
  log('MCP EVE Co-Pilot Proxy starting...');
  log('Server URL:', SERVER_URL);

  const stdin = process.stdin;
  const stdout = process.stdout;

  stdin.setEncoding('utf8');
  let buffer = '';

  stdin.on('data', async (chunk) => {
    buffer += chunk;
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;

      try {
        const request = JSON.parse(line);
        const response = await handleMessage(request);
        if (response !== null) {
          stdout.write(JSON.stringify(response) + '\n');
        }
      } catch (error) {
        log('Parse error:', error);
        stdout.write(JSON.stringify({
          jsonrpc: '2.0',
          id: null,
          error: {
            code: -32700,
            message: `Parse error: ${error.message}`
          }
        }) + '\n');
      }
    }
  });

  stdin.on('end', () => {
    log('stdin closed, exiting...');
    process.exit(0);
  });

  process.on('SIGINT', () => {
    log('SIGINT received, exiting...');
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    log('SIGTERM received, exiting...');
    process.exit(0);
  });
}

// Start the proxy
main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
