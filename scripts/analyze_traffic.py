#!/usr/bin/env python3
"""
EVE Intelligence Traffic Analyzer
Analyzes nginx access logs for eve.infinimind-creations.com
"""

import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import gzip

# Nginx log pattern
LOG_PATTERN = re.compile(
    r'(?P<ip>[\d\.]+) - - \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\w+) (?P<path>[^\s]+) HTTP/[\d\.]+" '
    r'(?P<status>\d+) (?P<size>\d+) '
    r'"(?P<referrer>[^"]*)" "(?P<user_agent>[^"]*)"'
)

class TrafficAnalyzer:
    def __init__(self, log_file: str = "/var/log/nginx/access.log"):
        self.log_file = log_file
        self.entries: List[Dict] = []

    def parse_logs(self, days: int = 7) -> None:
        """Parse nginx access logs"""
        print(f"📊 Analyzing nginx logs: {self.log_file}")

        # Parse current log
        self._parse_file(self.log_file)

        # Parse rotated logs (gzipped)
        for i in range(1, days + 1):
            rotated = f"{self.log_file}.{i}.gz"
            if Path(rotated).exists():
                self._parse_file(rotated, gzipped=True)

        print(f"✅ Parsed {len(self.entries)} log entries\n")

    def _parse_file(self, filepath: str, gzipped: bool = False) -> None:
        """Parse a single log file"""
        try:
            if gzipped:
                with gzip.open(filepath, 'rt') as f:
                    self._parse_lines(f)
            else:
                with open(filepath, 'r') as f:
                    self._parse_lines(f)
        except FileNotFoundError:
            pass
        except PermissionError:
            print(f"⚠️  Permission denied: {filepath}")
            print("   Run with: sudo python3 analyze_traffic.py")
            sys.exit(1)

    def _parse_lines(self, file_obj) -> None:
        """Parse lines from file object"""
        for line in file_obj:
            # Only parse eve.infinimind-creations.com requests
            if 'eve.infinimind-creations.com' not in line:
                continue

            match = LOG_PATTERN.match(line)
            if match:
                self.entries.append(match.groupdict())

    def get_unique_visitors(self) -> int:
        """Count unique IP addresses"""
        return len(set(entry['ip'] for entry in self.entries))

    def get_top_pages(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most visited pages"""
        pages = Counter(entry['path'] for entry in self.entries)
        return pages.most_common(limit)

    def get_top_ips(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top visitor IPs"""
        ips = Counter(entry['ip'] for entry in self.entries)
        return ips.most_common(limit)

    def get_browsers(self) -> Dict[str, int]:
        """Extract browser statistics from user agents"""
        browsers = Counter()

        for entry in self.entries:
            ua = entry['user_agent']

            if 'Edg/' in ua:
                browsers['Edge'] += 1
            elif 'Chrome/' in ua and 'Edg/' not in ua:
                browsers['Chrome'] += 1
            elif 'Firefox/' in ua:
                browsers['Firefox'] += 1
            elif 'Safari/' in ua and 'Chrome' not in ua:
                browsers['Safari'] += 1
            elif 'bot' in ua.lower() or 'crawler' in ua.lower():
                browsers['Bots'] += 1
            else:
                browsers['Other'] += 1

        return dict(browsers.most_common())

    def get_status_codes(self) -> Dict[str, int]:
        """Get HTTP status code distribution"""
        codes = Counter(entry['status'] for entry in self.entries)
        return dict(sorted(codes.items()))

    def get_traffic_by_hour(self) -> Dict[int, int]:
        """Get traffic distribution by hour"""
        hours = defaultdict(int)

        for entry in self.entries:
            try:
                # Parse: 07/Jan/2026:08:02:47 +0000
                time_str = entry['time'].split()[0]
                dt = datetime.strptime(time_str, '%d/%b/%Y:%H:%M:%S')
                hours[dt.hour] += 1
            except:
                continue

        return dict(sorted(hours.items()))

    def get_referrers(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get top referrers (excluding self-referrals)"""
        referrers = Counter()

        for entry in self.entries:
            ref = entry['referrer']
            if ref and ref != '-' and 'eve.infinimind-creations.com' not in ref:
                referrers[ref] += 1

        return referrers.most_common(limit)

    def print_report(self) -> None:
        """Print comprehensive traffic report"""
        print("=" * 70)
        print("EVE INTELLIGENCE TRAFFIC REPORT")
        print("=" * 70)
        print()

        # Overview
        print("📈 OVERVIEW")
        print("-" * 70)
        print(f"Total Requests:        {len(self.entries):,}")
        print(f"Unique Visitors:       {self.get_unique_visitors():,}")
        print()

        # Top Pages
        print("📄 TOP PAGES")
        print("-" * 70)
        for path, count in self.get_top_pages(10):
            print(f"{count:>6}x  {path}")
        print()

        # Top Visitors
        print("👥 TOP VISITORS")
        print("-" * 70)
        for ip, count in self.get_top_ips(10):
            print(f"{count:>6}x  {ip}")
        print()

        # Browsers
        print("🌐 BROWSERS")
        print("-" * 70)
        browsers = self.get_browsers()
        total = sum(browsers.values())
        for browser, count in browsers.items():
            pct = (count / total * 100) if total > 0 else 0
            print(f"{count:>6}x  {browser:<15} ({pct:>5.1f}%)")
        print()

        # Status Codes
        print("📊 HTTP STATUS CODES")
        print("-" * 70)
        for code, count in self.get_status_codes().items():
            status_name = {
                '200': 'OK',
                '301': 'Moved Permanently',
                '302': 'Found',
                '304': 'Not Modified',
                '400': 'Bad Request',
                '404': 'Not Found',
                '500': 'Internal Server Error',
                '502': 'Bad Gateway',
                '503': 'Service Unavailable'
            }.get(code, '')
            print(f"{count:>6}x  {code} {status_name}")
        print()

        # Traffic by Hour
        print("⏰ TRAFFIC BY HOUR (UTC)")
        print("-" * 70)
        traffic = self.get_traffic_by_hour()
        if traffic:
            max_count = max(traffic.values())
            for hour in range(24):
                count = traffic.get(hour, 0)
                bar_length = int((count / max_count * 40)) if max_count > 0 else 0
                bar = '█' * bar_length
                print(f"{hour:>2}:00  {count:>5}x  {bar}")
        print()

        # Referrers
        referrers = self.get_referrers(5)
        if referrers:
            print("🔗 TOP REFERRERS (External)")
            print("-" * 70)
            for ref, count in referrers:
                print(f"{count:>6}x  {ref}")
            print()

        print("=" * 70)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Analyze nginx access logs for eve.infinimind-creations.com'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to analyze (default: 7)'
    )
    parser.add_argument(
        '--log-file',
        default='/var/log/nginx/access.log',
        help='Path to nginx access log (default: /var/log/nginx/access.log)'
    )

    args = parser.parse_args()

    analyzer = TrafficAnalyzer(args.log_file)
    analyzer.parse_logs(days=args.days)
    analyzer.print_report()


if __name__ == '__main__':
    main()
