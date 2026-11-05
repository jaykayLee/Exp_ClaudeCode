from __future__ import annotations
from pathlib import Path
from io import BytesIO
from urllib.parse import urlsplit, urljoin
import hashlib
import http.client
import ipaddress
import json
import socket
import ssl
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from .validation import ALLOWED_RIGHTS, now_kst

MAX_BYTES=8*1024*1024
MAX_PIXELS=20_000_000
FORMATS={"JPEG":".jpg", "PNG":".png", "WEBP":".webp"}

class ImageError(ValueError):
    pass

def inspect_image(data: bytes, max_pixels: int=MAX_PIXELS) -> str:
    if not data or len(data)>MAX_BYTES:
        raise ImageError("IMAGE_SIZE_LIMIT")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error",Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as im:
                if im.format not in FORMATS or im.width*im.height>min(max_pixels,MAX_PIXELS):
                    raise ImageError("IMAGE_FORMAT_OR_PIXEL_LIMIT")
                kind=im.format
                im.verify()
        return kind
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning) as e:
        raise ImageError("IMAGE_INVALID") from e

def store_original(root: Path, data: bytes, rights: str, source: str="local_upload", credit: str="") -> str:
    if rights not in ALLOWED_RIGHTS:
        raise ImageError("IMAGE_RIGHTS_NOT_CONFIRMED")
    kind=inspect_image(data)
    digest=hashlib.sha256(data).hexdigest()
    path=root/"07_DATA/images/original"/(digest[:24]+FORMATS[kind])
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        path.write_bytes(data)
    # Keep evidence independently of the binary; the checkbox is a user declaration.
    evidence={"source":source,"rights_declared_by_user":rights,"credit":credit,
              "saved_at":now_kst().isoformat(),"sha256":digest,"legal_rights_verified_by_software":False}
    path.with_suffix(path.suffix+".json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")
    return path.relative_to(root).as_posix()

def resize_product_image(root: Path, relative_path: str, width: int=354, height: int=472, dpi: int=300, max_pixels: int=MAX_PIXELS) -> str:
    if type(width) is not int or type(height) is not int or not 80<=width<=2000 or not 80<=height<=2000:
        raise ImageError("IMAGE_DIMENSIONS_INVALID")
    path=(root/relative_path).resolve()
    allowed=[(root/"07_DATA/images").resolve(), (root/"07_DATA/samples").resolve()]
    if not any(path.is_relative_to(a) for a in allowed):
        raise ImageError("IMAGE_PATH_OUTSIDE_WORKSPACE")
    if not path.is_file() or path.stat().st_size>MAX_BYTES:
        raise ImageError("IMAGE_MISSING_OR_TOO_LARGE")
    data=path.read_bytes(); inspect_image(data,max_pixels)
    digest=hashlib.sha256(data+f"|{width}|{height}|{dpi}|white".encode()).hexdigest()[:24]
    dest=root/"07_DATA/images/resized"/(digest+".jpg")
    dest.parent.mkdir(parents=True,exist_ok=True)
    with Image.open(BytesIO(data)) as im:
        im=ImageOps.exif_transpose(im).convert("RGBA")
        im.thumbnail((width,height), Image.Resampling.LANCZOS)
        canvas=Image.new("RGB",(width,height),"white")
        canvas.paste(im,((width-im.width)//2,(height-im.height)//2),im)
        canvas.save(dest,"JPEG",quality=92,dpi=(dpi,dpi))
    return dest.relative_to(root).as_posix()

def validate_download_url(url: str, allowed_hosts: list[str]) -> tuple[str,str,str]:
    if not isinstance(url,str) or len(url)>2048 or any(ord(c)<32 for c in url):
        raise ImageError("IMAGE_URL_INVALID")
    p=urlsplit(url)
    host=(p.hostname or "").lower()
    if p.scheme!="https" or not host or p.username or p.password or p.port not in (None,443):
        raise ImageError("HTTPS_ONLY_NO_CREDENTIALS")
    if host not in {x.lower() for x in allowed_hosts}:
        raise ImageError("IMAGE_HOST_NOT_ALLOWED")
    try:
        answers=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
        addresses=list(dict.fromkeys(x[4][0] for x in answers))
    except OSError as e:
        raise ImageError("IMAGE_DNS_FAILED") from e
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ImageError("PRIVATE_NETWORK_BLOCKED")
    # Return a verified IP. HTTPS below connects to that exact IP (no second DNS lookup).
    return host,addresses[0],(p.path or "/")+("?"+p.query if p.query else "")

class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self,host: str,ip: str):
        super().__init__(host,443,timeout=10,context=ssl.create_default_context())
        self._ip=ip
    def connect(self):
        sock=socket.create_connection((self._ip,443),timeout=self.timeout)
        try:
            self.sock=self._context.wrap_socket(sock,server_hostname=self.host)
        except BaseException:
            sock.close(); raise

def download_image(root: Path,url: str,settings: dict,rights: str,credit: str="") -> str:
    if settings.get("download_enabled") is not True:
        raise ImageError("IMAGE_DOWNLOAD_DISABLED")
    if rights not in ALLOWED_RIGHTS:
        raise ImageError("IMAGE_RIGHTS_NOT_CONFIRMED")
    original=url
    for _ in range(3):
        host,ip,target=validate_download_url(url,settings.get("allowed_hosts",[]))
        conn=_PinnedHTTPSConnection(host,ip)
        try:
            conn.request("GET",target,headers={"User-Agent":"BlogWorkspace/1.0 (user-authorized image fetch)","Accept":"image/png,image/jpeg,image/webp"})
            response=conn.getresponse()
            if response.status in (301,302,303,307,308):
                location=response.getheader("Location")
                if not location: raise ImageError("IMAGE_REDIRECT_INVALID")
                url=urljoin(url,location)
                continue
            if response.status!=200:
                raise ImageError(f"IMAGE_HTTP_{response.status}")
            if response.getheader("Content-Type","").split(";")[0].lower() not in {"image/jpeg","image/png","image/webp"}:
                raise ImageError("IMAGE_CONTENT_TYPE_INVALID")
            cap=min(int(settings.get("max_bytes",MAX_BYTES)),MAX_BYTES)
            data=response.read(cap+1)
            if len(data)>cap: raise ImageError("IMAGE_SIZE_LIMIT")
            inspect_image(data,int(settings.get("max_pixels",MAX_PIXELS)))
            return store_original(root,data,rights,original,credit)
        finally:
            conn.close()
    raise ImageError("IMAGE_REDIRECT_LIMIT")
