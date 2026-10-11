module.exports = async (req, res) => {
  const unavailable = (reason, extra = {}) => {
    res.setHeader("Cache-Control", "no-store");
    return res
      .status(200)
      .json({ status: "DATA_UNAVAILABLE", reason, ...extra });
  };

  try {
    const { airline, flight, date } = req.query;

    if (!airline || !flight || !date) {
      return unavailable("Missing airline, flight, or date");
    }

    if (
      !/^[A-Za-z0-9]{2,3}$/.test(airline) ||
      !/^[A-Za-z0-9]{2,8}$/.test(flight) ||
      !/^\d{4}-\d{2}-\d{2}$/.test(date)
    ) {
      return unavailable("Invalid airline, flight, or date format");
    }

    const apiKey = process.env.AVIATIONSTACK_KEY;

    if (!apiKey) {
      return unavailable("Flight data service is not configured");
    }

    // Free plan: real-time data only, so no flight_date is sent upstream.
    // The date is checked below instead.
    const url =
      "https://api.aviationstack.com/v1/flights" +
      `?access_key=${encodeURIComponent(apiKey)}` +
      `&airline_iata=${encodeURIComponent(airline)}` +
      `&flight_iata=${encodeURIComponent(flight)}`;

    const response = await fetch(url);
    const text = await response.text();

    let data;
    try {
      data = JSON.parse(text);
    } catch {
      return unavailable("Flight data provider returned invalid JSON");
    }

    if (!response.ok || data?.error) {
      return unavailable(
        data?.error?.message || "Flight data provider returned an error",
        { provider_status: response.status }
      );
    }

    const records = Array.isArray(data?.data) ? data.data : [];
    const matches = records.filter((r) => r && r.flight_date === date);

    if (matches.length === 0) {
      return unavailable("No record for that flight on that date");
    }

    // Identical requests (the three validators) share one upstream call.
    res.setHeader("Cache-Control", "s-maxage=300");
    return res.status(200).json({ status: "AVAILABLE", data: matches });
  } catch (error) {
    return unavailable("Unable to retrieve flight data");
  }
};