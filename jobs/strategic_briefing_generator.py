#!/usr/bin/env python3
"""
Strategic Briefing Generator
Runs every 6 hours to pre-generate the strategic intelligence briefing.
This prevents slow page loads by ensuring the briefing is always cached.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm_analysis_service import generate_strategic_briefing
from datetime import datetime


def main():
    print(f"[{datetime.utcnow().isoformat()}] Starting strategic briefing generation...")

    try:
        result = generate_strategic_briefing()

        if result.get("error"):
            print(f"[ERROR] Briefing generated with error: {result['error']}")
        else:
            print(f"[SUCCESS] Strategic briefing generated successfully")
            print(f"  - Highlights: {len(result.get('highlights', []))}")
            print(f"  - Alerts: {len(result.get('alerts', []))}")
            if result.get('power_assessment'):
                pa = result['power_assessment']
                print(f"  - Gaining power: {len(pa.get('gaining_power', []))}")
                print(f"  - Losing power: {len(pa.get('losing_power', []))}")
                print(f"  - Contested: {len(pa.get('contested', []))}")

    except Exception as e:
        print(f"[FATAL] Strategic briefing generation failed: {e}")
        sys.exit(1)

    print(f"[{datetime.utcnow().isoformat()}] Strategic briefing generation complete")


if __name__ == "__main__":
    main()
