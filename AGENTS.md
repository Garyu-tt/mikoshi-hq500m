# Repository agent instructions

## Permanent README hero (required)

The top of `README.md` is intentionally pinned for humans opening this repository.

- The first line must remain `# Mikoshi HQ500M — CPU Playground`.
- Immediately below that title, keep the complete section bounded by
  `<!-- HQ500M_README_HERO_START -->` and `<!-- HQ500M_README_HERO_END -->`.
- Preserve the clickable Deep Ruby atlas image, the public interactive 3D viewer link,
  the full-size image link, the viewer-source link and geometry/source credits.
- Do not insert release notes, version announcements, navigation, badges, or other
  sections above the hero. Append new release notes and technical updates below it.
- When updating the visual or viewer, update the links **inside** this pinned block
  without moving it. Preserve provenance and the distinction between synthetic
  HQ500M neural addresses and measured biological connectomes.
- The GitHub Actions `readme-hero` workflow verifies the layout on pushes and PRs.
  A red layout check is not permission to remove or bypass the hero.

This instruction applies to every human and automated README edit.
