const APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx9fqbPZap1JN2dGrnutAYbZ_8dX-q1UNshnADmNGmAIUKijz8fG6Pnrbra2d1cVgyA/exec";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

export async function GET(request) {
  const url = new URL(request.url);
  const mode = url.searchParams.get("hub.mode");
  const challenge = url.searchParams.get("hub.challenge");

  if (mode === "subscribe" && challenge) {
    return new Response(challenge, {
      status: 200,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }

  return new Response("ok", { status: 200 });
}

export async function POST(request) {
  try {
    const body = await request.text();

    const upstream = await fetch(APPS_SCRIPT_URL, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    });

    if (!upstream.ok) {
      const detail = await upstream.text().catch(() => "");
      return jsonResponse(
        {
          ok: false,
          error: "Apps Script upstream failed",
          status: upstream.status,
          detail: detail.slice(0, 500),
        },
        502
      );
    }

    return new Response("EVENT_RECEIVED", {
      status: 200,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  } catch (error) {
    return jsonResponse(
      {
        ok: false,
        error: String(error),
      },
      502
    );
  }
}
