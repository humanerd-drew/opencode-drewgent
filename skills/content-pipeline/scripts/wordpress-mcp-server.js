#!/usr/bin/env node
/**
 * wordpress-mcp-server.js — STDIO MCP server for WordPress via wp-cli
 * 
 * Provides tools: create_post, upload_media, set_featured_image,
 * list_posts, get_post, update_post, create_category, list_categories
 * 
 * Registered in Hermes config.yaml mcp_servers.wordpress
 * 
 * Usage (test): printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | \
 *   node /Users/drew/.drewgent/scripts/wordpress-mcp-server.js
 */
const { execSync } = require('child_process');

const WP_CLI = ['docker', 'exec', 'humanerd-wp', 'wp', '--allow-root'];

function wp(...args) {
  try {
    const result = execSync([...WP_CLI, ...args].join(' '), {
      encoding: 'utf8', timeout: 30000, maxBuffer: 10 * 1024 * 1024,
    });
    return { success: true, stdout: result.trim() };
  } catch (e) {
    return { success: false, error: e.message || e.stderr || String(e) };
  }
}

const tools = {
  create_post: {
    description: 'Create a new WordPress post',
    parameters: { /* title, content, category, tags, status, date, featured_image */ },
    handler: (args) => {
      const cmd = ['post', 'create'];
      cmd.push('--post_title=' + args.title, '--post_content=' + args.content);
      cmd.push('--post_status=' + (args.status || 'publish'));
      if (args.category) cmd.push('--post_category=' + args.category);
      if (args.tags) cmd.push('--tags=' + args.tags);
      if (args.date) cmd.push('--post_date=' + args.date);
      return wp(...cmd);
    },
  },
  upload_media: {
    description: 'Upload a media file to WordPress library',
    parameters: { /* file_path, title */ },
    handler: (args) => wp('media', 'import', args.file_path, '--title=' + (args.title || ''), '--porcelain'),
  },
  list_posts: {
    description: 'List recent WordPress posts',
    handler: (args) => wp('post', 'list', '--posts_per_page=' + (args.posts_per_page || 10), '--format=json'),
  },
  get_post: {
    description: 'Get a WordPress post by ID',
    parameters: { required: ['id'] },
    handler: (args) => wp('post', 'get', String(args.id), '--format=json'),
  },
  set_theme_mod: {
    description: 'Set a WordPress theme modification (value must be JSON-encoded string)',
    parameters: { required: ['key', 'value'] },
    handler: (args) => wp('eval', `set_theme_mod("${args.key}", ${args.value}); echo "OK";`),
  },
};

// STDIO JSON-RPC 2.0 handler
let buffer = '';
process.stdin.on('data', (chunk) => {
  buffer += chunk.toString();
  for (const line of buffer.split('\n').slice(0, -1)) {
    try {
      const req = JSON.parse(line);
      if (req.method === 'tools/list') {
        process.stdout.write(JSON.stringify({
          jsonrpc: '2.0', id: req.id,
          result: Object.entries(tools).map(([n, t]) => ({ name: n, description: t.description, inputSchema: t.parameters })),
        }) + '\n');
      } else if (req.method === 'tools/call') {
        const tool = tools[req.params?.name];
        if (!tool) {
          process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: req.id, error: { code: -32601, message: 'Tool not found' } }) + '\n');
          continue;
        }
        const result = tool.handler(req.params?.arguments || {});
        process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: req.id, result: { content: [{ type: 'text', text: result.success ? result.stdout : 'Error: ' + result.error }] } }) + '\n');
      }
    } catch (e) { /* ignore partial chunks */ }
  }
  buffer = buffer.split('\n').pop();
});
process.stderr.write('wordpress-mcp-server: ready\n');
