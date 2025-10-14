// lib/openai.js — 使用官方 OpenAI SDK 的最小封裝
const OpenAI = require('openai');
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const MODEL = 'gpt-4o-mini';

async function chatWithModel(userText) {
  const messages = [
    { role: 'system', content: 'You are a helpful assistant for a LINE chat.' },
    { role: 'user', content: userText || '' }
  ];
  const resp = await client.chat.completions.create({
    model: MODEL,
    messages,
    temperature: 0.7,
    max_tokens: 300
  });
  return resp.choices?.[0]?.message?.content || '';
}

module.exports = { chatWithModel };
