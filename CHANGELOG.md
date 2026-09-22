# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## [0.3.0](https://github.com/pawamoy/devboard/releases/tag/0.3.0) - 2026-09-23

<small>[Compare with 0.2.0](https://github.com/pawamoy/devboard/compare/0.2.0...0.3.0)</small>

### Features

- Render Rich content in modals ([fb2393e](https://github.com/pawamoy/devboard/commit/fb2393e75edc21b71e4684b82394f4516785499c) by Timothée Mazzucotelli).
- Let columns report status bar progress ([08a6943](https://github.com/pawamoy/devboard/commit/08a6943c6ab66bde2699c116e22a1ab025c11f7a) by Timothée Mazzucotelli).
- Add maximize/unmaximize keybinding to all columns ([8fd99d4](https://github.com/pawamoy/devboard/commit/8fd99d48d715189c5679cb97edb07806964738d5) by Timothée Mazzucotelli). [Issue-2](https://github.com/pawamoy/devboard/issues/2)
- Allow collapsing/expanding column with keybinding ([51160e1](https://github.com/pawamoy/devboard/commit/51160e152a9bcbcc3a77ede5ee2878252b7a6946) by Timothée Mazzucotelli).
- Add progress bar (scanning/fetching) ([34290ea](https://github.com/pawamoy/devboard/commit/34290ea4b1bfb04ac9560b47d5fbd0244034e5a6) by Timothée Mazzucotelli).

### Bug Fixes

- Update cache after each (batch) row operation ([25b1370](https://github.com/pawamoy/devboard/commit/25b13703240c94107146d1de2fcff7a20f16d6c3) by Timothée Mazzucotelli).
- Emptied columns are collapsed ([6e49906](https://github.com/pawamoy/devboard/commit/6e49906ba1dcdb3cedc04d92909c838c4b9e1627) by Timothée Mazzucotelli).
- Always encode in UTF8 ([fe0f17f](https://github.com/pawamoy/devboard/commit/fe0f17f8016b55c8edff96dbcba2d12975987511) by Timothée Mazzucotelli).
- Support restoring cache with moved columns ([a014e82](https://github.com/pawamoy/devboard/commit/a014e82f49b4d3f3d47a0f5bf4d5edda1eacb5b0) by Timothée Mazzucotelli).
- Identify projects by their paths, to avoid redundant work ([2708a80](https://github.com/pawamoy/devboard/commit/2708a80282ef5a37b9a1b62efa081542bd1ef39f) by Timothée Mazzucotelli).
- Save to cache after each reload ([091a229](https://github.com/pawamoy/devboard/commit/091a2296ac968ba92ef562b50eb4b67db4165114) by Timothée Mazzucotelli).

### Code Refactoring

- Let each board declare its own bindings ([cf7a6a9](https://github.com/pawamoy/devboard/commit/cf7a6a928a6fb50bc50d4caa5d010117305e8eae) by Timothée Mazzucotelli).
- Declare keybindings with Textual actions ([5b1ec54](https://github.com/pawamoy/devboard/commit/5b1ec548daf2fc3c5db6171f35a1c680fa91b429) by Timothée Mazzucotelli).
- Generalize refresh/force-refresh ([342ef55](https://github.com/pawamoy/devboard/commit/342ef552ccbf3e151750ef44800fe68d0f6f8e20) by Timothée Mazzucotelli).
- Make columns generic ([6532042](https://github.com/pawamoy/devboard/commit/6532042da615c7f9c54ffa1cd9f713db552c77c3) by Timothée Mazzucotelli).
- Restructure app to separate concerns ([c11b897](https://github.com/pawamoy/devboard/commit/c11b897a3a5e45aad0e78b9c7a6749e0bbed7e91) by Timothée Mazzucotelli).

## [0.2.0](https://github.com/pawamoy/devboard/releases/tag/0.2.0) - 2026-09-10

<small>[Compare with 0.1.0](https://github.com/pawamoy/devboard/compare/0.1.0...0.2.0)</small>

The project is update to support latest version of Textual.

### Bug Fixes

- Prevent event propagation from modal ([e61eadd](https://github.com/pawamoy/devboard/commit/e61eaddaca58f91c02150c2f11465fcb82d576d1) by Timothée Mazzucotelli).
- Fix script entrypoint ([acb054d](https://github.com/pawamoy/devboard/commit/acb054d11395861c34a60e2a60711379a3b48019) by Timothée Mazzucotelli).

### Performance Improvements

- Start faster (cache), scan faster ([9a740e5](https://github.com/pawamoy/devboard/commit/9a740e55aff8add3016b438d1b0912376a5552aa) by Timothée Mazzucotelli).

## [0.1.0](https://github.com/pawamoy/devboard/releases/tag/0.1.0) - 2025-11-08

<small>[Compare with first commit](https://github.com/pawamoy/devboard/compare/286120e957168a9162d5a8dc19c7dd72fb0a6d65...0.1.0)</small>

### Features

- Release Insiders project to the public ([ce7aad4](https://github.com/pawamoy/devboard/commit/ce7aad4c6c2da3924aebcf143f3a0d1068573297) by Timothée Mazzucotelli).

### Code Refactoring

- Update imports ([976e578](https://github.com/pawamoy/devboard/commit/976e57897d92431c60f510efbe6d8be5516747cd) by Timothée Mazzucotelli).
- Move submodules under internal folder ([9ec90e1](https://github.com/pawamoy/devboard/commit/9ec90e11392d86022213e7dc4cfcfd520fa7783c) by Timothée Mazzucotelli).
