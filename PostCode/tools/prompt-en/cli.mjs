import { readFile } from 'node:fs/promises';
import { spawn, spawnSync } from 'node:child_process';
import { optimize } from './engine.mjs';

const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log(`Usage:
  prompt-en "Your request"           Print a concise English version
  prompt-en --file request.txt       Read a UTF-8 text file
  prompt-en --clipboard              Replace copied text with the prepared prompt
  Get-Content -Raw request.txt | prompt-en
  codex-en "Your request"            Prepare the prompt, then start Codex

Uses local Ollama and the installed Prompt Optimizer engine. No cloud model API.
--clipboard does not read or modify this app's input field and never submits a message.`);
  process.exit(0);
}

function clipboard(script, input) {
  const result = spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', `[Console]::InputEncoding = [Text.Encoding]::UTF8; [Console]::OutputEncoding = [Text.Encoding]::UTF8; ${script}`], { input, encoding: 'utf8', windowsHide: true });
  if (result.status !== 0) throw new Error('Clipboard operation failed; original text was kept.');
  return result.stdout;
}

try {
  let source;
  const launchCodex = args[0] === '--codex';
  if (launchCodex) args.shift();
  if (args[0] === '--clipboard') {
    if (launchCodex || args.length !== 1) throw new Error('--clipboard must be used by itself.');
    source = clipboard('Get-Clipboard -Raw');
  } else if (args[0] === '--file') {
    if (args.length !== 2) throw new Error('Usage: --file path-to-UTF8-text');
    source = await readFile(args[1], 'utf8');
  } else if (args.length) {
    if (args[0].startsWith('--')) throw new Error('Unknown option. Run prompt-en --help.');
    source = args.join(' ');
  } else if (!process.stdin.isTTY) {
    const chunks = [];
    for await (const chunk of process.stdin) chunks.push(chunk);
    source = Buffer.concat(chunks).toString('utf8');
  } else {
    throw new Error('Pass a prompt, --file, or --clipboard. Run prompt-en --help.');
  }
  process.stderr.write('Preparing English prompt locally...\n');
  const prepared = await optimize(source);
  if (args[0] === '--clipboard') {
    // Avoid replacing something the user copied while the model was running.
    if (clipboard('Get-Clipboard -Raw') !== source) throw new Error('Clipboard changed during preparation; nothing was overwritten.');
    clipboard('Set-Clipboard -Value ([Console]::In.ReadToEnd())', prepared);
    process.stderr.write('Prepared prompt copied. Paste it into Codex and review before sending.\n');
  } else if (launchCodex) {
    process.stderr.write(`Prepared prompt:\n${prepared}\nStarting Codex in the current folder.\n`);
    const child = spawn('codex.exe', [prepared], { stdio: 'inherit', shell: false });
    child.on('error', error => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
    child.on('exit', code => { process.exitCode = code ?? 1; });
  } else {
    process.stdout.write(`${prepared}\n`);
  }
} catch (error) {
  process.stderr.write(`prompt-en: ${error.message}\n`);
  process.exitCode = 1;
}
