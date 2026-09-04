-- SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
-- SPDX-License-Identifier: AGPL-3.0-or-later
--
-- Pandoc filters for the PDF rendering of IMPLEMENTATION_PLAN.md.
-- Build with `make pdf`; see AGENTS.md section 7.

-- 1. Drop the document's own level-1 heading: the title page already carries
--    it, and keeping it would give the PDF two titles.
-- 2. Set the running head from each level-2 heading.  titlesec, which shapes
--    the headings in header.tex, swallows the \sectionmark that LaTeX would
--    otherwise issue, so the running head would stay stuck on "Contents" for
--    the whole document.  Emitting \markboth explicitly is simpler and more
--    predictable than patching \@sect.
local dropped_title = false

local function to_latex(inlines)
  return pandoc.write(pandoc.Pandoc({ pandoc.Plain(inlines) }), "latex")
end

function Header(el)
  if el.level == 1 and not dropped_title then
    dropped_title = true
    return {}
  end
  if el.level == 2 then
    local mark = to_latex(el.content):gsub("%s+$", "")
    return { el, pandoc.RawBlock("latex", "\\markboth{" .. mark .. "}{}") }
  end
  return el
end

-- 3. Give fenced blocks that carry no language a shaded box too.  Pandoc
--    renders those as a bare `verbatim` environment, visually unlike the
--    highlighted ones, and 84 of the plan's 90 fences are unlabelled.
--    Verbatim (fvextra) is used without commandchars, so the body needs no
--    escaping; the only forbidden content is the end marker itself.
function CodeBlock(el)
  if #el.classes > 0 then
    return el
  end
  if el.text:find("\\end{Verbatim}", 1, true) then
    return el
  end
  return pandoc.RawBlock(
    "latex",
    "\\begin{plaincode}%\n\\begin{Verbatim}\n"
      .. el.text
      .. "\n\\end{Verbatim}\n\\end{plaincode}"
  )
end
