"""Step 9 of the pipeline: review analysis (Stage 6.1 to 6.4) and supplementary analyses (Stage 7).

Kept as a root script so the documented command `python stats_analysis.py` keeps working. The work
is in app/review/report.py.
"""
import sys

from app.review.report import main

if __name__ == "__main__":
    sys.exit(main())
