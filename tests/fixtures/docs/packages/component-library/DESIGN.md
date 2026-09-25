# Offline stand-in for ts-grc packages/component-library/DESIGN.md
**Always import MUI components and icons from `@workiva/unify`, not from `@mui/material` or `@mui/icons-material` directly.**
**Sections and surfaces do NOT get borders.**
**Default to Bucket A.** Wrapper proliferation is expensive: it creates a second API surface to learn and maintain.
