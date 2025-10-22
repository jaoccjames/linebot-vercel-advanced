// api/line-webhook.js — 修正版：支援 GET 和 POST
const { verifyLineSignature, replyText } = require('../lib/line');
const { chatWithModel } = require('../lib/openai');

module.exports = async function handler(req, res) {
  try {
    // 支援 GET 請求（瀏覽器測試 & LINE Webhook 驗證）
    if (req.method === 'GET' || req.method === 'HEAD') {
      console.log('✅ GET/HEAD 請求 - 回傳 OK');
      return res.status(200).send('Webhook is running');
    }

    // 只處理 POST 請求
    if (req.method !== 'POST') {
      console.log('❌ 不支援的請求方法：', req.method);
      return res.status(405).send('Method Not Allowed');
    }

    // 取得 raw body（驗簽必要）
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const rawBody = Buffer.concat(chunks);

    // 驗證簽章
    const signature = req.headers['x-line-signature'];
    if (!verifyLineSignature(rawBody, signature)) {
      console.error('❌ 驗簽失敗：簽章不符');
      return res.status(401).send('Invalid signature');
    }

    // 解析事件內容
    const bodyText = rawBody.toString('utf8');
    let body;
    try {
      body = JSON.parse(bodyText);
    } catch (parseError) {
      console.error('🚨 JSON 解析錯誤：', parseError, '\n原始內容：', bodyText);
      return res.status(400).send('Bad Request - Invalid JSON');
    }

    console.log('✅ 收到 LINE Webhook：', JSON.stringify(body, null, 2));

    // 事件檢查
    const event = body?.events?.[0];
    if (!event) {
      console.log('⚠️ 無事件內容，回傳 200 OK');
      return res.status(200).send('OK');
    }

    // 文字訊息處理
    if (event.type === 'message' && event.message?.type === 'text') {
      const userText = (event.message.text || '').trim();
      console.log('💬 使用者輸入：', userText);

      try {
        // 呼叫 OpenAI 模型
        const answer = await chatWithModel(userText);
        console.log('🤖 模型回覆：', answer);

        // 回覆 LINE 使用者
        await replyText(event.replyToken, answer || '⚠️ 模型未回覆');
      } catch (openaiError) {
        console.error('🚨 OpenAI 呼叫錯誤：', openaiError);
        await replyText(event.replyToken, '⚠️ 無法取得 AI 回覆，請稍後再試。');
      }
    } else {
      console.log('⚠️ 收到非文字訊息類型事件，略過。事件類型：', event.type);
    }

    // 成功處理
    return res.status(200).send('OK');
  } catch (err) {
    // 捕捉所有未預期錯誤
    console.error('🔥 全域錯誤捕捉：', err);
    return res.status(500).json({ error: 'Internal Server Error', message: err.message });
  }
};
