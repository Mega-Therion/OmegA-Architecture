# OmegA on iPhone — Setup Guide

Two ways to use OmegA on your iPhone:

---

## Method 1: PWA (Home Screen App)

The voice interface at `/omega.html` is a Progressive Web App.

1. Open Safari on your iPhone
2. Navigate to: `https://omega-sovereign.vercel.app/omega.html`
3. Tap the **Share** button (square with arrow)
4. Tap **Add to Home Screen**
5. Name it **OmegA** → tap **Add**

You now have an OmegA icon on your home screen. It opens full-screen with no browser chrome. Tap the mic button to talk, or type. The Three.js wireframe, word-by-word animation, and Charon voice all work.

**Tip:** On iPhone 15 Pro+, set the **Action Button** to open the OmegA shortcut (Method 2) for instant physical access.

---

## Method 2: Siri Shortcut (Voice Activated)

This creates a Shortcut you can trigger by saying **"Hey Siri, ask OmegA"**.

### Step-by-step:

1. Open the **Shortcuts** app
2. Tap **+** to create a new shortcut
3. Name it: **Ask OmegA**

### Add these actions in order:

**Action 1: Dictate Text**
- Search for "Dictate Text" and add it
- This captures your voice input

**Action 2: Get Contents of URL**
- URL: `https://omega-sovereign.vercel.app/api/ask`
- Method: **POST**
- Headers: `Content-Type` = `application/json`
- Request Body: **JSON**
  - Add key: `text` → Value: select **Dictated Text** (the variable from Action 1)

**Action 3: Get Dictionary Value**
- Key: `reply`
- From: **Contents of URL** (the variable from Action 2)

**Action 4: Speak Text**
- Text: select **Dictionary Value** (the variable from Action 3)
- Rate: 0.9
- Pitch: 0.85

### Done. Now:

- Say **"Hey Siri, ask OmegA"** → it listens → sends to OmegA → speaks the response
- Or tap the shortcut from your home screen / widget

### Optional: Action Button

On iPhone 15 Pro / 16 Pro:
1. Settings → Action Button
2. Set to: **Shortcut**
3. Select: **Ask OmegA**

Now one press of the physical button activates OmegA.

---

## How it works

Both methods hit `/api/ask` — a non-streaming JSON endpoint that:
- Pulls recent memory from the Neon database
- Runs through the provider waterfall (Vercel Gateway → xAI → Gemini)
- Returns a concise, voice-optimized response
- No API keys on the device — everything is server-side
