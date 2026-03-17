# Contributing

Thanks for your interest in improving AirQ Web GIS.

## Scope
- This repository is a portfolio-focused engineering prototype.
- Contributions that improve clarity, reliability, developer experience, QA/QC transparency, and documentation are welcome.
- Changes that imply certified regulatory use should document assumptions clearly.

## Local Setup
1. Clone the repository.
2. Copy `.env.example` to `.env`.
3. For easiest local review, keep `DATA_SOURCE=synthetic`.
4. Create a virtual environment and install backend dependencies:
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
5. Run tests:
   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q
   ```

## Pull Requests
- Keep PRs focused and easy to review.
- Add or update tests when changing backend behavior.
- Update docs when behavior, setup, or operational expectations change.
- Preserve explicit scientific and compliance boundaries.

## Coding Notes
- Prefer deterministic behavior for demo paths.
- Do not commit secrets, tokens, or private `.env` files.
- Keep public-facing copy clear about prototype vs regulatory-grade boundaries.

## Before Opening a PR
- Run the test suite.
- Verify the local app still starts cleanly.
- Check that README instructions still match the code.
