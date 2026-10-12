import { reportError } from "../_sentry";

interface Env {
  BREVO_API_KEY?: string;
}

export const onRequestPost: PagesFunction<Env> = async (context) => {
  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };

  try {
    const contentType = context.request.headers.get("content-type") || "";
    let email = "";

    if (contentType.includes("application/json")) {
      const data = (await context.request.json()) as any;
      email = (data?.email || "").trim();
    } else if (contentType.includes("application/x-www-form-urlencoded")) {
      const formData = await context.request.formData();
      email = ((formData.get("email") as string) || "").trim();
    }

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return new Response(
        JSON.stringify({ success: false, error: "有効なメールアドレスを入力してください。" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" } }
      );
    }

    const apiKey = context.env.BREVO_API_KEY;
    if (!apiKey) {
      reportError(context, "BREVO_API_KEY is not configured", { stage: "config" });
      return new Response(
        JSON.stringify({ success: false, error: "API key is not configured on server." }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" } }
      );
    }

    // Call Brevo API: Add contact to List 3 (SEOUL TRIP NOTE Subscribers)
    const brevoResp = await fetch("https://api.brevo.com/v3/contacts", {
      method: "POST",
      headers: {
        "api-key": apiKey,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "SeoulTripNote/1.0",
      },
      body: JSON.stringify({
        email: email,
        listIds: [3],
        updateEnabled: true,
      }),
    });

    if (brevoResp.status === 201 || brevoResp.status === 204 || brevoResp.ok) {
      return new Response(
        JSON.stringify({ success: true, message: "ご登録ありがとうございます！最新情報をお届けします。" }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" } }
      );
    }

    const errData = (await brevoResp.json().catch(() => ({}))) as any;

    // Handle existing contact / duplicate gracefully
    if (brevoResp.status === 400 && (errData?.code === "duplicate_parameter" || (errData?.message && errData.message.includes("already exist")))) {
      return new Response(
        JSON.stringify({ success: true, message: "既に登録されています。最新の配信をお待ちください！" }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" } }
      );
    }

    // A 400 is usually the visitor's address; anything else is our setup or Brevo.
    if (brevoResp.status !== 400) {
      reportError(context, `Brevo ${brevoResp.status}: ${errData?.code || ""} ${errData?.message || ""}`, {
        stage: "brevo",
        status: String(brevoResp.status),
      });
    }
    return new Response(
      JSON.stringify({ success: false, error: errData?.message || "登録処理に失敗しました。" }),
      { status: brevoResp.status, headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" } }
    );
  } catch (err: any) {
    reportError(context, err, { stage: "handler" });
    return new Response(
      JSON.stringify({ success: false, error: err?.message || "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json; charset=utf-8" } }
    );
  }
};

export const onRequestOptions: PagesFunction = async () => {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
};
