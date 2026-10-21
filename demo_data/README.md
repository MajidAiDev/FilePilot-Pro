# Safe demo dataset

This folder contains synthetic, non-personal sample files for trying FilePilot.

- `meeting_notes.txt` and `meeting_notes_copy.txt` are identical so duplicate detection should find one group.
- `sample_script.py`, `project.json`, and `brief.md` demonstrate different file categories.
- `nested/nested_example.txt` demonstrates recursive scanning. The organizer only proposes moves for files directly within the selected root folder.

Use this folder for your first scan. You may safely run the organizer preview and examine the proposed moves. Applying moves will move these sample files into category folders, and the Undo action can restore a recent FilePilot organization operation.
