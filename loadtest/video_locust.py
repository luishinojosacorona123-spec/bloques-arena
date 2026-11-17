"""Muestra HLS real: usar solo con un origen/CDN propio y presupuesto revisado."""
import os,time
from locust import HttpUser,task,between
class VideoViewer(HttpUser):
    wait_time=between(2,2)
    @task
    def video(self):
        with self.client.get(os.getenv('HLS_PATH','/sample/index.m3u8'),catch_response=True,name='HLS manifest') as r:
            if r.status_code!=200 or '#EXTM3U' not in r.text:
                r.failure('No es una lista HLS'); return
            lines=[x.strip() for x in r.text.splitlines() if x.strip() and not x.startswith('#')]
            if not lines: r.failure('Sin segmentos'); return
            # Requiere media playlist (no master) y URL relativa al manifiesto.
            from urllib.parse import urljoin
            segment=urljoin(r.url,lines[int(time.time()/2)%len(lines)])
        self.client.get(segment,name='HLS segment')
