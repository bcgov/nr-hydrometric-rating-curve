from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import render

try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False
    pisa = None

def render_to_pdf(template_src, context_dict={}):
    if not XHTML2PDF_AVAILABLE:
        raise ImportError("xhtml2pdf is required for PDF export. Install with: pip install rctool[pdf]")
    print('generating pdf from utils...')
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None
