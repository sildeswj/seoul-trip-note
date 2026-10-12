// Minimal Sentry reporter for Pages Functions (project jworld/seoul-trip-note).
// Posts one event to Sentry's envelope endpoint; no SDK, no compatibility flags.
// Issues: https://jworld.sentry.io/issues/?project=seoul-trip-note
const DSN = {
  host: "o4508851569426432.ingest.us.sentry.io",
  projectId: "4512243596394496",
  key: "06b6a3d90777fc7ee79006a36a93e256",
};

type Ctx = { request: Request; waitUntil: (p: Promise<unknown>) => void };

export function reportError(
  context: Ctx,
  error: unknown,
  tags: Record<string, string> = {},
  level: "error" | "warning" = "error",
) {
  const eventId = crypto.randomUUID().replace(/-/g, "");
  const err = error instanceof Error ? error : null;
  const url = new URL(context.request.url);
  const event = {
    event_id: eventId,
    timestamp: Date.now() / 1000,
    platform: "javascript",
    level,
    environment: "production",
    tags: { route: url.pathname, ...tags },
    request: { url: url.origin + url.pathname, method: context.request.method },
    ...(err
      ? { exception: { values: [{ type: err.name, value: err.message }] }, extra: { stack: err.stack } }
      : { message: { formatted: String(error).slice(0, 2000) } }),
  };
  const body = [
    JSON.stringify({ event_id: eventId, sent_at: new Date().toISOString() }),
    JSON.stringify({ type: "event" }),
    JSON.stringify(event),
  ].join("\n");
  const endpoint = `https://${DSN.host}/api/${DSN.projectId}/envelope/?sentry_key=${DSN.key}&sentry_version=7`;
  context.waitUntil(
    fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/x-sentry-envelope" }, body }).catch(
      () => undefined,
    ),
  );
}
