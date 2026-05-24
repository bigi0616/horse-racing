export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');
  const { serviceKey, meet, rc_date, rc_no } = req.query;
  if (!serviceKey || !meet || !rc_date || !rc_no) {
    return res.status(400).json({ error: '파라미터 누락' });
  }
  try {
    const url = `https://apis.data.go.kr/B551015/API214_1/RaceDetailInfo_1?serviceKey=${encodeURIComponent(serviceKey)}&numOfRows=20&pageNo=1&meet=${meet}&rc_date=${rc_date}&rc_no=${rc_no}&_type=json`;
    const response = await fetch(url);
    const data = await response.json();
    return res.status(200).json(data);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
