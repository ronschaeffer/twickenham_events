# PROJECT HANDOFF DOCUMENT
# Twickenham Events - AI-Powered Event Shortening System
# Created: August 1, 2025
# Status: FULLY IMPLEMENTED AND OPERATIONAL

## PROJECT OVERVIEW

This is a Python-based event scraping and publishing system for Twickenham Stadium events that:
- Scrapes events from Richmond Council website
- Uses AI (Google Gemini) to shorten event names with country flags
- Publishes to MQTT for Home Assistant integration
- Implements comprehensive caching and error handling

## CURRENT PROJECT STATE: ✅ COMPLETE & OPERATIONAL

### Recently Completed Work:
1. **AI-Powered Event Shortening**: Full implementation using Google Gemini API
2. **Country Flag Integration**: Unicode flag emojis with proper spacing
3. **Visual Width Calculation**: Flags count as 2 units, chars as 1 unit
4. **Rate Limiting**: 2-second delays between API calls to prevent 500 errors
5. **Comprehensive Testing**: 26 unit tests covering all functionality
6. **Configuration System**: Environment variable expansion for API keys

### System Status:
- ✅ All functionality working correctly
- ✅ Cache file being written to `output/event_name_cache.json`
- ✅ MQTT publishing with shortened names
- ✅ Home Assistant integration active
- ✅ All tests passing (26/26)

## ARCHITECTURE & KEY FILES

### Core Structure:
```
twickenham_events/
├── core/
│   ├── __main__.py              # Main entry point
│   ├── twick_event.py           # Event processing & scraping
│   ├── event_shortener.py       # 🆕 AI shortening with flags
│   ├── mqtt_publisher.py        # MQTT integration
│   ├── ha_mqtt_discovery.py     # Home Assistant discovery
│   └── config.py               # Configuration loading
├── config/
│   └── config.yaml             # 🆕 Updated with ai_shortener section
├── tests/
│   ├── test_event_shortener.py     # Updated legacy tests
│   └── test_event_shortener_new.py # 🆕 New functionality tests
├── output/
│   └── event_name_cache.json   # 🆕 AI-generated cache
└── docs/
    └── EVENT_SHORTENING.md     # Documentation
```

### Key Implementation Files:

#### 1. `core/event_shortener.py` - AI SHORTENING ENGINE
**Purpose**: AI-powered event name shortening with country flags
**Status**: FULLY IMPLEMENTED
**Key Functions**:
- `get_short_name()` - Main API function
- `calculate_visual_width()` - Flag-aware width calculation
- `standardize_flag_spacing()` - Post-processing for consistent spacing
- `load_cache()`, `save_cache()` - JSON caching system

**Features**:
- Google Gemini API integration (gemini-2.5-pro model)
- Environment variable expansion (${GEMINI_API_KEY})
- Visual width validation (flags = 2 units, chars = 1 unit)
- Rate limiting (2-second delays)
- Flag standardization for 11 rugby nations
- Comprehensive error handling

#### 2. `config/config.yaml` - CONFIGURATION
**AI Shortener Section**:
```yaml
ai_shortener:
  enabled: true
  api_key: ${GEMINI_API_KEY}  # Environment variable
  model: gemini-2.5-pro
  max_length: 25
  flags_enabled: true
  standardize_spacing: true
  prompt_template: >
    [Comprehensive prompt with flag instructions]
```

#### 3. `tests/` - COMPREHENSIVE TEST SUITE
**Status**: ALL TESTS PASSING (26/26)
**Coverage**:
- Original functionality (updated for new config keys)
- Flag spacing standardization
- Visual width calculations
- Environment variable expansion
- Rate limiting validation
- Error handling scenarios
- Cache operations
- Prompt generation

## AI SHORTENING SYSTEM DETAILS

### Flow:
1. Event scraped from Richmond Council website
2. `get_short_name()` called with event name + config
3. Check cache first (avoid API calls)
4. If not cached: API call to Gemini with dynamic prompt
5. Post-process result with `standardize_flag_spacing()`
6. Validate visual width <= 25 units
7. Save to cache if successful
8. Return shortened name or original if error

### Flag System:
**Supported Countries** (11 total):
- England: 🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG
- Scotland: 🏴󠁧󠁢󠁳󠁣󠁴󠁿 SCO  
- Wales: 🏴󠁧󠁢󠁷󠁬󠁳󠁿 WAL
- Australia: 🇦🇺 AUS
- New Zealand: 🇳🇿 NZ
- Argentina: 🇦🇷 ARG
- South Africa: 🇿🇦 RSA
- France: 🇫🇷 FRA
- Italy: 🇮🇹 ITA
- Ireland: 🇮🇪 IRE
- Fiji: 🇫🇯 FIJ

**Format**: `🇦🇷 ARG V 🇿🇦 RSA` (exactly one space between flag and country code)

### Cache System:
**File**: `output/event_name_cache.json`
**Format**:
```json
{
  "Original Event Name": {
    "short": "🇦🇷 ARG V 🇿🇦 RSA",
    "created": "2025-08-01T08:44:12.058285",
    "original": "Original Event Name"
  }
}
```

## INTEGRATION POINTS

### 1. Main Processing (`core/twick_event.py`):
```python
from core.event_shortener import get_short_name

# In summarize_events():
short_name, shortening_error = get_short_name(fixture_name, config)
if short_name != fixture_name:
    event_data['fixture_short'] = short_name
```

### 2. MQTT Publishing:
- Publishes both `fixture` (original) and `fixture_short` (AI-generated)
- Home Assistant receives flag-enhanced names
- Backward compatible (no `fixture_short` if same as original)

### 3. Error Handling:
- Missing API key: Returns original name, logs error
- API failures: Returns original name, logs error  
- Invalid responses: Returns original name, logs error
- Rate limiting: 2-second delays prevent 500 errors

## CONFIGURATION REQUIREMENTS

### Environment Variables:
- `GEMINI_API_KEY`: Required for AI functionality
- Set via: `export GEMINI_API_KEY="your_key_here"`

### Dependencies (in pyproject.toml):
- `google-generativeai`: For Gemini API
- All existing dependencies maintained

## TESTING

### Run Tests:
```bash
cd /home/ron/projects/twickenham_events
/home/ron/projects/twickenham_events/.venv/bin/python -m pytest tests/test_event_shortener.py tests/test_event_shortener_new.py -v
```

### Expected: 26/26 tests passing

## OPERATIONAL STATUS

### What's Working:
- ✅ Event scraping from Richmond Council
- ✅ AI-powered shortening with Gemini API
- ✅ Country flag integration
- ✅ Visual width validation
- ✅ Caching system
- ✅ Rate limiting
- ✅ MQTT publishing
- ✅ Home Assistant integration
- ✅ Error handling & logging

### Recent Performance:
- Successfully shortened events like:
  - `"Argentina V South Africa"` → `"🇦🇷 ARG V 🇿🇦 RSA"`
  - `"England vs Australia"` → `"🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG v 🇦🇺 AUS"`
  - `"Women's Rugby World Cup Final"` → `"W RWC Final"`

## TECHNICAL DECISIONS MADE

### 1. Visual Width System:
- **Decision**: Flags = 2 display units, characters = 1 unit
- **Reason**: Flags appear wider in UI displays
- **Implementation**: `calculate_visual_width()` function

### 2. Post-Processing Standardization:
- **Decision**: AI + post-processing hybrid approach
- **Reason**: AI inconsistent with flag spacing, post-processing ensures 100% reliability
- **Implementation**: `standardize_flag_spacing()` with regex patterns

### 3. Rate Limiting:
- **Decision**: 2-second delays between API calls
- **Reason**: Prevent 500 errors from Gemini API rate limits
- **Implementation**: `time.sleep(2)` before each API call

### 4. Config Key Migration:
- **Decision**: Changed from `event_shortener.*` to `ai_shortener.*`
- **Reason**: Better reflects AI-powered nature
- **Impact**: All tests updated, backward compatibility maintained

### 5. Environment Variable Expansion:
- **Decision**: Support `${GEMINI_API_KEY}` template in config
- **Reason**: Security - no hardcoded API keys
- **Implementation**: Manual expansion in `get_short_name()`

## POTENTIAL FUTURE ENHANCEMENTS

### If Needed:
1. **Additional Models**: Support for other AI providers (OpenAI, Claude)
2. **More Sports**: Expand beyond rugby (football, cricket)
3. **Custom Flag Mappings**: User-configurable flag preferences
4. **Batch Processing**: Multiple events in single API call
5. **Analytics**: Track shortening effectiveness metrics

## DEBUGGING & TROUBLESHOOTING

### Common Issues:
1. **"Event shortening enabled but no API key provided"**
   - Solution: Set `GEMINI_API_KEY` environment variable

2. **API 500 errors**
   - Solution: Rate limiting implemented (2-second delays)

3. **Inconsistent flag spacing**
   - Solution: Post-processing standardization implemented

4. **Cache not updating**
   - Check: API key set, output directory permissions, error logs

### Debug Commands:
```bash
# Test event shortening
GEMINI_API_KEY="your_key" python -c "from core.event_shortener import get_short_name; from core.config import Config; config = Config('config/config.yaml'); print(get_short_name('Test Event', config))"

# Run main script with API key
GEMINI_API_KEY="your_key" python -m core

# Check cache file
cat output/event_name_cache.json | jq
```

## FINAL STATUS

**Project State**: COMPLETE & OPERATIONAL ✅
**Last Updated**: August 1, 2025
**All Systems**: Functional and tested
**Ready For**: Production use or further enhancement

The AI-powered event shortening system is fully implemented, tested, and operational. The new chat agent can continue from this stable foundation.
