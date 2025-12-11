#!/usr/bin/env python3
"""Manual test script for dashboard service integration"""

from services.dashboard_service import DashboardService

service = DashboardService()
all_ops = service.get_opportunities(limit=10)

print(f"\nTop 10 Opportunities (All Categories):")
print("=" * 80)
for i, op in enumerate(all_ops, 1):
    category_icon = {
        'production': '🏭',
        'trade': '💰',
        'war_demand': '⚔️'
    }
    icon = category_icon.get(op['category'], '❓')
    print(f"{i}. {icon} {op['name']}")
    print(f"   Category: {op['category']}")
    print(f"   Profit: {op['profit']:,.0f} ISK")
    print(f"   ROI: {op.get('roi', 0):.1f}%")
    print()
