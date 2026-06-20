"""
Flask Routes — Dorking + Passive Recon
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from app.tasks import execute_dorking_scan, test_connection
from app.dorking_queries import get_all_categories, count_queries
from celery.result import AsyncResult
import json, csv, html as html_lib
from io import StringIO, BytesIO
from datetime import datetime

main_bp = Blueprint('main', __name__)
api_bp  = Blueprint('api',  __name__)

# ── Web routes ───────────────────────────────────────────────────────────────

@main_bp.route('/')
def index():
    categories  = get_all_categories()
    query_count = count_queries()
    return render_template('index.html',
                           categories=categories,
                           total_queries=query_count['total'],
                           per_category=query_count['per_category'])

@main_bp.route('/results/<task_id>')
def view_results(task_id):
    return render_template('results.html', task_id=task_id)

@main_bp.route('/recon/<task_id>')
def view_recon(task_id):
    return render_template('recon.html', task_id=task_id)

@main_bp.route('/help')
def help_page():
    return render_template('help.html')

# ── Dorking API ───────────────────────────────────────────────────────────────

@api_bp.route('/categories', methods=['GET'])
def get_categories():
    categories  = get_all_categories()
    query_count = count_queries()
    return jsonify({'status':'success','categories':categories,
                    'total_queries':query_count['total'],
                    'per_category':query_count['per_category']}), 200

@api_bp.route('/start-scan', methods=['POST'])
def start_scan():
    try:
        data = request.get_json()
        if not data or 'domain' not in data:
            return jsonify({'status':'error','message':'Domain is required'}), 400
        domain     = data['domain'].strip()
        categories = data.get('categories', None)
        if not domain or len(domain) < 3:
            return jsonify({'status':'error','message':'Invalid domain format'}), 400
        task = execute_dorking_scan.delay(domain, categories)
        return jsonify({'status':'started','task_id':task.id,
                        'message':f'Dorking scan started for {domain}',
                        'domain':domain,
                        'categories': categories if categories else 'all'}), 202
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@api_bp.route('/scan-status/<task_id>', methods=['GET'])
def get_scan_status(task_id):
    try:
        tr = AsyncResult(task_id)
        resp = {'task_id': task_id, 'status': tr.status}
        if tr.status == 'PENDING':
            resp.update({'progress':0, 'message':'Task is pending…'})
        elif tr.status == 'PROGRESS':
            info = tr.info or {}
            resp.update({'progress':info.get('current',0),'total':info.get('total',0),
                         'message':info.get('status',''),'current_query':info.get('current_query','')})
        elif tr.status == 'SUCCESS':
            resp.update({'progress':100,'message':'Scan completed','data':tr.result.get('data',{})})
        elif tr.status == 'FAILURE':
            resp.update({'message':'Scan failed','error':str(tr.info)})
        return jsonify(resp), 200
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@api_bp.route('/scan-results/<task_id>', methods=['GET'])
def get_scan_results(task_id):
    try:
        tr = AsyncResult(task_id)
        if tr.status != 'SUCCESS':
            return jsonify({'status':'error','message':f'Task status is {tr.status}'}), 400
        return jsonify({'status':'success','results':tr.result.get('data',{})}), 200
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@api_bp.route('/export-results/<task_id>', methods=['GET'])
def export_results(task_id):
    try:
        fmt = request.args.get('format','json').lower()
        tr  = AsyncResult(task_id)
        if tr.status != 'SUCCESS':
            return jsonify({'status':'error','message':'Scan not completed yet'}), 400
        results   = tr.result.get('data', {})
        domain    = results.get('domain','unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if fmt == 'json':
            buf = BytesIO(json.dumps(results, indent=2, default=str).encode('utf-8'))
            buf.seek(0)
            return send_file(buf, mimetype='application/json', as_attachment=True,
                             download_name=f'dorking_{domain}_{timestamp}.json')
        elif fmt == 'csv':
            sb = StringIO()
            w  = csv.writer(sb)
            w.writerow(['Category','Query','Status','Results Count','Result URLs'])
            for cat, queries in results.get('results_by_category',{}).items():
                for q in queries:
                    urls = ' | '.join(r.get('url','') for r in q.get('results',[]) if r.get('url') and 'google.com' not in r.get('url',''))
                    w.writerow([cat, q.get('query',''), q.get('status','unknown'), len(q.get('results',[])), urls])
            buf = BytesIO(sb.getvalue().encode('utf-8'))
            buf.seek(0)
            return send_file(buf, mimetype='text/csv', as_attachment=True,
                             download_name=f'dorking_{domain}_{timestamp}.csv')
        elif fmt == 'html':
            html_content = _render_html_report(results)
            buf = BytesIO(html_content.encode('utf-8'))
            buf.seek(0)
            return send_file(buf, mimetype='text/html', as_attachment=True,
                             download_name=f'dorking_{domain}_{timestamp}.html')
        elif fmt == 'pdf':
            pdf_buf = _render_pdf_report(results)
            return send_file(pdf_buf, mimetype='application/pdf', as_attachment=True,
                             download_name=f'dorking_{domain}_{timestamp}.pdf')
        else:
            return jsonify({'status':'error','message':'Use json, csv, html, or pdf'}), 400
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

# ── Passive Recon API ─────────────────────────────────────────────────────────

@api_bp.route('/start-recon', methods=['POST'])
def start_recon():
    """Start passive subdomain enumeration (no Google needed)."""
    try:
        from app.recon_tasks import run_subdomain_enum
        data = request.get_json()
        if not data or 'domain' not in data:
            return jsonify({'status':'error','message':'Domain is required'}), 400
        domain      = data['domain'].strip()
        brute_force = data.get('brute_force', True)
        if not domain or len(domain) < 3:
            return jsonify({'status':'error','message':'Invalid domain format'}), 400
        task = run_subdomain_enum.delay(domain, brute_force)
        return jsonify({'status':'started','task_id':task.id,
                        'message':f'Subdomain enumeration started for {domain}',
                        'domain': domain}), 202
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@api_bp.route('/recon-status/<task_id>', methods=['GET'])
def get_recon_status(task_id):
    try:
        tr   = AsyncResult(task_id)
        resp = {'task_id': task_id, 'status': tr.status}
        if tr.status == 'PENDING':
            resp.update({'progress':0,'message':'Waiting…'})
        elif tr.status == 'PROGRESS':
            info = tr.info or {}
            resp.update({'message':info.get('status',''),'current':info.get('current',0),'total':info.get('total',5)})
        elif tr.status == 'SUCCESS':
            resp.update({'message':'Completed','data':tr.result.get('data',{})})
        elif tr.status == 'FAILURE':
            resp.update({'message':'Failed','error':str(tr.info)})
        return jsonify(resp), 200
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@api_bp.route('/export-recon/<task_id>', methods=['GET'])
def export_recon(task_id):
    try:
        fmt = request.args.get('format','json').lower()
        tr  = AsyncResult(task_id)
        if tr.status != 'SUCCESS':
            return jsonify({'status':'error','message':'Recon not completed yet'}), 400
        data      = tr.result.get('data', {})
        domain    = data.get('domain','unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if fmt == 'json':
            buf = BytesIO(json.dumps(data, indent=2, default=str).encode('utf-8'))
            buf.seek(0)
            return send_file(buf, mimetype='application/json', as_attachment=True,
                             download_name=f'subdomains_{domain}_{timestamp}.json')
        elif fmt == 'csv':
            sb = StringIO()
            w  = csv.writer(sb)
            w.writerow(['Subdomain','IP','Source','Extra'])
            for s in data.get('subdomains',[]):
                w.writerow([s.get('subdomain',''), s.get('ip',''), s.get('source',''), s.get('extra','')])
            buf = BytesIO(sb.getvalue().encode('utf-8'))
            buf.seek(0)
            return send_file(buf, mimetype='text/csv', as_attachment=True,
                             download_name=f'subdomains_{domain}_{timestamp}.csv')
        else:
            return jsonify({'status':'error','message':'Use json or csv'}), 400
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

# ── Export helpers ───────────────────────────────────────────────────────────

def _render_html_report(results: dict) -> str:
    domain    = results.get('domain', 'unknown')
    scan_date = results.get('scan_date', '')
    stats     = results.get('statistics', {})
    cats      = results.get('results_by_category', {})

    def esc(s): return html_lib.escape(str(s))

    findings_total = sum(
        1 for qs in cats.values() for q in qs
        if q.get('results') and any('google.com' not in r.get('url','') for r in q['results'])
    )

    rows = ''
    for cat, queries in cats.items():
        for q in queries:
            real = [r for r in q.get('results', []) if r.get('url') and 'google.com' not in r['url']]
            status = 'BLOCKED' if q.get('blocked') else ('FOUND' if real else 'EMPTY')
            urls_html = ''.join(
                f'<div style="margin:2px 0"><a href="{esc(r["url"])}" style="color:#0066cc">{esc(r["url"])}</a></div>'
                for r in real
            ) or (f'<a href="{esc(q.get("url","#"))}" style="color:#e67e00">Open in Google ↗</a>' if q.get('blocked') else '—')
            color = '#1a7a1a' if status=='FOUND' else ('#cc6600' if status=='BLOCKED' else '#666')
            rows += f'''
            <tr>
                <td style="color:#555;font-size:12px">{esc(cat)}</td>
                <td style="font-family:monospace;font-size:11px;word-break:break-all">{esc(q.get("query",""))}</td>
                <td><span style="color:{color};font-weight:700;font-size:11px">{status}</span></td>
                <td style="font-size:12px">{urls_html}</td>
            </tr>'''

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Dorking Report — {esc(domain)}</title>
<style>
  body{{font-family:Arial,sans-serif;margin:0;padding:24px;background:#f5f7fa;color:#222}}
  h1{{color:#1a1a2e;margin-bottom:4px}} .meta{{color:#666;font-size:13px;margin-bottom:24px}}
  .stats{{display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap}}
  .stat{{background:#fff;border-radius:8px;padding:14px 20px;border:1px solid #dde;min-width:120px}}
  .stat-val{{font-size:28px;font-weight:700;color:#1a1a2e}} .stat-lbl{{font-size:11px;color:#888;text-transform:uppercase}}
  table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
  th{{background:#1a1a2e;color:#fff;padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase}}
  td{{padding:9px 12px;border-bottom:1px solid #eef;vertical-align:top}}
  tr:last-child td{{border-bottom:none}} tr:hover td{{background:#f9fbff}}
  .notice{{background:#fff8e1;border:1px solid #ffe082;border-radius:6px;padding:12px 16px;margin-bottom:20px;font-size:13px}}
</style></head><body>
<h1>Google Dorking Report</h1>
<div class="meta">Target: <strong>{esc(domain)}</strong> &nbsp;·&nbsp; Scan date: {esc(scan_date)}</div>
<div class="notice">⚠ For authorized security testing only. All results require manual verification.</div>
<div class="stats">
  <div class="stat"><div class="stat-val">{stats.get("total_queries",0)}</div><div class="stat-lbl">Queries</div></div>
  <div class="stat"><div class="stat-val" style="color:#1a7a1a">{findings_total}</div><div class="stat-lbl">Findings</div></div>
  <div class="stat"><div class="stat-val" style="color:#cc6600">{stats.get("failed_queries",0)}</div><div class="stat-lbl">Blocked</div></div>
  <div class="stat"><div class="stat-val">{stats.get("success_rate",0)}%</div><div class="stat-lbl">Success rate</div></div>
</div>
<table>
<thead><tr><th>Category</th><th>Query</th><th>Status</th><th>Results / URL</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p style="margin-top:24px;font-size:12px;color:#aaa;text-align:center">
Generated by Google Dorking Tool · {esc(scan_date)}
</p>
</body></html>'''


def _render_pdf_report(results: dict) -> BytesIO:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )

    buf    = BytesIO()
    domain = results.get('domain', 'unknown')
    date   = results.get('scan_date', '')
    stats  = results.get('statistics', {})
    cats   = results.get('results_by_category', {})

    doc  = SimpleDocTemplate(buf, pagesize=A4,
                              leftMargin=1.8*cm, rightMargin=1.8*cm,
                              topMargin=2*cm, bottomMargin=2*cm)
    base = getSampleStyleSheet()

    title_style = ParagraphStyle('title', parent=base['Title'],
                                  fontSize=20, textColor=colors.HexColor('#1a1a2e'), spaceAfter=4)
    h2_style    = ParagraphStyle('h2', parent=base['Heading2'],
                                  fontSize=12, textColor=colors.HexColor('#1a1a2e'), spaceBefore=14, spaceAfter=4)
    body_style  = ParagraphStyle('body', parent=base['Normal'],
                                  fontSize=8.5, leading=13, textColor=colors.HexColor('#333'))
    url_style   = ParagraphStyle('url', parent=base['Normal'],
                                  fontSize=7.5, leading=11, textColor=colors.HexColor('#0066cc'),
                                  wordWrap='CJK')
    warn_style  = ParagraphStyle('warn', parent=base['Normal'],
                                  fontSize=8, textColor=colors.HexColor('#b26a00'), backColor=colors.HexColor('#fff8e1'))

    story = []
    story.append(Paragraph('Google Dorking Report', title_style))
    story.append(Paragraph(f'Target: <b>{domain}</b> &nbsp; Scan date: {date}', body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph('⚠ For authorized security testing only. All results require manual verification.', warn_style))
    story.append(Spacer(1, 14))

    # Summary stats table
    findings_total = sum(
        1 for qs in cats.values() for q in qs
        if q.get('results') and any('google.com' not in r.get('url','') for r in q['results'])
    )
    stat_data = [
        ['Queries Run', 'Findings', 'Blocked', 'Success Rate'],
        [
            str(stats.get('total_queries', 0)),
            str(findings_total),
            str(stats.get('failed_queries', 0)),
            f"{stats.get('success_rate', 0)}%",
        ]
    ]
    stat_tbl = Table(stat_data, colWidths=[4*cm]*4)
    stat_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f5f7fa'), colors.white]),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#dde')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(stat_tbl)
    story.append(Spacer(1, 18))
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#ccd')))

    # Per-category results
    for cat, queries in cats.items():
        has_findings = any(
            q.get('results') and any('google.com' not in r.get('url','') for r in q['results'])
            for q in queries
        )
        story.append(Paragraph(cat.replace('_',' ').title(), h2_style))

        tbl_data = [['Query', 'Status', 'Findings']]
        for q in queries:
            real = [r for r in q.get('results', []) if r.get('url') and 'google.com' not in r['url']]
            status = 'BLOCKED' if q.get('blocked') else ('FOUND' if real else 'EMPTY')
            urls = '\n'.join(r['url'] for r in real) if real else (q.get('url','') if q.get('blocked') else '—')
            tbl_data.append([
                Paragraph(q.get('query',''), ParagraphStyle('qp', parent=body_style, fontSize=7.5, wordWrap='CJK')),
                status,
                Paragraph(urls, url_style),
            ])

        col_w = [doc.width * 0.50, doc.width * 0.12, doc.width * 0.38]
        tbl = Table(tbl_data, colWidths=col_w, repeatRows=1)

        status_colors = {'FOUND': colors.HexColor('#1a7a1a'), 'BLOCKED': colors.HexColor('#cc6600'), 'EMPTY': colors.HexColor('#888')}
        row_styles = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2d3561')),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 7.5),
            ('GRID',       (0,0), (-1,-1), 0.4, colors.HexColor('#dde')),
            ('VALIGN',     (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f9fbff'), colors.white]),
        ]
        for i, row in enumerate(tbl_data[1:], 1):
            s = row[1]
            if s in status_colors:
                row_styles.append(('TEXTCOLOR', (1,i), (1,i), status_colors[s]))
                row_styles.append(('FONTNAME',  (1,i), (1,i), 'Helvetica-Bold'))
        tbl.setStyle(TableStyle(row_styles))
        story.append(tbl)
        story.append(Spacer(1, 6))

    doc.build(story)
    buf.seek(0)
    return buf


# ── Utility ───────────────────────────────────────────────────────────────────

@api_bp.route('/test-connection', methods=['GET'])
def test_celery_connection():
    try:
        task = test_connection.delay()
        return jsonify({'status':'ok','message':'Celery connection successful','task_id':task.id}), 200
    except Exception as e:
        return jsonify({'status':'error','message':f'Celery connection failed: {str(e)}'}), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status':'healthy','service':'Google Dorking Tool',
                    'timestamp':datetime.now().isoformat()}), 200
