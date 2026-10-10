"""NexusAI Talent OS — Email Notification Service"""
import asyncio, logging, smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

BRAND = "#0A66C2"
BG = "#F3F6F8"

def _base_html(title: str, body: str) -> str:
    return f"""<!DOCTYPE html><html><body style="font-family:Inter,Arial,sans-serif;background:{BG};padding:32px 16px;margin:0">
<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;border:1px solid #E5E7EB">
  <div style="background:{BRAND};padding:24px 32px;display:flex;align-items:center;gap:12px">
    <div style="width:32px;height:32px;background:rgba(255,255,255,0.2);border-radius:6px;display:flex;align-items:center;justify-content:center">
      <span style="color:#fff;font-size:16px">⚡</span>
    </div>
    <div>
      <div style="color:#fff;font-weight:700;font-size:15px">NexusAI Talent OS</div>
      <div style="color:rgba(255,255,255,0.75);font-size:11px">Intelligent Hiring Platform</div>
    </div>
  </div>
  <div style="padding:32px">{body}</div>
  <div style="background:{BG};padding:16px 32px;border-top:1px solid #E5E7EB">
    <p style="margin:0;font-size:11px;color:#9CA3AF;text-align:center">
      © {datetime.utcnow().year} NexusAI · This is an automated message
    </p>
  </div>
</div></body></html>"""

async def send_shortlist_notification(application_id: str):
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.models import Application, Candidate, Job, Tenant
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            app = await db.get(Application, application_id)
            if not app: return
            cand = await db.get(Candidate, app.candidate_id)
            job  = await db.get(Job, app.job_id)
            tenant = await db.get(Tenant, app.org_id)
            if not cand or not job: return
        body = f"""
<h1 style="font-size:22px;font-weight:700;color:#111827;margin:0 0 8px">Great news, {cand.full_name.split()[0]}! 🎉</h1>
<p style="color:#6B7280;margin:0 0 24px;font-size:14px">You've been shortlisted for an interview</p>
<div style="background:{BG};border-radius:8px;padding:20px;margin:0 0 24px">
  <div style="font-size:13px;color:#6B7280;margin-bottom:4px">Position</div>
  <div style="font-size:16px;font-weight:600;color:#111827">{job.title}</div>
  <div style="font-size:13px;color:#6B7280;margin-top:8px">{tenant.name if tenant else 'NexusAI'}</div>
</div>
<p style="color:#374151;line-height:1.6;font-size:14px">
  Congratulations! Your profile has been reviewed and you've been shortlisted. 
  You'll receive a separate email with instructions to schedule your AI-powered interview.
</p>
<div style="background:#EFF6FF;border-left:3px solid {BRAND};padding:16px;border-radius:0 6px 6px 0;margin:20px 0">
  <p style="margin:0;font-size:13px;color:#1E40AF">
    💡 <strong>What's next:</strong> Watch for a scheduling link in your inbox to book your interview slot.
  </p>
</div>"""
        await _send(cand.email, f"You've been shortlisted — {job.title} at {tenant.name if tenant else 'NexusAI'}", _base_html("Shortlisted!", body))
    except Exception as e:
        logger.error(f"Shortlist notification failed: {e}")

async def send_schedule_invite_email(interview_id: str, schedule_link: str):
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.models import Interview, Candidate, Job, Tenant
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            iv = await db.get(Interview, interview_id)
            if not iv: return
            cand = await db.get(Candidate, iv.candidate_id)
            job  = await db.get(Job, iv.job_id)
            tenant = await db.get(Tenant, iv.org_id)
        body = f"""
<h1 style="font-size:22px;font-weight:700;color:#111827;margin:0 0 8px">Schedule Your Interview 📅</h1>
<p style="color:#6B7280;margin:0 0 24px;font-size:14px">Pick a time that works best for you</p>
<div style="background:{BG};border-radius:8px;padding:20px;margin:0 0 24px">
  <div style="font-size:13px;color:#6B7280;margin-bottom:4px">Position</div>
  <div style="font-size:16px;font-weight:600;color:#111827">{job.title if job else 'Open Position'}</div>
  <div style="font-size:13px;color:#6B7280;margin-top:8px">{tenant.name if tenant else 'NexusAI'}</div>
</div>
<p style="color:#374151;line-height:1.6;font-size:14px">
  Hi {cand.full_name.split()[0] if cand else 'there'}, please use the link below to select your preferred interview slot.
  The interview is conducted by an AI and takes approximately 45–60 minutes.
</p>
<a href="{schedule_link}" style="display:inline-block;margin:24px 0;padding:14px 28px;background:{BRAND};color:#fff;text-decoration:none;border-radius:24px;font-weight:600;font-size:15px">
  Choose Your Interview Slot →
</a>
<div style="background:{BG};border-radius:8px;padding:16px;margin-top:8px">
  <p style="margin:0;font-size:12px;color:#6B7280">
    🎙 Voice-based AI interview · 📊 Real-time assessment · ⏱ ~45-60 minutes<br>
    Ensure you have a working microphone and are in a quiet environment.
  </p>
</div>"""
        await _send(cand.email if cand else "", f"Schedule your interview — {job.title if job else 'Open Position'}", _base_html("Schedule Interview", body))
    except Exception as e:
        logger.error(f"Schedule invite failed: {e}")

async def send_interview_confirmation(interview_id: str):
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.models import Interview, Candidate, Job, Tenant, InterviewSlot
        async with AsyncSessionLocal() as db:
            iv = await db.get(Interview, interview_id)
            if not iv: return
            cand = await db.get(Candidate, iv.candidate_id)
            job  = await db.get(Job, iv.job_id)
            tenant = await db.get(Tenant, iv.org_id)
            slot = await db.get(InterviewSlot, iv.slot_id) if iv.slot_id else None
        interview_link = f"{settings.APP_BASE_URL}/interview/{iv.token}"
        slot_time = iv.scheduled_at.strftime('%A, %B %d, %Y at %I:%M %p UTC') if iv.scheduled_at else "TBD"
        body = f"""
<h1 style="font-size:22px;font-weight:700;color:#111827;margin:0 0 8px">Interview Confirmed ✅</h1>
<p style="color:#6B7280;margin:0 0 24px;font-size:14px">Your interview is scheduled</p>
<div style="background:{BG};border-radius:8px;padding:20px;margin:0 0 24px">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
    <div><div style="font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.05em">Position</div>
    <div style="font-size:14px;font-weight:600;color:#111827;margin-top:2px">{job.title if job else 'Open Position'}</div></div>
    <div><div style="font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.05em">Date & Time</div>
    <div style="font-size:14px;font-weight:600;color:#111827;margin-top:2px">{slot_time}</div></div>
  </div>
</div>
<a href="{interview_link}" style="display:inline-block;margin:8px 0 24px;padding:14px 28px;background:{BRAND};color:#fff;text-decoration:none;border-radius:24px;font-weight:600;font-size:15px">
  Join Interview Room →
</a>
<div style="background:#F0FDF4;border-left:3px solid #057642;padding:16px;border-radius:0 6px 6px 0">
  <p style="margin:0;font-size:13px;color:#14532D;font-weight:600">Tips for your interview:</p>
  <ul style="margin:8px 0 0;padding-left:16px;font-size:13px;color:#374151">
    <li>Find a quiet, well-lit space</li>
    <li>Test your microphone beforehand</li>
    <li>Have water nearby</li>
    <li>Speak clearly and take your time</li>
  </ul>
</div>"""
        await _send(cand.email if cand else "", f"Interview confirmed — {job.title if job else 'Open Position'}", _base_html("Confirmed!", body))
    except Exception as e:
        logger.error(f"Confirmation email failed: {e}")

async def send_evaluation_report_email(ev, iv, cand, job):
    try:
        if not cand or not job: return
        from app.core.database import AsyncSessionLocal
        from app.models.models import User
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            recruiter = await db.scalar(select(User).where(User.org_id == iv.org_id).limit(1))
            if not recruiter: return
        rec_color = {"Strong Hire":"#057642","Hire":"#0A66C2","Maybe":"#B45309","No Hire":"#B91C1C"}.get(ev.recommendation,"#6B7280")
        report_link = f"{settings.APP_BASE_URL}/admin/reports/{iv.id}"
        body = f"""
<h1 style="font-size:20px;font-weight:700;color:#111827;margin:0 0 4px">Interview Evaluation Report</h1>
<p style="color:#6B7280;margin:0 0 24px;font-size:13px">{cand.full_name} · {job.title}</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:24px">
  <div style="background:{BG};border-radius:8px;padding:20px;text-align:center">
    <div style="font-size:40px;font-weight:800;color:#111827">{ev.overall_score:.0f}</div>
    <div style="font-size:12px;color:#6B7280;margin-top:2px">/ 100 Overall Score</div>
  </div>
  <div style="background:{rec_color}15;border:1px solid {rec_color}40;border-radius:8px;padding:20px;text-align:center">
    <div style="font-size:18px;font-weight:700;color:{rec_color}">{ev.recommendation}</div>
    <div style="font-size:12px;color:#6B7280;margin-top:4px">Recommendation</div>
  </div>
</div>
<div style="margin-bottom:20px">
  <div style="font-size:13px;font-weight:600;color:#111827;margin-bottom:8px">Executive Summary</div>
  <p style="color:#374151;font-size:13px;line-height:1.6;margin:0">{ev.executive_summary or 'No summary available'}</p>
</div>
<a href="{report_link}" style="display:inline-block;padding:14px 28px;background:{BRAND};color:#fff;text-decoration:none;border-radius:24px;font-weight:600;font-size:15px">
  View Full Report →
</a>"""
        await _send(recruiter.email, f"Interview Report: {cand.full_name} — {ev.recommendation}", _base_html("Report Ready", body))
    except Exception as e:
        logger.error(f"Report email failed: {e}")

async def _send(to: str, subject: str, html: str):
    if not settings.EMAIL_ENABLED or not settings.SMTP_USERNAME:
        logger.info(f"[EMAIL DISABLED] Would send to {to}: {subject}")
        return
    if not to:
        return
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_sync, to, subject, html)

def _send_sync(to: str, subject: str, html: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg["To"]      = to
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as smtp:
            smtp.ehlo(); smtp.starttls()
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.sendmail(settings.EMAIL_FROM, [to], msg.as_string())
        logger.info(f"Email sent to {to}: {subject}")
    except Exception as e:
        logger.error(f"SMTP error to {to}: {e}")
