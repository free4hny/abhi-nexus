# agents/email_agent.py
# ─────────────────────────────────────────────
# Agent 4 — Email Agent
#
# JOB    : build and send the daily HTML digest
# INPUT  : ranked articles from ranked_articles.json
# OUTPUT : email sent to all recipients
#
# Uses Gmail SMTP with App Password.
# Never use your main Gmail password here —
# generate an App Password at:
# myaccount.google.com/apppasswords
# ─────────────────────────────────────────────

import os
import json
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from datetime             import datetime
from dotenv               import load_dotenv
import settings as settings_store

load_dotenv()
log = logging.getLogger("EmailAgent")


def _build_html(articles: list[dict]) -> str:
    """Build the HTML email digest from top 10 articles."""
    top = articles[:10]
    date_str = datetime.now().strftime("%B %d, %Y")

    # article rows
    rows = ""
    for i, a in enumerate(top):
        score = a.get("score", 0)
        score_color = (
            "#4ade80" if score >= 70 else
            "#FFD700" if score >= 40 else
            "#f87171"
        )
        summary = (
            a.get("ai_summary") or
            a.get("summary") or ""
        )[:300]
        tags = " · ".join(a.get("tags", [])[:3])

        rows += f"""
        <tr>
          <td style="padding:20px 0;
                     border-bottom:1px solid #1a1400;">
            <table width="100%" cellpadding="0"
                   cellspacing="0">
              <tr>
                <td>
                  <span style="font-family:monospace;
                               font-size:11px;
                               color:#8B6914;">
                    #{i+1} · {a.get('source','')}
                    · {a.get('category','')}
                  </span>
                </td>
                <td align="right">
                  <span style="font-family:monospace;
                               font-size:12px;
                               font-weight:700;
                               color:{score_color};">
                    {score}/100
                  </span>
                </td>
              </tr>
              <tr>
                <td colspan="2" style="padding-top:6px;">
                  <a href="{a.get('url','#')}"
                     style="font-size:16px;
                            font-weight:600;
                            color:#FFD700;
                            text-decoration:none;
                            line-height:1.4;">
                    {a.get('title','')}
                  </a>
                </td>
              </tr>
              <tr>
                <td colspan="2" style="padding-top:8px;">
                  <p style="margin:0;font-size:13px;
                             color:#c9a84c;
                             line-height:1.6;">
                    {summary}
                  </p>
                </td>
              </tr>
              {"<tr><td colspan='2' style='padding-top:6px;'><span style='font-family:monospace;font-size:10px;color:#8B6914;'>" + tags + "</span></td></tr>" if tags else ""}
            </table>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;
             background:#0a0800;
             font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#0a0800;">
  <tr>
    <td align="center" style="padding:32px 16px;">
      <table width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;">

        <!-- Header -->
        <tr>
          <td style="background:#110e00;
                     border:1px solid #8B6914;
                     border-radius:12px 12px 0 0;
                     padding:32px;
                     text-align:center;">
            <div style="font-size:32px;">🔷</div>
            <h1 style="margin:8px 0 4px;
                       font-size:24px;
                       font-weight:700;
                       color:#FFD700;
                       letter-spacing:3px;
                       font-family:monospace;">
              ABHI-NEXUS
            </h1>
            <p style="margin:0;font-size:11px;
                      color:#8B6914;
                      letter-spacing:2px;
                      font-family:monospace;">
              DAILY TECH INTELLIGENCE · {date_str}
            </p>
          </td>
        </tr>

        <!-- Articles -->
        <tr>
          <td style="background:#110e00;
                     border-left:1px solid #8B6914;
                     border-right:1px solid #8B6914;
                     padding:0 32px;">
            <table width="100%" cellpadding="0"
                   cellspacing="0">
              {rows}
            </table>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#110e00;
                     border:1px solid #8B6914;
                     border-top:none;
                     border-radius:0 0 12px 12px;
                     padding:24px 32px;
                     text-align:center;">
            <p style="margin:0;font-size:11px;
                      color:#8B6914;
                      font-family:monospace;">
              POWERED BY ABHI-NEXUS MULTI-AGENT SYSTEM
              · UNSUBSCRIBE ANYTIME
            </p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


def send_digest(recipients: list[str] = None,
                test_mode: bool = False) -> tuple[bool, str]:
    """
    Build and send the email digest.

    INPUT:
      recipients : list of email addresses
                   if None, reads from settings
      test_mode  : if True, adds [TEST] to subject

    OUTPUT:
      (success: bool, message: str)
    """
    # load settings if recipients not provided
    cfg = settings_store.load()
    if recipients is None:
        recipients = cfg.get("email_recipients", [])

    # get sender credentials from .env
    sender   = os.getenv("EMAIL_SENDER", "")
    password = os.getenv("EMAIL_PASSWORD", "")

    if not sender or not password:
        msg = "EMAIL_SENDER and EMAIL_PASSWORD not set in .env"
        log.error(msg)
        return False, msg

    if not recipients:
        msg = "No recipients configured"
        log.error(msg)
        return False, msg

    # load articles
    try:
        with open("data/ranked_articles.json") as f:
            data = json.load(f)
        articles = data.get("articles", [])
    except FileNotFoundError:
        msg = "No articles found — run pipeline first"
        log.error(msg)
        return False, msg

    if not articles:
        msg = "No articles in digest — run pipeline first"
        log.error(msg)
        return False, msg

    # build email
    date_str = datetime.now().strftime("%B %d, %Y")
    prefix   = "[TEST] " if test_mode else ""
    subject  = (
        f"{prefix}🔷 Abhi-Nexus · Daily Tech Intelligence"
        f" · {date_str}"
    )

    html_body = _build_html(articles)

    # plain text fallback
    plain = f"Abhi-Nexus Daily Digest — {date_str}\n\n"
    for i, a in enumerate(articles[:10]):
        plain += (
            f"{i+1}. {a.get('title','')}\n"
            f"   {a.get('ai_summary','')[:200]}\n"
            f"   {a.get('url','')}\n\n"
        )

    # build MIME message
    msg              = MIMEMultipart("alternative")
    msg["Subject"]   = subject
    msg["From"]      = f"Abhi-Nexus <{sender}>"
    msg["To"]        = ", ".join(recipients)

    msg.attach(MIMEText(plain,     "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # send via Gmail SMTP
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, password)
            smtp.sendmail(sender, recipients, msg.as_string())

        log.info(
            f"Email sent to {len(recipients)} recipient(s)"
        )

        # update last sent timestamp in settings
        settings_store.update(
            "last_email_sent",
            datetime.now().isoformat()
        )
        return True, f"Email sent to {', '.join(recipients)}"

    except smtplib.SMTPAuthenticationError:
        msg = (
            "Gmail auth failed. Use an App Password — "
            "myaccount.google.com/apppasswords"
        )
        log.error(msg)
        return False, msg

    except Exception as e:
        log.error(f"Email send failed: {e}")
        return False, str(e)