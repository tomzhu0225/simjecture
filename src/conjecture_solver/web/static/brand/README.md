# Simjecture brand assets

The shared mark is an S-shaped simulation trace with a separate sample point.
These are the approved logo kit's original SVG/ICO exports, without redesign.
Both application headers reference this directory rather than building their own
mark in HTML or CSS. Do not duplicate the paths in individual pages.

- `simjecture-lockup-light.svg`: violet `#6658D9` mark, `#202332` wordmark
- `simjecture-lockup-dark.svg`: pale violet `#B5A7FF` mark, `#F4F4FC` wordmark
- `favicon.svg` / `favicon.ico`: white optical-size mark on a violet tile

The sidebar is always dark, so it always uses the dark lockup. The monitor selects
its lockup from the existing `data-theme` state. Keep the aspect ratio and built-in
clear space. Header lockups use 180 px where space permits; 140 px or more is
preferred. Existing user-resized narrow sidebars scale the artwork down to fit
rather than overflowing. Page names remain live text.
Header images are decorative inside explicitly named home links. Favicon aliases
at `/favicon.svg` and `/favicon.ico` serve these same files with explicit MIME
types; the server does not expose the entire directory.

## Source and licensing

The SVG paths are editable vector sources, with the approved wordmark already
outlined. No webfonts, external assets, scripts, or runtime rendering dependencies
are required. The favicon uses a slightly heavier, wider-gap optical mark for
small browser-tab sizes. Its ICO contains 16, 32, and 48 px representations.

The wordmark was outlined from Open Sans Semibold, with tightened spacing. See
`OPEN-SANS-NOTICE.txt` and `APACHE-2.0.txt` for attribution and the full license.
No font binaries are distributed. The custom mark and application code are
covered by the repository's Apache 2.0 license. That license does not grant
trademark rights.

A bounded public visual similarity screen found no exact duplicate. S-and-dot
marks are established motifs; Stability AI's purple S with a baseline dot and
Segment's historic segmented S-and-dot are somewhat related. This screen is not
trademark clearance or a claim of uniqueness.
