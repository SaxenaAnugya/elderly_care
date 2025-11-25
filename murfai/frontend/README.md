# Loneliness Companion - Frontend

A Next.js frontend interface for the Loneliness Companion, designed specifically for elderly users with large buttons, clear text, and simple navigation.

## Features

- 🎤 **Voice Interface**: Large microphone button for easy voice interaction
- 💊 **Medication Reminders**: Manage medications with clear, simple interface
- 📚 **Word of the Day**: Cognitive exercises with large, readable text
- 💬 **Conversation History**: View past conversations with sentiment indicators
- ⚙️ **Settings**: Easy-to-use configuration options

## Design Principles

- **Large Text**: Minimum 18px font size, larger for important elements
- **Large Buttons**: Minimum 60px height, 120px width
- **High Contrast**: Clear color distinctions for visibility
- **Simple Navigation**: Tab-based interface, no complex menus
- **Clear Feedback**: Visual indicators for all actions
- **Accessibility**: ARIA labels, keyboard navigation support

## Setup

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running (see main README)

### Installation

```bash
cd frontend
npm install
```

### Configuration

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

Update the API URL to match your backend.

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Production Build

```bash
npm run build
npm start
```

## API Integration

The frontend expects the following API endpoints:

### Voice
- `POST /voice/start` - Start voice session
- `POST /voice/stop/:sessionId` - Stop voice session
- `POST /voice/message/:sessionId` - Send audio message
- `GET /voice/status/:sessionId` - Get voice status

### Conversations
- `GET /conversations?limit=10` - Get conversation history
- `POST /conversations` - Save conversation

### Medications
- `GET /medications` - Get all medications
- `POST /medications` - Add medication
- `PATCH /medications/:id` - Update medication
- `DELETE /medications/:id` - Delete medication
- `GET /medications/due` - Get due medications

### Word of Day
- `GET /word-of-day` - Get current word

### Settings
- `GET /settings` - Get settings
- `PATCH /settings` - Update settings

### Health
- `GET /health` - Health check

## Components

- `VoiceInterface`: Main voice interaction component
- `MedicationReminders`: Medication management
- `WordOfDay`: Word of the day display
- `ConversationHistory`: Conversation history viewer
- `Settings`: Configuration interface

## Customization

### Colors

Edit `tailwind.config.js` to change color scheme:

```js
colors: {
  primary: {
    // Your color palette
  }
}
```

### Font Sizes

Edit `app/globals.css` to adjust font sizes:

```css
body {
  font-size: 18px; /* Adjust base size */
}
```

### Button Sizes

Modify `.button-large` class in `globals.css`:

```css
.button-large {
  min-height: 70px; /* Adjust height */
  min-width: 150px; /* Adjust width */
}
```

## Accessibility

- All interactive elements have ARIA labels
- Keyboard navigation supported
- High contrast colors
- Large touch targets (minimum 44x44px)
- Screen reader friendly

## Browser Support

- Chrome/Edge (recommended)
- Firefox
- Safari
- Mobile browsers

## Troubleshooting

### API Connection Issues

1. Check `NEXT_PUBLIC_API_URL` in `.env.local`
2. Verify backend is running
3. Check browser console for CORS errors
4. Ensure backend allows frontend origin

### Microphone Not Working

1. Check browser permissions
2. Use HTTPS in production (required for microphone)
3. Verify microphone is connected
4. Check browser console for errors

### Build Errors

1. Clear `.next` folder: `rm -rf .next`
2. Reinstall dependencies: `rm -rf node_modules && npm install`
3. Check Node.js version (18+ required)

## License

Part of the Loneliness Companion project.

