# Vendored browser libraries

These pinned distributions make the localhost interface work offline and avoid
a runtime Node.js or CDN dependency.

- Marked 18.0.10 (`marked-18.0.10.umd.js`), MIT license.
- DOMPurify 3.4.14 (`dompurify-3.4.14.min.js`), Apache-2.0 license.
- KaTeX 0.18.4 (`katex-0.18.4.min.js` and
  `katex-auto-render-0.18.4.min.js`), MIT license.

The corresponding upstream license texts are stored alongside the files.
KaTeX is configured for MathML output, so its webfont bundle is not shipped.
