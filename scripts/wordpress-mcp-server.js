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
const { execSync } = require('child_process');
const fs = require('fs');
const os = require('os');

const WP_CLI = ['docker', 'exec', 'humanerd-wp', 'wp', '--allow-root'];

function shellEscape(s) {
  return "'" + String(s).replace(/'/g, "'\\''") + "'";
}

function wpStdin(stdin, ...args) {
  try {
    const cmd = [...WP_CLI, ...args].map(shellEscape).join(' ');
    const result = execSync(cmd, {
      input: stdin,
      encoding: 'utf8',
      timeout: 30000,
      maxBuffer: 10 * 1024 * 1024,
      shell: true,
    });
    return { success: true, stdout: result.trim() };
  } catch (e) {
    return { success: false, error: e.stderr ? e.stderr.trim() : e.message };
  }
}

function wp(...args) {
  try {
    const cmd = [...WP_CLI, ...args].map(shellEscape).join(' ');
    const result = execSync(cmd, {
      encoding: 'utf8',
      timeout: 30000,
      maxBuffer: 10 * 1024 * 1024,
      shell: true,
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
      // Write content to a temp file on the host and docker cp into container
      const hostFile = '/tmp/wp-content-' + Date.now() + '.html';
      const containerFile = '/tmp/wp-content-' + Date.now() + '.html';
      // Remove YAML frontmatter if present
      let content = args.content;
      content = content.replace(/^---[\s\S]*?---\n*/, '');
      try {
        fs.writeFileSync(hostFile, content, 'utf8');
        execSync(`docker cp "${hostFile}" humanerd-wp:${containerFile}`, { encoding: 'utf8', timeout: 10000 });
        fs.unlinkSync(hostFile);
      } catch (e) {
        return { success: false, error: 'File write error: ' + e.message };
      }
      // Build wp-cli command inside container via docker exec bash -c
      // Use $(cat file) inside the container bash to read the content we docker cp'd
      let pieceParts = [
        `--post_title="${args.title.replace(/"/g, '\\"').replace(/\\$/g, '\\\\$')}"`,
        `--post_status=${args.status || "publish"}`,
      ];
      pieceParts.push(`--post_author=1`);
      if (args.category) pieceParts.push(`--post_category="${args.category}"`);
      if (args.tags) pieceParts.push(`--tags="${args.tags}"`);
      if (args.date) pieceParts.push(`--post_date="${args.date}"`);
      const pieceArgs = pieceParts.join(' ');
      // Use single-quoted bash -c to prevent local shell from expanding $()
      const bashCmd = `/usr/local/bin/wp --allow-root post create --post_content="$(cat ${containerFile})" ${pieceArgs}`;
      try {
        const result = execSync(
          `docker exec humanerd-wp bash -c '${bashCmd.replace(/'/g, "'\\''")}'`,
          { encoding: 'utf8', timeout: 30000, maxBuffer: 10 * 1024 * 1024, shell: true }
        );
        return { success: true, stdout: result.trim() };
      } catch (e) {
        return { success: false, error: e.stderr ? e.stderr.trim() : e.message };
      }
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
  update_post: {
    description: 'Update an existing WordPress post (content, status, title)',
    parameters: {
      type: 'object',
      properties: {
        id: { type: 'number' },
        title: { type: 'string', default: '' },
        content: { type: 'string', default: '' },
        status: { type: 'string', enum: ['publish', 'draft'], default: '' },
      },
      required: ['id'],
    },
    handler: (args) => {
      const cmd = ['post', 'update', String(args.id)];
      if (args.title) cmd.push('--post_title=' + args.title);
      if (args.status) cmd.push('--post_status=' + args.status);
      if (args.content) {
        return wpStdin(args.content, 'post', 'update', String(args.id), '--post_status=' + (args.status || ''), '--post_title=' + (args.title || ''));
      }
      return wp(...cmd);
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

      // MCP initialize
      if (request.method === 'initialize') {
        process.stdout.write(JSON.stringify({
          jsonrpc: '2.0', id: request.id,
          result: {
            protocolVersion: '2024-11-05',
            capabilities: {
              tools: {},
              prompts: {},
              resources: {},
            },
            serverInfo: { name: 'wordpress-mcp-server', version: '1.0.0' },
          },
        }) + '\n');
        continue;
      }

      // MCP notifications/initialized — no response needed
      if (request.method === 'notifications/initialized') {
        continue;
      }

      // MCP tools/list
      if (request.method === 'tools/list') {
        process.stdout.write(JSON.stringify({
          jsonrpc: '2.0', id: request.id,
          result: {
            tools: Object.entries(tools).map(([name, t]) => ({
              name,
              description: t.description,
              inputSchema: t.parameters,
            })),
          },
        }) + '\n');
        continue;
      }

      // MCP tools/call
      if (request.method === 'tools/call') {
        const tool = tools[request.params?.name];
        if (!tool) {
          process.stdout.write(JSON.stringify({
            jsonrpc: '2.0', id: request.id,
            error: { code: -32601, message: `Tool not found: ${request.params?.name}` },
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
