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

function dockerBash(cmd) {
  const escaped = shellEscape(cmd);
  const fullCmd = `docker exec humanerd-wp bash -c ${escaped}`;
  try {
    const result = execSync(fullCmd, { encoding: 'utf8', timeout: 30000, maxBuffer: 10 * 1024 * 1024, shell: true });
    return { success: true, stdout: result.trim() };
  } catch (e) {
    return { success: false, error: e.message || e.stderr || String(e) };
  }
}

// Simple JSON-RPC 2.0 handler via STDIO
function copyToContainer(hostPath, containerPath) {
  execSync(`docker cp "${hostPath}" humanerd-wp:${containerPath}`, { encoding: 'utf8', timeout: 10000 });
}

const tools = {
  create_post: {
    description: 'Create a new WordPress post',
    parameters: {
      type: 'object',
      properties: {
        title: { type: 'string' },
        content: { type: 'string' },
        category: { type: 'string', default: '' },
        slug: { type: 'string', default: '', description: 'English kebab-case slug. Auto-generated from title if empty.' },
        author: { type: 'number', default: 1, description: 'IGNORED — always forced to 1 (humanerd). Only 1 user exists.' },
        status: { type: 'string', enum: ['publish', 'draft'], default: 'publish' },
        date: { type: 'string', default: '' },
        featured_image: { type: 'string', default: '', description: 'Host path to image file to set as featured image.' },
      },
      required: ['title', 'content'],
    },
    handler: (args) => {
      let content = (args.content || '').replace(/^---[\s\S]*?---\n*/, '').trim();
      if (content.length < 50) {
        return { success: false, error: 'Content too short (' + content.length + ' chars); minimum 50. Empty posts not allowed.' };
      }
      const ts = Date.now();
      const hostFile = '/tmp/wp-content-' + ts + '.html';
      const containerFile = '/tmp/wp-content-' + ts + '.html';
      try {
        fs.writeFileSync(hostFile, content, 'utf8');
        copyToContainer(hostFile, containerFile);
        fs.unlinkSync(hostFile);
      } catch (e) {
        return { success: false, error: 'File write error: ' + e.message };
      }
      const esc = (s) => String(s).replace(/"/g, '\\"');
      let innerCmd = `wp post create --post_title="${esc(args.title)}" --post_content="$(cat ${containerFile})" --post_status="${args.status || 'publish'}" --post_author=1`;
      if (args.category) innerCmd += ` --post_category="${esc(args.category)}"`;
      if (args.slug) innerCmd += ` --post_name=${esc(args.slug)}`;
      if (args.date) innerCmd += ` --post_date="${esc(args.date)}"`;
      innerCmd += ' --allow-root';
      const result = dockerBash(innerCmd);
      if (!result.success) return { success: false, error: result.error };
      // Extract post ID from output: "Success: Created post 306."
      const match = result.stdout.match(/Created post (\d+)/);
      const postId = match ? parseInt(match[1]) : null;
      // If featured_image provided, upload and set
      if (args.featured_image && postId) {
        const hostImg = args.featured_image;
        const ext = hostImg.split('.').pop() || 'bin';
        const containerImg = '/tmp/wp-featured-' + Date.now() + '.' + ext;
        try {
          copyToContainer(hostImg, containerImg);
          const uploadResult = wp('media', 'import', containerImg, '--porcelain');
          if (uploadResult.success) {
            const attachId = uploadResult.stdout.trim();
            if (attachId && /^\d+$/.test(attachId)) {
              wp('post', 'meta', 'update', String(postId), '_thumbnail_id', attachId);
            }
          }
        } catch (e) { /* non-fatal: featured image upload failed */ }
      }
      return { success: true, stdout: result.stdout };
    },
  },
  upload_media: {
    description: 'Upload a media file to WordPress. Copies host file into container first.',
    parameters: {
      type: 'object',
      properties: {
        file_path: { type: 'string', description: 'Absolute path to file on the HOST machine' },
        title: { type: 'string', default: '' },
      },
      required: ['file_path'],
    },
    handler: (args) => {
      try {
        const ts = Date.now();
        const ext = args.file_path.split('.').pop() || 'bin';
        const containerPath = '/tmp/wp-media-' + ts + '.' + ext;
        copyToContainer(args.file_path, containerPath);
        return wp('media', 'import', containerPath, '--title=' + shellEscape(args.title || ''), '--porcelain');
      } catch (e) {
        return { success: false, error: e.message };
      }
    },
  },
  set_featured_image: {
    description: 'Upload an image from host and set it as the featured image for a post.',
    parameters: {
      type: 'object',
      properties: {
        post_id: { type: 'number' },
        image_path: { type: 'string', description: 'Absolute path to image file on the HOST machine' },
      },
      required: ['post_id', 'image_path'],
    },
    handler: (args) => {
      try {
        const ext = args.image_path.split('.').pop() || 'bin';
        const containerPath = '/tmp/wp-featured-' + Date.now() + '.' + ext;
        copyToContainer(args.image_path, containerPath);
        const uploadResult = wp('media', 'import', containerPath, '--porcelain');
        if (!uploadResult.success) return { success: false, error: uploadResult.error };
        const attachId = uploadResult.stdout.trim();
        return wp('post', 'meta', 'update', String(args.post_id), '_thumbnail_id', attachId);
      } catch (e) {
        return { success: false, error: e.message };
      }
    },
  },
  update_post: {
    description: 'Update an existing WordPress post',
    parameters: {
      type: 'object',
      properties: {
        id: { type: 'number' },
        title: { type: 'string', default: '' },
        content: { type: 'string', default: '' },
        slug: { type: 'string', default: '' },
        status: { type: 'string', enum: ['publish', 'draft'], default: '' },
        category: { type: 'string', default: '' },
        date: { type: 'string', default: '' },
      },
      required: ['id'],
    },
    handler: (args) => {
      const wpArgs = ['post', 'update', String(args.id)];
      if (args.title) wpArgs.push('--post_title=' + args.title);
      if (args.status) wpArgs.push('--post_status=' + args.status);
      if (args.slug) wpArgs.push('--post_name=' + args.slug);
      if (args.category) wpArgs.push('--post_category=' + args.category);
      if (args.date) wpArgs.push('--post_date=' + args.date);
      if (args.content) {
        return wpStdin(args.content, ...wpArgs.slice(1));
      }
      return wp(...wpArgs);
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
  list_categories: {
    description: 'List all categories',
    parameters: {
      type: 'object',
      properties: {},
    },
    handler: () => {
      return wp('term', 'list', 'category', '--fields=term_id,name,slug,count', '--format=json');
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
      const tool = tools[request.params?.name || request.method];
      
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
