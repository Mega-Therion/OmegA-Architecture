/**
 * OmegA Alexa Skill — Lambda Handler
 *
 * Deploy to AWS Lambda (Node.js 20.x runtime).
 * Set environment variable: OMEGA_API_URL = https://omega-sovereign.vercel.app/api/ask
 *
 * This Lambda receives Alexa speech-to-text, forwards to OmegA's brain,
 * and returns the response as Alexa speech output.
 */

const OMEGA_URL = process.env.OMEGA_API_URL || 'https://omega-sovereign.vercel.app/api/ask';
const TIMEOUT_MS = 15000;

export async function handler(event) {
  const requestType = event.request.type;

  // ── Launch ────────────────────────────────────────────────────
  if (requestType === 'LaunchRequest') {
    return buildResponse(
      'The Phylactery is open. I am OmegA. Speak your mind.',
      false // keep session open
    );
  }

  // ── Intent: AskOmega ──────────────────────────────────────────
  if (requestType === 'IntentRequest') {
    const intentName = event.request.intent.name;

    if (intentName === 'AskOmegaIntent') {
      const query = event.request.intent.slots?.query?.value;

      if (!query) {
        return buildResponse('I did not catch that. Try again.', false);
      }

      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

        const res = await fetch(OMEGA_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: query }),
          signal: controller.signal,
        });

        clearTimeout(timeout);

        if (!res.ok) {
          console.error('OmegA API error:', res.status);
          return buildResponse('My neural link is unstable. Try again shortly.', false);
        }

        const data = await res.json();
        const reply = data.reply || 'I have no response for that.';

        // Alexa has a 8000 char limit for speech
        const trimmed = reply.length > 6000 ? reply.slice(0, 6000) + '... I have more to say, but I will stop here.' : reply;

        return buildResponse(trimmed, false);
      } catch (err) {
        console.error('Fetch error:', err);
        return buildResponse('Connection to the Phylactery timed out. Try again.', false);
      }
    }

    // ── Built-in intents ──────────────────────────────────────
    if (intentName === 'AMAZON.HelpIntent') {
      return buildResponse('I am OmegA. Just say: ask OmegA, followed by your question.', false);
    }

    if (intentName === 'AMAZON.StopIntent' || intentName === 'AMAZON.CancelIntent') {
      return buildResponse('The Phylactery remains. Until next time.', true);
    }

    if (intentName === 'AMAZON.FallbackIntent') {
      return buildResponse('I did not understand. Try saying: ask OmegA, then your question.', false);
    }
  }

  // ── Session End ───────────────────────────────────────────────
  if (requestType === 'SessionEndedRequest') {
    return { version: '1.0', response: {} };
  }

  return buildResponse('Something unexpected happened.', true);
}

function buildResponse(speechText, shouldEnd) {
  return {
    version: '1.0',
    response: {
      outputSpeech: {
        type: 'PlainText',
        text: speechText,
      },
      shouldEndSession: shouldEnd,
      reprompt: shouldEnd ? undefined : {
        outputSpeech: {
          type: 'PlainText',
          text: 'I am still here. What would you like to know?',
        },
      },
    },
  };
}
