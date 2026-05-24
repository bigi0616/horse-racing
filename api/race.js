export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const { serviceKey, meet, rc_date, rc_no } = req.query;
  
  if (!serviceKey || !meet || !rc_date || !rc_no) {
    return res.status(400).json({ error: '파라미터 누락' });
  }

  try {
    const url = `https://apis.data.go.kr/B551015/API186_1/RcRaceInfo_1?serviceKey=${serviceKey}&numOfRows=20&pageNo=1&meet=${meet}&rc_date=${rc_date}&rc_no=${rc_no}&_type=json`;
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' }
    });
    
    const text = await response.text();
    
    // 디버그용: 원본 응답 그대로 반환
    return res.status(200).send(text);
    
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
