export default async function handler(req, res) {
  try {
    const { airline, flight, date } = req.query;

    if (!airline || !flight || !date) {
      return res.status(400).json({
        error: "Missing airline, flight, or date",
      });
    }

    const apiKey = process.env.AVIATIONSTACK_KEY;

    if (!apiKey) {
      return res.status(500).json({
        error: "Flight data service is not configured",
      });
    }

    const url =
      "https://api.aviationstack.com/v1/flights" +
      `?access_key=${encodeURIComponent(apiKey)}` +
      `&airline_iata=${encodeURIComponent(airline)}` +
      `&flight_iata=${encodeURIComponent(flight)}` +
      `&flight_date=${encodeURIComponent(date)}`;

    const response = await fetch(url);

    const body = await response.text();

    return res.status(response.status).send(body);
  } catch (error) {
    console.error(error);

    return res.status(500).json({
      error: "Unable to retrieve flight data",
    });
  }
}