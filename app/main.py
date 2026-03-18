"""
app/main.py

Top-level entry point. Delegates to the pipeline CLI.
"""

from app.pipeline.run_filing_pipeline import main

if __name__ == "__main__":
    main()
