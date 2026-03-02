#!/usr/bin/env node

const fs = require('fs');
const { execSync } = require('child_process');
const path = require('path');

// Read the MCP configuration file
const mcpConfigPath = path.join(__dirname, '../.claude/mcp.json');
const mcpConfig = JSON.parse(fs.readFileSync(mcpConfigPath, 'utf8'));

console.log('Adding MCP servers from .claude/mcp.json...\n');

let successCount = 0;
let failCount = 0;
let skippedCount = 0;
const errors = [];

for (const [serverName, config] of Object.entries(mcpConfig.mcpServers)) {
  try {
    console.log(`\n📦 Adding server: ${serverName}`);

    let command;

    // Handle HTTP/URL-based servers
    if (config.url) {
      // Determine transport type - map streamable-http to http
      let transport = config.transport || 'http';
      if (transport === 'streamable-http') {
        transport = 'http';
      }

      command = `claude mcp add --transport ${transport} ${serverName} "${config.url}"`;

      // Add headers if present
      if (config.headers) {
        for (const [key, value] of Object.entries(config.headers)) {
          command += ` -H "${key}: ${value}"`;
        }
      }
    }
    // Handle command-based servers (stdio)
    else if (config.command) {
      // Server name comes first
      command = `claude mcp add ${serverName}`;

      // Add environment variables after the server name
      if (config.env) {
        for (const [key, value] of Object.entries(config.env)) {
          command += ` -e ${key}=${value}`;
        }
      }

      command += ` -- ${config.command}`;

      // Add args after the command
      if (config.args && config.args.length > 0) {
        const argsStr = config.args.join(' ');
        command += ` ${argsStr}`;
      }
    }

    console.log(`  Command: ${command}`);

    // Execute the command and capture output
    try {
      const output = execSync(command, {
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'pipe']
      });
      console.log(output);
      console.log(`  ✅ Successfully added ${serverName}`);
      successCount++;
    } catch (execError) {
      // Check if the server already exists
      const errorOutput = execError.stderr || execError.stdout || execError.message || '';
      if (errorOutput.includes('already exists')) {
        console.log(`  ⏭️  Skipped ${serverName} (already exists)`);
        skippedCount++;
      } else {
        console.error(`  ❌ Failed to add ${serverName}`);
        console.error(`  Error: ${execError.message}`);
        failCount++;
        errors.push({ serverName, error: execError.message });
      }
    }

  } catch (error) {
    console.error(`  ❌ Failed to add ${serverName}`);
    console.error(`  Error: ${error.message}`);
    failCount++;
    errors.push({ serverName, error: error.message });
  }
}

// Summary
console.log('\n' + '='.repeat(60));
console.log('Summary:');
console.log(`  ✅ Successfully added: ${successCount} servers`);
console.log(`  ⏭️  Skipped: ${skippedCount} servers`);
console.log(`  ❌ Failed: ${failCount} servers`);

if (errors.length > 0) {
  console.log('\nErrors:');
  errors.forEach(({ serverName, error }) => {
    console.log(`  - ${serverName}: ${error}`);
  });
}

console.log('\n✨ Done!');
process.exit(failCount > 0 ? 1 : 0);
