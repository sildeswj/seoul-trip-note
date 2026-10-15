"""
SEOUL TRIP NOTE Automated Newsletter Generator
Pulls the latest blog post, enriches it with real-time Seoul travel tips & hot spots via Gemini,
and generates a mobile-optimized Japanese HTML newsletter for Brevo publishing.

Usage:
  python scripts/generate_newsletter.py --draft   # Create draft campaign on Brevo
  python scripts/generate_newsletter.py --send    # Send campaign immediately to List 3
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Force IPv4 for Brevo API to avoid IPv6 whitelist restrictions
try:
    _orig_getaddrinfo = socket.getaddrinfo
    def _getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
        return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    socket.getaddrinfo = _getaddrinfo_ipv4
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
BLOG_DIR = os.path.join(PROJECT_ROOT, "src", "content", "blog")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "newsletter_output")

BREVO_API_BASE = "https://api.brevo.com/v3"


def get_gemini_api_key() -> str:
    """Retrieve Gemini API key from environment variable or local config."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    # Local fallback
    fallback_file = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "..", "config", "gemini_key.txt"))
    if os.path.isfile(fallback_file):
        try:
            with open(fallback_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""


def get_brevo_api_key() -> str:
    """Retrieve Brevo API key from environment variable or local config."""
    key = os.environ.get("BREVO_API_KEY", "").strip()
    if key:
        return key
    # Local fallback
    fallback_file = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "..", "config", "brevo_credentials.json"))
    if os.path.isfile(fallback_file):
        try:
            with open(fallback_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("api_key", "").strip()
        except Exception:
            pass
    return ""


def get_latest_blog_post() -> Dict[str, Any]:
    """Find and parse the most recent blog post in src/content/blog."""
    md_files = glob.glob(os.path.join(BLOG_DIR, "*.md"))
    if not md_files:
        raise FileNotFoundError(f"No blog markdown files found in {BLOG_DIR}")

    posts = []
    for filepath in md_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        fm_match = re.search(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not fm_match:
            continue

        fm_text = fm_match.group(1)
        body = fm_match.group(2).strip()

        meta = {}
        for line in fm_text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"\'')

        pub_date = meta.get("pubDate", "2026-01-01")
        slug = os.path.splitext(os.path.basename(filepath))[0]
        posts.append({
            "filepath": filepath,
            "slug": slug,
            "title": meta.get("title", ""),
            "description": meta.get("description", ""),
            "pubDate": pub_date,
            "body": body,
        })

    posts.sort(key=lambda x: x["pubDate"], reverse=True)
    return posts[0]


NEWSLETTER_SYSTEM_PROMPT = """
あなたは韓国・ソウル在住歴5年の日本人美容＆トレンドエディターです。
韓国旅行（渡韓）を計画している日本の20〜30代女性読者に向けて、
公式メールマガジン『SEOUL TRIP NOTE Weekly』の週刊ニュースレターを執筆します。

【読者が求める価値】
1. 今週の渡韓リアル速報（レート、天候・服装、空港や免税の注意点）
2. メイン特集（ブログ最新記事の核心ダイジェスト＋比較・要約）
3. エディター厳選の今週の推しスポット＆限定コスメ情報

【トーン＆マナー】
- 丁寧で親しみやすい「です・ます」調（「〜ですよね！」「ぜひチェックしてみてくださいね✨」など）。
- 機械翻訳感を完全排除した、雑誌エディターのような洗練された日本語。
- 読んですぐに役立つ具体的かつ実践的な情報（駅名、金額の目安、現地リアルな感想）。

【出力フォーマット（JSON必須）】
以下のキーを持つ厳密なJSONのみを出力してください。コードブロックや前置きは含めないでください。
{
  "subject": "【SEOUL TRIP NOTE】件名（開封したくなる魅力的な30〜45文字、絵文字含む）",
  "preview_text": "メール一覧に表示されるプレビュー文（50〜70文字）",
  "editorial_greeting": "冒頭の挨拶と今週のソウルの空気感（200〜250文字）",
  "exchange_rate_weather_tip": "今週のレート動向と天気・おすすめの服装ワンポイント（150〜200文字）",
  "main_feature_title": "メイン特集の見出し",
  "main_feature_summary": "ブログ記事の核心要約と実践アドバイス（350〜450文字）",
  "main_feature_checklist": ["チェックポイント1", "チェックポイント2", "チェックポイント3"],
  "weekly_editor_pick_title": "今週のエディター推しコスメ or スポット名",
  "weekly_editor_pick_desc": "推しの理由と現地リアルな魅力（200〜250文字）",
  "closing_note": "結びのメッセージ（100〜150文字）"
}
"""


def generate_newsletter_content(post: Dict[str, Any]) -> Dict[str, Any]:
    """Use Gemini to enrich the blog post into structured newsletter sections."""
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)

        user_prompt = f"""
最新のブログ記事をベースに、今週のメルマガ用コンテンツをJSONで生成してください。

【対象ブログ記事】
タイトル: {post['title']}
説明: {post['description']}
URL: https://seoul.jworld.dev/blog/{post['slug']}/
本文抜粋:
{post['body'][:1500]}

【重要】
- 出力は必ず指定されたキーを持つJSON形式のみにしてください。
- 読者が「今週韓国に行くなら絶対知っておきたい！」と感じる高密度な情報にしてください。
"""

        print("[*] Generating newsletter content with Gemini 2.5 Flash...", flush=True)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=NEWSLETTER_SYSTEM_PROMPT,
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )
        return json.loads(resp.text.strip())
    except Exception as e:
        print(f"[!] Gemini generation error: {e}", flush=True)
        raise


def render_newsletter_html(data: Dict[str, Any], post: Dict[str, Any]) -> str:
    """Render modern, responsive, mobile-first HTML email."""
    post_url = f"https://seoul.jworld.dev/blog/{post['slug']}/"
    checklist_items = "".join(f"<li style='margin-bottom: 8px; color: #4b5563;'>✓ {item}</li>" for item in data.get("main_feature_checklist", []))

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('subject', 'SEOUL TRIP NOTE Weekly')}</title>
  <style>
    body {{ margin: 0; padding: 0; background-color: #fdfaf7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; -webkit-font-smoothing: antialiased; }}
    table {{ border-spacing: 0; border-collapse: collapse; }}
    img {{ border: 0; }}
    .wrapper {{ width: 100%; background-color: #fdfaf7; padding: 24px 0; }}
    .main {{ background-color: #ffffff; max-width: 600px; margin: 0 auto; border-radius: 16px; overflow: hidden; border: 1px solid #f3ece6; box-shadow: 0 4px 12px rgba(0,0,0,0.03); }}
    .header {{ background: linear-gradient(135deg, #ff7e79 0%, #ff5b79 100%); padding: 32px 24px; text-align: center; color: #ffffff; }}
    .content {{ padding: 32px 24px; }}
    .card {{ background-color: #faf5f0; border-left: 4px solid #ff5b79; padding: 18px; border-radius: 8px; margin-bottom: 24px; }}
    .btn {{ display: inline-block; background: linear-gradient(135deg, #ff7e79 0%, #ff5b79 100%); color: #ffffff !important; padding: 14px 28px; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 15px; margin-top: 16px; box-shadow: 0 4px 10px rgba(255, 91, 121, 0.3); }}
    .footer {{ background-color: #f7f3ee; padding: 24px; text-align: center; font-size: 12px; color: #8c827a; line-height: 1.6; }}
    .footer a {{ color: #8c827a; text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <!-- Preview Text -->
    <div style="display: none; font-size: 1px; color: #fdfaf7; line-height: 1px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
      {data.get('preview_text', '')}
    </div>

    <table class="main" width="100%" align="center">
      <tr>
        <td class="header">
          <div style="font-size: 12px; letter-spacing: 2px; text-transform: uppercase; opacity: 0.9; margin-bottom: 6px;">SEOUL TRIP NOTE Official Newsletter</div>
          <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">渡韓女子のリアル攻略速報</h1>
          <p style="margin: 8px 0 0; font-size: 14px; opacity: 0.95;">現地エディターがお届けする今週のソウル最新情報</p>
        </td>
      </tr>
      <tr>
        <td class="content">
          <p style="font-size: 15px; line-height: 1.8; color: #374151; margin-top: 0;">
            {data.get('editorial_greeting', '')}
          </p>

          <div class="card">
            <h3 style="margin: 0 0 8px; font-size: 16px; color: #b91c1c; display: flex; align-items: center;">
              💡 今週のリアル渡韓Tips（レート＆気候）
            </h3>
            <p style="margin: 0; font-size: 14px; line-height: 1.7; color: #4b5563;">
              {data.get('exchange_rate_weather_tip', '')}
            </p>
          </div>

          <div style="margin-bottom: 32px;">
            <div style="display: inline-block; background-color: #ffe4e6; color: #e11d48; font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 20px; margin-bottom: 8px;">
              今週のメイン特集
            </div>
            <h2 style="margin: 0 0 12px; font-size: 20px; color: #111827; line-height: 1.4;">
              {data.get('main_feature_title', post['title'])}
            </h2>
            <p style="font-size: 15px; line-height: 1.8; color: #4b5563; margin-bottom: 16px;">
              {data.get('main_feature_summary', post['description'])}
            </p>
            <ul style="list-style: none; padding-left: 0; margin: 16px 0; background-color: #f9fafb; padding: 16px; border-radius: 8px;">
              {checklist_items}
            </ul>
            <div style="text-align: center; margin-top: 20px;">
              <a href="{post_url}" class="btn" target="_blank" rel="noopener">
                記事の全文と徹底比較を見る ➔
              </a>
            </div>
          </div>

          <hr style="border: none; border-top: 1px solid #f3ece6; margin: 28px 0;">

          <div>
            <div style="display: inline-block; background-color: #fef3c7; color: #d97706; font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 20px; margin-bottom: 8px;">
              エディターの今週の推し
            </div>
            <h3 style="margin: 0 0 8px; font-size: 17px; color: #1f2937;">
              🛍️ {data.get('weekly_editor_pick_title', '')}
            </h3>
            <p style="font-size: 14px; line-height: 1.7; color: #4b5563; margin: 0;">
              {data.get('weekly_editor_pick_desc', '')}
            </p>
          </div>

          <div style="margin-top: 24px; padding: 16px; background-color: #ffffff; border: 1px solid #f3ece6; border-radius: 8px;">
            <div style="font-size: 11px; font-weight: bold; color: #e11d48; margin-bottom: 6px;">PR · TRAVEL PREP</div>
            <div style="font-size: 15px; font-weight: bold; color: #111827; margin-bottom: 8px;">渡韓前に手配しておくと安心な定番チケット（Klook公式）</div>
            <p style="margin: 0 0 8px; font-size: 13.5px; line-height: 1.75; color: #4b5563;">
              • <a href="https://www.klook.com/ja/activity/1163-airport-to-seoul-city-center-arex-train-incheon/?aid=138920" target="_blank" style="color: #e11d48; font-weight: bold;">仁川空港鉄道 AREX 直通列車</a>（ソウル駅まで約43分・QR乗車）<br>
              • <a href="https://www.klook.com/ja/activity/109354-south-korea-esim-high-speed-internet-qr-code-voucher/?aid=138920" target="_blank" style="color: #e11d48; font-weight: bold;">韓国 高速データ通信 eSIM</a>（カウンター受取不要・即時QR発行）<br>
              • <a href="https://www.klook.com/ja/activity/1309-kal-limousine-bus-seoul/?aid=138920" target="_blank" style="color: #e11d48; font-weight: bold;">仁川空港 KALリムジンバス</a>（明洞・江南エリアへ直行）
            </p>
            <p style="margin: 0; font-size: 11px; color: #6b7280;">※ 上記はアフィリエイトリンク（PR）を含みます。最新料金・条件は予約画面でご確認ください。</p>
          </div>

          <div style="margin-top: 32px; padding: 16px; background-color: #faf5f0; border-radius: 8px; text-align: center;">
            <p style="margin: 0; font-size: 13px; color: #6b7280; line-height: 1.6;">
              {data.get('closing_note', '次回の渡韓計画にぜひお役立てください！')}
            </p>
          </div>
        </td>
      </tr>
      <tr>
        <td class="footer">
          <p style="margin: 0 0 8px; font-weight: bold; color: #57534e;">SEOUL TRIP NOTE（ソウルトリップノート）</p>
          <p style="margin: 0 0 12px;">渡韓女子のためのリアルソウル攻略ガイドメディア</p>
          <p style="margin: 0 0 16px;">
            <a href="https://seoul.jworld.dev">公式サイト</a> ｜ 
            <a href="https://seoul.jworld.dev/about">運営者について</a> ｜ 
            <a href="https://seoul.jworld.dev/privacy">プライバシーポリシー</a>
          </p>
          <p style="margin: 0; font-size: 11px; opacity: 0.8;">
            ※ 本メールは、SEOUL TRIP NOTEにてメルマガ登録をいただいた方へお送りしております。<br>
            配信停止をご希望の場合は、<a href="{{{{ unsubscribe }}}}" style="color: #8c827a;">こちらから配信解除</a>をお願いいたします。
          </p>
        </td>
      </tr>
    </table>
  </div>
</body>
</html>
"""
    return html


def call_brevo_api(endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    api_key = get_brevo_api_key()
    if not api_key:
        return {"success": False, "error": "BREVO_API_KEY is not configured."}

    url = f"{BREVO_API_BASE}/{endpoint.lstrip('/')}"
    data_bytes = json.dumps(payload).encode("utf-8") if payload else None

    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "api-key": api_key,
            "accept": "application/json",
            "content-type": "application/json",
            "User-Agent": "SeoulTripNoteBot/1.0",
        },
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return {"success": True, "data": json.loads(raw) if raw else {}}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            err_json = json.loads(body)
        except Exception:
            err_json = {"message": body}
        return {"success": False, "status_code": e.code, "error": err_json}
    except Exception as e:
        return {"success": False, "error": str(e)}


def publish_to_brevo(campaign_name: str, subject: str, html_content: str, send_now: bool = False) -> Dict[str, Any]:
    # Step 1: Create campaign draft
    payload = {
        "name": campaign_name,
        "subject": subject,
        "sender": {"id": 1, "name": "SEOUL TRIP NOTE"},
        "type": "classic",
        "htmlContent": html_content,
    }

    create_res = call_brevo_api("emailCampaigns", method="POST", payload=payload)
    if not create_res.get("success"):
        return create_res

    campaign_id = create_res.get("data", {}).get("id")
    if not campaign_id:
        return {"success": False, "error": "No campaign ID returned from Brevo."}

    # Step 2: Set recipient list (List 3: SEOUL TRIP NOTE Subscribers)
    call_brevo_api(f"emailCampaigns/{campaign_id}", method="PUT", payload={"recipients": {"listIds": [3]}})

    if send_now:
        send_res = call_brevo_api(f"emailCampaigns/{campaign_id}/sendNow", method="POST")
        return {"success": send_res.get("success", False), "campaign_id": campaign_id, "sent": True, "details": send_res}

    return {"success": True, "campaign_id": campaign_id, "sent": False, "status": "draft"}


def main():
    parser = argparse.ArgumentParser(description="SEOUL TRIP NOTE Newsletter Generator")
    parser.add_argument("--send", action="store_true", help="Send campaign immediately to subscribers.")
    parser.add_argument("--draft", action="store_true", help="Create as a draft campaign on Brevo without sending.")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("[*] Finding latest blog post...", flush=True)
    post = get_latest_blog_post()
    print(f"[*] Found post: {post['title']} ({post['slug']})", flush=True)

    data = generate_newsletter_content(post)
    subject = data.get("subject", f"【SEOUL TRIP NOTE】{post['title']}")
    print(f"[*] Subject: {subject}", flush=True)

    html_content = render_newsletter_html(data, post)

    # Save local copies
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = os.path.join(OUTPUT_DIR, f"{timestamp}_{post['slug']}.html")
    json_path = os.path.join(OUTPUT_DIR, f"{timestamp}_{post['slug']}.json")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[✓] Saved local newsletter to {html_path}", flush=True)

    if args.send or args.draft:
        send_now = args.send and not args.draft
        print(f"[*] Publishing to Brevo (send_now={send_now})...", flush=True)
        res = publish_to_brevo(
            campaign_name=f"Newsletter_{timestamp}_{post['slug']}",
            subject=subject,
            html_content=html_content,
            send_now=send_now,
        )
        if res.get("success"):
            print(f"[✓] Brevo campaign created! ID: {res.get('campaign_id')} (Sent: {res.get('sent')})", flush=True)
        else:
            print(f"[!] Brevo error: {res.get('error')}", flush=True)
    else:
        print("[*] To send or create draft on Brevo, use --draft or --send", flush=True)


if __name__ == "__main__":
    main()
