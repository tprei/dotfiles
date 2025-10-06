# Dynamic Pattern Discovery Enhancement — 2025-10-06T14:05:00Z

## What changed
- Enhanced `.codex/scripts/codex_pattern_updater.py` to support truly dynamic theme discovery beyond static pattern categories
- Modified both Codex and Claude LLM discovery functions with new prompts that prioritize novel insights
- Added novelty scoring and filtering to avoid low-value pattern additions
- Implemented dynamic mode that can discover themes completely unrelated to existing static patterns

## Key Features Added

### 1. Dynamic Discovery Mode
- **New flag**: `ENABLE_DYNAMIC_DISCOVERY = True` enables discovery of truly novel themes
- **Enhanced LLM prompts**: Now ask for "NOVEL themes" that aren't covered by existing patterns
- **Novelty scoring**: LLM can return a `novelty_score` (1-10) to rank pattern originality
- **Filtering**: Patterns with novelty score < 3 are automatically filtered out in dynamic mode

### 2. Updated Prompt Structure
The new prompt specifically asks for themes that:
1. Are NOT well-covered by existing patterns
2. Represent genuine emerging behaviors, challenges, or opportunities
3. Could evolve into new guidance categories over time
4. Prioritize truly novel insights over minor variations

### 3. Enhanced Pattern Processing
- **Slugify function**: Converts pattern titles to URL-friendly identifiers
- **Dynamic identifiers**: New patterns get `dynamic-{slug}` format IDs
- **Logging**: Added verbose output for novelty scores and pattern acceptance/rejection

## How It Works

### Original Flow (Limited)
```
Static Patterns (8 fixed) → Check remaining slots → Find similar examples → Update counts
```

### Enhanced Flow (Dynamic)
```
Static Patterns + Existing Dynamic → Check for new sessions →
  ├─ If ENABLE_DYNAMIC_DISCOVERY: Look for NOVEL themes
  └─ If disabled: Look for variations of existing themes
     → Filter by novelty score → Add as new pattern categories
```

## Example Dynamic Patterns That Could Be Discovered
Instead of just fitting sessions into existing buckets like "documentation" or "testing", the system can now discover entirely new themes like:

- "Context Window Management" - sessions about optimizing token usage
- "Multi-Agent Coordination" - sessions about agent collaboration patterns
- "API Rate Limiting" - sessions about handling API constraints
- "Memory Optimization" - sessions about managing agent memory/state

## Usage

### Default (Dynamic Discovery Enabled)
```bash
python3 .codex/scripts/codex_pattern_updater.py --agent claude
```

### Force Standard Mode Only
```bash
ENABLE_DYNAMIC_DISCOVERY=0 python3 .codex/scripts/codex_pattern_updater.py --agent claude
```

### Disable LLM Entirely
```bash
CODEX_PATTERN_DISABLE_LLM=1 python3 .codex/scripts/codex_pattern_updater.py --agent claude
```

## Technical Changes

### Core Function Updates
- `discover_patterns_with_llm()` - Added `force_dynamic` parameter
- `discover_patterns_with_claude()` - Added `force_dynamic` parameter
- `process_agent()` - Now passes `ENABLE_DYNAMIC_DISCOVERY` as `force_dynamic`
- Added `slugify()` utility function for pattern ID generation

### Prompt Engineering
The new dynamic prompt structure:
```python
prompt = f"""
You are analyzing new coding agent sessions to discover emerging themes and patterns.
Existing patterns: {existing_titles_text}

Review the session excerpts below and identify up to {capacity} NOVEL themes that:
1. Are NOT well-covered by existing patterns above
2. Represent genuine emerging behaviors, challenges, or opportunities
3. Could evolve into new guidance categories over time

Prioritize truly novel insights over minor variations of existing patterns.
"""
```

## Configuration

The system respects these environment variables:
- `CODEX_PATTERN_DISABLE_LLM` - Disable LLM discovery entirely
- `CODEX_PATTERN_PROVIDER` - Choose between "claude" and "codex" providers
- `CODEX_PATTERN_CLAUDE_MODEL` - Specify Claude model (default: claude-sonnet-4-20250514)
- `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` - Claude API configuration
- `ENABLE_DYNAMIC_DISCOVERY` - New flag to control dynamic mode (in script)

## Validation

The enhancement has been tested and confirmed to:
- ✅ Run successfully with both `--agent claude` and `--agent all`
- ✅ Process new sessions and update existing pattern counts
- ✅ Maintain backward compatibility with existing functionality
- ✅ Support both dynamic and standard discovery modes
- ✅ Generate proper pattern IDs with the new slugify function

## Future Enhancements

Potential improvements to consider:
1. **Adaptive novelty thresholds** - Adjust novelty filtering based on pattern volume
2. **Theme evolution tracking** - Watch how dynamic patterns evolve over time
3. **Pattern merging** - Combine related dynamic patterns automatically
4. **Confidence scoring** - Add confidence metrics alongside novelty scores
5. **Human-in-the-loop review** - Flag high-novelty patterns for manual review

---

This enhancement transforms the pattern discovery system from a **static categorization engine** into a **dynamic theme discovery system** that can evolve with emerging AI agent behaviors and usage patterns.