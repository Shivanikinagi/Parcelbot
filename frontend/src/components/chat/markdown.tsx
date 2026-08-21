import * as React from "react";

/**
 * Minimal, dependency-free Markdown renderer for the subset the agent emits:
 * headings, bullets, blockquotes, bold/italic/code inline, links, and [S#]
 * citation markers (rendered as subtle chips). Kept tiny on purpose — the agent
 * controls the output format, so a full CommonMark parser would be overkill.
 */
function renderInline(text: string, keyBase: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  // Order matters: process code, bold, italic, citation markers, links.
  const regex = /(`[^`]+`)|(\*\*[^*]+\*\*)|(_[^_]+_)|(\[S\d+\])|(\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = regex.exec(text))) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    const tok = m[0];
    const key = `${keyBase}-${i++}`;
    if (tok.startsWith("`")) nodes.push(<code key={key}>{tok.slice(1, -1)}</code>);
    else if (tok.startsWith("**")) nodes.push(<strong key={key}>{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith("_")) nodes.push(<em key={key}>{tok.slice(1, -1)}</em>);
    else if (/^\[S\d+\]$/.test(tok))
      nodes.push(
        <span key={key} className="mx-0.5 inline-flex items-center rounded bg-primary/10 px-1 text-[11px] font-medium text-primary">
          {tok.slice(1, -1)}
        </span>,
      );
    else {
      const lm = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(tok);
      if (lm) nodes.push(<a key={key} href={lm[2]} target="_blank" rel="noreferrer">{lm[1]}</a>);
    }
    last = m.index + tok.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

export function Markdown({ content }: { content: string }) {
  const blocks = content.split(/\n{2,}/);
  return (
    <div className="prose-chat text-sm">
      {blocks.map((block, bi) => {
        const lines = block.split("\n");
        if (lines.every((l) => l.trim().startsWith("- "))) {
          return (
            <ul key={bi}>
              {lines.map((l, li) => (
                <li key={li}>{renderInline(l.replace(/^\s*-\s/, ""), `${bi}-${li}`)}</li>
              ))}
            </ul>
          );
        }
        if (block.startsWith("> ")) {
          return <blockquote key={bi}>{renderInline(block.replace(/^>\s?/gm, ""), `${bi}`)}</blockquote>;
        }
        const h = /^(#{1,3})\s+(.*)$/.exec(block);
        if (h) {
          const Tag = (["h1", "h2", "h3"][h[1].length - 1] ?? "h3") as any;
          return <Tag key={bi}>{renderInline(h[2], `${bi}`)}</Tag>;
        }
        return <p key={bi}>{renderInline(block, `${bi}`)}</p>;
      })}
    </div>
  );
}
