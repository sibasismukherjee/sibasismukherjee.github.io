Regenerate the resume PDF (`sibasismukherjee.pdf`) from the current state of `sibasismukherjee-resume.html`, then commit and push the result.

## Steps

1. Run the generation script from the repo root:
   ```
   python scripts/gen_resume_pdf.py
   ```
   The script auto-installs `playwright` and Chromium on first run — no manual setup needed.

2. If the user supplied a specific commit message, pass it:
   ```
   python scripts/gen_resume_pdf.py -m "<message>"
   ```

3. To preview the PDF without committing (e.g. after a content tweak the user wants to review first):
   ```
   python scripts/gen_resume_pdf.py --dry-run
   ```

4. After the script exits, report back:
   - PDF file size
   - Whether a commit was made and which branch was pushed to
   - Any errors from the script output

## When to use this skill

- After any edit to `sibasismukherjee-resume.html` (layout, content, styles)
- After the user asks to "update the PDF", "regenerate the resume", or "sync the PDF"
- After a batch of resume content changes before a job application

## Notes

- The PDF source of truth is `sibasismukherjee-resume.html`, not `index.html`.
  `index.html` is the website resume; the PDF is generated from the dedicated resume HTML.
- The script requires Python 3.9+ and network access on first run (to download Chromium).
- Playwright browser cache is gitignored — it is re-downloaded if the cache is missing.
