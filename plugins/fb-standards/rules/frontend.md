# Frontend — templates, HTMX, Tailwind/DaisyUI

Server-rendered Django templates; no SPA, no separate API.

- HTMX request (`HX-Request` header) → render a partial, otherwise the full page.
- Partials live next to their page templates (e.g. `templates/<app>/partials/_<name>.html`); one fragment,
  one template.
- Set `hx-target` / `hx-swap` explicitly; use `HX-Trigger` for events and `HX-Redirect` after a successful POST.
- CSRF: send the token with every HTMX request (e.g. `hx-headers` on `<body>`).
- Never `|safe` / `mark_safe` user content.
- DaisyUI components first, Tailwind utilities when no component fits, custom CSS only with a reason.
- CSS is built ahead of time; Tailwind's content globs cover all templates.
- Forms have labels; keep focus states and contrast intact.

## Visual quality (what `qa` checks in the browser)
- The base template has `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- Layout holds at mobile 390×844 and desktop 1440×900: no horizontal scroll, overlap, clipping or cut-off text.
- Nothing renders unstyled (raw HTML = Tailwind build/content-glob problem); one consistent DaisyUI theme.
- Empty, loading (`hx-indicator`), validation-error and success states are designed, not blank.
- HTMX swaps land in the right place without layout jumps; focus is visible; contrast meets WCAG AA.
