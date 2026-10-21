# FilePilot safety model

- Scan operations only read file metadata and (for same-size candidates) file content to calculate SHA-256.
- Symbolic links are skipped during recursive scanning.
- The organizer's preview includes only regular files directly in the selected root directory; it does not move folders or nested files.
- Applying a plan moves files into category folders, choosing a unique destination name if needed. It does not delete files and does not overwrite a conflicting destination.
- Operations are written to a per-user journal folder under local application data.
- Undo never overwrites a file that currently exists at the original source path.
- Reports can include local paths. Review a report before sharing it.
- First-time users should test using `demo_data` before choosing personal folders.

Before applying an organization plan, review the custom confirmation dialog: it shows the exact selected folder, the number of proposed moves, and explains that file paths will change. Cancel with No, Escape, or the window close button if anything looks unexpected.
