# EVE Co-Pilot AI - User Guide

**Version:** 2.0.0
**Date:** 2025-12-22

Complete guide for using the EVE Co-Pilot AI gaming assistant powered by Claude.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Features Overview](#features-overview)
4. [Using the Chat Interface](#using-the-chat-interface)
5. [Voice Commands](#voice-commands)
6. [Available Commands](#available-commands)
7. [Market Analysis](#market-analysis)
8. [Production Planning](#production-planning)
9. [War Room Intelligence](#war-room-intelligence)
10. [Shopping Lists](#shopping-lists)
11. [Tips & Best Practices](#tips--best-practices)
12. [Troubleshooting](#troubleshooting)

---

## Introduction

EVE Co-Pilot AI is an intelligent assistant for EVE Online that combines:

- **115 specialized tools** for market analysis, production, combat intelligence
- **Claude Sonnet 4.5** LLM for natural language understanding
- **Real-time chat** with WebSocket communication
- **Voice input** for hands-free operation
- **Comprehensive EVE data** from SDE and ESI APIs

### What Can It Do?

**Market & Trading:**
- Find arbitrage opportunities across regions
- Compare prices at trade hubs
- Analyze market trends and volume

**Production & Manufacturing:**
- Calculate production costs and profits
- Optimize material sourcing
- Plan complete production chains

**Combat Intelligence:**
- Track ship losses by region
- Identify combat hotspots
- Analyze doctrine compositions
- Monitor sovereignty campaigns

**Shopping & Logistics:**
- Create optimized shopping lists
- Plan multi-region shopping routes
- Calculate cargo requirements

---

## Getting Started

### 1. Access the Application

Open your web browser and navigate to:
```
http://localhost:5173
```

Or for remote access:
```
http://your-server-ip:5173
```

### 2. First Time Setup

**Character Authentication** (Coming Soon):
- Currently operates in guest mode
- Full EVE SSO integration planned for character-specific features

**Select Your Region:**
1. Click the **Region** dropdown in the left sidebar
2. Choose your primary trading region:
   - **Jita** (The Forge) - Largest market
   - **Amarr** (Domain) - Second largest
   - **Dodixie** (Sinq Laison) - Gallente hub
   - **Rens** (Heimatar) - Minmatar hub
   - **Hek** (Metropolis) - Alternative Minmatar hub

### 3. Start Chatting

Type your question in the input box and press **Enter** or click **Send**.

**Example questions:**
```
What's the current price of Tritanium in Jita?
Calculate the profit for building a Raven battleship
Show me the top combat hotspots
Is Hobgoblin I profitable to manufacture?
Find me arbitrage opportunities for PLEX
```

---

## Features Overview

### Real-Time Chat

- **Streaming responses** - See the AI's answer as it types
- **Tool visualization** - Expandable details of what tools were used
- **Message history** - Scrollable conversation log
- **Context awareness** - AI remembers previous messages

### Voice Input

- **Click the microphone** button to start recording
- **Click again** to stop and transcribe
- **Automatic population** of input field with transcribed text
- **Press Send** to submit your voice command

### Context Panel

**Region Selection:**
- Choose primary region for price lookups
- Affects default market data source

**Quick Tips:**
- Market analysis examples
- Production queries
- War room commands
- Shopping list help

---

## Using the Chat Interface

### Basic Interaction

```
User: How much does Tritanium cost?
AI: Let me check the current market price for Tritanium in Jita...

[Used 2 tools: search_item, get_market_stats]

Current Tritanium prices in Jita (The Forge):
- Lowest Sell: 7.50 ISK
- Highest Buy: 7.45 ISK
- Daily Volume: 1.2B units
```

### Understanding Tool Calls

When the AI uses tools, you'll see:

```
🔧 Used 3 tool(s)

▼ View Details
  • search_item: "Hobgoblin I"
    → Found type_id: 2454

  • get_production_cost: type_id=2454
    → Materials: 125,000 ISK
    → Time: 30 minutes

  • get_market_stats: type_id=2454, region=10000002
    → Sell: 180,000 ISK
    → Profit: 55,000 ISK (30.6%)
```

### Multi-Step Queries

The AI can perform complex multi-step analysis:

```
User: Compare Raven production costs across all trade hubs
      and find the most profitable location

AI: I'll analyze Raven battleship production across
    5 major trade hubs...

[Used 15 tools across multiple iterations]

Analysis Complete:

Jita (The Forge):
- Material Cost: 285M ISK
- Sell Price: 320M ISK
- Profit: 35M ISK (12.3%)

Amarr (Domain):
- Material Cost: 290M ISK
- Sell Price: 318M ISK
- Profit: 28M ISK (9.7%)

...

Recommendation: Build in Jita for highest profit margin
```

---

## Voice Commands

### Activating Voice Input

1. **Click the microphone icon** (or press `Alt + V`)
2. **Speak your command** clearly
3. **Click the microphone again** to stop
4. **Review transcription** in input field
5. **Press Enter** to submit

### Voice Command Examples

**Market Queries:**
```
"What is the price of PLEX in Jita?"
"Find me arbitrage opportunities for Ishtar"
"Compare Tritanium prices across all hubs"
```

**Production:**
```
"Calculate profit for building Drake battlecruiser"
"Show me the materials needed for Hobgoblin two"
"What's the most profitable tech one frigate?"
```

**War Room:**
```
"What are the current combat hotspots?"
"Show me ship losses in Delve region"
"Are there any sovereignty timers today?"
```

### Tips for Voice Input

- **Speak clearly** and at normal pace
- **Use full item names** ("Hobgoblin One", not "Hob")
- **Spell out numbers** ("one thousand" vs "1000")
- **Pause between commands** if asking multiple questions

---

## Available Commands

### Market Analysis

#### Price Lookup
```
What's the price of [item] in [region]?
Current market price for [item]
Show me [item] prices
```

#### Arbitrage
```
Find arbitrage opportunities for [item]
Show me the best arbitrage trades
Compare [item] prices across all hubs
Where can I buy [item] cheapest?
```

#### Market Stats
```
What's the trading volume for [item]?
Show me market statistics for [item]
Is [item] actively traded?
```

### Production Planning

#### Cost Calculation
```
Calculate production cost for [item]
What materials do I need to build [item]?
How much does it cost to manufacture [item]?
```

#### Profit Analysis
```
Is [item] profitable to build?
Calculate profit margin for [item]
What's the ROI for manufacturing [item]?
```

#### Material Sourcing
```
Where should I buy materials for [item]?
Cheapest region for [material]
Optimize material purchasing for [item]
```

#### Production Chains
```
Show me the complete production chain for [item]
What are all the components needed for [item]?
Break down [item] into raw materials
```

### War Room Intelligence

#### Combat Activity
```
Show me combat hotspots
What are the most dangerous systems?
Where is PvP activity highest?
```

#### Ship Losses
```
What ships are being destroyed in [region]?
Show me losses for [ship type]
Most destroyed ship this week
```

#### Demand Analysis
```
What items are in demand in [region]?
Show me market gaps in [region]
War supplies needed in [region]
```

#### Sovereignty
```
Are there any sovereignty timers?
Show me contested systems
What's happening in [region] sov-wise?
```

#### Faction Warfare
```
Show me FW hotspots
What systems are vulnerable?
FW activity in [region]
```

### Shopping Lists

#### Creation
```
Create a shopping list for [item] production
I need to buy materials for [quantity] [item]
Make a shopping list for [blueprint runs] runs
```

#### Optimization
```
Where should I buy items on my list?
Optimize my shopping route
What's the total cost across all regions?
```

#### Logistics
```
How much cargo space do I need?
What ship can carry my shopping list?
Calculate trips needed for [ship type]
```

### Routes & Navigation

```
Calculate route from [system] to [system]
How many jumps to [hub] from [system]?
Find nearest trade hub to [system]
```

### Item Information

```
Tell me about [item]
What is [item] used for?
Show me stats for [item]
```

---

## Market Analysis

### Finding Arbitrage Opportunities

**Basic Arbitrage:**
```
User: Find arbitrage opportunities for PLEX

AI: Analyzing PLEX across 5 trade hubs...

Best Arbitrage Opportunities:

1. Dodixie → Jita
   - Buy: 3,250,000 ISK
   - Sell: 3,320,000 ISK
   - Profit: 70,000 ISK/unit (2.15%)
   - Distance: 23 jumps

2. Rens → Jita
   - Buy: 3,265,000 ISK
   - Sell: 3,320,000 ISK
   - Profit: 55,000 ISK/unit (1.68%)
   - Distance: 15 jumps

Recommendation: Rens → Jita offers best ISK/jump ratio
```

**Enhanced Arbitrage with Routing:**
```
User: Show me arbitrage with routing details for Ishtar

AI: [Provides arbitrage + jump route + danger scores]
```

### Multi-Region Comparison

```
User: Compare Tritanium prices across all hubs

AI: Tritanium Price Comparison:

Jita:     7.50 ISK (lowest)
Amarr:    7.68 ISK (+2.4%)
Dodixie:  7.85 ISK (+4.7%)
Rens:     7.92 ISK (+5.6%)
Hek:      8.10 ISK (+8.0%) (highest)

Best Buy Location: Jita
Best Sell Location: Hek
Arbitrage Margin: 0.60 ISK/unit (8.0%)
```

### Market Trend Analysis

```
User: What's the market volume for PLEX?

AI: PLEX Market Statistics (Jita):

Daily Volume: 45,000 units
Total Value: 149.4B ISK

Buy Orders: 12,500 units
Sell Orders: 32,800 units

Market Depth: Healthy
Liquidity: Excellent
```

---

## Production Planning

### Simple Profit Check

```
User: Is Hobgoblin I profitable?

AI: Let me analyze Hobgoblin I production...

Material Cost: 125,000 ISK
  - Tritanium: 35,000 ISK
  - Pyerite: 22,000 ISK
  - Mexallon: 45,000 ISK
  - ...

Sell Price: 180,000 ISK
Profit: 55,000 ISK per unit
ROI: 44.0%
Build Time: 30 minutes

Verdict: ✅ PROFITABLE
```

### Complete Production Chain

```
User: Show me the full production chain for Raven

AI: Raven Battleship Production Chain:

Tier 1 (Raw Materials):
├─ Tritanium: 5.2M units
├─ Pyerite: 2.1M units
├─ Mexallon: 650K units
├─ Isogen: 280K units
└─ Nocxium: 85K units

Tier 2 (Components):
├─ Capital Ship Construction Parts
│   ├─ Tritanium Bar (T1 materials)
│   └─ Pyerite Sheets (T1 materials)
├─ Electronic Systems
│   └─ Capital Electronics (T1 + minerals)
└─ Propulsion Systems

Tier 3 (Final Assembly):
└─ Raven (All T2 components + Nocxium)

Total Material Cost: 285M ISK
Estimated Build Time: 4 hours 30 minutes
```

### Regional Production Optimization

```
User: Where should I build Drake for maximum profit?

AI: Drake Production Analysis (5 Regions):

┌─────────┬──────────┬──────────┬─────────┬──────┐
│ Region  │ Materials│ Sell     │ Profit  │ ROI  │
├─────────┼──────────┼──────────┼─────────┼──────┤
│ Jita    │ 42.5M    │ 48.2M    │ 5.7M    │13.4% │
│ Amarr   │ 43.1M    │ 47.8M    │ 4.7M    │10.9% │
│ Dodixie │ 44.0M    │ 48.5M    │ 4.5M    │10.2% │
│ Rens    │ 43.8M    │ 47.2M    │ 3.4M    │ 7.8% │
│ Hek     │ 45.2M    │ 48.0M    │ 2.8M    │ 6.2% │
└─────────┴──────────┴──────────┴─────────┴──────┘

Recommendation: Build in Jita
- Cheapest materials: ✓
- Best sell price: ✓
- Highest ROI: ✓
```

---

## War Room Intelligence

### Combat Hotspots

```
User: Show me current combat hotspots

AI: Combat Hotspots (Last 24 Hours):

🔥 Critical Activity (100+ kills):
1. Delve (10000060)
   - 347 ships destroyed
   - Total Value: 142B ISK
   - Danger Level: CRITICAL

2. Pure Blind (10000023)
   - 186 ships destroyed
   - Total Value: 68B ISK
   - Danger Level: HIGH

🌡️ Moderate Activity (50-100 kills):
3. Syndicate (10000041) - 78 kills
4. Fountain (10000045) - 62 kills

Safe Regions:
- The Forge: 12 kills (trade hub, highsec)
- Domain: 8 kills (trade hub, highsec)
```

### Ship Loss Analysis

```
User: What ships are being destroyed in Delve?

AI: Ship Losses - Delve Region (Last 7 Days):

Top 10 Destroyed Ships:

1. Sabre (Interdictor)
   - 145 destroyed
   - Avg Value: 65M ISK each
   - Total: 9.4B ISK

2. Muninn (Heavy Assault Cruiser)
   - 98 destroyed
   - Avg Value: 280M ISK each
   - Total: 27.4B ISK

3. Eagle (Heavy Assault Cruiser)
   - 87 destroyed
   - Avg Value: 310M ISK each
   - Total: 27.0B ISK

Doctrine Detection:
- Primary: Muninn/Eagle HAC fleet
- Support: Sabre interdictors
- Estimated Fleet Size: 80-120 pilots
```

### Demand Analysis & Market Gaps

```
User: What's in demand in Delve for war supplies?

AI: War Demand Analysis - Delve:

🎯 High Demand Items (Market Gap):

1. Sabre (Interdictor)
   - Weekly Losses: 145 units
   - Available on Market: 12 units
   - Gap: 133 units (91.7%)
   - Opportunity: ⭐⭐⭐⭐⭐

2. 200mm AutoCannon II
   - Weekly Losses: 1,240 units
   - Available: 450 units
   - Gap: 790 units (63.7%)
   - Opportunity: ⭐⭐⭐⭐

3. Adaptive Invulnerability Field II
   - Weekly Losses: 890 units
   - Available: 180 units
   - Gap: 710 units (79.8%)
   - Opportunity: ⭐⭐⭐⭐⭐

Recommendation: Stock Sabres and faction modules
Expected ROI: 15-25% premium during active campaigns
```

### Sovereignty Campaigns

```
User: Any sov timers today?

AI: Active Sovereignty Campaigns:

⚔️ CONTESTED SYSTEMS:

1. 1DQ1-A (Delve)
   - Attacker: Pandemic Legion
   - Defender: Goonswarm Federation
   - Timer: 2025-12-22 18:30 UTC (6h 15m)
   - Type: Infrastructure Hub

2. M2-XFE (Delve)
   - Attacker: Test Alliance Please Ignore
   - Defender: Goonswarm Federation
   - Timer: 2025-12-22 20:00 UTC (7h 45m)
   - Type: Territorial Claim Unit

No timers expiring in next 2 hours.
```

---

## Shopping Lists

### Creating a Shopping List

```
User: Create a shopping list for building 10 Hobgoblin I

AI: Creating shopping list for 10x Hobgoblin I...

Shopping List Created:

Materials Needed:
- Tritanium: 350,000 units
- Pyerite: 220,000 units
- Mexallon: 450,000 units
- Isogen: 180,000 units

Total Estimated Cost: 1,250,000 ISK

Would you like me to:
1. Compare prices across regions
2. Calculate cargo requirements
3. Plan shopping route
```

### Regional Shopping Comparison

```
User: Compare prices for my shopping list

AI: Regional Price Comparison:

┌──────────┬────────────┬─────────┬──────────┐
│ Region   │ Materials  │ Markup  │ Jumps    │
├──────────┼────────────┼─────────┼──────────┤
│ Jita     │ 1.25M ISK  │ Base    │ 0 (hub)  │
│ Amarr    │ 1.28M ISK  │ +2.4%   │ 23       │
│ Dodixie  │ 1.31M ISK  │ +4.8%   │ 19       │
│ Rens     │ 1.33M ISK  │ +6.4%   │ 15       │
│ Hek      │ 1.38M ISK  │ +10.4%  │ 18       │
└──────────┴────────────┴─────────┴──────────┘

Recommendation: Buy all materials in Jita
Savings vs Hek: 130,000 ISK (10.4%)
```

### Cargo Calculation

```
User: How much cargo space do I need?

AI: Cargo Requirements:

Total Volume: 14,500 m³

Suitable Ships:
1. Bestower (Industrial)
   - Capacity: 19,850 m³
   - Trips: 1
   - Status: ✅ Recommended

2. Badger (Industrial)
   - Capacity: 15,000 m³
   - Trips: 1
   - Status: ✅ Works (tight fit)

3. Tayra (Industrial)
   - Capacity: 12,000 m³
   - Trips: 2
   - Status: ⚠️ Multiple trips needed

Recommendation: Use Bestower for single-trip hauling
```

### Shopping Route Planning

```
User: Plan my shopping route for this list

AI: Optimized Shopping Route:

Start: Jita (The Forge)
├─ Item 1-5: Available in Jita (0 jumps)
├─ Item 6-8: Cheaper in Amarr (+23 jumps)
│   └─ Savings: 850K ISK
└─ Item 9-12: Best price in Rens (+15 jumps from Amarr)
    └─ Savings: 420K ISK

Total Route:
- Jita → Amarr → Rens → [Return to base]
- Total Jumps: 53
- Total Savings: 1.27M ISK
- Time Estimate: ~30 minutes

Would you like waypoints for autopilot?
```

---

## Tips & Best Practices

### Market Analysis

**✅ DO:**
- Check prices before large purchases
- Compare multiple regions for arbitrage
- Consider volume and liquidity
- Factor in hauling costs and time

**❌ DON'T:**
- Trust stale data (always ask for current prices)
- Ignore market volume (low volume = price manipulation risk)
- Forget about taxes and fees
- Overlook hauling danger in lowsec/nullsec

### Production Planning

**✅ DO:**
- Calculate full material costs including components
- Check production chains for nested items
- Consider material efficiency (ME) and time efficiency (TE)
- Factor in build time for opportunity cost

**❌ DON'T:**
- Use buy-order prices for profit calculation (use sell prices)
- Ignore skill requirements
- Forget about blueprint costs
- Assume prices stay constant during production

### War Room Intelligence

**✅ DO:**
- Check combat hotspots before traveling
- Monitor sov timers if operating in nullsec
- Use demand analysis for market opportunities
- Track doctrines to predict ship demand

**❌ DON'T:**
- Ignore danger scores on routes
- Assume highsec is always safe
- Neglect to check FW zones
- Overlook station access in hostile territory

### Shopping Lists

**✅ DO:**
- Create lists for complex production runs
- Use regional comparison for bulk purchases
- Calculate cargo before shopping trips
- Plan routes to minimize jumps

**❌ DON'T:**
- Buy everything in one region without comparing
- Forget to check cargo capacity
- Ignore trip optimization
- Skip safety checks on routes

---

## Troubleshooting

### Chat Issues

**Problem: Messages not sending**
- **Check:** Connection status (top right corner)
- **Fix:** Refresh page, check internet connection

**Problem: Slow responses**
- **Cause:** Complex queries may take 10-30 seconds
- **Fix:** Wait for tool execution to complete

**Problem: Incorrect data**
- **Check:** Verify region selection
- **Fix:** Ask AI to confirm data source and timestamp

### Voice Input Issues

**Problem: Microphone not working**
- **Check:** Browser permissions (allow microphone access)
- **Fix:** Check browser settings → Permissions → Microphone

**Problem: Poor transcription accuracy**
- **Fix:** Speak clearly, reduce background noise
- **Fix:** Use text input for complex item names

**Problem: Transcription fails**
- **Check:** OpenAI API key configuration
- **Fix:** Contact administrator

### Data Issues

**Problem: "Item not found"**
- **Cause:** Typo or exact name mismatch
- **Fix:** Try alternative name, check spelling
- **Fix:** Ask "Search for items like [name]"

**Problem: No market data**
- **Cause:** Item may not be tradeable or ESI API issue
- **Fix:** Verify item is marketable
- **Fix:** Try again in a few minutes

**Problem: Outdated prices**
- **Cause:** Cache not refreshed
- **Fix:** Ask "Get fresh market data for [item]"

### General Issues

**Problem: Page won't load**
- **Check:** Backend services running (http://localhost:8000/docs)
- **Fix:** Restart Docker containers

**Problem: Features not working**
- **Check:** All services healthy (`docker compose ps`)
- **Fix:** Check logs (`docker compose logs`)

---

## Advanced Features

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Alt + V` | Toggle voice input |
| `Ctrl + L` | Clear chat (coming soon) |
| `Ctrl + /` | Show shortcuts help |

### Export & Integration

**Coming Soon:**
- Export shopping lists to EVE format
- Import fitting data
- Character skill integration
- Corporation wallet analysis

---

## Getting Help

### In-App Help

Ask the AI:
```
What can you help me with?
Show me example commands
How do I use the shopping list feature?
```

### Documentation

- **Deployment Guide:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Technical Docs:** [ARCHITECTURE.md](../ARCHITECTURE.md)
- **Developer Guide:** [CLAUDE.md](../CLAUDE.md)

### Support

- **GitHub Issues:** https://github.com/CytrexSGR/Eve-Online-Copilot/issues
- **Contact:** Cytrex in EVE Online

---

## Appendix

### Supported Regions

| Region Name | Region ID | Hub System |
|-------------|-----------|------------|
| The Forge | 10000002 | Jita |
| Domain | 10000043 | Amarr |
| Sinq Laison | 10000032 | Dodixie |
| Heimatar | 10000030 | Rens |
| Metropolis | 10000042 | Hek |

### Common Item Categories

**Ships:**
- Frigates, Destroyers, Cruisers, Battlecruisers, Battleships
- Haulers, Mining Barges, Exhumers
- Capitals, Super Capitals

**Modules:**
- Weapons, Armor, Shields
- Electronics, Engineering
- Drones, Fighters

**Materials:**
- Minerals (Tritanium, Pyerite, etc.)
- Salvage, Planetary Materials
- Moon Materials, Ice Products

### API Rate Limits

The AI Copilot respects ESI API rate limits:
- **150 requests per second** (burst)
- **3000 requests per minute** (sustained)

If you encounter rate limiting, wait 60 seconds before retrying.

---

**Last Updated:** 2025-12-22
**Version:** 2.0.0

---

**Welcome to EVE Co-Pilot AI!** 🚀

*Fly safe, and may your profits be ever in your favor.* o7
