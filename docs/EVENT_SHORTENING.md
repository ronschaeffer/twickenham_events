# Event Name Shortening Feature

This project includes an optional AI-powered event name shortening feature that uses Google's Gemini API to create concise event names suitable for compact displays.

## Setup

### 1. Install Dependencies

The shortening feature requires the `google-generativeai` package:

```bash
# Install the AI dependency group
poetry install --with ai
```

### 2. Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Keep this key secure - you'll add it to your config

### 3. Enable the Feature

Update your `config/config.yaml` file:

```yaml
event_shortener:
  enabled: true # Set to true to enable
  api_key: "YOUR_GEMINI_API_KEY" # Add your API key here
  model_name: "gemini-2.0-flash" # Model to use
  char_limit: 16 # Maximum characters for shortened names
  prompt_template: > # Template for the AI prompt
    You are an expert editor. Your task is to shorten event names
    to a maximum of {char_limit} characters while keeping them recognizable.
    The events are usually rugby matches, but can also be concerts.
    Use standard abbreviations.

    Examples:
    fixture: Women's Rugby World Cup Final
    fixture_short: W RWC Final

    fixture: Taylor Swift | The Eras Tour
    fixture_short: Taylor Swift

    fixture: Harlequins Big Game
    fixture_short: Quins Big Game
    ---
    Now, shorten this event name:
    fixture: {event_name}
    fixture_short:

### 4. Flag Compatibility

The AI shortening feature can optionally add country flag emojis to event names. However, flag rendering compatibility varies across platforms:

#### Standard Country Flags (Recommended)
- **Examples**: 🇦🇺 🇫🇯 🇳🇿 🇫🇷 🇮🇪 🇮🇹 🇿🇦
- **Compatibility**: Render properly across all platforms, browsers, and applications
- **Usage**: Best choice for international events

#### Subdivision Flags (Limited Compatibility) 
- **Examples**: England 🏴󠁧󠁢󠁥󠁮󠁧󠁿, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿, Scotland 🏴󠁧󠁢󠁳󠁣󠁴󠁿
- **Technical Details**: Use complex Unicode subsequences that may not render properly in some browsers and platforms
- **Known Issues**: May appear as question marks or broken characters in Edge, older browsers, or some systems
- **Home Assistant**: All flag types have been tested and render properly in the Home Assistant Android app

#### Configuration Options

To disable flag emojis entirely:

```yaml
event_shortener:
  enabled: true
  add_flags: false  # Set to false to disable flag emojis
  # ... other settings
```

This will generate shortened names without flag emojis, ensuring maximum compatibility across all platforms.
```

## How It Works

### Event Data Structure

When enabled, events will include both the original and shortened names:

```json
{
  "fixture": "Women's Rugby World Cup Final",
  "fixture_short": "W RWC Final",
  "start_time": "15:00",
  "crowd": "80,000"
}
```

### Usage in Home Assistant Cards

You can now use either field in your dashboard cards:

```yaml
# Use full names
{{ event.fixture }}

# Use shortened names for compact displays
{{ event.fixture_short if event.fixture_short else event.fixture }}
```

### Error Handling

The feature is designed to be robust:

- **Disabled by default**: No impact until you explicitly enable it
- **Graceful fallback**: Uses original names if shortening fails
- **Error logging**: Shortening errors are logged but don't break event processing
- **Optional dependency**: Works without the AI library installed (just disables the feature)

## Configuration Options

| Option            | Default              | Description                            |
| ----------------- | -------------------- | -------------------------------------- |
| `enabled`         | `false`              | Enable/disable the shortening feature  |
| `api_key`         | `""`                 | Your Google Gemini API key             |
| `model_name`      | `"gemini-2.0-flash"` | Gemini model to use                    |
| `char_limit`      | `16`                 | Maximum characters for shortened names |
| `prompt_template` | (see above)          | Template for the AI prompt             |

## Cost Considerations

- Google Gemini API has usage-based pricing
- The feature is called once per unique event name
- Consider your event volume when enabling
- Free tier is available for light usage

## Troubleshooting

### Feature Not Working

1. Check that `enabled: true` in config
2. Verify API key is correct
3. Ensure `google-generativeai` is installed
4. Check logs for error messages

### Shortened Names Too Long

- Decrease the `char_limit` value
- Adjust the prompt template to emphasize brevity

### API Quota Exceeded

- Check your Google AI Studio usage
- Consider upgrading your API plan
- Temporarily disable the feature if needed

## Examples

With a 16-character limit:

| Original                      | Shortened      |
| ----------------------------- | -------------- |
| Women's Rugby World Cup Final | W RWC Final    |
| England vs New Zealand        | England v NZ   |
| Harlequins Big Game           | Quins Big Game |
| Taylor Swift \| The Eras Tour | Taylor Swift   |

The AI learns from the examples in the prompt template and applies similar abbreviation patterns to new events.
