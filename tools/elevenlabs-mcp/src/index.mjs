import "dotenv/config";

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const apiKey = process.env.ELEVENLABS_API_KEY;
const defaultModelId = process.env.ELEVENLABS_MODEL_ID || "eleven_multilingual_v2";
const defaultOutputFormat = process.env.ELEVENLABS_OUTPUT_FORMAT || "mp3_44100_128";

if (!apiKey) {
  console.error("ELEVENLABS_API_KEY is required.");
  process.exit(1);
}

const server = new McpServer({
  name: "anw-elevenlabs",
  version: "0.1.0"
});

async function elevenLabsRequest(path, init = {}) {
  const headers = {
    Accept: "application/json",
    "xi-api-key": apiKey,
    ...init.headers
  };

  const response = await fetch(`https://api.elevenlabs.io${path}`, {
    ...init,
    headers
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`ElevenLabs ${response.status}: ${body}`);
  }

  return response;
}

function toTextContent(value) {
  return {
    content: [
      {
        type: "text",
        text: typeof value === "string" ? value : JSON.stringify(value, null, 2)
      }
    ]
  };
}

server.tool(
  "list_voices",
  "List available ElevenLabs voices for voice casting and taunt production.",
  {},
  async () => {
    const response = await elevenLabsRequest("/v2/voices");
    const data = await response.json();
    const voices = (data.voices || []).map((voice) => ({
      voice_id: voice.voice_id,
      name: voice.name,
      category: voice.category,
      labels: voice.labels || {}
    }));

    return toTextContent({ voices });
  }
);

server.tool(
  "text_to_speech",
  "Generate speech audio from text and return base64 audio for saving in the asset pipeline.",
  {
    voiceId: z.string().min(1),
    text: z.string().min(1),
    modelId: z.string().optional(),
    outputFormat: z.string().optional(),
    stability: z.number().min(0).max(1).optional(),
    similarityBoost: z.number().min(0).max(1).optional(),
    style: z.number().min(0).max(1).optional(),
    useSpeakerBoost: z.boolean().optional()
  },
  async ({
    voiceId,
    text,
    modelId = defaultModelId,
    outputFormat = defaultOutputFormat,
    stability = 0.55,
    similarityBoost = 0.8,
    style = 0.2,
    useSpeakerBoost = true
  }) => {
    const response = await elevenLabsRequest(
      `/v1/text-to-speech/${voiceId}?output_format=${encodeURIComponent(outputFormat)}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "audio/mpeg"
        },
        body: JSON.stringify({
          text,
          model_id: modelId,
          voice_settings: {
            stability,
            similarity_boost: similarityBoost,
            style,
            use_speaker_boost: useSpeakerBoost
          }
        })
      }
    );

    const audio = Buffer.from(await response.arrayBuffer()).toString("base64");
    return toTextContent({
      voiceId,
      modelId,
      outputFormat,
      audioBase64: audio
    });
  }
);

server.tool(
  "get_models",
  "List available ElevenLabs models and their capabilities.",
  {},
  async () => {
    const response = await elevenLabsRequest("/v1/models");
    const data = await response.json();
    const models = (data || []).map((model) => ({
      model_id: model.model_id,
      name: model.name,
      description: model.description,
      can_do_text_to_speech: model.can_do_text_to_speech,
      languages: model.languages || []
    }));

    return toTextContent({ models });
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);