# Safe Audio Device Handling

**Status:** Approved for Planning

## Problem & Goals

**Problem:** The current audio device detection code in `streaming_player.py` calls private sounddevice APIs (`sd._terminate()` and `sd._initialize()`) on every message start. This aggressively reinitializes the entire PortAudio subsystem, which can corrupt macOS CoreAudio state system-wide - causing audio glitches, distortion, or complete audio failure that persists until restart.

**Goals:**
1. Remove the dangerous `_terminate/_initialize` pattern
2. Maintain automatic device switching (essential for AirPods use case)
3. Keep the fix simple and maintainable

## Chosen Approach

**Trust macOS CoreAudio to handle device routing.**

Instead of manually querying devices and reinitializing PortAudio, we use `device=None` when creating the `OutputStream`. This tells sounddevice/PortAudio to use the current system default device, letting macOS handle routing.

**Rationale:**
- Simplest solution - removes ~50 lines of problematic code
- CoreAudio is designed for exactly this purpose
- No private APIs, no global state manipulation
- Most audio applications work this way

## Key Decisions

| Decision | Choice | Trade-off |
|----------|--------|-----------|
| Device selection | `device=None` (system default) | Relies on macOS routing; no manual control |
| Mid-stream device changes | Not supported | Current message finishes on old device; acceptable |
| Device query/refresh | Removed entirely | Simpler but less proactive |
| Error handling | Existing `PortAudioError` catch | No retry logic; fails gracefully |

## Architecture

### Before (Dangerous)
```
start()
  → get_output_device_with_refresh()
    → query system_profiler for device
    → compare to cached device name
    → if mismatch: sd._terminate() + sd._initialize()  ← CORRUPTS AUDIO
  → create OutputStream with explicit device index
```

### After (Safe)
```
start()
  → create OutputStream with device=None
  → macOS routes to current default automatically
```

### Code Changes

**File:** `src/claude_tts_mcp/streaming_player.py`

**Remove:**
1. Global `_last_device_name` variable
2. Entire `get_output_device_with_refresh()` function (~50 lines)
3. Device index parameter in `start()` method

**Modify:**
```python
# In StreamingPlayer.start()
self._stream = sd.OutputStream(
    samplerate=sample_rate,
    channels=1,
    dtype=np.float32,
    blocksize=1024,
    device=None,  # Use system default
)
```

## Scope

### Must Have
- Remove `sd._terminate()` / `sd._initialize()` calls
- Remove `get_output_device_with_refresh()` function
- Use `device=None` for system default routing
- Existing tests continue to pass

### Nice to Have
- None - keeping this minimal

### Explicitly Out of Scope
- Mid-stream device switching (restart required)
- Soft device refresh (Approach 2 - can add later if needed)
- CoreAudio notification listener (Approach 3 - too complex)
- Retry logic on device failure
- Fallback device selection

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| AirPods connect between messages | Next message uses AirPods |
| AirPods disconnect mid-message | Stream fails with PortAudioError, next message uses new default |
| No audio device available | PortAudioError raised on stream creation |
| Device changes during stream creation | Rare; stream uses device at creation time |

## Testing

**Manual verification:**
1. Play multiple messages rapidly - no audio corruption
2. Plug headphones between messages - next message uses headphones
3. Unplug mid-message - graceful failure, next message works
4. Extended session - no degradation

**Automated:**
- Existing `tests/test_streaming_player.py` should pass
- Remove/update any mocks of deleted functions

## Open Questions

None - core assumption verified (see below).

## Verification

**Core Assumption Test (2026-01-16):**

Tested whether `device=None` picks up new default devices mid-session:

1. Created `OutputStream` with `device=None` → MacBook Pro Speakers (index 2)
2. Connected AirPods, set as system default
3. Created new `OutputStream` with `device=None` → Zach's AirPods (index 1)

**Result:** `device=None` DOES query fresh on each stream creation. No caching issue.

## Design Review Results

**Reviewed by:** Claude Opus 4.5 (Adversarial Subagent)
**Review Date:** 2026-01-16

**Key Feedback Addressed:**

1. **"Untested core assumption"** → Verified with live test above. Confirmed working.
2. **"Potential deadlock in start()"** → Pre-existing bug, noted but out of scope for this fix.
3. **"No logging/observability"** → Out of scope; can add later if debugging needed.
4. **"Cross-platform behavior"** → This is macOS-focused (TTS for Claude Code on Mac).

**Deferred Items:**

1. Deadlock fix in `start()` - separate issue, not caused by device handling
2. Failure feedback to tool caller - nice to have, not critical for this fix

**Recommendation:** Approved for Planning
