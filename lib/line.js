// lib/line.js — 使用 LINE 官方 SDK 建 client；自行做簽章驗證（HMAC-SHA256）
const crypto = require('crypto');
const line = require('@line/bot-sdk');


function createLineClient() {
const config = {
channelAccessToken: process.env.LINE_CHANNEL_ACCESS_TOKEN,
channelSecret: process.env.LINE_CHANNEL_SECRET
};
return new line.Client(config);
}


function verifyLineSignature(rawBody, signature) {
const channelSecret = process.env.LINE_CHANNEL_SECRET || '';
const hmac = crypto.createHmac('sha256', channelSecret);
hmac.update(rawBody);
const digest = hmac.digest('base64');
const a = Buffer.from(digest);
const b = Buffer.from(signature || '', 'utf8');
return a.length === b.length && crypto.timingSafeEqual(a, b);
}


async function replyText(replyToken, text) {
const client = createLineClient();
await client.replyMessage(replyToken, [{ type: 'text', text: String(text || '') }]);
}


async function pushText(userId, text) {
const client = createLineClient();
await client.pushMessage(userId, [{ type: 'text', text: String(text || '') }]);
}


module.exports = { createLineClient, verifyLineSignature, replyText, pushText };
