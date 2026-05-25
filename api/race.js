export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { serviceKey, meet, rc_date, rc_no, type } = req.query;

  try {
    let url;

    if (type === 'result') {
      // 경주성적정보
      url = `https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1?serviceKey=${serviceKey}&numOfRows=20&pageNo=1&meet=${meet}&rc_date=${rc_date}&rc_no=${rc_no}&_type=json`;
    } else if (type === 'stats') {
      // 최근 한달 성적 통계용 (rc_no 없이 날짜 범위로 조회)
      url = `https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1?serviceKey=${serviceKey}&numOfRows=100&pageNo=1&meet=${meet}&rc_date=${rc_date}&_type=json`;
    } else {
      // 경주기록정보 기본
      url = `https://apis.data.go.kr/B551015/API4_3/raceResult_3?serviceKey=${serviceKey}&numOfRows=20&pageNo=1&meet=${meet}&rc_date=${rc_date}&rc_no=${rc_no}&_type=json`;
    }

    const response = await fetch(url);
    const text = await response.text();
    return res.status(200).send(text);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
