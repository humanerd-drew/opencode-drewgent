#!/usr/bin/env node
/**
 * wordpress-mcp-server.js — STDIO MCP server for WordPress via wp-cli
 * 
 * Provides tools: create_post, upload_media, set_featured_image,
 * list_posts, get_post, update_post, create_category, list_categories
 * 
 * Usage: node wordpress-mcp-server.js
 * Register in Hermes config.yaml as an MCP server.
 */
const { spawn, execSync } = require('child_process');

const WP_CLI = ['docker', 'exec', 'humanerd-wp', 'wp', '--allow-root'];

function wp(...args) {
  try {
    const result = execSync([...WP_CLI, ...args].join(' '), {
      encoding: 'utf8',
      timeout: 30000,
      maxBuffer: 10 * 1024 * 1024,
    });
    return { success: true, stdout: result.trim() };
  } catch (e) {
    return { success: false, error: e.message || e.stderr || String(e) };
  }
}

// Simple JSON-RPC 2.0 handler via STDIO
const tools = {
  create_post: {
    description: 'Create a new WordPress post',
    parameters: {
      type: 'object',
      properties: {
        title: { type: 'string' },
        content: { type: 'string' },
        category: { type: 'string', default: 'systems' },
        tags: { type: 'string', default: '' },
        status: { type: 'string', enum: ['publish', 'draft'], default: 'publish' },
        date: { type: 'string', default: '' },
        featured_image: { type: 'string', default: '' },
      },
      required: ['title', 'content'],
    },
    handler: (args) => {
      const cmd = ['post', 'create'];
      cmd.push('--post_title=' + args.title);
      cmd.push('--post_content=' + args.content);
      cmd.push('--post_status=' + (args.status || 'publish'));
      if (args.category) cmd.push('--post_category=' + args.category);
      if (args.tags) cmd.push('--tags=' + args.tags);
      if (args.date) cmd.push('--post_date=' + args.date);
      if (args.featured_image) cmd.push('--featured_image=' + args.featured_image);
      return wp(...cmd);
    },
  },
  upload_media: {
    description: 'Upload a media file (image, SVG, etc.) to WordPress',
    parameters: {
      type: 'object',
      properties: {
        file_path: { type: 'string', description: 'Absolute path to file in the container or host' },
        title: { type: 'string', default: '' },
      },
      required: ['file_path'],
    },
    handler: (args) => {
      return wp('media', 'import', args.file_path, '--title=' + (args.title || ''), '--porcelain');
    },
  },
  list_posts: {
    description: 'List recent WordPress posts',
    parameters: {
      type: 'object',
      properties: {
        posts_per_page: { type: 'number', default: 10 },
        status: { type: 'string', default: 'publish' },
      },
    },
    handler: (args) => {
      return wp('post', 'list', '--posts_per_page=' + (args.posts_per_page || 10), '--post_status=' + (args.status || 'publish'), '--fields=ID,post_title,post_date,post_status', '--format=json');
    },
  },
  get_post: {
    description: 'Get a WordPress post by ID',
    parameters: {
      type: 'object',
      properties: { id: { type: 'number' } },
      required: ['id'],
    },
    handler: (args) => {
      return wp('post', 'get', String(args.id), '--format=json');
    },
  },
  create_category: {
    description: 'Create a WordPress category',
    parameters: {
      type: 'object',
      properties: {
        name: { type: 'string' },
        slug: { type: 'string', default: '' },
      },
      required: ['name'],
    },
    handler: (args) => {
      const cmd = ['term', 'create', 'category', args.name];
      if (args.slug) cmd.push('--slug=' + args.slug);
      return wp(...cmd);
    },
  },
  set_site_option: {
    description: 'Set a WordPress site option',
    parameters: {
      type: 'object',
      properties: {
        key: { type: 'string' },
        value: { type: 'string' },
      },
      required: ['key', 'value'],
    },
    handler: (args) => {
      return wp('option', 'update', args.key, args.value);
    },
  },
  set_theme_mod: {
    description: 'Set a WordPress theme modification',
    parameters: {
      type: 'object',
      properties: {
        key: { type: 'string' },
        value: { type: 'string', description: 'JSON-encoded value' },
      },
      required: ['key', 'value'],
    },
    handler: (args) => {
      return wp('eval', `set_theme_mod("${args.key}", ${args.value}); echo "OK";`);
    },
  },
};

// Handle STDIO JSON-RPC 2.0
let buffer = '';
process.stdin.on('data', (chunk) => {
  buffer += chunk.toString();
  const lines = buffer.split('\n');
  buffer = lines.pop(); // keep incomplete line

  for (const line of lines) {
    try {
      const request = JSON.parse(line);
      const tool = tools[request.method];
      
      if (request.method === 'list_tools') {
        const response = {
          jsonrpc: '2.0',
          id: request.id,
          result: Object.entries(tools).map(([name, t]) => ({
            name,
            description: t.description,
            inputSchema: t.parameters,
          })),
        };
        process.stdout.write(JSON.stringify(response) + '\n');
        continue;
      }

      if (request.method === 'call_tool') {
        if (!tool) {
          process.stdout.write(JSON.stringify({
            jsonrpc: '2.0', id: request.id,
            error: { code: -32601, message: `Tool not found: ${request.method}` },
          }) + '\n');
          continue;
        }
        const result = tool.handler(request.params?.arguments || {});
        process.stdout.write(JSON.stringify({
          jsonrpc: '2.0', id: request.id,
          result: {
            content: [{
              type: 'text',
              text: result.success ? result.stdout : `Error: ${result.error}`,
            }],
          },
        }) + '\n');
        continue;
      }
    } catch (e) {
      // ignore parse errors on incomplete chunks
    }
  }
});

// Send initialize response
process.stdin.on('end', () => {
  process.exit(0);
});

// Ping parent that we're ready
process.stderr.write('wordpress-mcp-server: ready\n');
