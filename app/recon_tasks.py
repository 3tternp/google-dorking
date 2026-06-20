"""
Celery tasks for passive recon (subdomain enumeration).
Separate from the Google dorking tasks.
"""
from app.tasks import celery_app
from app.recon_engine import enumerate_subdomains
from datetime import datetime


@celery_app.task(bind=True, name="app.tasks.run_subdomain_enum")
def run_subdomain_enum(self, domain: str, brute_force: bool = True):
    self.update_state(state='PROGRESS', meta={
        'status': f'Starting passive subdomain enumeration for {domain}…',
        'current': 0, 'total': 5,
    })

    result = enumerate_subdomains(domain, brute_force=brute_force)

    return {'status': 'completed', 'data': result}
