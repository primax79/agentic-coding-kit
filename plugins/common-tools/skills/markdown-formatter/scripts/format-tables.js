#!/usr/bin/env node
/**
 * format-tables.js — GFM table formatter, a faithful, dependency-free port of the
 * table-formatting algorithm in the "Markdown All in One" VS Code extension
 * (yzhang-gh/vscode-markdown, src/tableFormatter.ts).
 *
 * Why this exists: `markdownlint --fix` formats everything EXCEPT tables. This
 * script owns table formatting so the pair reproduces the user's two-plugin
 * editor workflow (markdownlint + Markdown All in One) from the command line.
 *
 * It edits ONLY table blocks; every other line is left byte-for-byte untouched,
 * and fenced code blocks (``` / ~~~) are skipped so pipes inside code are never
 * mistaken for tables.
 *
 * Ported details kept identical to the original:
 *   - display width = grapheme count + number of double-width chars
 *     (regex: \p{Extended_Pictographic} | CJK/full-width ranges), so CJK/emoji
 *     columns align the same way the extension aligns them;
 *   - cell split regex ((\\\||[^|])*)\| — honours escaped pipes \|;
 *   - alignment parsed from the delimiter row (:--- left, :---: center, ---:
 *     right, --- none) with the same minimum delimiter widths (3/4/4/5);
 *   - padded delimiter style (the extension's default delimiterRowNoPadding=false).
 *
 * Usage:  node format-tables.js <file.md> [more.md ...]
 *   Rewrites each file in place. Exit 0 on success.
 */

'use strict';
const fs = require('fs');

const segmenter = new Intl.Segmenter('en', { granularity: 'grapheme' });
const graphemes = (s) => Array.from(segmenter.segment(s), (x) => x.segment);
const countGraphemes = (s) => graphemes(s).length;

// Chars rendered two cells wide (emoji + CJK / full-width ranges), matching the
// original doubleWidthRegex.
const doubleWidthRegex =
  /\p{Extended_Pictographic}|[　-鿿가-힯！-｠]/gu;
const countDoubleWidth = (s) => (s.match(doubleWidthRegex) || []).length;

const Align = { None: 0, Left: 1, Center: 2, Right: 3 };

// A delimiter row: optional leading/trailing pipes around one-or-more cells that
// are each `:?-+:?` (with surrounding spaces). Must contain at least one dash.
const DELIMITER_RE =
  /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/;

function isDelimiterRow(line) {
  return line.includes('-') && DELIMITER_RE.test(line);
}

// Split one table row into trimmed cell strings, honouring escaped pipes.
function splitRow(row) {
  row = row.trim();
  if (row.startsWith('|')) row = row.slice(1);
  if (!row.endsWith('|')) row = row + '|';
  const fieldRe = /((\\\||[^|])*)\|/gu;
  const cells = [];
  for (const m of row.matchAll(fieldRe)) cells.push(m[1].trim());
  return cells;
}

function alignText(text, align, length) {
  if (align === Align.Center && length > text.length) {
    return (' '.repeat(Math.floor((length - text.length) / 2)) + text + ' '.repeat(length)).slice(
      0,
      length
    );
  } else if (align === Align.Right) {
    return (' '.repeat(length) + text).slice(-length);
  }
  return (text + ' '.repeat(length)).slice(0, length);
}

// Format a table given its raw block lines (header, delimiter, body...).
// `indentation` is the leading whitespace of the block, preserved on every line.
function formatTable(blockLines, indentation) {
  const delimiterRowIndex = 1;
  const rowsCells = blockLines.map((l) => splitRow(l));

  const colWidth = [];
  const colAlign = [];

  rowsCells.forEach((cells, iRow) => {
    if (iRow === delimiterRowIndex) return;
    cells.forEach((cell, iCol) => {
      const width = countGraphemes(cell) + countDoubleWidth(cell);
      colWidth[iCol] = Math.max(colWidth[iCol] || 0, width);
    });
  });

  // Parse alignment + set minimum delimiter widths, then rebuild delimiter cells.
  rowsCells[delimiterRowIndex] = rowsCells[delimiterRowIndex].map((cell, iCol) => {
    if (/:-+:/.test(cell)) {
      colAlign[iCol] = Align.Center;
      colWidth[iCol] = Math.max(colWidth[iCol] || 0, 5);
      return ':' + '-'.repeat(colWidth[iCol] - 2) + ':';
    } else if (/:-+/.test(cell)) {
      colAlign[iCol] = Align.Left;
      colWidth[iCol] = Math.max(colWidth[iCol] || 0, 4);
      return ':' + '-'.repeat(colWidth[iCol] - 1);
    } else if (/-+:/.test(cell)) {
      colAlign[iCol] = Align.Right;
      colWidth[iCol] = Math.max(colWidth[iCol] || 0, 4);
      return '-'.repeat(colWidth[iCol] - 1) + ':';
    }
    colAlign[iCol] = Align.None;
    colWidth[iCol] = Math.max(colWidth[iCol] || 0, 3);
    return '-'.repeat(colWidth[iCol]);
  });

  return rowsCells
    .map((cells, iRow) => {
      if (iRow === delimiterRowIndex) {
        return indentation + '| ' + cells.join(' | ') + ' |';
      }
      const out = colWidth.map((visualWidth, iCol) => {
        const cell = cells[iCol] || '';
        // JS-string length that corresponds to `visualWidth` display cells,
        // discounting double-width chars — mirrors the original padding math.
        let jsLength = graphemes(cell + ' '.repeat(visualWidth)).slice(0, visualWidth).join('').length;
        jsLength -= countDoubleWidth(cell);
        return alignText(cell, colAlign[iCol] || Align.None, jsLength);
      });
      return indentation + '| ' + out.join(' | ') + ' |';
    })
    .join('\n');
}

// Walk the document, format every GFM table block, leave everything else intact.
function formatDocument(text) {
  const newline = text.includes('\r\n') ? '\r\n' : '\n';
  const lines = text.split(/\r?\n/);
  const out = [];
  let fence = null; // active code-fence marker (``` or ~~~) or null

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const fenceMatch = line.match(/^(\s*)(`{3,}|~{3,})/);
    if (fence) {
      out.push(line);
      if (fenceMatch && line.trim().startsWith(fence)) fence = null;
      continue;
    }
    if (fenceMatch) {
      fence = fenceMatch[2][0].repeat(3); // normalise to ``` or ~~~
      out.push(line);
      continue;
    }

    // Table start: this line and the next both look like a table, next is delimiter.
    const next = lines[i + 1];
    if (
      line.includes('|') &&
      next !== undefined &&
      isDelimiterRow(next) &&
      line.trim() !== ''
    ) {
      const indentation = (line.match(/^\s*/) || [''])[0];
      const block = [line, next];
      let j = i + 2;
      while (j < lines.length && lines[j].includes('|') && lines[j].trim() !== '' && !lines[j].match(/^(\s*)(`{3,}|~{3,})/)) {
        block.push(lines[j]);
        j++;
      }
      out.push(formatTable(block, indentation));
      i = j - 1;
      continue;
    }

    out.push(line);
  }

  return out.join(newline);
}

function main() {
  const files = process.argv.slice(2);
  if (files.length === 0) {
    console.error('usage: node format-tables.js <file.md> [more.md ...]');
    process.exit(2);
  }
  let changed = 0;
  for (const file of files) {
    const before = fs.readFileSync(file, 'utf8');
    const after = formatDocument(before);
    if (after !== before) {
      fs.writeFileSync(file, after);
      changed++;
    }
  }
  console.error(`format-tables: processed ${files.length} file(s), rewrote ${changed}.`);
}

main();
