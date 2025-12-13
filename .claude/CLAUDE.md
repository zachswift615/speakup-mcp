## Voice/TTS (Text-to-Speech)

Use `mcp__tts__speak_tool` to speak to the user aloud. Use it liberally - for thinking
out loud, narrating what you're doing, conversing naturally, or any time voice adds to
the experience.

**Parameters:**
- `text` (required): What to say
- `tone`: neutral | excited | concerned | calm | urgent (default: neutral)
- `speed`: 0.5 to 2.0 (default: 1.0)
- `interrupt`: Stop current speech before starting (default: false - messages queue up)

**Example uses:**
- Thinking through a problem out loud
- Announcing task completion or updates
- Reading errors or warnings aloud
- Conversational back-and-forth

**Tone guide:**
- `calm` - explanations, walkthroughs
- `urgent` - errors, critical issues
- `excited` - successes, good news
- `concerned` - warnings, risky operations

Use `mcp__tts__stop_tool` to stop speech mid-playback.
