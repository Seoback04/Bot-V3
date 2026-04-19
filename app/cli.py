"""Typer CLI."""
from __future__ import annotations

import http.server
import os
import socketserver
import threading
import webbrowser
from pathlib import Path
from typing import Optional

import typer

from app.logger import get_logger
from app.services.application_service import ApplicationService
from app.services.profile_service import ProfileService
from app.services.report_service import ReportService
from config.settings import SETTINGS


log = get_logger(__name__)

app = typer.Typer(
    add_completion=False,
    help="AI Resume Job Apply Bot — parse resumes and autofill job applications.",
)


@app.command("parse-resume")
def parse_resume_cmd(
    resume: Path = typer.Option(..., "--resume", exists=True, readable=True, help="Resume PDF/DOCX/TXT"),
    out: Optional[Path] = typer.Option(None, "--out", help="Where to write the candidate profile JSON."),
) -> None:
    """Parse a resume into a structured candidate profile JSON."""
    svc = ProfileService()
    profile = svc.parse_resume(resume)
    out_path = out or (SETTINGS.output_dir / "candidate_profile.json")
    svc.save_profile(profile, out_path)
    typer.echo(f"Wrote profile: {out_path}")


@app.command("apply")
def apply_cmd(
    url: str = typer.Option(..., "--url", help="Job application URL."),
    resume: Optional[Path] = typer.Option(None, "--resume", exists=True, readable=True, help="Resume path."),
    profile_path: Optional[Path] = typer.Option(None, "--profile", exists=True, readable=True, help="Pre-parsed profile JSON."),
    submit: bool = typer.Option(False, "--submit/--no-submit", help="Attempt final submit (requires ALLOW_REAL_SUBMIT=true)."),
    headless: Optional[bool] = typer.Option(None, "--headless/--no-headless", help="Override HEADLESS env."),
) -> None:
    """Run the full apply flow: scan, map, fill, validate, screenshot."""
    if not resume and not profile_path:
        raise typer.BadParameter("Provide either --resume or --profile.")

    psvc = ProfileService()
    profile = psvc.load_profile(profile_path) if profile_path else psvc.parse_resume(resume)  # type: ignore[arg-type]
    resume_file_path = str(resume.resolve()) if resume else None

    asvc = ApplicationService()
    report = asvc.run(
        profile, url,
        submit=submit,
        resume_file_path=resume_file_path,
        headless=headless,
    )
    out = ReportService().write(report)
    typer.echo(f"Run finished. Report: {out}")
    if report.errors:
        raise typer.Exit(code=1)


@app.command("demo-local-form")
def demo_local_form_cmd(
    port: int = typer.Option(8000, "--port"),
    open_browser: bool = typer.Option(True, "--open/--no-open"),
) -> None:
    """Serve the local demo HTML form."""
    demo_dir = SETTINGS.project_root / "demo"
    if not demo_dir.exists():
        raise typer.BadParameter(f"Demo directory missing: {demo_dir}")

    os.chdir(demo_dir)
    httpd = socketserver.TCPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler)
    url = f"http://127.0.0.1:{port}/local_job_application_form.html"
    typer.echo(f"Serving {demo_dir} at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        typer.echo("Shutting down demo server.")
    finally:
        httpd.server_close()
