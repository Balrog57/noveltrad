git add -A
git commit -m "feat(pipeline): accept source_paths so one project handles N files

Before: the GUI emitted N separate POST /projects calls (one per
file) and the orchestrator rejected every request after the first
because it only supports one running project at a time. The
rejections surfaced as HTTP 500 and the error popup kept coming
back, locking the user out of the GUI.

After: POST /projects accepts a ``source_paths`` list. The Parser
iterates every file in a single pass and stamps each chunk with
``source_file``. The Assembler (already source-aware via the
``source_file`` column) writes one output per source. The GUI now
sends ONE request with the full file list and treats a multi-file
selection the same way it treats a single file."
git push origin main
git tag v4.1.9 main
git push origin v4.1.9
