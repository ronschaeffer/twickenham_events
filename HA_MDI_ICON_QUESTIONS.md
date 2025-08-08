# Home Assistant MDI Icon Cards - Implementation Questions

## Overview

User requested creation of equivalent Home Assistant cards that use MDI icons received over MQTT instead of emojis, except for special cases like errors.

## Current State

- Updated existing cards to support emoji/icon display from MQTT data
- Cards currently use `event.emoji` first, then fall back to `event.icon`
- Error handling uses `<ha-icon icon="mdi:alert-circle">`
- Month headers use `<ha-icon icon="mdi:calendar-month">`

## Files to Create

New MDI-focused versions of:

1. `twickenham_events_upcoming_markdown.yaml`
2. `twickenham_events_all_upcoming_pop_up.yaml`

## Questions for Implementation

### 1. MQTT Icon Field Structure

- Should we use `event.mdi_icon` or `event.icon` for MQTT-provided MDI icons?
- Current implementation uses `event.icon` as fallback after `event.emoji`

### 2. Error Handling

- Current: `<ha-icon icon="mdi:alert-circle">` for errors
- Question: Keep this same approach in new MDI cards?

### 3. Calendar Icons

- Current: `<ha-icon icon="mdi:calendar-month">` for month headers
- Question: Keep this or use month-specific icons via MQTT?

### 4. Naming Convention

Proposed names:

- `twickenham_events_upcoming_markdown_mdi.yaml`
- `twickenham_events_all_upcoming_pop_up_mdi.yaml`

### 5. Fallback Behavior

If no MDI icon available via MQTT, should cards:

- Show no icon (clean text only)
- Fall back to default MDI icon
- Fall back to emoji (current behavior)

### 6. Additional Files

Also noticed in file explorer:

- `twickenham_events_card.yaml`
- `twickenham_events_short_card.yaml`

Question: Should these be updated as well?

## Expected MQTT Data Structure

Assuming events will have:

```yaml
event:
  fixture: "Event Name"
  start_time: "19:30"
  emoji: "🏉" # Current emoji field
  icon: "mdi:rugby" # MDI icon field (to be clarified)
  mdi_icon: "mdi:rugby" # Alternative field name?
```

## Implementation Notes

- Keep error icons as hardcoded MDI icons (special case)
- Maintain existing card structure and logic
- Focus on replacing emoji display with MDI icon display
- Preserve all existing functionality (error handling, month grouping, etc.)
