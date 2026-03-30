# Changelog

All notable changes to this project will be documented in this file.

## [1.0.4] - 2026-03-30

### Fixed

- Aligned `html_render` screenshot options with the working `astrbot_plugin_picstatus` strategy:
  - use `jpeg`
  - set `quality` to `90`
  - keep `full_page=True`
  - use `device_scale_factor_level="ultra"`
- Removed the previous `timeout=30` screenshot option that could be interpreted by Playwright as a 30ms timeout instead of 30 seconds.

### Changed

- Bumped plugin version metadata to `1.0.4` / `v1.0.4`.

## [1.0.3] - 2026-03-30

### Fixed

- Changed the image rendering flow to follow the `astrbot_plugin_picstatus` pattern more closely:
  - render the final HTML in-plugin first
  - call `html_render(final_html, {}, return_url=True, options=...)`
- Inlined avatar resources before rendering so the T2I backend no longer needs to fetch the QQ avatar URL itself.

### Changed

- Added `jinja2` as a runtime dependency for local HTML template rendering.
- Bumped plugin version metadata to `1.0.3` / `v1.0.3`.

## [1.0.2] - 2026-03-30

### Fixed

- Fixed abnormal line breaks in plain-text output after the GPU and process sections by replacing markdown-like list prefixes with plain Chinese labels.
- Switched the image rendering call to the AstrBot `html_render(template_string, data, options)` style used in the official HTML-to-Image guide to avoid falling back to text mode after `\status image`.

### Changed

- Bumped plugin version metadata to `1.0.2` / `v1.0.2`.

## [1.0.1] - 2026-03-30

### Fixed

- Replaced the image rendering chain with AstrBot `html_render` template-path rendering.
- Fixed text-to-image rendering compatibility issues caused by the previous render path usage.

### Changed

- Localized status output and image-panel labels into Chinese where appropriate.
- Improved CPU name detection so Windows and other platforms prefer product/brand names over generic family/model identifiers.
- Synchronized plugin version metadata to `1.0.1` / `v1.0.1`.

## [1.0.0] - 2026-03-30

### Added

- Initial release of the AstrBot QQ status panel plugin for NapCat / OneBot v11.
- `\status`, `\status image`, `\status text`, and `/status` command support.
- Plain-text status replies with CPU, GPU, RAM, disk, uptime, and active-process information.
- Image status panel rendering with customizable bot nickname and avatar.
- AstrBot WebUI configuration schema for reply mode, avatar, nickname, and process count.
