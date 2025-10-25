// api/line-webhook.js — 加入 AI 關聯性判斷（使用 chatWithModel）版
const { verifyLineSignature, replyText } = require('../lib/line');
const { chatWithModel } = require('../lib/openai');

/**
 * 以 chatWithModel 做語意關聯判斷：
 * 回傳 { related: boolean, score: number(0~1), reason: string }
 * - 僅使用 chatWithModel，不依賴額外 SDK。
 * - 嘗試強制模型輸出 JSON，並具備健壯解析（抓第一個 JSON 片段）。
 */
async function checkRelevanceWithModel(userText) {
  const prompt = `
你是一位分類器。判斷「使用者問題」是否與「內政大數據」主題相關。

「內政大數據」範圍舉例（不限於此）：
- 內政部資料、人口/戶政/移民/不動產/地籍/建築/治安/統計資料
- 資料治理、資料平台、資料品質、資料標準、資料交換、資料可視化、資料應用
- AI/資料科學在上述內政領域的應用
- 政府開放資料（與內政領域直接關聯者）
- 以內政為核心的跨機關資料整合

輸出規則（非常重要）：
- 僅輸出一段 JSON，無任何其他文字、註解或解釋。其中，中文字必須是繁體中文，不可有簡體字。
- 輸出內容必須為直述句，可以有建議，但絕不可有任何反問句。
- JSON 格式必須為：
  {"related": boolean, "score": number, "reason": string}
- "score" 範圍 0~1，越高代表與主題關聯越強。

判斷口訣（簡要）：
- 明確提到內政部、內政資料、戶政、地政、建築管理、警政、移民署、不動產、人口統計等 → 高分。
- 純聊天/娛樂、他部會領域且與內政無連結 → 低分。
- 與資料/大數據/AI 有關但未見內政領域關聯 → 低分，除非可合理推定與內政連動。

使用者問題：
${userText}
  `.trim();

  let raw;
  try {
    raw = await chatWithModel(prompt);
  } catch (e) {
    // 模型不可用時，回傳保守結果
    return { related: false, score: 0, reason: `model error: ${e.message || e}` };
  }

  // 從模型回覆中擷取第一個 JSON 物件
  const text = typeof raw === 'string' ? raw : String(raw ?? '');
  const match = text.match(/\{[\s\S]*\}/);
  const jsonText = match ? match[0] : text;

  try {
    const parsed = JSON.parse(jsonText);
    const related = Boolean(parsed.related);
    const score = typeof parsed.score === 'number' ? Math.max(0, Math.min(1, parsed.score)) : 0;
    const reason = typeof parsed.reason === 'string' ? parsed.reason : '';
    return { related, score, reason };
  } catch {
    // 解析失敗 → 保守視為不相關
    return { related: false, score: 0, reason: 'parse error or non-json response' };
  }
}

module.exports = async function handler(req, res) {
  try {
    // 支援 GET/HEAD（瀏覽器測試 & LINE Webhook 驗證）
    if (req.method === 'GET' || req.method === 'HEAD') {
      console.log('✅ GET/HEAD 請求 - 回傳 OK');
      return res.status(200).send('Webhook is running');
    }

    // 只處理 POST
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
    if (!signature) {
      console.error('❌ 缺少簽章');
      return res.status(401).send('Missing signature');
    }
    if (!verifyLineSignature(rawBody, signature)) {
      console.error('❌ 驗簽失敗：簽章不符');
      return res.status(403).send('Invalid signature');
    }

    // 解析事件 JSON
    const bodyText = rawBody.toString('utf8');
    let body;
    try {
      body = JSON.parse(bodyText);
    } catch (parseError) {
      console.error('🚨 JSON 解析錯誤：', parseError, '\n原始內容：', bodyText);
      return res.status(400).send('Bad Request - Invalid JSON');
    }

    console.log('✅ 收到 LINE Webhook：', JSON.stringify(body, null, 2));

    // 事件檢查（僅處理第一個事件，維持最小改動）
    const event = body?.events?.[0];
    if (!event) {
      console.log('⚠️ 無事件內容，回傳 200 OK');
      return res.status(200).send('OK');
    }

    // 文字訊息處理 + 關聯性判斷
    if (event.type === 'message' && event.message?.type === 'text') {
      const userText = (event.message.text || '').trim();
      console.log('💬 使用者輸入：', userText);

      try {
        // 先用 AI 判斷是否與「內政大數據」相關（使用 chatWithModel）
        const { related, score, reason } = await checkRelevanceWithModel(userText);
        console.log('🧮 關聯性判斷：', { related, score, reason });

        // 你可調整門檻；此處採 0.6
        const PASS_THRESHOLD = 0.6;
        if (!related || score < PASS_THRESHOLD) {
          await replyText(event.replyToken, '歡迎點選選單，或提出與內政大數據相關問題 。');
          return res.status(200).send('OK');
        }

        // ✅ 與內政大數據相關 → 呼叫模型生成回覆
        const answer = await chatWithModel(userText);
        console.log('🤖 模型回覆：', answer);
        await replyText(event.replyToken, answer || '⚠️ 模型未回覆');
      } catch (err) {
        console.error('🚨 關聯性判斷/模型呼叫錯誤：', err);
        await replyText(event.replyToken, '⚠️ 系統忙碌中，請稍後再試。');
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
