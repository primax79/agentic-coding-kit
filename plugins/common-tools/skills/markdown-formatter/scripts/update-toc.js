#!/usr/bin/env node
/**
 * update-toc.js — Table-of-Contents generator/updater, a dependency-free port of
 * the "Markdown All in One" VS Code extension (yzhang-gh/vscode-markdown,
 * src/toc.ts + src/util/slugify.ts), GitHub slug mode.
 *
 * Deterministic & safe: it only (re)generates the TOC BETWEEN explicit markers
 *   <!-- toc -->
 *   ...generated list...
 *   <!-- /toc -->
 * If a file has no `<!-- toc -->` marker, it is left untouched. If the opening
 * marker exists without a closing one, the closing marker is inserted. Nothing
 * outside the marker block is ever modified.
 *
 * Ported details kept faithful to the extension:
 *   - GitHub slug: strip inline markdown to plain text, remove every char except
 *     \p{L}\p{M}\p{Nd}\p{Nl}\p{Pc}, hyphen and space, lowercase, spaces->hyphens;
 *   - duplicate anchors get -1, -2, … suffixes, counted over ALL headings in the
 *     document (anchors are global), not just the ones shown in the TOC;
 *   - ATX headings only (`#`..`######`), Setext ignored like a plain CLI run;
 *   - headings inside fenced code blocks are skipped;
 *   - a heading tagged `<!-- omit in toc -->` / `<!-- omit from toc -->` (same
 *     line, or the line immediately above) is excluded;
 *   - link label reduces links to their text and drops images/inline HTML.
 *
 * Options (optional flags, before the file list):
 *   --levels a-b   heading levels to include (default 2-6; e.g. --levels 1-6)
 *   --marker <c>   unordered list marker char, default "-"
 *
 * Usage:  node update-toc.js [--levels 2-6] [--marker -] <file.md> [more.md ...]
 */

'use strict';
const fs = require('fs');

// ---- GitHub slug: keep letters, marks, digits, letter-numbers, connector
// punctuation, hyphen and space; drop everything else. (Verbatim regex.) ----
const GITHUB_PUNCTUATION = /[^\p{L}\p{M}\p{Nd}\p{Nl}\p{Pc}\- ]/gu;

// Reduce inline markdown to the plain text GitHub slugifies (drop images & inline
// HTML entirely; keep the textual content of links, code spans, emphasis).
function stripInlineToPlain(text) {
  return text
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '') // images -> removed
    .replace(/!\[[^\]]*\]\[[^\]]*\]/g, '') // reference images -> removed
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // inline links -> text
    .replace(/\[([^\]]*)\]\[[^\]]*\]/g, '$1') // reference links -> text
    .replace(/<[^>]+>/g, '') // inline HTML -> removed
    .replace(/`([^`]*)`/g, '$1') // code spans -> content
    .replace(/(\*\*|__)(.*?)\1/g, '$2') // strong -> content
    .replace(/(\*|_)(.*?)\1/g, '$2') // emphasis -> content
    .replace(/~~(.*?)~~/g, '$1'); // strikethrough -> content
}

function githubSlug(raw) {
  return stripInlineToPlain(raw)
    .replace(GITHUB_PUNCTUATION, '')
    .toLowerCase()
    .replace(/ /g, '-');
}

// Visible label for the TOC link: reduce links to their text, drop images/HTML,
// keep emphasis/code as-is, and escape brackets so the [label](#slug) stays valid.
function linkLabel(raw) {
  return raw
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]*)\]\[[^\]]*\]/g, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/\[/g, '\\[')
    .replace(/\]/g, '\\]')
    .trim();
}

// Collect ATX headings (level, raw text), skipping code fences, YAML front matter,
// and `omit in toc` headings.
function collectHeadings(lines) {
  const headings = [];
  let fence = null;
  let inFrontMatter = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // YAML front matter only at the very top.
    if (i === 0 && /^---\s*$/.test(line)) {
      inFrontMatter = true;
      continue;
    }
    if (inFrontMatter) {
      if (/^---\s*$/.test(line)) inFrontMatter = false;
      continue;
    }

    const fenceMatch = line.match(/^\s*(`{3,}|~{3,})/);
    if (fence) {
      if (fenceMatch && line.trim().startsWith(fence)) fence = null;
      continue;
    }
    if (fenceMatch) {
      fence = fenceMatch[1][0].repeat(3);
      continue;
    }

    const m = line.match(/^ {0,3}(#{1,6})(?: +| *$)(.*?)\s*#*\s*$/);
    if (!m) continue;

    const level = m[1].length;
    const rawContent = m[2].trim();

    const omitHere = /<!-- omit (in|from) toc -->\s*$/.test(line);
    const omitAbove = i > 0 && /^\s*<!-- omit (in|from) toc -->\s*$/.test(lines[i - 1]);
    const canInToc = !(omitHere || omitAbove);

    headings.push({ level, rawContent: rawContent.replace(/<!-- omit (in|from) toc -->\s*$/, '').trim(), canInToc });
  }
  return headings;
}

// Assign global (GitHub-style) slugs with -1/-2 duplicate suffixes over ALL headings.
function assignSlugs(headings) {
  const seen = new Map();
  for (const h of headings) {
    let slug = githubSlug(h.rawContent);
    const count = seen.get(slug);
    if (count === undefined) {
      seen.set(slug, 0);
    } else {
      const next = count + 1;
      seen.set(slug, next);
      slug = slug + '-' + next;
    }
    h.slug = slug;
  }
}

function buildToc(headings, startDepth, endDepth, marker) {
  const shown = headings.filter((h) => h.canInToc && h.level >= startDepth && h.level <= endDepth);
  if (shown.length === 0) return '';
  const baseDepth = Math.max(startDepth, Math.min(...shown.map((h) => h.level)));
  return shown
    .map((h) => {
      const indent = '  '.repeat(Math.max(0, h.level - baseDepth));
      return `${indent}${marker} [${linkLabel(h.rawContent)}](#${h.slug})`;
    })
    .join('\n');
}

const OPEN_RE = /^<!--\s*toc\s*-->\s*$/i;
const CLOSE_RE = /^<!--\s*(\/toc|tocstop)\s*-->\s*$/i;

function updateDocument(text, startDepth, endDepth, marker) {
  const newline = text.includes('\r\n') ? '\r\n' : '\n';
  const lines = text.split(/\r?\n/);

  const openIdx = lines.findIndex((l) => OPEN_RE.test(l));
  if (openIdx === -1) return { text, changed: false, hadMarker: false };

  // Headings/slugs are computed over the whole document (minus the TOC block).
  const headings = collectHeadings(lines);
  assignSlugs(headings);
  const toc = buildToc(headings, startDepth, endDepth, marker);

  let closeIdx = -1;
  for (let i = openIdx + 1; i < lines.length; i++) {
    if (CLOSE_RE.test(lines[i])) {
      closeIdx = i;
      break;
    }
  }

  const before = lines.slice(0, openIdx + 1);
  const after = closeIdx === -1 ? lines.slice(openIdx + 1) : lines.slice(closeIdx + 1);
  const block = toc ? ['', toc, ''] : [''];
  const rebuilt = [...before, ...block, '<!-- /toc -->', ...after].join(newline);
  return { text: rebuilt, changed: rebuilt !== text, hadMarker: true };
}

function main() {
  const argv = process.argv.slice(2);
  let startDepth = 2;
  let endDepth = 6;
  let marker = '-';
  const files = [];
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--levels') {
      const m = (argv[++i] || '').match(/^(\d)\s*-\s*(\d)$/);
      if (m) {
        startDepth = parseInt(m[1], 10);
        endDepth = parseInt(m[2], 10);
      }
    } else if (argv[i] === '--marker') {
      marker = argv[++i] || '-';
    } else {
      files.push(argv[i]);
    }
  }
  if (files.length === 0) {
    console.error('usage: node update-toc.js [--levels 2-6] [--marker -] <file.md> [more.md ...]');
    process.exit(2);
  }

  let changed = 0;
  let noMarker = 0;
  for (const file of files) {
    const before = fs.readFileSync(file, 'utf8');
    const res = updateDocument(before, startDepth, endDepth, marker);
    if (!res.hadMarker) {
      noMarker++;
      continue;
    }
    if (res.changed) {
      fs.writeFileSync(file, res.text);
      changed++;
    }
  }
  console.error(
    `update-toc: processed ${files.length} file(s), rewrote ${changed}` +
      (noMarker ? `, skipped ${noMarker} without a <!-- toc --> marker` : '') +
      '.'
  );
}

main();
