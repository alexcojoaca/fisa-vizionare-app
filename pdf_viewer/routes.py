"""
PDF Viewer Blueprint - Provides a wrapper page for viewing PDFs with toolbar
to fix PWA standalone mode UX issue on iOS.
"""
from urllib.parse import urlencode, quote_plus
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    abort,
    send_file,
)
from flask_login import login_required, current_user

from access_control import access_required, agent_required
from extensions import db
from models import ChirieRemoteSigning, VanzareRemoteSigning

from . import pdf_viewer_bp


def get_tmp_dir():
    """Get temporary directory for PDFs."""
    from pathlib import Path
    tmp_dir = Path(current_app.root_path) / "static" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir


@pdf_viewer_bp.route("/view")
@login_required
@agent_required
@access_required
def view_pdf():
    """
    Universal PDF viewer page with toolbar.
    
    Query params:
    - url: Direct PDF URL (encoded)
    - kind: PDF type (chirie, vanzare, contract, prestari)
    - id: Document ID (for regular PDFs)
    - type: Remote type (chirie/vanzare) for remote PDFs
    - token: Remote token (for remote PDFs)
    - next: Fallback URL for back button (defaults to menu)
    - action: 'download' to auto-trigger download (optional)
    """
    auto_download = request.args.get("action") == "download"
    # Option 1: Direct URL provided
    pdf_url = request.args.get("url")
    if pdf_url:
        try:
            # Decode URL if needed
            pdf_url = pdf_url
        except Exception:
            flash("URL PDF invalid.", "error")
            return redirect(url_for("menu.menu_home"))
        
        download_url = pdf_url
        back_url = request.args.get("next") or url_for("menu.menu_home")
        return render_template(
            "pdf_viewer.html",
            pdf_url=pdf_url,
            download_url=download_url,
            back_url=back_url,
            title="Vizualizare PDF",
            auto_download=auto_download
        )
    
    # Option 2: Kind + ID (regular PDFs)
    kind = request.args.get("kind", "").strip().lower()
    doc_id = request.args.get("id", "").strip()
    
    if kind and doc_id:
        # Build PDF URL based on kind
        if kind == "chirie":
            pdf_url = url_for("chirie.view_pdf", doc_id=doc_id, _external=True)
            download_url = url_for("chirie.download_pdf", doc_id=doc_id, _external=True)
            back_url = request.args.get("next") or url_for("chirie.form_page")
        elif kind == "vanzare":
            pdf_url = url_for("vanzare.view_pdf", doc_id=doc_id, _external=True)
            download_url = url_for("vanzare.download_pdf", doc_id=doc_id, _external=True)
            back_url = request.args.get("next") or url_for("vanzare.form_page")
        elif kind == "contract":
            pdf_url = url_for("contract.view_pdf", doc_id=doc_id, _external=True)
            download_url = url_for("contract.download_pdf", doc_id=doc_id, _external=True)
            back_url = request.args.get("next") or url_for("contract.form_page")
        elif kind == "prestari":
            pdf_url = url_for("prestari.view_pdf", doc_id=doc_id, _external=True)
            download_url = url_for("prestari.download_pdf", doc_id=doc_id, _external=True)
            back_url = request.args.get("next") or url_for("prestari.form_page")
        else:
            flash("Tip PDF invalid.", "error")
            return redirect(url_for("menu.menu_home"))
        
        # Verify PDF exists
        tmp_dir = get_tmp_dir()
        if kind == "vanzare":
            pdf_path = tmp_dir / f"vanzare-{doc_id}.pdf"
        else:
            pdf_path = tmp_dir / f"{doc_id}.pdf"
        
        if not pdf_path.exists():
            flash("PDF inexistent.", "error")
            return redirect(back_url)
        
        title_map = {
            "chirie": "Fișă de vizionare - Închiriere",
            "vanzare": "Fișă de vizionare - Vânzare",
            "contract": "Contract de închiriere",
            "prestari": "Contract prestări servicii",
        }
        title = title_map.get(kind, "Vizualizare PDF")
        
        return render_template(
            "pdf_viewer.html",
            pdf_url=pdf_url,
            download_url=download_url,
            back_url=back_url,
            title=title,
            auto_download=auto_download
        )
    
    # Option 3: Remote PDF (type + token)
    remote_type = request.args.get("type", "").strip().lower()
    token = request.args.get("token", "").strip()
    
    if remote_type and token:
        # Verify token and get PDF
        if remote_type == "chirie":
            rec = ChirieRemoteSigning.query.filter_by(
                public_token=token,
                user_id=current_user.id
            ).first()
            if not rec or not rec.pdf_doc_id:
                flash("PDF inexistent sau neautorizat.", "error")
                return redirect(url_for("chirie.remote_list"))
            
            tmp_dir = get_tmp_dir()
            # Remote chirie PDFs: pdf_doc_id = "remote-{doc_id}", file = "remote-{doc_id}.pdf"
            pdf_path = tmp_dir / f"{rec.pdf_doc_id}.pdf"
            if not pdf_path.exists():
                flash("PDF inexistent.", "error")
                return redirect(url_for("chirie.remote_list"))
            
            # For remote PDFs, we need to serve them directly since view_pdf expects different pattern
            # Use the download route but serve inline, or create direct URL
            # Actually, we'll use a direct URL to the PDF file via a special route or use the download route
            # For now, let's use the download route URL but we'll need to modify it to serve inline
            # Better: serve PDF directly in the viewer using send_file
            from flask import send_file
            # We'll serve it inline in the iframe, so we need a route that serves it inline
            # For now, use the download URL but note that it will download - we'll fix this
            # Actually, let's create a direct inline serving approach
            pdf_url = url_for("pdf_viewer.serve_pdf_inline", kind="remote", type="chirie", token=token, _external=True)
            download_url = url_for("chirie.remote_download_pdf", token=token, _external=True)
            back_url = request.args.get("next") or url_for("chirie.remote_list")
            title = "Fișă de vizionare - Închiriere (Semnată)"
            
        elif remote_type == "vanzare":
            rec = VanzareRemoteSigning.query.filter_by(
                public_token=token,
                user_id=current_user.id
            ).first()
            if not rec or not rec.pdf_doc_id:
                flash("PDF inexistent sau neautorizat.", "error")
                return redirect(url_for("chirie.remote_list"))  # Shared list
            
            tmp_dir = get_tmp_dir()
            # Remote vanzare PDFs: pdf_doc_id = "remote-vanzare-{doc_id}", file = "remote-vanzare-{doc_id}.pdf"
            pdf_path = tmp_dir / f"{rec.pdf_doc_id}.pdf"
            if not pdf_path.exists():
                flash("PDF inexistent.", "error")
                return redirect(url_for("chirie.remote_list"))
            
            # For remote PDFs, serve them inline via our own route
            pdf_url = url_for("pdf_viewer.serve_pdf_inline", type="vanzare", token=token, _external=True)
            download_url = url_for("vanzare.remote_download_pdf", token=token, _external=True)
            back_url = request.args.get("next") or url_for("chirie.remote_list")
            title = "Fișă de vizionare - Vânzare (Semnată)"
        else:
            flash("Tip remote invalid.", "error")
            return redirect(url_for("menu.menu_home"))
        
        return render_template(
            "pdf_viewer.html",
            pdf_url=pdf_url,
            download_url=download_url,
            back_url=back_url,
            title=title,
            auto_download=auto_download
        )
    
    # No valid params
    flash("Parametri invalizi pentru vizualizare PDF.", "error")
    return redirect(url_for("menu.menu_home"))


@pdf_viewer_bp.route("/inline")
@login_required
@agent_required
@access_required
def serve_pdf_inline():
    """
    Serve remote PDFs inline (for iframe embedding).
    Used for remote signed PDFs that have different file naming patterns.
    """
    remote_type = request.args.get("type", "").strip().lower()
    token = request.args.get("token", "").strip()
    
    if not remote_type or not token:
        abort(400)
    
    tmp_dir = get_tmp_dir()
    
    if remote_type == "chirie":
        rec = ChirieRemoteSigning.query.filter_by(
            public_token=token,
            user_id=current_user.id
        ).first()
        if not rec or not rec.pdf_doc_id:
            abort(404)
        
        pdf_path = tmp_dir / f"{rec.pdf_doc_id}.pdf"
        if not pdf_path.exists():
            abort(404)
        
        download_name = "fisa-vizionare-chirie.pdf"
        
    elif remote_type == "vanzare":
        rec = VanzareRemoteSigning.query.filter_by(
            public_token=token,
            user_id=current_user.id
        ).first()
        if not rec or not rec.pdf_doc_id:
            abort(404)
        
        pdf_path = tmp_dir / f"{rec.pdf_doc_id}.pdf"
        if not pdf_path.exists():
            abort(404)
        
        download_name = "fisa-vizionare-vanzare.pdf"
    else:
        abort(400)
    
    resp = send_file(
        pdf_path,
        as_attachment=False,
        mimetype="application/pdf",
        download_name=download_name,
        conditional=True,
        max_age=0,
    )
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp
