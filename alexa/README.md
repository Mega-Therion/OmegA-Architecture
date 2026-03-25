# OmegA Alexa Skill

Voice interface for OmegA through Amazon Alexa devices.

**Usage:** "Alexa, open OmegA" or "Alexa, ask OmegA [your question]"

## Setup

### 1. Create the Alexa Skill

1. Go to [developer.amazon.com/alexa/console](https://developer.amazon.com/alexa/console/ask)
2. Click **Create Skill**
3. Name: `OmegA` → Language: `English (US)` → Model: `Custom` → Backend: `Alexa-hosted (Node.js)` or `Provision your own`
4. Under **Interaction Model → JSON Editor**, paste the contents of `interactionModel.json`
5. Click **Save Model** → **Build Model**

### 2. Deploy the Lambda

**Option A: Alexa-hosted (easiest)**
- In the Alexa console, go to **Code** tab
- Replace `index.mjs` with the contents of this repo's `index.mjs`
- Add environment variable: `OMEGA_API_URL` = `https://omega-sovereign.vercel.app/api/ask`
- Click **Deploy**

**Option B: Your own AWS Lambda**
1. Create a Lambda function (Node.js 20.x, arm64)
2. Upload `index.mjs` as the handler
3. Set env var: `OMEGA_API_URL` = `https://omega-sovereign.vercel.app/api/ask`
4. Set timeout to 20 seconds
5. Add Alexa Skills Kit as a trigger
6. Copy the Lambda ARN into the Alexa skill endpoint config

### 3. Test

- Go to the **Test** tab in the Alexa console
- Enable testing for "Development"
- Type or say: "open omega"
- Then ask anything

The skill stays in dev mode (your account only) unless you submit for certification.
