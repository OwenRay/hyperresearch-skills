#!/usr/bin/env python3
"""Convert a hyperresearch final report markdown to a clean, styled, self-contained HTML.

Handles the subset of markdown used in hyperresearch reports:
- # / ## / ### headings
- **bold** and *italic* inline
- [[note-id]] wikilinks (rendered as muted [source] chips)
- pipe tables
- bulleted / numbered lists
- horizontal rules (---)
- blockquotes (>) if present

There is no pandoc and no python-markdown on the default Hermes box, so this
hand-rolled converter is the reliable path. Run:
    python3 report_to_html.py <input.md> <output.html>
"""
import re, sys, html

DEFAULT_SRC = "$HOME/research/notes/final_report_plugplay-cost-resolved-f56d7c.md"
DEFAULT_OUT = "$HOME/research/notes/final_report_plugplay-cost-resolved-f56d7c.html"

def inline(text):
    text = html.escape(text)
    # [[note-id]] wikilinks -> muted citation chip
    text = re.sub(r'\[\[([a-zA-Z0-9_-]+)\]\]', r'<span class="cite">[source]</span>', text)
    # **bold**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # *italic*
    text = re.sub(r'\*(?!\*)(.+?)\*', r'<em>\1</em>', text)
    # inline `code`
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text

def convert(src, out):
    with open(src, encoding="utf-8") as f:
        lines = f.read().split("\n")
    out_lines = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if i == 0 and s == "---":  # skip YAML frontmatter
            i += 1
            while i < n and lines[i].strip() != "---":
                i += 1
            i += 1
            continue
        if s in ("---", "***", "___"):
            out_lines.append('<hr>'); i += 1; continue
        m = re.match(r'^(#{1,3})\s+(.*)$', s)
        if m:
            lvl = len(m.group(1)); out_lines.append(f'<h{lvl}>{inline(m.group(2))}</h{lvl}>'); i += 1; continue
        if s.startswith("|") and i + 1 < n and re.match(r'^\|[\s:|-]+\|$', lines[i+1].strip()):
            hdr = [inline(c.strip()) for c in s.strip("|").split("|")]; i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([inline(c.strip()) for c in lines[i].strip().strip("|").split("|")]); i += 1
            t = ['<div class="table-wrap"><table><thead><tr>']
            t += [f'<th>{c}</th>' for c in hdr]; t.append('</tr></thead><tbody>')
            for r in rows:
                t.append('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>')
            t.append('</tbody></table></div>')
            out_lines.append("".join(t)); continue
        if s.startswith(">"):
            q = []
            while i < n and lines[i].strip().startswith(">"):
                q.append(inline(lines[i].strip().lstrip(">").strip())); i += 1
            out_lines.append(f'<blockquote>{" ".join(q)}</blockquote>'); continue
        if re.match(r'^[-*]\s+', s):
            items = []
            while i < n and re.match(r'^[-*]\s+', lines[i].strip()):
                items.append(f'<li>{inline(re.sub(r"^[-*]\s+", "", lines[i].strip()))}</li>'); i += 1
            out_lines.append(f'<ul>{"".join(items)}</ul>'); continue
        if re.match(r'^\d+[.)]\s+', s):
            items = []
            while i < n and re.match(r'^\d+[.)]\s+', lines[i].strip()):
                items.append(f'<li>{inline(re.sub(r"^\d+[.)]\s+", "", lines[i].strip()))}</li>'); i += 1
            out_lines.append(f'<ol>{"".join(items)}</ol>'); continue
        if not s:
            out_lines.append(""); i += 1; continue
        para = [inline(s)]; i += 1
        while i < n and lines[i].strip() and not lines[i].startswith(("#", "|", "-", "*", ">", "1.")) \
              and not re.match(r'^\d+[.)]\s+', lines[i].strip()) and lines[i].strip() != "---":
            para.append(inline(lines[i].strip())); i += 1
        out_lines.append(f'<p>{" ".join(para)}</p>')
    body = "\n".join(out_lines)

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Research Report</title>
<style>
  :root {{ --bg:#0f1115; --card:#171a21; --fg:#e6e8ee; --muted:#9aa3b2; --accent:#4f8cff; --accent2:#7aa2ff; --line:#2a2f3a; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:880px; margin:0 auto; padding:56px 28px 96px; }}
  h1 {{ font-size:2.1rem; line-height:1.2; margin:0 0 8px; background:linear-gradient(120deg,#fff,var(--accent2)); -webkit-background-clip:text; background-clip:text; color:transparent; }}
  .subtitle {{ color:var(--muted); margin:0 0 40px; }}
  h2 {{ font-size:1.45rem; margin:48px 0 14px; padding-bottom:8px; border-bottom:1px solid var(--line); color:#fff; }}
  h3 {{ font-size:1.15rem; margin:28px 0 10px; color:var(--accent2); }}
  p {{ margin:14px 0; }}
  strong {{ color:#fff; }}
  .cite {{ display:inline-block; font-size:.68rem; color:var(--muted); background:var(--line); border:1px solid var(--line); border-radius:4px; padding:1px 6px; margin:0 2px; vertical-align:1px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
  .table-wrap {{ overflow-x:auto; margin:20px 0; border-radius:10px; border:1px solid var(--line); }}
  table {{ border-collapse:collapse; width:100%; font-size:.92rem; }}
  th {{ background:var(--card); color:#fff; text-align:left; padding:11px 14px; border-bottom:1px solid var(--line); }}
  td {{ padding:11px 14px; border-bottom:1px solid var(--line); vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  ul, ol {{ margin:14px 0; padding-left:26px; }}
  li {{ margin:6px 0; }}
  blockquote {{ margin:18px 0; padding:14px 20px; border-left:3px solid var(--accent); background:var(--card); border-radius:0 8px 8px 0; color:var(--muted); }}
  code {{ background:var(--card); border:1px solid var(--line); border-radius:4px; padding:1px 5px; font-size:.86em; }}
  hr {{ border:none; border-top:1px solid var(--line); margin:28px 0; }}
  @media (max-width:600px) {{ .wrap {{ padding:32px 18px 72px; }} h1 {{ font-size:1.6rem; }} }}
</style>
</head>
<body>
<div class="wrap">
{body}
</div>
</body>
</html>"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"Wrote {out} ({len(html_doc)} bytes)")

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT
    convert(src, out)
