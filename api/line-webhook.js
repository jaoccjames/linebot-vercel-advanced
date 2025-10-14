// api/line-webhook.js — Vercel Serverless：讀 raw body → 驗簽 → 呼叫 OpenAI → Reply
const { verifyLineSignature, replyText } = require('../lib/line');
const { chatWithModel } = require('../lib/openai');

module.exports = async function handler(req, res) {
  try {
    if (req.method !== 'POST') {
      return res.status(405).send('Method Not Allowed');
    }

    // 取得 raw body（必要：用於 HMAC 驗簽）
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const rawBody = Buffer.concat(chunks);

    // 簽章驗證（必須）
    const signature = req.headers['x-line-signature'];
    if (!verifyLineSignature(rawBody, signature)) {
      return res.status(401).send('Invalid signature');
    }

    const body = JSON.parse(rawBody.toString('utf8'));
    const event = body?.events?.[0];
    if (!event) return res.status(200).send('OK');

    if (event.type === 'message' && event.message?.type === 'text') {
      const userText = event.message.text || '';
      const answer = await chatWithModel(userText);
      await replyText(event.replyToken, answer || '');
    }

    return res.status(200).send('OK');
  } catch (err) {
    return res.status(200).send('OK');
  }
};
