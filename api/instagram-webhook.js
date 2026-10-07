const APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx9fqbPZap1JN2dGrnutAYbZ_8dX-q1UNshnADmNGmAIUKijz8fG6Pnrbra2d1cVgyA/exec";

export default async function handler(req, res) {
  if (req.method === "GET") {
    const mode = req.query?.["hub.mode"];
    const challenge = req.query?.["hub.challenge"];

    // Meta's verification handshake: return the raw challenge immediately.
    if (mode === "subscribe" && challenge) {
      return res.status(200).send(String(challenge));
    }

    return res.status(200).send("ok");
  }

  if (req.method === "POST") {
    try {
      const body =
        typeof req.body === "string"
          ? req.body
          : JSON.stringify(req.body ?? {});

      const upstream = await fetch(APPS_SCRIPT_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });

      if (!upstream.ok) {
        const detail = await upstream.text().catch(() => "");
        return res.status(502).json({
          ok: false,
          error: "Apps Script upstream failed",
          status: upstream.status,
          detail: detail.slice(0, 500),
        });
      }

      return res.status(200).send("EVENT_RECEIVED");
    } catch (error) {
      return res.status(502).json({
        ok: false,
        error: String(error),
      });
    }
  }

  res.setHeader("Allow", "GET, POST");
  return res.status(405).send("Method Not Allowed");
}
