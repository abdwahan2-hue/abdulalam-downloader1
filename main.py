from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import yt_dlp
import uuid
from pathlib import Path
import os
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str
    quality: str = "best"
    audio_only: bool = False

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
def home():
    return {
        "message": "✅ Abdulalam Downloader - يدعم جميع المنصات!",
        "status": "ok",
        "supported_sites": "YouTube, TikTok, Instagram, Snapchat, Twitter, Facebook, Reddit, وغيرها 1000+ موقع"
    }

@app.get("/api/healthz")
def health():
    return {"status": "ok"}

@app.post("/api/get-info")
async def get_info(request: VideoRequest):
    try:
        # قبول أي رابط بدون تحقق مسبق
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:            info = ydl.extract_info(request.url, download=False)
            
            # جلب جميع الجودات المتاحة
            formats = []
            seen_resolutions = set()
            
            for f in info.get('formats', []):
                resolution = f.get('height') or f.get('width')
                if resolution and resolution not in seen_resolutions:
                    seen_resolutions.add(resolution)
                    formats.append({
                        'format_id': f.get('format_id', ''),
                        'resolution': f"{resolution}p" if resolution > 100 else f"{resolution}",
                        'ext': f.get('ext', 'mp4').upper(),
                        'filesize': f.get('filesize', 0),
                        'format_note': f.get('format_note', ''),
                        'acodec': f.get('acodec', ''),
                        'vcodec': f.get('vcodec', '')
                    })
            
            # ترتيب الجودات
            formats.sort(key=lambda x: int(x['resolution'].replace('p', '')) if x['resolution'].replace('p', '').isdigit() else 0, reverse=True)
            
            return {
                'success': True,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration_string', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'formats': formats[:20],  # أفضل 20 جودة
                'platform': info.get('extractor', 'unknown')
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"خطأ في جلب المعلومات: {str(e)}")

@app.post("/api/download")
async def download(request: VideoRequest):
    try:
        filename = f"video_{uuid.uuid4().hex}"
        output = DOWNLOAD_DIR / filename
        
        # إعدادات التحميل
        ydl_opts = {
            'outtmpl': str(output),
            'quiet': True,
            'no_warnings': True,
        }
        
        if request.audio_only:            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            ydl_opts['format'] = f'bestvideo[height<={request.quality.replace("p", "")}]+bestaudio/best' if request.quality != 'best' else 'bestvideo+bestaudio/best'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([request.url])
        
        # البحث عن الملف المحمل
        files = list(DOWNLOAD_DIR.glob(f"{filename}*"))
        if files:
            return FileResponse(
                path=files[0],
                filename=files[0].name,
                media_type='application/octet-stream'
            )
        else:
            raise HTTPException(status_code=500, detail="لم يتم العثور على الملف")
            
    except Exception as e:
        print(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ في التحميل: {str(e)}")

@app.get("/api/supported-sites")
async def supported_sites():
    """إرجاع قائمة بجميع المواقع المدعومة"""
    return {
        "platforms": [
            "YouTube", "TikTok", "Instagram", "Snapchat", "Twitter/X", 
            "Facebook", "Reddit", "Pinterest", "LinkedIn", "Vimeo",
            "Dailymotion", "Twitch", "SoundCloud", "Spotify", "Apple Music",
            "و +1000 موقع آخر"
        ],
        "total": "1000+"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
